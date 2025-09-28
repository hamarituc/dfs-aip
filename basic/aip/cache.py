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



class AipCache:
    _TYPES = \
    {
        'VFR':
        {
            'url': 'https://aip.dfs.de/BasicVFR/',
        },
        'IFR':
        {
            'url': 'https://aip.dfs.de/BasicIFR/',
        },
    }

    _MONTHS = \
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

    _PERMAPATTERN = re.compile(r'const myPermalink = "(\S+)";')


    def __init__(self, basedir = None):
        if basedir is None:
            self.basedir = xdg.BaseDirectory.save_cache_path('dfs-aip')
        else:
            self.basedir = basedir


    #
    # Aktuelles AIRAC-Datum abrufen
    #
    def current_airac(self, aiptype):
        # Startseite abrufen
        response = requests.get(self._TYPES[aiptype]['url'], headers = { 'User-Agent': 'AIP Download Tool' })
        response.raise_for_status()

        # Startseite parsen
        soup = BeautifulSoup(response.content, 'html.parser')

        # Ausgabedatum bestimmen
        aip_airac = soup.find('div', class_ = 'subHeader').text.strip()
        aip_airac = re.fullmatch(r'Effective: ([0-9]{2}) ([A-Z]{3}) ([0-9]{4})', aip_airac)
        if not aip_airac:
            raise AssertionError("Kann Ausgabedatum des AIPs nicht bestimmen.")

        airac_month = aip_airac[2].upper()
        if airac_month not in self._MONTHS:
            raise AssertionError("Ungültiger Monat '%s'", airac_month)
        airac_month = self._MONTHS[airac_month]

        airac_day  = int(aip_airac[1])
        airac_year = int(aip_airac[3])

        return datetime.date(airac_year, airac_month, airac_day)


    #
    # Alle AIP-Inhaltsverzeichnisse auflisten
    #
    def list(self, aiptype):
        result = []

        for entry in os.scandir(self.basedir):
            if not entry.is_file():
                continue
            if not entry.name.endswith('.json'):
                continue

            path = os.path.abspath(os.path.join(self.basedir, entry.name))

            with open(entry) as f:
                toc = json.load(f)

                if aiptype is not None and toc['type'] != aiptype:
                    continue

                result.append(( toc['type'], datetime.date.fromisoformat(toc['airac']), path ))

        result.sort(key = lambda x : ( x[1], x[0] ), reverse = True)

        return result


    #
    # Inhaltsverzeichnis anhand von Typ und ggf. AIRAC-Datum bestimmen
    #
    def get(self, aiptype, airac = None):
        for _aiptype, _airac, filename in self.list(aiptype):
            if airac is None or airac == _airac:
                return ( _aiptype, _airac, filename )

        return None


    #
    # AIP-Inhaltsverzeichnis herunterladen
    #
    def fetch(self, aiptype: str, debug: bool = False, refresh: bool = False):
        airac = self.current_airac(aiptype)
        airac_string = airac.isoformat()
        tocpath = os.path.join(self.basedir, '%s-%s.json' % ( aiptype, airac_string ))

        if os.path.exists(tocpath) and not refresh:
            return

        toc = {}
        toc['type'] = aiptype
        toc['version'] = 1
        toc['airac'] = airac_string
        toc['name'] = 'AIP %s' % aiptype
        toc.update(self._fetch_folder(self._TYPES[aiptype]['url'], debug = debug))

        with open(tocpath, 'w') as f:
            json.dump(toc, f, indent = 2)

        return ( aiptype, airac, tocpath )


    #
    # Einen Unterordner herunterladen
    #
    def _fetch_folder(self, url: str, depth: int = 0, debug: bool = False):
        response = requests.get(url, headers = { 'User-Agent': 'AIP Download Tool' })
        response.raise_for_status()

        # Ggf. einem Meta-Redirect folgen
        while True:
            soup = BeautifulSoup(response.content, 'html.parser')
            metarefresh = soup.find('meta', attrs = { 'http-equiv': 'Refresh' })
            if not metarefresh:
                break

            url = metarefresh['content'].split(';')[1].strip().split('=', maxsplit = 1)[1]
            url = urllib.parse.urljoin(response.url, url)
            response = requests.get(url, headers = { 'User-Agent': 'AIP Download Tool' })
            response.raise_for_status()

        result = {}

        # URL
        result['href'] = response.url

        # Permalink
        permalink = self._PERMAPATTERN.search(response.content.decode())
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
                if debug:
                    print(depth * "  " + entry['name'])
                entry.update(self._fetch_folder(url, depth = depth + 1, debug = debug))

            result['folder'].append(entry)

        return result


    #
    # Cache leeren
    #
    def purge(self):
        #
        # TODO
        #
        # - Alle Inhaltsverzeichnisse einlesen.
        # - Menge aller referenzierten Files bestimmen.
        # - Über Datenverzeichnis iterieren und Files außerhalb der obigen Menge löschen.
        #
        pass
