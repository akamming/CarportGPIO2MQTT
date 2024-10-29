# CarportGPIO2MQTT
Convert GPIO 2 MQTT autodiscovery so pin can be controlled from both domoticz and home assistant

how to install: 
- git clone <this repository>
- go to the newly cloned dir
- python3 -m venv .
- ./bin/pip install -r requirements.txt
- copy gpio2mqtt.service to /etc/systemd/system
- edit ini file so it has the correct mqtt settings
- test locally with ./bin/python3 *.py  install/run as deamon by: systemctl enable gpio2mqtt and systemctl start gpio2mqtt
