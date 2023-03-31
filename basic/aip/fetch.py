#
# Copyright (C) 2022-2023 Mario Haustein, mario@mariohaustein.de
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

from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import requests
import urllib.parse
import xdg.BaseDirectory

from .airac import get_airac
from .type import TYPES



#
# Inhaltsverzeichnis erstellen
#
PERMAPATTERN = re.compile(r'const myPermalink = "(\S+)";')

def _fetch_folder(url: str):
    response = requests.get(url)
    response.raise_for_status()

    # Ggf. einem Meta-Redirect folgen
    while True:
        soup = BeautifulSoup(response.content, 'html.parser')
        metarefresh = soup.find('meta', attrs = { 'http-equiv': 'Refresh' })
        if not metarefresh:
            break

        url = metarefresh['content'].split(';')[1].strip().split('=', maxsplit = 1)[1]
        url = urllib.parse.urljoin(response.url, url)
        response = requests.get(url)
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

        entry = {}
        entry['href'] = url

        cls = e['class'][0]

        if cls == 'folder-link':
            entry['name'] = e.find('span', class_ = 'folder-name', lang = 'de').text.strip()

        elif cls == 'document-link':
            entry['name'] = e.find('span', class_ = 'document-name', lang = 'de').text.strip()

        else:
            continue

        if cls == 'folder-link':
            entry.update(_fetch_folder(url))

        result['folder'].append(entry)

    return result



def get_toc(aiptype: str, fetch : bool = False, airac: datetime.date = None, basedir = None):
    # Cache-Verzeichnis anlegen
    if basedir is None:
        basedir = xdg.BaseDirectory.save_cache_path('dfs-aip')

    if airac is None:
        airac = get_airac(aiptype)

    airac_string = airac.isoformat()

    # Cache für die AIP-Ausgabe anlegen
    cachedir = os.path.join(basedir, '%s-%s' % (aiptype, airac_string))
    try:
        os.mkdir(cachedir)
    except FileExistsError:
        pass

    tocpath = os.path.join(cachedir, 'toc.json')

    try:
        with open(tocpath) as f:
            toc = json.load(f)

        if toc['airac'] != airac_string:
            raise AssertionError("AIRAC-Datum '%s' des Inhaltsverzeichnisses '%s' stimmt nicht mit dem Datum der Webseite '%s' überein." % ( toc['airac'], tocpath, airac_string ))

    except FileNotFoundError:
        if not fetch:
            raise ValueError("AIP-Ausgabe '%s' ist nicht im Cache." % airac_string)

        # AIRAC-Datum prüfen
        if airac != get_airac(aiptype):
            raise AssertionError("AIP-Ausgabe '%s' ist weder im Cache noch die aktuelle Ausgabe. Download nicht möglich." % airac_string)

        toc = {}
        toc['type'] = aiptype
        toc['airac'] = airac_string
        toc.update(_fetch_folder(TYPES[aiptype]['url']))

        with open(tocpath, 'w') as f:
            json.dump(toc, f, indent = 2)

    return toc
