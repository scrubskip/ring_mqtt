from threading import Lock
from ring_doorbell import Ring
from pprint import pprint

import paho.mqtt.client as mqtt
import threading

class RingMqtt:

    def __init__(self, ring: Ring, ring_mutex: Lock):
        self.ring = ring
        self.ring_mutex = ring_mutex

    def setup_mqtt_client(self, hostname):
        self.ring.update_data()
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(hostname)
        self.client.loop_forever()


    def update_mqtt(self):
        self.ring_mutex.acquire()
        try:
            self.ring.update_groups()
            groups = self.ring.groups()
            for groupKey in groups:
                group = groups[groupKey]
                print(group.name, " ", group.lights)
                self.client.publish(group.name.lower() + "/light/status", ("ON" if group.lights else "OFF"))
        finally:
            self.ring_mutex.release()

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self.update_mqtt()
        groups = self.ring.groups()
        for groupKey in groups:
            group = groups[groupKey]
            client.subscribe(group.name.lower() + "/light/switch")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg : mqtt.MQTTMessage):
        print(msg.topic+" "+str(msg.payload))
        
        topicParts = msg.topic.split("/")
        self.ring_mutex.acquire()
        try:
            groups = self.ring.groups()
            for groupKey in groups:
                group = groups[groupKey]
                if group.name.lower() == topicParts[0]:
                    # check the payload
                    payloadStr = msg.payload.decode()
                    print("Setting", group.name, " ", payloadStr)
                    
                    group.lights = True if payloadStr == "ON" else False
                    break
        finally:
            self.ring_mutex.release()
