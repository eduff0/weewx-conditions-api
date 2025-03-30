# weewx-conditions-api
Creates a REST API to expose current conditions from WeeWX, with initial focus on MagicMirror clients.

TODO:
-rework install scripts to use relative paths.
-check that WeeWX is installed but don't automatically install it if it isn't.
-make a sample file for weewx-conditions-api.service
-create an installation package so that git doen't need to be installed.
-reorder attributes in order of "importance"
-add a second endpoint to demonstrate that the extension is scalable
-add reference to working only with SQLite in the description 

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