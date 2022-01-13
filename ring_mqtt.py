import argparse
import json
import getpass
from pathlib import Path
from pprint import pprint

from ring_doorbell import Ring, Auth
from oauthlib.oauth2 import MissingTokenError

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

    ring = Ring(auth)
    ring.update_data()

    devices = ring.devices()
    pprint(devices)
    groups = ring.groups()
    for groupKey in groups:
        group = groups[groupKey]
        group.update()
        print(group.name, " ", group.lights)

    ringMqtt = RingMqtt(ring)
    ringMqtt.setup_mqtt_client(args.hostname)

if __name__ == "__main__":
    main()
