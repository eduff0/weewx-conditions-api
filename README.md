# weewx-conditions-api

Creates a REST API, using Flask, to expose current weather conditions from the SQLite database used by [WeeWX](http://weewx.com/), with initial focus on [MagicMirror](https://magicmirror.builders/) clients (see instructions for MagicMirror below).

## API Endpoints

| Endpoint          | Description                                                          |
|-------------------|----------------------------------------------------------------------|
| `GET /api/mmwo`   | Current conditions in MagicMirror WeatherObject format               |
| `GET /api/owm`    | Current conditions in OpenWeatherMap One Call 3.0 `current` format   |

## Testing the API

Once the service is running, verify it with curl:

```bash
curl http://192.168.1.111:5000/api/mmwo
curl http://192.168.1.111:5000/api/owm
```

Or open the URLs in a browser (replace the IP with your WeeWX server's address).

## Example JSON: `/api/mmwo`

```json
{
  "humidity": 57.1,
  "pressure": 1013.9,
  "sunrise": "2024-04-16T06:28:18.496292",
  "sunset": "2024-04-16T20:02:44.294692",
  "temperature": 8.8,
  "timestamp": "2025-04-15T00:12:00Z",
  "windDirection": 316.2,
  "windSpeed": 2.34
}
```

## Example JSON: `/api/owm`

```json
{
  "lat": 44.9,
  "lon": -93.2,
  "timezone": "America/Chicago",
  "timezone_offset": -18000,
  "current": {
    "dt": 1744700000,
    "sunrise": 1744701234,
    "sunset": 1744745678,
    "temp": 8.8,
    "feels_like": null,
    "pressure": 1013.9,
    "humidity": 57.1,
    "dew_point": null,
    "uvi": null,
    "clouds": null,
    "visibility": null,
    "wind_speed": 2.34,
    "wind_gust": null,
    "wind_deg": 316.2,
    "rain": {},
    "snow": {},
    "weather": []
  }
}
```

**Notes on `/api/owm`:**

- `sunrise` and `sunset` return `null` for polar locations where the sun does not rise or set (ephem `AlwaysUpError`/`NeverUpError`). This is documented behavior, not an error.
- `rain`, `snow`, and `weather` are always present but empty (`{}`, `{}`, `[]`). WeeWX does not currently provide precipitation accumulation or sky-condition data in the format these fields require.
- Fields with no WeeWX equivalent (`feels_like`, `dew_point`, `uvi`, `clouds`, `visibility`, `wind_gust`) always return `null`.

### Optional: explicit timezone configuration

By default the API resolves the IANA timezone string from `/etc/localtime`. If your server's timezone symlink is non-standard, you can override it by adding a `timezone` key to the `[Station]` section of `weewx.conf`:

```ini
[Station]
    ...
    timezone = America/Chicago
```

This key is ignored by WeeWX itself and is read only by this API. It is the highest-priority source for the `timezone` field returned by `/api/owm`.

## Basic Setup Instructions

### 1. Log into the WeeWX server CLI

### 2. Activate the virtual environment where WeeWX is installed

```bash
source /home/sysadmin/weewx-env/bin/activate
```

### 3. Install the `weewx-conditions-api` package

```bash
pip install git+https://github.com/eduff0/weewx-conditions-api.git
```

### 4. Configure systemd service to start the API automatically

Create the service file:

```bash
sudo nano /etc/systemd/system/weewx-conditions-api.service
```

Paste the following content:

```ini
[Unit]
Description=WeeWX Conditions API Server
After=network.target

[Service]
User=sysadmin
Group=sysadmin
WorkingDirectory=/home/sysadmin/weewx-env/lib/python3.11/site-packages/weewx_conditions_api
ExecStart=/home/sysadmin/weewx-env/bin/python3 -m weewx_conditions_api.api_server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then run the following commands to enable and start the service:

```bash
sudo mkdir -p /home/sysadmin/weewx-env/lib/python3.11/site-packages/weewx_conditions_api
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable weewx-conditions-api.service
sudo systemctl start weewx-conditions-api.service
sudo systemctl status weewx-conditions-api.service
```

---

## Integration with MagicMirror

Although the API can be used independently, it was designed with MagicMirror integration in mind.

### 5. Install the MagicMirror weather provider

Create the following file:

```bash
~/MagicMirror/modules/default/weather/providers/weewxmm.js
```

> The `weewxmm.js` file is available in the **Documents** folder of this repository.

### 6. Configure MagicMirror to use the provider

Edit your MagicMirror `config.js` to use the new provider. Example module config:

```js
modules: [
  {
    module: "weather",
    position: "top_right",
    config: {
      weatherProvider: "weewxmm",
      apiBase: "http://192.168.1.101:5000", // your WeeWX API base URL
      units: "imperial",
      tempUnits: "imperial",
      degreeLabel: true,
      windUnits: "imperial",
      showWindDirection: true,
      showWindDirectionAsArrow: true,
      timeFormat: 12,
      showPeriod: true,
      lang: "en",
      useCorsProxy: false,
      type: "current",
      showSun: true,
      showHumidity: true
    }
  }
]
```

A sample MagicMirror config.js file is also available in the **Documents** folder of this repo (named `config (MagicMirror sample).js`).

---

## TODO

- [ ] Create an installation package so that Git is not required.
- [ ] Add automated tests for both endpoints.

---

## Notes

- This API is intended for local network use and does not include authentication.
- Tested with Python 3.11 and WeeWX running in a virtual environment.
