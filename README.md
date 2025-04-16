# weewx-conditions-api

Creates a REST API, using Flask, to expose current weather conditions from the SQLite database used by [WeeWX](http://weewx.com/), with initial focus on [MagicMirror](https://magicmirror.builders/) clients (see instructions for MagicMirror below).

The API has a single endpoint that returns a JSON structure compatible with the MagicMirror `weather` module’s [WeatherObject](https://docs.magicmirror.builders/development/weather-provider.html#weatherobject) format. Future versions may have endpoints for other formats, such as Openweathermap, Weather.gov, or Pirate Weather.
## Example of JSON returned by API

```json
{
  "humidity": 57.1,
  "pressure": 1013.9,
  "sunrise": "2025-04-16T06:28:18.496292",
  "sunset": "2025-04-16T20:02:44.294692",
  "temperature": 8.8,
  "timestamp": "2025-04-15T00:12:00Z",
  "windDirection": 316.2,
  "windSpeed": 2.34
}
```
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
- [ ] Add a second endpoint to demonstrate that the API can scale to multiple JSON structures.
---

## Notes

- This API is intended for local network use and does not include authentication.
- Tested with Python 3.11 and WeeWX running in a virtual environment.
