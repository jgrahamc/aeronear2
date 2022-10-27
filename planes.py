# Small device that shows the nearest plane using the ADSB Exchange API
#
# Copyright (c) 2022 John Graham-Cumming
#
# TODO
#
# fbi
# set up linux image
# 3D print case
# make mode switchable between auto/arrivals/departures

from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
import csv
import requests
import math
import time
import subprocess
import unidecode

# Contains API_KEY, MY_LAT, MY_LONG and RADIUS

from planes_config import API_KEY, MY_LAT, MY_LONG, RADIUS, AIRPORT

xleft = 9
ytop = 10

# Cache of loaded CSV data

cache = {}

# findcsv reads a CSV file from filename and tries to find match in
# column col. If it finds it returns the row, if it doesn't it returns
# a fake row containing match.
def findcsv(filename, col, match):
    key = "%s%d" % (filename, col)
    if not key in cache:
        cache[key] = {}
        with open(filename, 'r') as f:
            r = csv.reader(f)
            for row in r:
                cache[key][row[col].strip()] = row

    match = match.strip()
    if match in cache[key]:
        return cache[key][match]

    return [match, match, match, match, match, match, match, match, match, match, match, match, match]

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

foreground_yellow = (255, 204, 1)
background_yellow = (46, 46, 28)
highlight = (255, 255, 255)
background = (0, 0, 0)

spacing = 10

# icon adds the departures or arrivals icon
def icon(img, t, x, y):
    icon_png = 'images/' + t.lower() + '.png'
    
    if os.path.isfile(icon_png):
        icon_img = Image.open(icon_png, 'r').resize((26, 26))
        img.paste(icon_img, (x, y+6), icon_img)
        icon_img.close()
        return x + 35

    return x

# truncate shortens a string without breaking in the middle of
# a word
def truncate(t, s):
    if len(t) <= s:
        return t
    else:
        return ' '.join(t[:s+1].split(' ')[0:-1])

# text writes a line of text to d
def text(d, x, y, t, s, c=foreground_yellow):
    f = ImageFont.truetype('PrimaSansMonoBT-Roman.otf', s)
    t = t.upper()
    t = unidecode.unidecode(t)
    (left, top, right, bottom) = f.getbbox(t)
    w = right - left
    h = bottom - top
    d.text((x, y+2), t, fill=c, font=f)
    return y + h + spacing

# draw_grid draws black lines that make it look like this is an LED
# display with gutters between letters
def draw_grid(d, y, s):
    f = ImageFont.truetype('PrimaSansMonoBT-Roman.otf', s)
    t = 'A'
    t = t.upper()
    (left, top, right, bottom) = f.getbbox(t)
    w = right - left
    h = bottom - top

    for y0 in range(y, 320-10, h + spacing):
        d.line([(xleft, y0), (480-4, y0)], fill=background, width=2)

    for x in range(xleft-1, 480-xleft, w):
        d.line([(x, y), (x, 320-10)], fill=background, width=1)

    d.rectangle([(xleft, 320-24), (480-xleft, 320-ytop)], fill=foreground_yellow)

    clock = time.strftime("%H:%M", time.localtime())
    text(d, 433, 293, clock, 12, background)
        
# add_line adds a line of text to the display putting the fields
# into aligned columns using the special fixed-width font
def add_line(d, y, airline, flight, city, code, alt):
    line = "%-18s  %-9.9s %-3.3s %-15s %8.8s" % (truncate(airline, 18), flight, code, truncate(city, 15), alt)
    y = text(d, xleft, y, line, 13)
    return y

# add_header adds the header to the display
def add_header(d, img, title, direction):
    y = text(d, xleft, ytop, title, 18, background)
    d.rectangle([(xleft, ytop), (480-xleft, y+spacing)], fill=foreground_yellow)
    line = "%-18s  %-9s %-19s %8s" % ("Airline", "Flight", direction, "Altitude")

    x = icon(img, title, xleft+2, ytop-2)
    
    y = text(d, x, ytop+1, "%s %s" % (AIRPORT, title), 18, background)
    y += spacing * 2

    y = text(d, xleft, y, line, 13, highlight)

    bbox = (xleft-1, y, 480-xleft+1, 320-15)
    d.rectangle(bbox, fill=background_yellow)
    d.line([(0, 0), (480, 0)], fill=highlight, width=2)
    d.line([(0, 0), (0, 320)], fill=highlight, width=2)
    d.line([(478, 0), (478, 320)], fill=highlight, width=2)
    d.line([(0, 318), (480, 318)], fill=highlight, width=2)

    return y

