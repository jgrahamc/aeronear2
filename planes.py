# Small device that shows the nearest plane using the ADSB Exchange API
#
# Copyright (c) 2022 John Graham-Cumming

from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import csv
import requests
import math

import time

import subprocess

# Contains API_KEY, MY_LAT, MY_LONG and RADIUS

from planes_config import API_KEY, MY_LAT, MY_LONG, RADIUS

# findcsv reads a CSV file from filename and tries to find match in
# column col. If it finds it returns the row, if it doesn't it returns
# a fake row containing match. Yeah, this really should just read the
# CSV once on startup and make a dictionary but this allowed me to
# fiddle with the CSV files while the program was running
def findcsv(filename, col, match):
    with open(filename, 'r') as f:
        r = csv.reader(f)
        for row in r:
            if row[col] == match.strip():
                return row

    return [match, match, match, match, match]

# getplanes calls the ADBS Exchange API to get the JSON containing
# nearby planes. It returns the result of requests.get()
def getplanes():
    url = "https://adsbexchange-com1.p.rapidapi.com/json/lat/%.3f/lon/%.3f/dist/%d/" % (MY_LAT, MY_LONG, RADIUS)
    return requests.get(url,
      headers={
        "X-RapidAPI-Host": "adsbexchange-com1.p.rapidapi.com",
        "X-RapidAPI-Key": API_KEY,
        "Accept-Encoding": "None"
      })

# FUNCTIONS FOR DRAWING TEXT AND IMAGES ON THE SCREEN

screen_tmp = '/tmp/planes.tmp.png'
screen_file = '/tmp/planes.png'
screen_links = ['/tmp/planes%d.png' % i for i in range(1, 4)]

# screen_show takes an image in img and writes it to a file and then
# uses fbi to draw it to the screen
def screen_show(img):
    
    # This is done to prevent fbi from getting an error if it tries to
    # read one of the images it is displaying while we write it. It's
    # written to a temporary file and then mv'ed into place.
    
    img.save(screen_tmp)
    subprocess.run('mv %s %s' % (screen_tmp, screen_file), shell=True)

    # Determine if there are any instance of fbi running. Start one if
    # there is not
    running = []
    try:
        running = subprocess.check_output(['pgrep', 'fbi']).decode("utf-8").strip().split('\n')
    except:
        pass

    if len(running) == 0:
        subprocess.run('fbi -t 1 -T 2 -a -cachemem 0 -noverbose -d /dev/fb1 %s' % ' '.join(screen_links),
                       shell=True)
    
# screen_start sets up the screen for use. The most important thing it
# does is create three symbolic links that are fed to fbi in
# screen_show. This is a trick to get fbi to cycle through images and
# allow a single fbi instance to updated smoothly
def screen_start():
    subprocess.run(['pkill', 'fbcp'])
    
    for l in screen_links:
        subprocess.run(['ln -s %s %s' % (screen_file, l)], shell=True)

# haversine works out the distance on the Earth's surface between
# two points given a latitude and longitude. 
def haversine(la1, lo1, la2, lo2):
    phi1 = math.radians(la1)
    phi2 = math.radians(la2)
    delta_phi = math.radians(la2-la1)
    delta_lambda = math.radians(lo2-lo1)

    a = math.sin(delta_phi/2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda/2.0) ** 2
    return 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# distance returns the distance to an aircraft
def distance(a):
    return haversine(MY_LAT, MY_LONG, float(a['lat']), float(a['lon']))

# bearing works out the bearing of one lat/long from another
def bearing(la1, lo1, la2, lo2):
    lat1 = math.radians(la1)
    lat2 = math.radians(la2)

    diff = math.radians(lo2 - lo1)

    x = math.sin(diff) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diff))

    b = math.degrees(math.atan2(x, y))
    return (b + 360) % 360

# required contains a list of fields that must be present and
# non-empty in the returned JSON

required = ['call', 'type', 'opicao', 'from', 'to', 'lat', 'lon',
            'trak', 'gnd']

screen_start()

# The default update_delay is 60 seconds. 

planes_delay = 60
update_delay = 0

while True:
    time.sleep(update_delay)
    
    planes = getplanes()
    j = planes.json()

    if j is None or j['ac'] is None:
        blank()
        continue

    # Build near so that it contains aircraft that have all the fields
    # in required and are not on the ground

    near = []
    for ac in j['ac']:
        ok = True
        for r in required:
            if r not in ac or ac[r].strip() == '':
                ok = False
                break
            
        if ok and ac['gnd'] == '0':
            near.append(ac)

    # If there are aircraft then sort them by distance from the device
    # and display the nearest
   
    if len(near) > 0:
        near.sort(key=distance)
#        ac = near[0]
#        flight = ac['call']
#        plane = findcsv('planes.dat', 2, ac['type'])[0]
#        airline = findcsv('airlines.dat', 4, ac['opicao'])[1]
#        altitude = ac['alt']
#        from_ = findcsv('airports.dat', 4, ac['from'][:4])
#        from_airport = from_[1]
#        from_city = from_[2]
#        from_country = from_[3]
#        to_ = findcsv('airports.dat', 4, ac['to'][:4])
#        to_airport = to_[1]
#        to_city = to_[2]
#        to_country = to_[3]
#        b = bearing(MY_LAT, MY_LONG, float(ac['lat']), float(ac['lon']))
#        trak = float(ac['trak'])
#        spotted(flight, airline, from_airport, from_city, from_country,
#                to_airport, to_city, to_country, plane, altitude, b, trak)

    update_delay = planes_delay

    
    
