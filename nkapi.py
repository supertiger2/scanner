import requests
import time
import sys

def get(endpoint):
    bad = 0
    while True:
        try:
            r = requests.get(endpoint, timeout=120)
            if r.status_code == 200:
                return r
            if r.status_code == 403:
                time.sleep(27)
            time.sleep(3)
        except:
            time.sleep(10)
        bad += 1
        if bad == 4:
            time.sleep(60)
        if bad >= 6:
            time.sleep(2*60)
            if bad >= 10:
                time.sleep(15*60)
                sys.exit(-1)

