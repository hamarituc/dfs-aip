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
import re
import requests

from .type import TYPES


#
# AIRAC-Datum bestimmen
#

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


def get_airac(aiptype):
    # Startseite abrufen
    response = requests.get(TYPES[aiptype]['url'])
    response.raise_for_status()

    # Startseite parsen
    soup = BeautifulSoup(response.content, 'html.parser')

    # Ausgabedatum bestimmen
    aip_airac = soup.find('div', class_ = 'subHeader').text.strip()
    aip_airac = re.fullmatch(r'Effective: ([0-9]{2}) ([A-Z]{3}) ([0-9]{4})', aip_airac)
    if not aip_airac:
        raise AssertionError("Kann Ausgabedatum des AIPs nicht bestimmen.")

    airac_month = aip_airac[2].upper()
    if airac_month not in _MONTHS:
        raise AssertionError("Ungültiger Monat '%s'", airac_month)
    airac_month = _MONTHS[airac_month]

    airac_day  = int(aip_airac[1])
    airac_year = int(aip_airac[3])

    return datetime.date(airac_year, airac_month, airac_day)
