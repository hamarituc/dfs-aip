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
from io import BytesIO
import json
import os
from PIL import Image
import re
import requests
import urllib.parse



# Die `removesuffix`-Methode gibt es es ab Python 3.9. So lange Python 3.8 noch
# nicht end of life ist, unterstützen wir diesen Quirk.
def removesuffix(s, suffix):
    if hasattr(s, 'removesuffix'):
        return s.removesuffix(suffix)

    if s.endswith(suffix):
        return s[:-len(suffix)]

    return s



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
        newentry['pageid'] = removesuffix(url.path.split('/')[-1], '.html').lower()

        if 'folder' in entry:
            newentry['folder'] = []
            component, title = self._parse_folder(entry, path)
            componentpage = None
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
                newentry['odd'] = bool(newentry['subpage'] % 2)
                componentpage += subpage

        if component is not None and not isinstance(component, tuple):
            component = ( component, )

        if componentpage is not None:
            if component is None:
                component = tuple()
            component += ( componentpage, )

        if path is None:
            path = tuple()

        elif component is not None:
            path += component
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

        # Unterabschnittsnummer in AIP IFR erkennen
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 2 and \
           path[0] in [ "GEN", "ENR", "AD" ]:
            match = re.fullmatch(r'(GEN|ENR|AD) [0-9]\.([0-9]+)( (.+))?', entry['name'])
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
        if self.toc_raw['type'] == 'VFR' and \
           path in [ ( "AD", ), ( "HEL AD", ) ]:
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

        # Militärische Plätzer in der AIP IFR behandeln
        if self.toc_raw['type'] == 'IFR' and \
           path == ( "AD", ):
            match = re.fullmatch(r'MIL-AD ([0-9])( (.+))?', entry['name'])
            if match:
                return ( 'MIL', match[1] ), match[3]

        # Überflüssigen Ordner "MIL-AD" eliminieren
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 3 and path[0] == "AD" and path[1] == "MIL":
            if path[2] == "1" and entry['name'] == "MIL-AD":
                return None, None

        # Anflugblätter behandeln
        if self.toc_raw['type'] == 'IFR' and \
           path in [ ( "AD", "2" ), ( "AD", "3" ), ( "AD", "MIL", "2" ) ]:
            # Der ICAO-Locator ist nicht im Titel kodiert. Wir müssen eine
            # Ebene absteigen.
            return entry['folder'][0]['name'].split()[2], entry['name']

        # Rundschreiben (AIC)
        if path == ( "AIC", ):
            # Jahresregister in der Navigation überspringen
            match = re.fullmatch(r'20[0-9][0-9]', entry['name'])
            if match:
                return None, None

            if self.toc_raw['type'] == 'VFR' and \
               entry['name'] == "AIC Prüfliste":
                return "Liste", "Prüfliste"

            match = re.fullmatch(r'AIC ([0-9][0-9]/[0-9][0-9]) (.+)', entry['name'])
            if match:
                return match[1], match[2]

        # Ergänzungen (SUP)
        if path == ( "SUP", ):
            # Jahresregister in der Navigation überspringen
            match = re.fullmatch(r'20[0-9][0-9]', entry['name'])
            if match:
                return None, None

            if self.toc_raw['type'] == 'VFR' and \
               entry['name'] == "SUP Liste der Ergänzungen":
                return "Liste", "Liste der Ergänzungen"

            match = re.fullmatch(r'SUP ([0-9][0-9]/[0-9][0-9]) (.+)', entry['name'])
            if match:
                return match[1], match[2]

        raise ValueError("Unerwarteter Abschnitt '%s' in Abschnitt '%s'" % ( entry['name'], " ".join(path) ))


    def _parse_page(self, entry, path):
        # Seitennummer der Textseiten in der AIP VFR bestimmen
        if self.toc_raw['type'] == 'VFR' and \
           len(path) == 2 and path[0] in [ "GEN", "ENR", "AD", "HEL AD" ]:
            match = re.fullmatch(r'(GEN|ENR|AD|HEL AD) ([0-9])[-\.]([0-9]+)([A-Za-z])?( (.+))?', entry['name'])

            if match:
                # Seite aus dem Flugplatzverzeichnis (AD 2) ignorieren, die
                # unterhalb der Platzkarten einsortiert sind.
                if path[1] != "2" and match[2] == "2":
                    return None, None, None, None

                return None, match[3], match[4], match[6]

            # Bei einigen VFR ADs fehlt Präfix "AD 2", z.B. (AIRAC 2023-12-14)
            #  - "AD 2-4 Ailertchen" (normal)
            #  - "5 Allstedt" (Spezialfall)
            if path[0] == "AD" and path[1] == "2":
                match = re.fullmatch(r'([0-9]+)([A-Za-z])? (.+)', entry['name'])
                if match:
                    return None, match[1], match[2], match[3]

        # Seitennummer der Textseiten in der AIP IFR bestimmen
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 3 and path[0] in [ "GEN", "ENR", "AD" ]:
            match = re.fullmatch(r'(GEN|ENR|AD) [0-9][\. ][0-9]+[- ]([0-9]+)([A-Za-z])?( (.+))?', entry['name'])

            if match:
                return None, match[2], match[3], match[5]

        # Seitnnummern der Textseiten im Abschnitt MIL-AD der AIP-IFR bestimmen
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 3 and path[0] == "AD" and path[1] == "MIL":
            match = re.fullmatch(r'MIL-AD [0-9]-([0-9]+)([A-Za-z])?( (.+))?', entry['name'])
            if match:
                return None, match[1], match[2], match[4]

        # Streckenverzeichnisse behandeln
        if self.toc_raw['type'] == 'IFR' and \
           path == ( "ENR", "3", "2" ):
            match = re.fullmatch(r'ENR 3\.2-([A-Z]+)-([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return match[1], match[2], match[3], match[1]

        # Streckenkarten haben keine Seitennummern
        if len(path) == 3 and path[0] == "ENR" and path[1] == "6":
            return None, "1", None, entry['name']

        # Flugplatzkarten behandeln
        if self.toc_raw['type'] == 'VFR' and \
           len(path) == 2 and path[0] == "AD":
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

        # Flugplatzkarten behandeln
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 3 and path[0] == "AD" and path[1] in [ "2", "3" ]:
            # einfache Nummierung: 1-1, 1-2, ..., 2-1, ...
            match = re.fullmatch(r'AD [23] E[DT][A-Z][A-Z] ([126])-([0-9]+)([A-Za-z])?( (.+))?', entry['name'])
            if match:
                return match[1], match[2], match[3], match[5]

            # geschachtelte Nummerierung: 1-1-1, 1-1-2, ..., 1-2-1, ..., 2-1-1, ...
            match = re.fullmatch(r'AD [23] E[DT][A-Z][A-Z] ([345])-([0-9]+)-([0-9]+)([A-Za-z])?( (.+))?', entry['name'])
            if match:
                return ( match[1], match[2] ), match[3], match[4], match[6]

        # Flugplatzkarten für Abschnitt "MIL-AD" behandeln
        if self.toc_raw['type'] == 'IFR' and \
           len(path) == 4 and path[0] == "AD" and path[1] == "MIL" and path[2] == "2":
            match = re.fullmatch(r'AD 2 E[DT][A-Z][A-Z] ([0-9])[- ]([0-9]+)([A-Za-z])?( (.+))?', entry['name'])
            if match:
                return match[1], match[2], match[3], match[5]

        # Helikopterplätze behandeln
        if self.toc_raw['type'] == 'VFR' and \
           len(path) == 2 and path[0] == "HEL AD":
            # Verzeichnis der Helikopterplätze
            match = re.fullmatch(r'HEL AD 3-([A-Z]+)-([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                # Seite aus dem Flugplatzverzeichnis (HEL AD 3) ignorieren, die
                # unterhalb der Platzkarten einsortiert sind.
                if path[1] != "3":
                    return None, None, None, None

                return match[1], match[2], match[3], match[1]

            # Anflugblätter
            match = re.fullmatch(r'(.+) ([0-9]+)([A-Za-z])?', entry['name'])
            if match:
                return None, match[2], match[3], match[1]

        # Rundschreiben (AIC)
        if len(path) == 2 and path[0] == "AIC":
            match = re.fullmatch(r'AIC( VFR| IFR)? .+(-|- | Seite | Page-)([0-9]+)', entry['name'])
            if match:
                return None, match[3], None, None

        # Ergänzungen (SUP)
        if len(path) == 2 and path[0] == "SUP":
            match = re.fullmatch(r'(LIST OF )?SUP( VFR)? .+(-| Seite | Page-)([0-9]+)( .+)?', entry['name'])
            if match:
                return None, match[4], None, None

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
            return list(self.index_num.values())

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

        filename = os.path.join(self.datadir, page['pageid'] + '.pdf')
        if not refresh and os.path.exists(filename):
            return filename

        print(page['name'])

        chapter = page['path'][0]
        if chapter == "HEL AD":
            chapter = "AD"

        url = urllib.parse.urlparse(page['href'])
        url = url.path.split('/')
        urlbase = url[1]
        pageid = removesuffix(url[-1], '.html')

        url = 'https://aip.dfs.de/%s/print/%s/%s/%s' % \
            (
                urlbase,
                chapter,
                pageid,
                urllib.parse.quote(page['name'])
            )

        # Seite abrufen
        response = requests.get(url, headers = { 'referer': page['href'] })
        response.raise_for_status()

        content_type = response.headers['content-type'].split(';')[0]
        if content_type == 'application/pdf':
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename

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
        mediastream = BytesIO(mediacontent)
        img = Image.open(mediastream)
        img.save(filename, resolution = 300, optimize = True)

        return filename
