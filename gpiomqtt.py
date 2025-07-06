#!/usr/bin/env python3

import time
import json
import signal
import sys
import configparser
from gpiozero import Button
import paho.mqtt.client as mqtt

mqtt_client = None
running = True

mqtt_qos = 0
mqtt_retain = True

# Config variabelen, worden later geladen
gpio_pin = 18
meterfile = "meterstand.txt"
domoticz_idx = 0
MQTT_TOPIC_DOMOTICZ_IN = "domoticz/in"

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"Connected to MQTT Broker with result code {rc} ({mqtt.error_string(rc)})")

def read_meter_value():
    try:
        with open(meterfile, "r") as f:
            val = f.read().strip()
            return int(val)
    except Exception as e:
        print(f"Fout bij lezen van meterstand uit {meterfile}: {e}")
        return 0

def write_meter_value(value):
    try:
        with open(meterfile, "w") as f:
            f.write(str(value))
    except Exception as e:
        print(f"Fout bij schrijven van meterstand naar {meterfile}: {e}")

def pulse_detected():
    global mqtt_client, domoticz_idx

    # Lees huidige stand
    current_value = read_meter_value()
    new_value = current_value + 1
    print(f"Pulse detected! Meterstand verhoogd van {current_value} naar {new_value}")

    # Schrijf nieuwe stand terug
    write_meter_value(new_value)

    # Bouw Domoticz MQTT payload
    payload = json.dumps({
        "command": "udevice",
        "idx": domoticz_idx,
        "nvalue": new_value,
        "svalue": str(new_value)
    })

    mqtt_client.publish(MQTT_TOPIC_DOMOTICZ_IN, payload, qos=mqtt_qos, retain=mqtt_retain)
    print(f"Verzonden naar Domoticz topic [{MQTT_TOPIC_DOMOTICZ_IN}]: {payload} (qos={mqtt_qos}, retain={mqtt_retain})")

def run():
    global mqtt_client, gpio_pin, meterfile, domoticz_idx, mqtt_qos, mqtt_retain, MQTT_TOPIC_DOMOTICZ_IN

    # Config inlezen
    config = configparser.ConfigParser()
    config.read("config.ini")

    mqtt_broker = config.get("mqtt", "broker", fallback="localhost")
    mqtt_port = config.getint("mqtt", "port", fallback=1883)
    mqtt_user = config.get("mqtt", "username", fallback=None)
    mqtt_pass = config.get("mqtt", "password", fallback=None)
    mqtt_qos = config.getint("mqtt", "qos", fallback=0)
    mqtt_retain = config.getboolean("mqtt", "retain", fallback=True)

    gpio_pin = config.getint("domoticz", "gpio_pin", fallback=18)
    meterfile = config.get("domoticz", "meterfile", fallback="meterstand.txt")
    domoticz_idx = config.getint("domoticz", "idx", fallback=0)
    # Topic voor Domoticz command
    MQTT_TOPIC_DOMOTICZ_IN = config.get("mqtt", "domoticzin", fallback="domoticz/in")

    print(f"Start met GPIO pin {gpio_pin} voor watermeter puls")
    print(f"Meterbestand: {meterfile}")
    print(f"Domoticz IDX: {domoticz_idx}")
    print(f"MQTT broker: {mqtt_broker}:{mqtt_port}")

    # Setup MQTT client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if mqtt_user and mqtt_pass:
        mqtt_client.username_pw_set(mqtt_user, mqtt_pass)

    mqtt_client.on_connect = on_connect

    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()

    # Setup pulse input met gpiozero Button (kan ook Button maar gebruiken voor puls detectie)
    button = Button(gpio_pin, pull_up=True, bounce_time=0.05)
    button.when_pressed = pulse_detected

    print("Running, press CTRL+C to exit")

    while running:
        time.sleep(1)

def signal_handler(sig, frame):
    global running
    print('Exiting gracefully')
    running = False
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    run()

