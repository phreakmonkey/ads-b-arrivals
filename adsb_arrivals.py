#!/usr/bin/env python

import datetime
import select
import socket
import time
import errno
from operator import itemgetter

from geopy import distance
import paho.mqtt.publish as publish


MQTT_HOST = 'localhost'  # MQTT broker
ADSB_HOST = 'pi-sdr001'  # Host running dump1090
ADSB_PORT = 30003
AIRCRAFT = ['A8F94E']    # List of Mode-S HexIDs we want to alert on

LOC = (38.893888, -119.995333) # KTVL Airport
ARM_ALT = (8000, 10000)  # Aircraft between these altitudes
ARM_NM = 15              # within this distance are considered "ARMed"

ARR_ALT = 7800           # ARMed aircraft that descend below this altitude,
ARR_NM = 8               # and within this distance are assumed to arrive.
LOGFILE = "arrivals.log"


class Aircraft():
  def __init__(self, hexid):
    self.hexid = hexid
    self.latlon = None
    self.altitude = None
    self.speed = None
    self.timestamp = time.time()
    self.status = 0
  def update(self, attribute, param):
    setattr(self, attribute, param)
    self.timestamp = time.time()

class SpeedRecords():
  def __init__(self):
    self.low = {}
    self.mid = {}
    self.high = {}
    self.number = 5
    
  def check(self, aid, alt, spd):
    if (not alt) or (not spd):
      return
    if alt < 12000:
      d = self.low
    elif alt < 18000:
      d = self.mid
    else:
      d = self.high

    if aid in d:
      if spd > d[aid]:
        d[aid] = spd
    else:
      d[aid] = spd

    if len(d) > self.number:
      del(d[sorted(d.items(), key=itemgetter(1), reverse=True)[-1][0]])

  def highscores(self, d):
    return sorted(d.items(), key=itemgetter(1), reverse=True)


aircraft = {}
records = SpeedRecords()
starttime = datetime.datetime.now()

def parse(line):
  fields = line.split(',')
  if len(fields) != 22:
    print "Discarding invalid packet [Len: %d]" % len(fields)
    return
  msg_type = fields[1]
  if msg_type == '3' or msg_type == '4':
    aircraft_id = fields[4]
    alt = fields[11]
    speed = fields[12]
    lat, lon = fields[14], fields[15]
    if aircraft_id not in aircraft:
      aircraft[aircraft_id] = Aircraft(aircraft_id)
    if alt:
      aircraft[aircraft_id].update('altitude', int(alt))
    if speed:
      aircraft[aircraft_id].update('speed', int(speed))
    if lat and lon:
      aircraft[aircraft_id].update('latlon', (lat, lon))

def prune():
  for k, a in aircraft.items():
    if time.time() - a.timestamp > 60:
      del(aircraft[k])

def scan():
  for k, a in aircraft.items():
    age = time.time() - a.timestamp
    if a.altitude and a.latlon:
      records.check(k, a.altitude, a.speed)
      nm = distance.distance(LOC, a.latlon).nm
      if (a.status == 0 and nm < ARM_NM and 
          a.altitude > ARM_ALT[0] and a.altitude < ARM_ALT[1]):
        aircraft[k].status = 1
      elif a.status == 1 and nm < ARR_NM and a.altitude < ARR_ALT:
        if k in AIRCRAFT:
          # MQTT Message for aircraft of interest:
          publish.single({'topic':"lastseen/", 'payload':str(int(time.time())),
                          'retain':True}, hostname=MQTT_HOST)
        aircraft[k].status = 2
        arrstr =  '%s %s: Arriving (%s feet at %s nm)' % (
            time.ctime(), k, a.altitude, nm)
        with open(LOGFILE, 'a') as f:
          f.write(arrstr + '\n')

def draw():
  ESC = chr(27)
  CLEAR = '%s[H%s[J' % (ESC, ESC)
  print '%sUptime: %s' % (CLEAR, str(datetime.datetime.now() - starttime).split('.')[0])
  print 'ID\tDis\tAlt\tSpeed\tAge\tStatus'
  for k, a in aircraft.items():
    nm = distance.distance(LOC, a.latlon).nm
    age = int(time.time() - a.timestamp)
    if nm < 6000:
      print '%s\t%.1f\t%s\t%s\t%s\t%s' % (k, nm, a.altitude, a.speed, age, 
                                          a.status)
    else:
      print '%s\tUNK\t%s\t%s\t%s\t%s' % (k,  a.altitude, a.speed, age, a.status)

  print '\n---- Speed Records ----'
  print '===== Above FL180 ====='
  for i,s in records.highscores(records.high):
    print '%s\t%s' % (i,s)
  print '\n===== 12000 MSL - 18000 MSL ====='
  for i,s in records.highscores(records.mid):
    print '%s\t%s' % (i,s)
  print '\n===== Below 12000 MSL ====='
  for i,s in records.highscores(records.low):
    print '%s\t%s' % (i,s)
    
def connect():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  while True:
    try:
      s.connect((socket.gethostbyname(ADSB_HOST), ADSB_PORT))
    except socket.error, e:
      print "Failed to connect: %s  Retrying." % e
      time.sleep(30)
      continue
    break
  s.settimeout(None)
  print "Connected to %s:%s" % (ADSB_HOST, ADSB_PORT)
  return s

def main():
  s = connect()
  data = ''
  buf = ''
  buffer_size = 4096
  prunetime = time.time()
  drawtime = 0
  while True:
    try:
      if not '\r\n' in data:
        d = s.recv(buffer_size)
      if d == '':
        s.shutdown(2)
        s.close()
        print "Connection terminated.  Attempting to re-establish."
        time.sleep(1)
        s = connect()
        continue
      data += d
      if not '\r\n' in data:
        continue
    except socket.error:
      s.shutdown(2)
      s.close()
      print "Connection terminated.  Attempting to re-establish."
      time.sleep(1)
      s = connect()
      continue
    i = data.rfind('\r\n')
    data, buf = data[:i+2], data[i+2:]
    lines = data.split('\r\n')
    lines = filter(None, lines)
    for line in lines:
      parse(line)
    data = buf
    scan()
    if time.time() - prunetime > 5:
      prune()
    if time.time() - drawtime >= 1:
      draw()

if __name__ == '__main__':
  main()
