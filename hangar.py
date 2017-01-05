#!/usr/bin/env python
"""
On startup
- load initial settings
- load schedule (in case interwebs disconnect)

Loop
- Report temperatures and switch statuses

Handler
- Receive websocket notifications to turn switches on

"""

import time
import random
import json
import pusher
import pusherclient
import RPi.GPIO as io
import logging
import sys
from w1thermsensor import W1ThermSensor

from config import *

root = logging.getLogger()
root.setLevel(logging.INFO)
ch = logging.StreamHandler(sys.stdout)
root.addHandler(ch)

pusher_client = pusher.Pusher(
  app_id = PUSHER_APP_ID,
  key = PUSHER_KEY,
  secret = PUSHER_SECRET,
  ssl = True
)


probes = False
switches = False


def receive_setup(data):
    global switches
    global probes

    data = json.loads(data)
    switches = data['switches']
    probes = data['probes']


def set_switch_status(data):
    data = json.loads(data)

    name = data['name']
    pin = data['pin']
    state = False if data['state'] == "0" else True

    io.setmode(io.BCM)
    io.setup(pin, io.OUT)
    io.output(pin, state)
    io.cleanup()

    pusher_client.trigger('hangar-status', 'switch-log', {
        'name': name,
        'pin': pin,
        'state': state,
    })


def send_temperature_data():
    global probes

    probe_data = []

    for probe in probes:
        try:
            sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, probe.serial)
        except w1thermsensor.core.NoSensorFoundError:
            sensor = False

        if sensor:
            probe_data.append({
                'name': probe.name,
                'serial': probe.serial,
                'temperature': sensor.get_temperature()  
            })
    
    pusher_client.trigger('hangar-status', 'temperature-log', probe_data)



def connect_handler(data):
    channel = pc.subscribe('hangar-status')
    channel.bind('switches', set_switch_status)
    channel.bind('setup-response', receive_setup)

    pusher_client.trigger('hangar-status', 'setup-request', {
        'setup': 'please',
    })


pc = pusherclient.Pusher(PUSHER_KEY)
pc.connection.bind('pusher:connection_established', connect_handler)
pc.connect()

while True:
    time.sleep(5)
    send_temperature_data()
    time.sleep(55)

