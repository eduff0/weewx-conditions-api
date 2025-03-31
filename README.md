# weewx-conditions-api
Creates a REST API to expose current conditions from SQLite database used by WeeWX, with initial focus on MagicMirror clients.

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
	
TODO:
-create an installation package so that git doen't need to be installed.
-add a second endpoint to demonstrate that the extension is scalable
-add reference to working only with SQLite in the description 