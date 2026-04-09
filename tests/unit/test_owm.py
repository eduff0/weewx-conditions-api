"""Unit tests for GET /api/owm."""


class TestOwmOk:
    def test_returns_200(self, client):
        rv = client.get('/api/owm')
        assert rv.status_code == 200

    def test_top_level_keys_present(self, client):
        data = client.get('/api/owm').get_json()
        assert {'lat', 'lon', 'timezone', 'timezone_offset', 'current'} == set(data.keys())

    def test_lat_lon(self, client):
        data = client.get('/api/owm').get_json()
        assert data['lat'] == 44.9
        assert data['lon'] == -93.2

    def test_timezone_is_string(self, client):
        data = client.get('/api/owm').get_json()
        assert isinstance(data['timezone'], str)
        assert len(data['timezone']) > 0

    def test_timezone_offset_is_int(self, client):
        data = client.get('/api/owm').get_json()
        assert isinstance(data['timezone_offset'], int)


class TestOwmCurrent:
    def test_dt_matches_seed(self, client):
        data = client.get('/api/owm').get_json()
        assert data['current']['dt'] == 1744700000

    def test_dt_is_int(self, client):
        data = client.get('/api/owm').get_json()
        assert isinstance(data['current']['dt'], int)

    def test_temp_converted_to_celsius(self, client):
        data = client.get('/api/owm').get_json()
        # 47.84 °F → 8.8 °C (±0.1)
        assert data['current']['temp'] is not None
        assert abs(data['current']['temp'] - 8.8) < 0.1

    def test_pressure_converted_to_hpa(self, client):
        data = client.get('/api/owm').get_json()
        # 29.92 inHg → 1013.2 hPa (±1.0)
        assert data['current']['pressure'] is not None
        assert abs(data['current']['pressure'] - 1013.2) < 1.0

    def test_humidity(self, client):
        data = client.get('/api/owm').get_json()
        assert abs(data['current']['humidity'] - 57.0) < 0.1

    def test_wind_speed_converted_to_mps(self, client):
        data = client.get('/api/owm').get_json()
        # 5.24 mph → 2.34 m/s (±0.05)
        assert data['current']['wind_speed'] is not None
        assert abs(data['current']['wind_speed'] - 2.34) < 0.05

    def test_wind_deg(self, client):
        data = client.get('/api/owm').get_json()
        assert abs(data['current']['wind_deg'] - 316.0) < 0.1

    def test_sunrise_is_int_or_null(self, client):
        data = client.get('/api/owm').get_json()
        sr = data['current']['sunrise']
        assert sr is None or isinstance(sr, int)

    def test_sunset_is_int_or_null(self, client):
        data = client.get('/api/owm').get_json()
        ss = data['current']['sunset']
        assert ss is None or isinstance(ss, int)

    def test_sunrise_before_sunset(self, client):
        data = client.get('/api/owm').get_json()
        sr = data['current']['sunrise']
        ss = data['current']['sunset']
        if sr is not None and ss is not None:
            assert sr < ss

    def test_typed_empty_rain(self, client):
        data = client.get('/api/owm').get_json()
        assert data['current']['rain'] == {}

    def test_typed_empty_snow(self, client):
        data = client.get('/api/owm').get_json()
        assert data['current']['snow'] == {}

    def test_typed_empty_weather(self, client):
        data = client.get('/api/owm').get_json()
        assert data['current']['weather'] == []

    def test_null_fields(self, client):
        data = client.get('/api/owm').get_json()
        cur = data['current']
        for field in ('feels_like', 'dew_point', 'uvi', 'clouds', 'visibility', 'wind_gust'):
            assert cur[field] is None, f"Expected {field} to be null"

    def test_all_current_keys_present(self, client):
        data = client.get('/api/owm').get_json()
        expected = {
            'dt', 'sunrise', 'sunset', 'temp', 'feels_like', 'pressure',
            'humidity', 'dew_point', 'uvi', 'clouds', 'visibility',
            'wind_speed', 'wind_gust', 'wind_deg', 'rain', 'snow', 'weather',
        }
        assert expected == set(data['current'].keys())


class TestOwmNullSensors:
    def test_null_temp_returns_null_not_error(self, null_sensor_client):
        rv = null_sensor_client.get('/api/owm')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['current']['temp'] is None

    def test_null_wind_returns_null_not_error(self, null_sensor_client):
        rv = null_sensor_client.get('/api/owm')
        assert rv.status_code == 200
        data = rv.get_json()
        assert data['current']['wind_speed'] is None


class TestOwmErrors:
    def test_empty_archive_returns_404(self, empty_client):
        rv = empty_client.get('/api/owm')
        assert rv.status_code == 404

    def test_empty_archive_error_body(self, empty_client):
        data = empty_client.get('/api/owm').get_json()
        assert 'error' in data
        assert 'archive' in data['error'].lower()

    def test_bad_conf_returns_503(self, bad_conf_client):
        rv = bad_conf_client.get('/api/owm')
        assert rv.status_code == 503

    def test_bad_conf_error_body(self, bad_conf_client):
        data = bad_conf_client.get('/api/owm').get_json()
        assert 'error' in data
