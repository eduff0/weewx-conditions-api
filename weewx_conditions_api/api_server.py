import threading
import sqlite3
import time
import os
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

# Endpoint with payload aligning with MagicMirror's Weather Object
@app.route('/api/mmwo')
def mmwo():
    conn = None
    try:
        # Load configuration
        conf = ConfigObj(CONF_PATH)
        lat = float(conf['Station']['latitude'])
        lon = float(conf['Station']['longitude'])

        # Derive the database path from the configuration:
        # - SQLITE_ROOT is defined in [DatabaseTypes] -> [[SQLite]]
        # - database_name is defined in [Databases] -> [[archive_sqlite]]
        sqlite_root = conf["DatabaseTypes"]["SQLite"]["SQLITE_ROOT"]
        db_name = conf["Databases"]["archive_sqlite"]["database_name"]
        db_path = os.path.join(sqlite_root, db_name)
        
        # Connect to DB with named columns
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM archive ORDER BY dateTime DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'No data found'}), HTTPStatus.NOT_FOUND.value

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

    finally:
        if conn:
            conn.close()

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
