#!/bin/env python3

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

import argparse

from aip.cache import AipCache



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

parser.add_argument(
    '--refresh',
    action = 'store_true',
    help = 'Aktualisierung des Caches erzwingen')

args = parser.parse_args()


cache = AipCache()
cache.fetch(args.type, debug = args.debug, refresh = args.refresh)
