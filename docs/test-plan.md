# Test Plan: weewx-conditions-api

## Overview

Testing is split into two layers that can run independently:

| Layer        | Requires WeeWX?      | Speed                 | When to run            |
|--------------|----------------------|-----------------------|------------------------|
| Unit / API   | No                   | Fast (~seconds)       | Every change, CI       |
| Integration  | Yes (WSL simulator)  | Slow (~minutes setup) | Before merging to main |

The layers are separated so unit tests can run anywhere — Windows, WSL, or CI — without any services.

---

## Layer 1 — Unit and API Tests

### How it works

The Flask test client is used to call endpoints in-process. A fixture SQLite database (committed to the repo) with one known archive row substitutes for the production WeeWX database. The `WEEWX_CONF_PATH` environment variable points the API at a test config file that references the fixture database, so no prod paths are touched.

### Dependencies

```bash
pip install pytest pytest-flask
```

No additional dependencies. `ephem`, `weewx`, and `configobj` are already required by the API itself.

### File layout

```text
tests/
  fixtures/
    weewx.conf        # minimal config pointing at fixture.db
    fixture.db        # SQLite archive with one known row (committed to repo)
  unit/
    test_helpers.py   # safe_round, _is_valid_iana_tz, _resolve_timezone
    test_mmwo.py      # /api/mmwo endpoint
    test_owm.py       # /api/owm endpoint
  conftest.py         # shared fixtures: app client, env var setup
```

### Fixture database

WeeWX creates and initializes the SQLite database (including the full `archive` schema) automatically on first run — there is no manual schema creation step. The fixture database is sourced from a real WeeWX-generated file.

**One-time fixture creation (done in WSL, not repeated per test run):**

1. Run the WeeWX simulator long enough for it to initialize the database (it creates the DB on startup, before writing any rows):

   ```bash
   weewxd ~/weewx-test-data/weewx.conf &
   sleep 5 && kill %1
   ```

2. Copy the empty (schema-only) database to the repo:

   ```bash
   cp ~/weewx-test-data/archive/weewx.sdb \
      /mnt/c/Users/eric/GitHub/weewx-conditions-api/tests/fixtures/fixture.db
   ```

3. Commit `tests/fixtures/fixture.db` — it contains only the schema, no rows.

**Why source it from WeeWX:** The real archive schema has ~100 columns. Using it ensures the fixture matches production exactly and avoids schema drift from a hand-maintained `CREATE TABLE`.

**Seeding known rows at test time:** `conftest.py` copies `fixture.db` to a `tmp_path` before each test and inserts one row of US-customary data chosen so converted metric values match the README examples exactly:

```python
# usUnits=1 (US customary): °F, mph, inHg
# Converts to: temp=8.8°C, wind=2.34 m/s, pressure=1013.2 hPa
INSERT_ROW = (1744700000, 1, 5, 29.92, 47.84, 57.0, 5.24, 316.0)
# columns:     dateTime   usU int  baro   temp   hum   wind  dir
```

Using `tmp_path` means tests never write to the committed `.db` file, so it stays schema-only and repeatable.

The fixture `weewx.conf` only needs the sections `_get_weather_data()` reads:

```ini
[Station]
    latitude = 44.9
    longitude = -93.2

[DatabaseTypes]
    [[SQLite]]
        SQLITE_ROOT = %(here)s

[Databases]
    [[archive_sqlite]]
        database_name = fixture.db
```

`conftest.py` sets `WEEWX_CONF_PATH` to a rewritten copy of this file with `SQLITE_ROOT` pointing at the `tmp_path` directory containing the seeded database.

### Test cases

#### `test_helpers.py`

| Test | What it checks |
|------|----------------|
| `test_safe_round_none` | `safe_round(None, 1)` returns `None` |
| `test_safe_round_value` | `safe_round(8.778, 1)` returns `8.8` |
| `test_is_valid_iana_canonical` | `America/Chicago` → valid |
| `test_is_valid_iana_bare` | `UTC`, `GMT`, `GMT0` → valid |
| `test_is_valid_iana_legacy` | `US/Central` → valid |
| `test_is_valid_iana_rejects_abbrev` | `CST`, `CDT` → invalid |
| `test_is_valid_iana_rejects_empty` | `""`, `None` → invalid |
| `test_resolve_tz_from_conf` | env var config with `timezone = America/Chicago` → returns that value |
| `test_resolve_tz_fallback_utc` | all sources mocked to fail → returns `"UTC"` |

#### `test_mmwo.py`

| Test | Expected result |
|------|-----------------|
| `test_mmwo_ok` | 200; `temperature` ≈ 8.8, `humidity` = 57.0, `windSpeed` ≈ 2.34, `windDirection` = 316.0, `pressure` ≈ 1013.2 |
| `test_mmwo_timestamp_format` | `timestamp` ends with `Z`, is valid ISO-8601 |
| `test_mmwo_sunrise_sunset_present` | both keys present, values are ISO datetime strings |
| `test_mmwo_empty_db` | seed with empty archive → 500 |
| `test_mmwo_bad_conf_path` | `WEEWX_CONF_PATH` set to nonexistent file → 500 |

#### `test_owm.py`

