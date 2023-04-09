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

import base64
from bs4 import BeautifulSoup
import json
import os
import re
import requests
import urllib.parse



class AipToc:
    def __init__(self, filename: str):
        with open(filename) as f:
            self.toc_raw = json.load(f)

        self.basedir = os.path.dirname(os.path.abspath(filename))
        self.datadir = os.path.join(self.basedir, 'data')
        try:
            os.mkdir(self.datadir)
        except FileExistsError:
            pass

        self.toc = self._parse(self.toc_raw)

        self.index_num = {}
        self.index_prefix = {}
        self._numerate(self.toc, 0)


    def _parse(self, entry, path = None):
        newentry = { k: v for k, v in entry.items() if not isinstance(v, list) }

        url = urllib.parse.urlparse(newentry['href'])
        newentry['pageid'] = url.path.split('/')[-1].removesuffix('.html').lower()

        if 'folder' in entry:
            newentry['folder'] = []
            component, title = self._parse_folder(entry, path)
        else:
            component, page, subpage, title = self._parse_page(entry, path)

            # Nicht zu berücksichtigende Seiten überspringen
            if page is None:
                return None

            if subpage is not None:
                subpage = subpage.upper()

            newentry['page'] = int(page)
            newentry['odd'] = bool(newentry['page'] % 2)
            componentpage = page

            if subpage is not None:
                newentry['subpage'] = ord(subpage[0]) - ord('A') + 1
                if newentry['odd']:
                    raise ValueError("Seitenangabe '%s' ist ungültig. Einschubseiten können nur auf eine gerade Seite folgen." % component)
                newentry['odd'] = bool(newentry['subpage'] % 2)
                componentpage += subpage

            if component is None:
                component = componentpage
            else:
                component = ( component, componentpage )

        if path is None:
            path = tuple()

        elif component is not None:
            if isinstance(component, tuple):
                path += component
            else:
                path += ( component, )

            newentry['path'] = path
            newentry['prefix'] = " ".join(path)

        if title is not None:
            newentry['title'] = title

        if 'folder' in entry:
            for nextentry in entry['folder']:
                newnextentry = self._parse(nextentry, path)
                if newnextentry is not None:
                    newentry['folder'].append(newnextentry)

        return newentry


    def _parse_folder(self, entry, path):
        # In der Wurzel ist nichts zu tun
        if path is None:
            return tuple(), None

        # Kapitel erkennen
        if path == tuple():
            match = re.fullmatch(r'(GEN|ENR|AD|HEL AD|AIC|SUP)( (.+))?', entry['name'])
            if match:
                return match[1], match[3]
            raise ValueError("Unerwartetes Kapitel '%s'" % entry['name'])

        # Abschnittsnummer erkennen
        if path in [ ( "GEN", ), ( "ENR", ), ( "AD", ), ( "HEL AD", ) ]:
            match = re.fullmatch(r'(GEN|ENR|AD|HEL AD) ([0-9])( (.+))?', entry['name'])
            if match:
                return match[2], match[4]

        # Den Verweis von der AIP-VFR auf die Streckenkarte in der AIP-IFR hart kodieren
        if self.toc_raw['type'] == 'VFR' and \
           path == ( "ENR", ) and \
           entry['name'].startswith("ENR Enroute Charts siehe AIP IFR"):
            return "6", "Streckenkarte"

        # Einzelne Unterordner für die Streckenkartenblätter überspringen
        if path == ( "ENR", "6" ):
            if entry['name'].endswith("Streckenkarte Oberer Luftraum"):
                return "UPPER", entry['name']
            if entry['name'].endswith("Streckenkarte Unterer Luftraum"):
                return "LOWER", entry['name']
            if entry['name'].endswith("Streckenkarte - Kursführungsmindesthöhenkarte"):
                return "MVA", entry['name']
            raise ValueError("Unerwartete Streckenkarte '%s'" % entry['name'])

        # Anflugblätter behandeln
        if self.toc_raw['type'] == 'VFR' and path in [ ( "AD", ), ( "HEL AD", ) ]:
            # Alphabetisches Register in der Navigation überspringen
            match = re.fullmatch(r'[A-Z](-[A-Z])?', entry['name'])
            if match:
                return None, None

            # Flugplätze mit ICAO-Locator
            match = re.match(r'(.+) (E[DT][A-Z][A-Z])', entry['name'])
            if match:
                return match[2], match[1]

            # Flugplätze ohne ICAO-Locator
            return entry['name'], entry['name']

        # Rundschreiben (AIC)
        if self.toc_raw['type'] == 'VFR' and path == ( "AIC", ):
            # Jahresregister in der Navigation überspringen
            match = re.fullmatch(r'20[0-9][0-9]', entry['name'])
            if match:
                return None, None

            if entry['name'] == "AIC Prüfliste":
                return "Liste", "Prüfliste"

            match = re.fullmatch(r'AIC ([0-9][0-9]/[0-9][0-9]) (.+)', entry['name'])
            if match:
                return match[1], match[2]

        # Ergänzungen (SUP)
        if self.toc_raw['type'] == 'VFR' and path == ( "SUP", ):
            # Jahresregister in der Navigation überspringen
            match = re.fullmatch(r'20[0-9][0-9]', entry['name'])
            if match:
                return None, None

            if entry['name'] == "SUP Liste der Ergänzungen":
                return "Liste", "Liste der Ergänzungen"

            match = re.fullmatch(r'SUP ([0-9][0-9]/[0-9][0-9]) (.+)', entry['name'])
            if match:
                return match[1], match[2]

        raise ValueError("Unerwarteter Abschnitt '%s' in Abschnitt '%s'" % ( entry['name'], " ".join(path) ))


    def _parse_page(self, entry, path):
        # Seitennummer der Textseiten bestimmen
        if len(path) == 2 and path[0] in [ "GEN", "ENR", "AD", "HEL AD" ]:
            match = re.fullmatch(r'(GEN|ENR|AD|HEL AD) ([0-9])-([0-9]+)([A-Za-z])?( (.+))?', entry['name'])

            if match:
                # Seite aus dem Flugplatzverzeichnis (AD 2) ignorieren, die
                # unterhalb der Platzkarten einsortiert sind.
                if path[1] != "2" and match[2] == "2":
                    return None, None, None, None

                return None, match[3], match[4], match[6]

        # Streckenkarten haben keine Seitennummern
        if len(path) == 3 and path[0] == "ENR" and path[1] == "6":
            return None, "1", None, entry['name']

        # Flugplatzkarten behandeln
        if len(path) == 2 and path[0] == "AD":
            # Terminal Chart mit Seitennummer
            match = re.fullmatch(r'E[DT][A-Z][A-Z] (.+) Terminal Chart ([0-9]+)', entry['name'])
            if match:
                return "TC", match[2], None, match[1] + " Terminal Chart"

            # Terminal Chart Vorderseite
            match = re.fullmatch(r'E[DT][A-Z][A-Z] (.+) Terminal Chart( Vorderseite)?', entry['name'])
            if match:
                return "TC", "1", None, match[1] + " Terminal Chart"

            # Terminal Chart Rückseite
            match = re.fullmatch(r'E[DT][A-Z][A-Z] (.+) Terminal Chart Rueckseite', entry['name'])
            if match:
                return "TC", "2", None, match[1] + " Terminal Chart"

            # Textseiten für Flugplatzkarten
            match = re.fullmatch(r'AD 3-(.+) ([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return None, match[2], match[3], match[1]

            # Anflugblätter
            match = re.fullmatch(r'(E[DT][A-Z][A-Z] )?(.+)[- ]([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return None, match[3], match[4], match[2]

        # Helikopterplätze behandeln
        if len(path) == 2 and path[0] == "HEL AD":
            # Verzeichnis der Helikopterplätze
            match = re.fullmatch(r'HEL AD 3-([A-Z])+-([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return None, match[2], match[3], match[1]

            # Anflugblätter
            match = re.fullmatch(r'(.+) ([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return None, match[2], match[3], match[1]

        # Rundschreiben (AIC)
        if self.toc_raw['type'] == 'VFR' and len(path) == 2 and path[0] == "AIC":
            match = re.fullmatch(r'AIC VFR .+(-| Seite | Page-)([0-9]+)', entry['name'])
            if match:
                return None, match[2], None, None

        # Ergänzungen (SUP)
        if self.toc_raw['type'] == 'VFR' and len(path) == 2 and path[0] == "SUP":
            match = re.fullmatch(r'(LIST OF )?SUP VFR .+(-| Seite | Page-)([0-9]+)( .+)?', entry['name'])
            if match:
                return None, match[3], None, None

        raise ValueError("Unerwartete Seite '%s' in Abschnitt '%s'" % ( entry['name'], " ".join(path) ))


    def _numerate(self, entry, num):
        if 'prefix' in entry:
            self.index_prefix[entry['prefix']] = entry

        if 'folder' not in entry:
            num += 1
            entry['num'] = num
            self.index_num[num] = entry
            return num

        lastnum = num
        for nextentry in entry['folder']:
            lastnum = self._numerate(nextentry, lastnum)

        if lastnum is None or lastnum == num:
            return None

        entry['numfirst'] = num + 1
        entry['numlast']  = lastnum

        return lastnum


    def filter(self, prefixes):
        if prefixes is None:
            return self.index_num.values()

        marker = []

        # Grenzen in Seitennummern auflösen
        for prefix in prefixes:
            if isinstance(prefix, tuple):
                prefixfirst, prefixlast = prefix
                if prefixfirst not in self.index_prefix:
                    raise KeyError("Unbekannter Abschnitt '%s'" % prefixfirst)
                if prefixlast not in self.index_prefix:
                    raise KeyError("Unbekannter Abschnitt '%s'" % prefixlast)

                entryfirst = self.index_prefix[prefixfirst]
                entrylast  = self.index_prefix[prefixlast]

                numfirst = entryfirst['numfirst'] if 'numfirst' in entryfirst else entryfirst['num']
                numlast  = entrylast['numlast']   if 'numlast'  in entrylast  else entrylast['num']
                if numfirst > numlast:
                    raise ValueError("Ungültiger Bereich '%s'-'%s'. Anfang muss vor dem Ende liegen." % ( prefixfirst, prefixlast ))

            else:
                if prefix not in self.index_prefix:
                    raise KeyError("Unbekannter Abschnitt '%s'" % prefix)

                entryfirst = self.index_prefix[prefix]
                entrylast  = entryfirst

            marker.append(( entryfirst['numfirst'] if 'numfirst' in entryfirst else entryfirst['num'],  1 ))
            marker.append(( entrylast['numlast']   if 'numlast'  in entrylast  else entrylast['num'],  -1 ))

        # Effektive Grenzen bestimmen (Marzullo-Algorithmus)
        marker.sort(key = lambda x : ( x[0], -x[1] ))
        count = 0
        currstart = None
        currstop  = None
        ranges = []

        for num, diff in marker:
            newcount = count + diff

            if count == 0 and newcount > 0:
                # Ein neues Intervall beginnt
                if currstop is None:
                    currstart = num

                elif currstop + 1 < num:
                    # Das alte Intervall abschließen und ein neues beginnen.
                    # Andernfalls verlängen wir ein bereits gefundenes
                    # Intervall schlicht.
                    ranges.append(( currstart, currstop ))
                    currstart = num

                currstop = None

            elif count > 0 and newcount == 0:
                # Das aktuelle Intervall endet. Wir fügen es aber noch nicht in
                # die Ergebnisliste ein, da ein Anschlussintervall folgen
                # könnte.
                currstop = num

            count = newcount

        if currstart is not None and currstop is not None:
            ranges.append(( currstart, currstop ))

        # Intervalle ausnormalisieren
        pages = []
        for start, stop in ranges:
            for num in range(start, stop + 1):
                pages.append(self.index_num[num])

        return pages


    def pairs(self, pages, pairs = False):
        # Ggf. Vor- und Rückseiten ergänzen
        pagepairs = []

        for pagecurr in pages:
            num = pagecurr['num']

            if pagecurr['odd']:
                pagenext = self.index_num[num + 1] if num < len(self.index_num) - 1 else None

                # Ist die Folgeseite gerade?
                if pagenext is not None and pagenext['odd']:
                    pagenext = None

                if pagenext in pages or pairs:
                    pagepairs.append(( pagecurr, pagenext ))
                else:
                    pagepairs.append(( pagecurr, None ))

            else:
                pageprev = self.index_num[num - 1] if num > 1 else None

                # Die gerade Seite haben wir bereits zusammen mit der ungeraden
                # Seite ausgegeben.
                if pageprev in pages:
                    continue

                # Ist die Vorgängerseite ungerade? Theoretisch muss zu jeder
                # geraden Seite eine ungerade Seite existieren. Aber wir prüfen
                # hier zur Sicherheit ab.
                if pageprev is not None and not pageprev['odd']:
                    pageprev = None

                if pairs:
                    pagepairs.append(( pageprev, pagecurr ))
                else:
                    pagepairs.append(( None, pagecurr ))

        return pagepairs


    def fetchthumbnail(self, page, refresh = False):
        if 'folder' in page:
            return None

        filename = os.path.join(self.datadir, page['pageid'] + '_thumb.png')
        if not refresh and os.path.exists(filename):
            return filename

        print(page['name'])

        # Seite abrufen
        response = requests.get(page['href'])
        response.raise_for_status()

        # Seite parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        soup = soup.find('main', class_ = 'container')
        soup = soup.find('img', class_ = 'pageImage')
        if soup is None:
            raise ValueError("Inhalt von Seite '%s' nicht bestimmbar" % page['name'])

        mediatype, mediacontent = soup['src'].split(',', maxsplit = 1)
        if mediatype != 'data:image/png;base64':
            raise ValueError("Unbekannter Medientyp '%s' auf Seite '%s'" % ( mediatype, page['name'] ))

        mediacontent = base64.b64decode(mediacontent)

        with open(filename, 'wb') as f:
            f.write(mediacontent)

        return filename


    def fetchpage(self, page, refresh = False):
        if 'folder' in page:
            return None

        basefilename = os.path.join(self.datadir, page['pageid'])
        if not refresh:
            if os.path.exists(basefilename + '.png'):
                return basefilename + '.png'
            if os.path.exists(basefilename + '.pdf'):
                return basefilename + '.pdf'

        print(page['name'])

        chapter = page['path'][0]
        if chapter == "HEL AD":
            chapter = "AD"

        url = urllib.parse.urlparse(page['href'])
        url = url.path.split('/')
        urlbase = url[1]
        pageid = url[-1].removesuffix('.html')

        url = 'https://aip.dfs.de/%s/print/%s/%s/%s' % \
            (
                urlbase,
                chapter,
                pageid,
                urllib.parse.quote(page['name'])
            )

        # Seite abrufen
        response = requests.get(url)
        response.raise_for_status()

        content_type = response.headers['content-type'].split(';')[0]
        if content_type == 'application/pdf':
            with open(basefilename + '.pdf', 'wb') as f:
                f.write(response.content)
            return basefilename + '.pdf'

        if content_type != 'text/html':
            raise ValueError("Unbekannter Medientyp '%s' für Seite '%s'" % ( response.headers['content-type'], page['name'] ))

        # Seite parsen
        soup = BeautifulSoup(response.content, 'html.parser')
        soup = soup.find('body')

        if soup is not None:
            soup = soup.find('div', class_ = 'pageAIP d-print-block')
        if soup is not None:
            soup = soup.find('img')
        if soup is None:
            raise ValueError("Inhalt von Seite '%s' nicht bestimmbar" % page['name'])

        mediatype, mediacontent = soup['src'].split(',', maxsplit = 1)
        if mediatype != 'data:image/png;base64':
            raise ValueError("Unbekannter Medientyp '%s' auf Seite '%s'" % ( mediatype, page['name'] ))

        mediacontent = base64.b64decode(mediacontent)

        with open(basefilename + '.png', 'wb') as f:
            f.write(mediacontent)

        return basefilename + '.png'
