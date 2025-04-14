# weewx-conditions-api
Creates a REST API to expose current conditions from SQLite database used by WeeWX, with initial focus on MagicMirror clients.  The initial version returns a JSON structure corresponding to current conditions in the MagiceMirror Weather Object.  In the future, additional structures could be exposed from WeeWX such as WeatherObject, Weather.gov, Pirate Weather, etc.

Basic instructions:
1) Log into WeeWx server

2) Activate virtual environment in which WeeWx is installed
	source /home/sysadmin/weewx-env/bin/activate

3) Install weewx-conditions-api
	pip install git+https://<username>:<token>@github.com/eduff0/weewx-conditions-api.git

4) Configure service to automatically start
	sudo nano /etc/systemd/system/weewx-conditions-api.service
	File contents
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

	sudo mkdir -p /home/sysadmin/weewx-env/lib/python3.11/site-packages/weewx_conditions_api
	sudo systemctl daemon-reexec
	sudo systemctl daemon-reload
	sudo systemctl enable weewx-conditions-api.service
	sudo systemctl start weewx-conditions-api.service
	sudo systemctl status weewx-conditions-api.service

If needing to consume this API using the weather module in MagicMirror, which is the reason the API was created (but not limited to this use case), then
5) Install WeeWX weather module provider for MagicMirror
    Create file "weewxmm.js" in ~ /MagicMirror/modules/default/weather/providers
	File "weewxmm.js" is available in the Documents folder of this repository

6) Configure MagicMirror to use the provider
    Edit the MagicMirror configuration file, "config.js".
	File "config (MagicMirror sample).js" is available in the Documents folder of this repository.
	The important thing is to edit the "apiBase" attribute to point to the WeeWx server and port for which weewx-conditions-api is listening.
	
	File contents
	modules: [
                {
                        module: "weather",
                        position: "top_right",
                        config: {
                                weatherProvider: "weewxmm",
                                apiBase: "http://192.168.1.101:5000", // your WeeWX API URL
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
                                showHumidity: true,
                                showWindDirection: true
                        }
                }
	]	
	
TODO:
-create an installation package so that git doen't need to be installed.
-add a second endpoint to demonstrate that the extension is scalable
-add reference to working only with SQLite in the description 