| Test | Expected result |
|------|-----------------|
| `test_owm_ok` | 200; top-level keys: `lat`, `lon`, `timezone`, `timezone_offset`, `current` |
| `test_owm_temp` | `current.temp` ≈ 8.8 |
| `test_owm_pressure` | `current.pressure` ≈ 1013.2 |
| `test_owm_humidity` | `current.humidity` = 57.0 |
| `test_owm_wind_speed` | `current.wind_speed` ≈ 2.34 |
| `test_owm_wind_deg` | `current.wind_deg` = 316.0 |
| `test_owm_dt_is_int` | `current.dt` == 1744700000 (exact) |
| `test_owm_sunrise_sunset_are_ints` | both are integers (Unix timestamps) |
| `test_owm_typed_empties` | `rain == {}`, `snow == {}`, `weather == []` |
| `test_owm_null_fields` | `feels_like`, `dew_point`, `uvi`, `clouds`, `visibility`, `wind_gust` are all `null` |
| `test_owm_timezone_offset_is_int` | `timezone_offset` is an integer |
| `test_owm_empty_db` | 404 with `{"error": "No archive data found"}` |
| `test_owm_bad_conf_path` | `WEEWX_CONF_PATH` set to nonexistent file → 503 |
| `test_owm_null_temp` | row with `outTemp = NULL` → `current.temp` is `null` (not an error) |
| `test_owm_null_wind` | row with `windSpeed = NULL` → `current.wind_speed` is `null` |

### Running unit tests

```bash
# From repo root, with the venv active:
pytest tests/unit/ -v
```

---

## Layer 2 — Integration Tests (WeeWX Simulator)

### Why WSL, not Windows

WeeWX is Linux-native. The API's production paths (`/etc/localtime`, `/etc/timezone`, `/home/sysadmin/...`) are Linux paths. Running in WSL keeps the test environment consistent with prod and avoids unsupported WeeWX-on-Windows workarounds.

### One-time WSL setup

These steps install WeeWX with the simulator driver into a dedicated virtual environment in WSL. They only need to be done once.

**1. Install Ubuntu in WSL** (if not already):

```powershell
# In PowerShell (Windows)
wsl --install -d Ubuntu
```

**2. Inside WSL — install system dependencies:**

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv python3-dev
```

**3. Create a virtual environment for WeeWX:**

```bash
python3 -m venv ~/weewx-env
source ~/weewx-env/bin/activate
pip install weewx
```

**4. Create a WeeWX data directory and config:**

```bash
mkdir -p ~/weewx-test-data
weectl station create ~/weewx-test-data --driver=weewx.drivers.simulator --no-prompt
```

**5. Edit `~/weewx-test-data/weewx.conf`** — set these keys:

```ini
[Station]
    location = Test Station
    latitude = 44.9
    longitude = -93.2
    altitude = 300, foot
    station_type = Simulator

[Simulator]
    driver = weewx.drivers.simulator
    mode = generator        # emits records as fast as possible; designed for testing

[StdArchive]
    archive_interval = 5    # seconds; default is 300 — set low so tests don't wait 5 minutes

[DatabaseTypes]
    [[SQLite]]
        SQLITE_ROOT = /home/<your-wsl-username>/weewx-test-data/archive

[Databases]
    [[archive_sqlite]]
        database_name = weewx.sdb
```

Replace `<your-wsl-username>` with your WSL username (`whoami`). Note: `SQLITE_ROOT` must be an **absolute path** — a relative path will cause "unable to open database file" errors.

**Why `mode = generator`:** The WeeWX simulator has two modes. `simulator` sleeps between loop packets (real-time pacing). `generator` emits packets as fast as possible — the simulator source code describes it as "useful for testing". Combined with a short `archive_interval`, the database has rows within seconds of startup.

**6. Install the API package into the same venv:**

```bash
pip install git+https://github.com/eduff0/weewx-conditions-api.git
# Or, for local development:
pip install -e /mnt/c/Users/eric/GitHub/weewx-conditions-api
```

### Running the simulator and API

Each integration test session:

```bash
# Terminal 1 — start WeeWX simulator (generator mode writes rows within seconds)
source ~/weewx-env/bin/activate
weewxd ~/weewx-test-data/weewx.conf

# Terminal 2 — start the API pointing at the test config
source ~/weewx-env/bin/activate
WEEWX_CONF_PATH=~/weewx-test-data/weewx.conf python -m weewx_conditions_api.api_server
```

Wait ~10 seconds for WeeWX to write the first archive record, then run the integration tests:

```bash
# Terminal 3
pytest tests/integration/ -v
```

### Integration test cases

#### `test_live.py`

| Test | What it checks |
|------|----------------|
| `test_mmwo_live_200` | `GET /api/mmwo` returns 200 |
| `test_mmwo_live_schema` | all expected keys present, no unexpected keys |
| `test_mmwo_live_types` | `temperature`, `humidity`, `windSpeed`, `windDirection`, `pressure` are floats or null; `timestamp` is a string ending in `Z`; `sunrise`/`sunset` are strings |
| `test_owm_live_200` | `GET /api/owm` returns 200 |
| `test_owm_live_schema` | top-level keys present; `current` has all OWM fields |
| `test_owm_live_typed_empties` | `rain == {}`, `snow == {}`, `weather == []` |
| `test_owm_live_dt_recent` | `current.dt` is within the last 5 minutes of test run time |
| `test_owm_live_sunrise_before_sunset` | if not null, `sunrise < sunset` |

---

## CI considerations

Layer 1 (unit tests) is suitable for GitHub Actions with no special setup — just a standard Python matrix job. Layer 2 requires a Linux runner with WeeWX installed; it is not recommended for CI until a Docker-based WeeWX image is available.

Suggested GitHub Actions trigger for Layer 1: on every push and pull request to `main` and `feature/*`.
