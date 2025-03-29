# weewx_conditions_api/setup.py
"""
Installer for WeeWX-ConditionsAPI
"""

from setup import ExtensionInstaller

def loader():
    return ConditionsAPIInstaller()

class ConditionsAPIInstaller(ExtensionInstaller):
    def __init__(self):
        super().__init__(
            name='WeeWX-ConditionsAPI',
            version='0.1',
            description='Exposes RESTful API with current weather data from weewx.sdb',
            author='Your Name',
            author_email='your@email.com',
            files=[
                ('bin/user/weewx_conditions_api', [
                    'bin/user/weewx_conditions_api/__init__.py',
                    'bin/user/weewx_conditions_api/api_server.py',
                ]),
            ],
            config={}
        )
