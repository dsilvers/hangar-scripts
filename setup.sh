#!/bin/bash

sudo easy_install pip
sudo apt-get install -y build-essential libssl-dev libffi-dev python-dev libsystemd-{journal,daemon,login,id128}-dev pkg-config
sudo pip install -r requirements.txt

sudo cp hangar.service /etc/systemd/system/
sudo systemd enable hangar
sudo systemd start hangar

sudo cp autossh.service /etc/systemd/system/
sudo systemd enable autossh
sudo systemd start autossh