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

#from bs4 import BeautifulSoup
#import copy
#import datetime
import json
#import os
import re
#import requests
#import urllib.parse
#import xdg.BaseDirectory



class AipToc:
    def __init__(self, filename: str):
        with open(filename) as f:
            self.toc_raw = json.load(f)

        self.toc = self._parse(self.toc_raw)


    def _parse(self, entry, path = None):
        newentry = { k: v for k, v in entry.items() if not isinstance(v, list) }

        if 'folder' in entry:
            newentry['folder'] = []
            component, title = self._parse_folder(entry, path)
        else:
            component, page, subpage, title = self._parse_page(entry, path)

            # Nicht zu berücksichtigende Seiten überspringen
            if page is None:
                return None

            newentry['page'] = int(page)
            newentry['odd'] = bool(newentry['page'] % 2)
            componentpage = page

            if subpage is not None:
                newentry['subpage'] = ord(subpage.upper()[0]) - ord('A')
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

                return None, match[3], match[4], match[5]

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


    def _filter_ad_charts(self):
        pass


    def _numerate(self):
        pass


    def _ranges(self):
        pass


    def filter(self):
        pass


    def fetchpage(self):
        pass


#def filter_toc(toc, aiptype: str, prefix = None):
#    if prefix is None:
#        result = []
#        for entry in toc['folder']:
#
#    pass
