"""
Shared pytest fixtures for weewx-conditions-api unit tests.

Strategy
--------
- fixture.db  : schema-only SQLite DB generated from a real WeeWX install
                (committed to repo, never written to during tests)
- Each test gets a fresh copy in tmp_path with one known row inserted
- CONF_PATH is patched to a temp weewx.conf pointing at that copy
- Flask test client is returned to callers

Known seed row  (usUnits=1, US customary)
------------------------------------------
outTemp    = 47.84 °F  → 8.8 °C
windSpeed  = 5.24 mph  → 2.34 m/s
barometer  = 29.92 inHg → 1013.2 hPa
outHumidity= 57.0 %
windDir    = 316.0 °
dateTime   = 1744700000 (fixed Unix timestamp)
"""
import os
import shutil
import sqlite3
import textwrap

import pytest

from weewx_conditions_api import api_server

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
FIXTURE_DB = os.path.join(FIXTURES_DIR, 'fixture.db')

# US-customary seed row — values chosen to match README metric examples
SEED_ROW = {
    'dateTime':    1744700000,
    'usUnits':     1,
    'interval':    5,
    'barometer':   29.92,
    'outTemp':     47.84,
    'outHumidity': 57.0,
    'windSpeed':   5.24,
    'windDir':     316.0,
}


def _write_conf(tmp_path):
    """Write a minimal weewx.conf pointing at tmp_path/fixture.db."""
    conf_text = textwrap.dedent(f"""\
        [Station]
            latitude = 44.9
            longitude = -93.2

        [DatabaseTypes]
            [[SQLite]]
                SQLITE_ROOT = {str(tmp_path)}

        [Databases]
            [[archive_sqlite]]
                database_name = fixture.db
    """)
    conf_path = tmp_path / 'weewx.conf'
    conf_path.write_text(conf_text)
    return str(conf_path)


def _make_db(tmp_path, insert_row=True):
    """Copy fixture.db to tmp_path and optionally insert the seed row."""
    db_path = tmp_path / 'fixture.db'
    shutil.copy(FIXTURE_DB, db_path)
    if insert_row:
        conn = sqlite3.connect(str(db_path))
        cols = ', '.join(f'"{k}"' for k in SEED_ROW)
        placeholders = ', '.join('?' for _ in SEED_ROW)
        conn.execute(
            f'INSERT INTO archive ({cols}) VALUES ({placeholders})',
            list(SEED_ROW.values())
        )
        conn.commit()
        conn.close()
    return db_path


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with one known archive row."""
    _make_db(tmp_path)
    conf_path = _write_conf(tmp_path)
    monkeypatch.setattr(api_server, 'CONF_PATH', conf_path)
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as c:
        yield c


@pytest.fixture
def empty_client(tmp_path, monkeypatch):
    """Flask test client with an empty archive table (no rows)."""
    _make_db(tmp_path, insert_row=False)
    conf_path = _write_conf(tmp_path)
    monkeypatch.setattr(api_server, 'CONF_PATH', conf_path)
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as c:
        yield c


@pytest.fixture
def bad_conf_client(monkeypatch):
    """Flask test client pointing at a nonexistent weewx.conf."""
    monkeypatch.setattr(api_server, 'CONF_PATH', '/nonexistent/weewx.conf')
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as c:
        yield c


@pytest.fixture
def null_sensor_client(tmp_path, monkeypatch):
    """Flask test client with outTemp and windSpeed set to NULL."""
    _make_db(tmp_path, insert_row=False)
    db_path = tmp_path / 'fixture.db'
    conn = sqlite3.connect(str(db_path))
    null_row = dict(SEED_ROW)
    null_row['outTemp'] = None
    null_row['windSpeed'] = None
    cols = ', '.join(f'"{k}"' for k in null_row)
    placeholders = ', '.join('?' for _ in null_row)
    conn.execute(
        f'INSERT INTO archive ({cols}) VALUES ({placeholders})',
        list(null_row.values())
    )
    conn.commit()
    conn.close()
    conf_path = _write_conf(tmp_path)
    monkeypatch.setattr(api_server, 'CONF_PATH', conf_path)
    api_server.app.config['TESTING'] = True
    with api_server.app.test_client() as c:
        yield c
