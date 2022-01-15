import argparse
import json
import getpass
from pathlib import Path
from pprint import pprint

from ring_doorbell import Ring, Auth
from oauthlib.oauth2 import MissingTokenError

import time
import threading
from threading import Lock

from mqtt_client import RingMqtt

cache_file = Path("test_token.cache")


def token_updated(token):
    cache_file.write_text(json.dumps(token))


def otp_callback():
    auth_code = input("2FA code: ")
    return auth_code


def main():
    parser = argparse.ArgumentParser(description='Start an MQTT client.')
    parser.add_argument("--hostname", default="127.0.0.1")
    parser.add_argument("--update_frequency", default="10", type=int,
            help="Update frequency, in minutes")
    args = parser.parse_args()

    if cache_file.is_file():
        auth = Auth("RingMqtt/2.0", json.loads(cache_file.read_text()), token_updated)
    else:
        username = input("Username: ")
        password = getpass.getpass("Password: ")
        auth = Auth("RingMqtt/2.0", None, token_updated)
        try:
            auth.fetch_token(username, password)
        except MissingTokenError:
            auth.fetch_token(username, password, otp_callback())

    ring_mutex = Lock()

    ring = Ring(auth)
    ring.update_data()

    devices = ring.devices()
    pprint(devices)
    groups = ring.groups()
    for groupKey in groups:
        group = groups[groupKey]
        group.update()
        print(group.name, " ", group.lights)

    ringMqtt = RingMqtt(ring, ring_mutex)

    # Start the update thread loop
    updateThread = threading.Thread(target=update_loop,
            args=(ring, ring_mutex, args.update_frequency), daemon=True)
    updateThread.start()
    # Start the server
    ringMqtt.setup_mqtt_client(args.hostname)


def update_loop(ring: Ring, ring_mutex: Lock, update_frequency: int):
    while True:
        print("Updating Ring groups")
        ring_mutex.acquire()
        try:
            ring.update_groups()
        finally:
            ring_mutex.release()
        time.sleep(update_frequency * 60)

if __name__ == "__main__":
    main()
