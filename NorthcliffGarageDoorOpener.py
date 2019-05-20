# Northcliff Garage Door Opener Version 1.1 with Restart Message
#!/usr/bin/ env python3
import RPi.GPIO as GPIO
import time
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import os

class NorthcliffGarageDoorOpener(object):
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        self.open_door = 18
        GPIO.setup(self.open_door, GPIO.OUT)
        GPIO.output(self.open_door, False)
        self.door_open = False
        self.heartbeat_count = 0
        self.no_heartbeat_ack = False

    def print_status(self, print_message):
        today = datetime.now()
        print(print_message + today.strftime('%A %d %B %Y @ %H:%M:%S'))

    def startup(self): # Set up the mqtt communications
        self.client = mqtt.Client('garage')
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(<Your mqtt Broker Here', 1883, 60)
        self.client.loop_start()
        self.client.subscribe('GarageControl')
        self.client.publish('GarageStatus', '{"service": "Closed"}') # Set current Garage Door state to closed

    def on_connect(self, client, userdata, flags, rc):
        time.sleep(1)
        self.print_status('Connected to mqtt server with result code '+str(rc)+' on')

    def on_message(self, client, userdata, msg): # Handles incoming mqtt messages
        #print("Message", str(msg.topic), str(msg.payload.decode('utf-8')))
        decoded_payload = str(msg.payload.decode('utf-8'))
        parsed_json = json.loads(decoded_payload)
        if msg.topic == 'GarageControl':
            if parsed_json['service'] == 'OpenGarage' and parsed_json['value'] == 0:
                self.door_open = True
            elif parsed_json['service'] == 'Heartbeat Ack':
                self.heartbeat_ack()
            else:
                print('Invalid Garage Door Command Received', parsed_json)
                self.door_open = False

    def heartbeat_ack(self):
        self.print_status('Heartbeat received from Home Manager on ')
        self.heartbeat_count = 0
        self.no_heartbeat_ack = False

    def process_home_manager_heartbeat(self):
        self.heartbeat_count +=1
        if self.heartbeat_count == 240:
            self.print_status('Sending Heartbeat to Home Manager on ')
            self.send_heartbeat_to_home_manager()
        if self.heartbeat_count > 320:
            self.print_status('Home Manager Heartbeat Lost. Restarting code on ')
            self.no_heartbeat_ack = True
            self.restart_code()

    def send_heartbeat_to_home_manager(self):
        self.client.publish('GarageStatus', '{"service": "Heartbeat"}') 

    def restart_code(self):
        self.client.publish('GarageStatus', '{"service": "Restart"}')
        self.shutdown()
        os.system('sudo reboot')

    def shutdown(self):
        self.print_status('Shutting down on ')
        GPIO.cleanup()
        self.client.loop_stop()

    def run(self):
        self.startup()
        try:
            while True:
                #print("waiting for message")
                if self.door_open == True:# This is done outside on_message because client.publish doesn't like time.sleep
                    self.print_status('Garage Door opening on ')
                    GPIO.output(self.open_door, True)
                    time.sleep(1)
                    GPIO.output(self.open_door, False)
                    time.sleep(29)
                    self.print_status('Garage Door opened on ')
                    self.client.publish('GarageStatus', '{"service": "Opened"}')
                    time.sleep(10)
                    self.print_status('Garage Door closing on ')
                    self.client.publish('GarageStatus', '{"service": "Closing"}')
                    time.sleep(30)
                    self.print_status('Garage Door closed on ')
                    self.client.publish('GarageStatus', '{"service": "Closed"}')
                    self.door_open = False
                else:
                    self.process_home_manager_heartbeat()
                    time.sleep(0.5)
        except KeyboardInterrupt:
            self.shutdown()

if __name__ == '__main__':
    garage = NorthcliffGarageDoorOpener()
    garage.run()
