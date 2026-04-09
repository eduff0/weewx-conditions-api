"""Unit tests for pure helper functions (no DB, no Flask)."""
from unittest.mock import patch, mock_open

from weewx_conditions_api.api_server import (
    safe_round,
    _is_valid_iana_tz,
    _resolve_timezone,
)


# ---------------------------------------------------------------------------
# safe_round
# ---------------------------------------------------------------------------

class TestSafeRound:
    def test_none_returns_none(self):
        assert safe_round(None, 1) is None

    def test_none_with_zero_digits(self):
        assert safe_round(None, 0) is None

    def test_rounds_to_one_decimal(self):
        assert safe_round(8.778, 1) == 8.8

    def test_rounds_to_two_decimals(self):
        assert safe_round(2.3456, 2) == 2.35

    def test_zero_value(self):
        assert safe_round(0.0, 1) == 0.0

    def test_negative_value(self):
        assert safe_round(-3.456, 1) == -3.5


# ---------------------------------------------------------------------------
# _is_valid_iana_tz
# ---------------------------------------------------------------------------

class TestIsValidIanaTz:
    def test_canonical_prefix(self):
        assert _is_valid_iana_tz('America/Chicago') is True

    def test_all_canonical_prefixes(self):
        zones = [
            'Africa/Nairobi', 'Antarctica/South_Pole', 'Asia/Tokyo',
            'Atlantic/Reykjavik', 'Australia/Sydney', 'Europe/London',
            'Indian/Maldives', 'Pacific/Auckland', 'Etc/UTC',
        ]
        for z in zones:
            assert _is_valid_iana_tz(z) is True, f"Expected valid: {z}"

    def test_bare_utc(self):
        assert _is_valid_iana_tz('UTC') is True

    def test_bare_gmt(self):
        assert _is_valid_iana_tz('GMT') is True

    def test_bare_gmt0(self):
        assert _is_valid_iana_tz('GMT0') is True

    def test_legacy_us(self):
        assert _is_valid_iana_tz('US/Central') is True

    def test_legacy_canada(self):
        assert _is_valid_iana_tz('Canada/Eastern') is True

    def test_legacy_mexico(self):
        assert _is_valid_iana_tz('Mexico/General') is True

    def test_rejects_abbreviation(self):
        assert _is_valid_iana_tz('CST') is False

    def test_rejects_cdt(self):
        assert _is_valid_iana_tz('CDT') is False

    def test_rejects_windows_name(self):
        assert _is_valid_iana_tz('Central Standard Time') is False

    def test_rejects_empty_string(self):
        assert _is_valid_iana_tz('') is False

    def test_rejects_none(self):
        assert _is_valid_iana_tz(None) is False


# ---------------------------------------------------------------------------
# _resolve_timezone
# ---------------------------------------------------------------------------

class TestResolveTimezone:
    def test_reads_from_conf_station_key(self, tmp_path):
        conf = tmp_path / 'weewx.conf'
        conf.write_text('[Station]\n    timezone = America/Chicago\n')
        with patch('weewx_conditions_api.api_server.CONF_PATH', str(conf)):
            tz = _resolve_timezone()
        assert tz == 'America/Chicago'

    def test_ignores_invalid_conf_tz_and_falls_through(self, tmp_path):
        # weewx.conf has an invalid (non-IANA) timezone string
        conf = tmp_path / 'weewx.conf'
        conf.write_text('[Station]\n    timezone = CST\n')
        etc_localtime_target = '/usr/share/zoneinfo/America/Denver'
        with patch('weewx_conditions_api.api_server.CONF_PATH', str(conf)), \
             patch('os.path.realpath', return_value=etc_localtime_target):
            tz = _resolve_timezone()
        assert tz == 'America/Denver'

    def test_falls_back_to_etc_localtime(self, tmp_path):
        conf = tmp_path / 'weewx.conf'
        conf.write_text('[Station]\n')  # no timezone key
        etc_localtime_target = '/usr/share/zoneinfo/America/New_York'
        with patch('weewx_conditions_api.api_server.CONF_PATH', str(conf)), \
             patch('os.path.realpath', return_value=etc_localtime_target):
            tz = _resolve_timezone()
        assert tz == 'America/New_York'

    def test_falls_back_to_etc_timezone_file(self, tmp_path):
        conf = tmp_path / 'weewx.conf'
        conf.write_text('[Station]\n')
        # realpath returns path unchanged (not under a zoneinfo prefix)
        with patch('weewx_conditions_api.api_server.CONF_PATH', str(conf)), \
             patch('os.path.realpath', return_value='/etc/localtime'), \
             patch('builtins.open', mock_open(read_data='Europe/Berlin')):
            tz = _resolve_timezone()
        assert tz == 'Europe/Berlin'

    def test_last_resort_returns_utc(self, tmp_path):
        conf = tmp_path / 'weewx.conf'
        conf.write_text('[Station]\n')
        with patch('weewx_conditions_api.api_server.CONF_PATH', str(conf)), \
             patch('os.path.realpath', return_value='/etc/localtime'), \
             patch('builtins.open', side_effect=OSError), \
             patch('weewx_conditions_api.api_server.datetime') as mock_dt:
            mock_dt.now.return_value.astimezone.return_value.tzname.return_value = 'CST'
            tz = _resolve_timezone()
        assert tz == 'UTC'
