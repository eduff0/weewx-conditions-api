import calendar
import threading
import sqlite3
import time
import os
import logging
from datetime import datetime
from http import HTTPStatus

from flask import Flask, jsonify
from configobj import ConfigObj
import weewx.units as wu
from weeutil.weeutil import to_int
import ephem

# Enable CORS using flask_cors.
from flask_cors import CORS

CONF_PATH = '/home/sysadmin/weewx-data/weewx.conf'
API_PORT = 5000

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # This enables CORS for all routes.

# Additionally, add headers manually (this is optional)
@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    # Only allow GET and OPTIONS methods for this API.
    response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
    return response


# ---------------------------------------------------------------------------
# Timezone resolution (done once at module load)
# ---------------------------------------------------------------------------

_VALID_TZ_PREFIXES = (
    'Africa/', 'America/', 'Antarctica/', 'Asia/', 'Atlantic/',
    'Australia/', 'Europe/', 'Indian/', 'Pacific/', 'Etc/',
    'US/', 'Canada/', 'Mexico/',
)
_VALID_TZ_BARE = {'UTC', 'GMT', 'GMT0'}


def _is_valid_iana_tz(tz):
    if not tz:
        return False
    if tz in _VALID_TZ_BARE:
        return True
    return any(tz.startswith(p) for p in _VALID_TZ_PREFIXES)


def _resolve_timezone():
    # Step 1: weewx.conf [Station] timezone (highest priority)
    try:
        conf = ConfigObj(CONF_PATH)
        tz = conf.get('Station', {}).get('timezone')
        if tz:
            if _is_valid_iana_tz(tz):
                return tz
        else:
            logger.info(
                "[Station] timezone not set in weewx.conf; "
                "add 'timezone = America/Chicago' (or your zone) to enable explicit override"
            )
    except Exception:
        pass

    # Step 2: /etc/localtime symlink
    try:
        real = os.path.realpath('/etc/localtime')
        tz = None
        for prefix in (
            '/usr/share/zoneinfo/',
            '/usr/lib/zoneinfo/',
            '/usr/share/zoneinfo/posix/',
            '/usr/share/lib/zoneinfo/',
        ):
            if real.startswith(prefix):
                tz = real[len(prefix):]
                break
        if tz:
            for sub in ('posix/', 'right/'):
                if tz.startswith(sub):
                    tz = tz[len(sub):]
                    break
            if _is_valid_iana_tz(tz):
                return tz
    except Exception:
        pass

    # Step 3+: warn once, then try remaining sources
    logger.warning(
        "Could not determine IANA timezone from weewx.conf or /etc/localtime; "
        "falling back to /etc/timezone"
    )

    # Step 3: /etc/timezone
    try:
        with open('/etc/timezone') as f:
            tz = f.read().strip()
        if _is_valid_iana_tz(tz):
            return tz
    except Exception:
        pass

    # Step 4: tzname() — may return abbreviation, not IANA; validated below
    try:
        tz = datetime.now().astimezone().tzname()
        if _is_valid_iana_tz(tz):
            return tz
    except Exception:
        pass

    # Last resort
    logger.error("Could not determine IANA timezone from any source; defaulting to UTC")
    return 'UTC'


LOCAL_TIMEZONE = _resolve_timezone()


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _get_weather_data():
    """Load config and query the latest archive row.

    Returns {'row': dict, 'lat': float, 'lon': float}.
    Raises RuntimeError on config/DB failure, ValueError if no archive rows exist.
    """
    conn = None
    try:
        try:
            conf = ConfigObj(CONF_PATH)
        except Exception as e:
            raise RuntimeError("Failed to load weewx configuration") from e

        try:
            lat = float(conf['Station']['latitude'])
            lon = float(conf['Station']['longitude'])
        except (KeyError, ValueError, TypeError) as e:
            logger.error("Station location config error: %s", e)
            raise RuntimeError("Station location not configured")

        sqlite_root = conf["DatabaseTypes"]["SQLite"]["SQLITE_ROOT"]
        db_name = conf["Databases"]["archive_sqlite"]["database_name"]
        db_path = os.path.join(sqlite_root, db_name)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM archive ORDER BY dateTime DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            raise ValueError("No archive data found")

        # Convert to plain dict before closing the connection
        return {'row': dict(row), 'lat': lat, 'lon': lon}

    except (RuntimeError, ValueError):
        raise
    except Exception as e:
        raise RuntimeError(str(e)) from e
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

