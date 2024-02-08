import requests
import time
import sys

def get(endpoint):
    bad = 0
    while True:
        try:
            r = requests.get(endpoint, timeout=10)
            if r.status_code == 200:
                return r
            if r.status_code == 403:
                time.sleep(57)
            time.sleep(3)
        except:
            time.sleep(10)
        bad += 1
        if bad == 4:
            time.sleep(60)
        if bad >= 4:
            time.sleep(3*60)
            sys.exit(-1)