# screen_show takes an image in img and writes it to a file and then
# uses fbi to draw it to the screen
def screen_show(img):
    
    # This is done to prevent fbi from getting an error if it tries to
    # read one of the images it is displaying while we write it. It's
    # written to a temporary file and then mv'ed into place.
    
    img.save(screen_tmp)
#    subprocess.run('mv %s %s' % (screen_tmp, screen_file), shell=True)

    # Determine if there are any instance of fbi running. Start one if
    # there is not
#    running = []
#    try:
#        running = subprocess.check_output(['pgrep', 'fbi']).decode("utf-8").strip().split('\n')
#    except:
#        pass

#    if len(running) == 0:
#        subprocess.run('fbi -t 1 -T 2 -a -cachemem 0 -noverbose -d /dev/fb1 %s' % ' '.join(screen_links),
#                       shell=True)
    
# screen_start sets up the screen for use. The most important thing it
# does is create three symbolic links that are fed to fbi in
# screen_show. This is a trick to get fbi to cycle through images and
# allow a single fbi instance to updated smoothly.
def screen_start():
    subprocess.run(['pkill', 'fbcp'])
    
#    for l in screen_links:
#        subprocess.run(['ln -s %s %s' % (screen_file, l)], shell=True)

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

# altitude returns the altitude of the aircraft
def altitude(a):
    return int(a['alt'])

# city extracts the city from airport data
def city(a):
    return a[10]

# airport returns the airport data for an aircraft
# 4461,"LPPT","large_airport","Humberto Delgado Airport (Lisbon Portela Airport)",38.7813,-9.13592,374,"EU","PT","PT-11","Lisbon","yes","LPPT","LIS",,"http://www.ana.pt/en-US/Aeroportos/lisboa/Lisboa/Pages/HomeLisboa.aspx","https://en.wikipedia.org/wiki/Lisbon_Portela_Airport","Lisboa"
def airport(a):
    return findcsv('airports.csv', 13, a)

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
    # in required and are not on the ground and are either arriving at
    # or leaving from the airport being monitored.

    near = []
    for ac in j['ac']:
        ok = True
        for r in required:
            if r not in ac or ac[r].strip() == '':
                ok = False
                break
            
        if ok and ac['gnd'] == '0':
            from_ = city(airport(ac['from'][:4]))
            to_ = city(airport(ac['to'][:4]))
            if from_ == AIRPORT or to_ == AIRPORT:
                near.append(ac)

    # If there are aircraft then sort them by distance from the device
    # and then decide whether the nearest aircraft is arriving or
    # departing.
   
    if len(near) > 0:
        near.sort(key=distance)

        # If the closest aircraft is arriving at the chosen city
        # then show arrivals, otherwise show departures.
        
        closest = near[0]
        from_ = city(airport(closest['from'][:4]))
        arrivals = True
        if from_ == AIRPORT:
            arrivals = False

        img = Image.new('RGB', (480, 320), color = (0, 0, 0))
        d = ImageDraw.Draw(img)
        y = 0
            
        if arrivals:
            y = add_header(d, img, "Arrivals", "Arriving from")
        else: 
            y = add_header(d, img, "Departures", "Destination")

        ysave = y

        # Resort by altitude rather than distance as aircraft may be
        # turning to line up to the airport
        
        near.sort(key=altitude)

        for ac in near:
            flight = ac['call']
            airline = findcsv('airlines.dat', 4, ac['opicao'])[1]
            alt = altitude(ac)

            from_code = ac['from'][:4].strip()
            from_city = city(airport(from_code))
            to_code = ac['to'][:4].strip()
            to_city = city(airport(to_code))

            if (arrivals and to_city == AIRPORT):
                y = add_line(d, y, airline, flight, from_city, from_code, alt)
            if (not arrivals and from_city == AIRPORT):
                y = add_line(d, y, airline, flight, to_city, to_code, alt)

        draw_grid(d, ysave, 13)
        screen_show(img)
        
    update_delay = planes_delay

    
    
