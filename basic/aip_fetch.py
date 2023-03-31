#!/bin/env python3

#
# Copyright (C) 2022 Mario Haustein, mario@mariohaustein.de
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import argparse
from bs4 import BeautifulSoup
import datetime
import json
import re
import requests
import urllib.parse



parser = argparse.ArgumentParser(
        description = "AIP-Daten herunterladen"
    )

type_group = parser.add_mutually_exclusive_group(required = True)

type_group.add_argument(
    '--vfr',
    action = 'store_const',
    dest = 'type',
    const = 'VFR',
    help = 'AIP VFR')

type_group.add_argument(
    '--ifr',
    action = 'store_const',
    dest = 'type',
    const = 'IFR',
    help = 'AIP IFR')

parser.add_argument(
    '--debug',
    action = 'store_true',
    help = 'Debug-Ausgabe erzeugen')

args = parser.parse_args()


TYPES = \
{
    'VFR': 'https://aip.dfs.de/basicVFR',
    'IFR': 'https://aip.dfs.de/basicIFR',
}

# Startseite abrufen
response = requests.get(TYPES[args.type])
response.raise_for_status()
BASEURL = response.url


# Startseite parsen
soup = BeautifulSoup(response.content, 'html.parser')


# Ausgabedatum bestimmen
aip_airac = soup.find('div', class_ = 'subHeader').text.strip()
aip_airac = re.fullmatch(r'Effective: ([0-9]{2}) ([A-Z]{3}) ([0-9]{4})', aip_airac)
if not aip_airac:
    raise AssertionError("Kann Ausgabedatum des AIPs nicht bestimmen.")

MONTHS = \
{
  'JAN':  1,
  'FEB':  2,
  'MAR':  3,
  'APR':  4,
  'MAY':  5,
  'JUN':  6,
  'JUL':  7,
  'AUG':  8,
  'SEP':  9,
  'OCT': 10,
  'NOV': 11,
  'DEC': 12,
}

airac_month = aip_airac[2].upper()
if airac_month not in MONTHS:
    raise AssertionError("Ungültiger Monat '%s'", airac_month)
airac_month = MONTHS[airac_month]

airac_day  = int(aip_airac[1])
airac_year = int(aip_airac[3])

AIRAC_DATE = datetime.date(airac_year, airac_month, airac_day)


#
# Inhaltsverzeichnis erstellen
#
PERMAPATTERN = re.compile(r'const myPermalink = "(\S+)";')

def fetch_folder(url, hrefindex = {}, session = requests):
    response = session.get(url)
    response.raise_for_status()

    # Ggf. einem Meta-Redirect folgen
    while True:
        soup = BeautifulSoup(response.content, 'html.parser')
        metarefresh = soup.find('meta', attrs = { 'http-equiv': 'Refresh' })
        if not metarefresh:
            break

        url = metarefresh['content'].split(';')[1].strip().split('=', maxsplit = 1)[1]
        url = urllib.parse.urljoin(response.url, url)
        response = session.get(url)
        response.raise_for_status()


    result = {}

    # URL
    result['href'] = url

    # Permalink
    permalink = PERMAPATTERN.search(response.content.decode())
    if permalink:
        permaurl = urllib.parse.urlparse(response.url)
        permaurl = permaurl._replace(path = '/' + permaurl.path.split('/')[1])
        result['permalink'] = permaurl.geturl() + '/' + permalink[1]


    # Über alle Einträge iterieren. Nur die erste Liste auswerten. Auf der
    # Startseite gibt es mehrere Listen, aber dort interessiert uns nur die
    # erste.
    result['folder'] = []

    soup = soup.find('main', class_ = 'container')
    soup = soup.find('ul')
    soup = soup.find_all('a')

    for e in soup:
        url = urllib.parse.urljoin(response.url, e['href'])

        # Jede seite nur einmal im Index verzeichnen. Die VFR-Platzkarten
        # enthalten einen zusätzlichen Verweis auf das entsprechende Blatt in
        # AD 2.
        if url in hrefindex:
            continue
        hrefindex[url] = True

        entry = {}
        entry['href'] = url

        cls = e['class'][0]

        if cls == 'folder-link':
            entry['name'] = e.find('span', class_ = 'folder-name', lang = 'de').text.strip()

        elif cls == 'document-link':
            entry['name'] = e.find('span', class_ = 'document-name', lang = 'de').text.strip()

        else:
            continue

        if args.debug:
            print(entry['name'])

        if cls == 'folder-link':
            entry.update(fetch_folder(url, hrefindex = hrefindex, session = session))

        result['folder'].append(entry)

    return result


airac_string = AIRAC_DATE.isoformat()
toc_file = '%s.json' % airac_string

try:
    with open(toc_file) as f:
        toc = json.load(f)

    if toc['airac'] != airac_string:
        raise AssertionError("AIRAC-Datum '%s' des Inhaltsverzeichnisses '%s' stimmt nicht mit dem Datum der Webseite '%s' überein." % ( toc['airac'], toc_file, airac_string ))

except FileNotFoundError:
    toc = {}
    toc['type'] = args.type
    toc['airac'] = airac_string
    toc.update(fetch_folder(BASEURL, session = requests.Session()))

    with open(toc_file, 'w') as f:
        json.dump(toc, f, indent = 2)


#
# TODO: Seiten herunterladen
#

# def fetch_docurl(url):
#     response = requests.get(url)
#     response.raise_for_status()
# 
#     soup = BeautifulSoup(response.content, 'html.parser')
#     soup = soup.find('header')
#     soup = soup.find('a', target = '_blank')
# 
#     return soup['href']
