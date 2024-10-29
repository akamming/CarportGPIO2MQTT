#standard libs
import signal
import sys
import socket
import time
import json
import os
import uuid
import configparser

#additional libs (see requirements.txt)
from paho.mqtt import client as mqtt_client

Debugging=True

switchname= "CarportLamp"
client_id = socket.gethostname()

Softwareversion = os.uname().release

#commands to export the pin
ExportPinCommand="echo 526 > /sys/class/gpio/export ; echo out > /sys/class/gpio/gpio526/direction ; echo 1 > /sys/class/gpio/gpio526/active_low"
UnexportPinCommand="echo 526 > /sys/class/gpio/unexport"
SwitchOnCommand="echo 1 > /sys/class/gpio/gpio526/value"
SwitchOffCommand="echo 0 > /sys/class/gpio/gpio526/value"

def Debug(text):
    if Debugging: print(text)

def switch_carportlamp(value):
    global client
    if (value):
        os.system(SwitchOnCommand)
        Debug("Switching on carportlamp")
        client.publish(CarportStateTopic,"ON",qos,retain)
    else:
        os.system(SwitchOffCommand)
        Debug("Switching off carportlamp")
        client.publish(CarportStateTopic,"OFF",qos,retain)

def on_connect(client, userdata, flags, rc, Properties=None):
    if rc == 0:
        Debug("Connected to MQTT Broker!")

        #listen to messages
        publishCarportLamp()
    else:
        Debug("Failed to connect, return code "+str(rc))

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    Debug("client disconnected due to reason: "+str(reason_code))
    disconnected=True
    NumberOfTries=1
    while disconnected:
        try:
            client.reconnect()
            disconnected=False
        except:
            Debug("Connection ("+str(NumberOfTries)+") failed, trying again in "+str(reconnectdelay)+" sec")
            NumberOfTries+=1
            time.sleep(reconnectdelay)

def connect_mqtt():
    global broker,port,username,password

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    disconnected=True
    NumberOfTries=1
    while disconnected:
        try:
            client.connect(broker, port)
            disconnected=False
        except:
            Debug("Connection ("+str(NumberOfTries)+") failed, trying again in "+str(reconnectdelay)+" sec")
            NumberOfTries+=1
            time.sleep(reconnectdelay)
    return client

def publishCarportLamp():

    ADmessage = {
            "name": "CarportLamp",
            "unique_id": client_id+"_"+switchname,
            "cmd_t": CarportCommandTopic,
            "stat_t": CarportStateTopic,
            "dev": {
                "ids": hex(uuid.getnode()),
                "name": client_id,
                "sw": Softwareversion,
                "mdl": "pi4b",
                "mf": "raspberry pi foundation"
                }
            }
    client.publish(CarportDiscoveryTopic, json.dumps(ADmessage), qos, retain)
    Debug("Publish ["+json.dumps(ADmessage)+"] on ["+CarportDiscoveryTopic+"]")

    client.subscribe(CarportCommandTopic)
    Debug("Subscribed to "+CarportCommandTopic)

    #Set initial value
    switch_carportlamp(False)

def on_message(client, userdata, msg):
    Debug(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    if (msg.topic==CarportCommandTopic):
        Debug("Received command for Carport light")
        if (msg.payload.decode()=="ON" or msg.payload.decode()=='{"state":"ON"}'):
            switch_carportlamp(True)
        else:
            switch_carportlamp(False)

def exit_gracefully(sig, frame):
    Debug('exited gracefully!')
    client.loop_stop()
    client.disconnect()
    sys.exit(0)

def readIniFile():
    global broker,port,username,password,qos,retain,reconnectdelay,publishinterval,hatopic
    global CarportDiscoveryTopic,CarportStateTopic,CarportCommandTopic

    Debug("ReadIniFIle()")

    config=configparser.ConfigParser()
    config.read("config.ini")
    broker=config["mqtt"]["broker"]
    port=int(config["mqtt"]["port"])
    username=config["mqtt"]["username"]
    password=config["mqtt"]["password"]
    qos=int(config["mqtt"]["qos"])
    hatopic=config["mqtt"]["hatopic"]
    retain=config.getboolean("mqtt","retain")
    reconnectdelay=int(config["intervals"]["reconnectdelay"])
    publishinterval=int(config["intervals"]["publishinterval"])

    #set topics
    CarportDiscoveryTopic=hatopic+"/light/"+client_id+"/"+switchname+"/config"
    CarportStateTopic=client_id+"/light/"+switchname+"/state"
    CarportCommandTopic=client_id+"/light/"+switchname+"/set"

def run():
    global client

    # read ini file
    readIniFile()

    # connect
    client = connect_mqtt()

    #catch the signals to be able to stop gracefully in case of keyboard interrupts of kill signals
    signal.signal(signal.SIGTERM,exit_gracefully)
    signal.signal(signal.SIGINT,exit_gracefully)

    #Create listening thread
    client.loop_start()

    #Loop forever (until sigterm of sigint, which are handled in exit_gracefully)
    while True:
        time.sleep(publishinterval)
        publishCarportLamp()

if __name__ == '__main__':
    run()