# Endpoint with payload aligning with MagicMirror's Weather Object
@app.route('/api/mmwo')
def mmwo():
    try:
        data = _get_weather_data()
        row = data['row']
        lat = data['lat']
        lon = data['lon']

        # Extract values
        usUnits = row['usUnits']
        outTemp = row['outTemp']
        outHumidity = row['outHumidity']
        windSpeed = row['windSpeed']
        windDir = row['windDir']
        barometer = row['barometer']

        # Unit conversion - MagicMirror expects metric units
        temp_c = wu.convert((outTemp, 'degree_F', usUnits), 'degree_C')[0] if outTemp is not None else None
        wind_mps = wu.convert((windSpeed, 'mile_per_hour', usUnits), 'meter_per_second')[0] if windSpeed is not None else None
        press_hpa = wu.convert((barometer, 'inHg', usUnits), 'hPa')[0] if barometer is not None else None

        # Format timestamp
        archive_epoch = to_int(row['dateTime'])
        timestamp = datetime.utcfromtimestamp(archive_epoch).isoformat() + 'Z'

        # Calculate sunrise/sunset using ephem
        obs = ephem.Observer()
        obs.lat = str(lat)
        obs.lon = str(lon)
        obs.date = datetime.utcnow()

        sunrise = ephem.localtime(obs.next_rising(ephem.Sun())).isoformat()
        sunset = ephem.localtime(obs.next_setting(ephem.Sun())).isoformat()

        payload = {
            'timestamp': timestamp,
            'temperature': safe_round(temp_c, 1),
            'humidity': safe_round(outHumidity, 1),
            'windSpeed': safe_round(wind_mps, 2),
            'windDirection': safe_round(windDir, 1),
            'pressure': safe_round(press_hpa, 1),
            'sunrise': sunrise,
            'sunset': sunset
        }

        return jsonify(payload)

    except Exception as e:
        return jsonify({'error': str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR.value


@app.route('/api/owm')
def owm():
    try:
        data = _get_weather_data()
        row = data['row']
        lat = data['lat']
        lon = data['lon']

        # Extract values
        usUnits = row['usUnits']
        outTemp = row['outTemp']
        outHumidity = row['outHumidity']
        windSpeed = row['windSpeed']
        windDir = row['windDir']
        barometer = row['barometer']

        # Unit conversion to OWM metric units
        temp_c = wu.convert((outTemp, 'degree_F', usUnits), 'degree_C')[0] if outTemp is not None else None
        wind_mps = wu.convert((windSpeed, 'mile_per_hour', usUnits), 'meter_per_second')[0] if windSpeed is not None else None
        press_hpa = wu.convert((barometer, 'inHg', usUnits), 'hPa')[0] if barometer is not None else None

        dt = int(row['dateTime'])
        timezone_offset = int(datetime.now().astimezone().utcoffset().total_seconds())

        # Calculate sunrise/sunset using ephem (UTC Unix timestamps)
        obs = ephem.Observer()
        obs.lat = str(lat)
        obs.lon = str(lon)
        obs.date = datetime.utcnow()

        try:
            sr = obs.next_rising(ephem.Sun())
            ss = obs.next_setting(ephem.Sun())
            sr_t = sr.tuple()
            ss_t = ss.tuple()
            sunrise = calendar.timegm((
                int(sr_t[0]), int(sr_t[1]), int(sr_t[2]),
                int(sr_t[3]), int(sr_t[4]), int(sr_t[5]),
                0, 0, -1
            ))
            sunset = calendar.timegm((
                int(ss_t[0]), int(ss_t[1]), int(ss_t[2]),
                int(ss_t[3]), int(ss_t[4]), int(ss_t[5]),
                0, 0, -1
            ))
        except (ephem.AlwaysUpError, ephem.NeverUpError):
            sunrise = None
            sunset = None

        payload = {
            'lat': lat,
            'lon': lon,
            'timezone': LOCAL_TIMEZONE,
            'timezone_offset': timezone_offset,
            'current': {
                'dt': dt,
                'sunrise': sunrise,
                'sunset': sunset,
                'temp': safe_round(temp_c, 1),
                'feels_like': None,
                'pressure': safe_round(press_hpa, 1),
                'humidity': safe_round(outHumidity, 1),
                'dew_point': None,
                'uvi': None,
                'clouds': None,
                'visibility': None,
                'wind_speed': safe_round(wind_mps, 2),
                'wind_gust': None,
                'wind_deg': safe_round(windDir, 1),
                'rain': {},
                'snow': {},
                'weather': [],
            }
        }

        return jsonify(payload)

    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def safe_round(value, digits=1):
    return round(value, digits) if value is not None else None

def start_api():
    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)
    )
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    start_api()
    while True:
        time.sleep(60)
