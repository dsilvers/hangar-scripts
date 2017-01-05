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
from systemd.journal import JournalHandler
from w1thermsensor import W1ThermSensor
from w1thermsensor.core import W1ThermSensorError

from config import *

root = logging.getLogger()
root.setLevel(logging.INFO)
root.addHandler(JournalHandler())


pusher_client = pusher.Pusher(
  app_id = PUSHER_APP_ID,
  key = PUSHER_APP_KEY,
  secret = PUSHER_APP_SECRET,
  ssl = True
)


probes = False
switches = False


def receive_setup(data):
    global switches
    global probes

    logging.info("Received setup data: {}".format(data))

    data = json.loads(data)
    switches = data['switches']
    probes = data['probes']

    for switch in switches:
        logging.info("Switch {} is on pin {}, current state is {}".format(
            switch['name'],
            switch['pin'],
            switch['state'],
        ))
        write_switch_state(switch['pin'], switch['state'], switch['name'])

    for probe in probes:
        logging.info("Probe {} has serial {}".format(probe['name'], probe['serial']))


def write_switch_state(pin, state, name=""):
    if state is not True and state is not False:
        logging.info("Switch {} has invalid state specifed. ('{}') Not writing switch state.".format(
            name,
            state,
        ))
        return

    logging.info("Writing switch state on pin {} to {}".format(pin, state))
    io.setmode(io.BCM)
    io.setup(int(pin), io.OUT)
    io.output(int(pin), state)
    logging.info("Done writing switch state on pin {} to {}".format(pin, state))


def receive_switch_state(data):
    logging.info("Receive switch state change: {}".format(data))

    data = json.loads(data)

    name = data['name']
    pin = data['pin']
    state = data['state']

    write_switch_state(pin, state, name)

    pusher_client.trigger(['hangar-status'], 'switch-log', {
        'name': name,
        'pin': pin,
        'state': state,
    })


def send_temperature_data():
    global probes

    probe_data = []

    for probe in probes:
        try:
            sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, probe['serial'])
        except W1ThermSensorError:
            logging.info("No probe found for '{}' on serial {}".format(
                probe['name'],
                probe['serial'],
            ))
            sensor = False

        if sensor:
            temperature = sensor.get_temperature() 
            probe_data.append({
                'name': probe['name'],
                'serial': probe['serial'],
                'temperature':  temperature,
            })
            logging.info("Probe {} on {} has temperature of {}'C".format(
                probe['name'],
                probe['serial'],
                temperature,
            ))
    
    pusher_client.trigger(['hangar-status'], 'temperature-log', probe_data)



def connect_handler(data):
    channel = pc.subscribe('hangar-status')
    channel.bind('switches', receive_switch_state)
    channel.bind('setup-response', receive_setup)

    logging.info("Sending setup request")
    pusher_client.trigger(['hangar-status'], 'setup-request', {
        'setup': 'please',
    })


pc = pusherclient.Pusher(PUSHER_APP_KEY)
pc.connection.bind('pusher:connection_established', connect_handler)
pc.connect()

while True:
    time.sleep(5)
    send_temperature_data()
    time.sleep(55)

