#!/usr/bin/env python3

import time
import json
import signal
import sys
from gpiozero import Device, Button
import paho.mqtt.client as mqtt

# Forceer RPi.GPIO backend voor gpiozero

# Configuratie (pas aan naar jouw situatie)
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_CLIENT_ID = "gpio2mqtt"
GPIO_PIN = 17  # Voorbeeld GPIO pin (BCM nummering)
MQTT_TOPIC_COMMAND = "domoticz/light/CarportLamp/set"
MQTT_TOPIC_STATE = "domoticz/light/CarportLamp/state"
MQTT_TOPIC_CONFIG = "homeassistant/light/domoticz/CarportLamp/config"

# Globale variabelen
mqtt_client = None
button = None
running = True
lamp_status = False

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC_COMMAND)
    # Publiceer HomeAssistant discovery config
    config_payload = json.dumps([{
        "name": "CarportLamp",
        "unique_id": "domoticz_CarportLamp",
        "cmd_t": MQTT_TOPIC_COMMAND,
        "stat_t": MQTT_TOPIC_STATE,
        "dev": {
            "ids": "0xe45f0110128e",
            "name": "domoticz",
            "sw": "6.12.25+rpt-rpi-v8",
            "mdl": "pi4b",
            "mf": "raspberry pi foundation"
        }
    }])
    client.publish(MQTT_TOPIC_CONFIG, config_payload, retain=True)
    print(f"Publish {config_payload} on [{MQTT_TOPIC_CONFIG}]")

def on_message(client, userdata, msg):
    global lamp_status
    payload = msg.payload.decode()
    print(f"Message received on topic {msg.topic}: {payload}")

    if msg.topic == MQTT_TOPIC_COMMAND:
        if payload.lower() in ["on", "true", "1"]:
            lamp_status = True
            print("Switching on carportlamp")
            # TODO: GPIO output aanzetten als je output gebruikt
            publish_state(True)
        elif payload.lower() in ["off", "false", "0"]:
            lamp_status = False
            print("Switching off carportlamp")
            # TODO: GPIO output uitzetten
            publish_state(False)

def publish_state(state):
    mqtt_client.publish(MQTT_TOPIC_STATE, "ON" if state else "OFF", retain=True)
    print(f"Published lamp state: {'ON' if state else 'OFF'}")

def button_pressed():
    global lamp_status
    lamp_status = not lamp_status
    print(f"Button pressed, toggling lamp to {'ON' if lamp_status else 'OFF'}")
    publish_state(lamp_status)

def run():
    global mqtt_client, button

    # Setup button input
    button = Button(GPIO_PIN)
    button.when_pressed = button_pressed

    # Setup MQTT client
    mqtt_client = mqtt.Client(MQTT_CLIENT_ID)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()

    print("Running, press CTRL+C to exit")

    # Run until stopped
    while running:
        time.sleep(1)

def signal_handler(sig, frame):
    global running
    print('Exiting gracefully')
    running = False
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    run()

