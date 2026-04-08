"""Unit tests for GET /api/mmwo."""


class TestMmwoOk:
    def test_returns_200(self, client):
        rv = client.get('/api/mmwo')
        assert rv.status_code == 200

    def test_temperature_converted_to_celsius(self, client):
        data = client.get('/api/mmwo').get_json()
        # 47.84 °F → 8.8 °C (±0.1)
        assert data['temperature'] is not None
        assert abs(data['temperature'] - 8.8) < 0.1

    def test_humidity_present(self, client):
        data = client.get('/api/mmwo').get_json()
        assert abs(data['humidity'] - 57.0) < 0.1

    def test_wind_speed_converted_to_mps(self, client):
        data = client.get('/api/mmwo').get_json()
        # 5.24 mph → 2.34 m/s (±0.05)
        assert data['windSpeed'] is not None
        assert abs(data['windSpeed'] - 2.34) < 0.05

    def test_wind_direction_present(self, client):
        data = client.get('/api/mmwo').get_json()
        assert abs(data['windDirection'] - 316.0) < 0.1

    def test_pressure_converted_to_hpa(self, client):
        data = client.get('/api/mmwo').get_json()
        # 29.92 inHg → 1013.2 hPa (±1.0)
        assert data['pressure'] is not None
        assert abs(data['pressure'] - 1013.2) < 1.0

    def test_timestamp_is_utc_iso8601(self, client):
        data = client.get('/api/mmwo').get_json()
        ts = data['timestamp']
        assert isinstance(ts, str)
        assert ts.endswith('Z')
        # Should be parseable
        from datetime import datetime
        datetime.fromisoformat(ts.rstrip('Z'))

    def test_timestamp_matches_seed_datetime(self, client):
        data = client.get('/api/mmwo').get_json()
        # seed dateTime = 1744700000 → 2025-04-15T00:13:20Z
        assert '2025-04-15' in data['timestamp']

    def test_sunrise_and_sunset_present(self, client):
        data = client.get('/api/mmwo').get_json()
        assert 'sunrise' in data
        assert 'sunset' in data

    def test_sunrise_sunset_are_strings(self, client):
        data = client.get('/api/mmwo').get_json()
        assert isinstance(data['sunrise'], str)
        assert isinstance(data['sunset'], str)

    def test_no_unexpected_keys(self, client):
        data = client.get('/api/mmwo').get_json()
        expected = {'timestamp', 'temperature', 'humidity', 'windSpeed',
                    'windDirection', 'pressure', 'sunrise', 'sunset'}
        assert set(data.keys()) == expected


class TestMmwoErrors:
    def test_empty_archive_returns_500(self, empty_client):
        rv = empty_client.get('/api/mmwo')
        assert rv.status_code == 500

    def test_bad_conf_returns_500(self, bad_conf_client):
        rv = bad_conf_client.get('/api/mmwo')
        assert rv.status_code == 500

    def test_error_response_has_error_key(self, empty_client):
        data = empty_client.get('/api/mmwo').get_json()
        assert 'error' in data
