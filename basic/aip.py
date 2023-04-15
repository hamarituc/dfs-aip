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

from aip.functions import toc_fetch
from aip.functions import toc_list
from aip.functions import toc_delete
from aip.functions import page_list
from aip.functions import page_filter
from aip.functions import page_fetch
from aip.functions import page_purge
from aip.functions import pdf_summary



def parse_type(parser):
    group = parser.add_mutually_exclusive_group(required = True)

    group.add_argument(
        '--vfr',
        action = 'store_const',
        dest = 'type',
        const = 'VFR',
        help = "AIP VFR")

    group.add_argument(
        '--ifr',
        action = 'store_const',
        dest = 'type',
        const = 'IFR',
        help = "AIP IFR")


def parse_type_multi(parser):
    group = parser.add_argument_group("Typ")

    group.add_argument(
        '--vfr',
        action = 'store_true',
        help = "AIP VFR")

    group.add_argument(
        '--ifr',
        action = 'store_true',
        help = "AIP IFR")


def parse_refresh(parser):
    parser.add_argument(
        '-r', '--refresh',
        action = 'store_true',
        help = "Aktualisierung des Caches erzwingen")


def parse_baseairac(parser, required = False):
    parser.add_argument(
        '-b', '--base-airac',
        required = required,
        type = str,
        metavar = "YYYY-MM-DD",
        help = "AIRAC-Bezugsdatum für Änderungsdokumente")


def parse_airac(parser):
    parser.add_argument(
        '-a', '--airac',
        type = str,
        metavar = "YYYY-MM-DD",
        help = "AIRAC-Datum")


def parse_filter(parser):
    parser.add_argument(
        '-f', '--filter',
        type = str,
        metavar = "Abschnit || von-bis",
        nargs = '+',
        help = "Filter")


def parse_pairs(parser, help):
    parser.add_argument(
        '--pairs',
        action = 'store_true',
        help = help)



parser = argparse.ArgumentParser(
        description = "Zugriff auf das Luftfahrthandbuch AIP"
    )

parser.add_argument(
    '-c', '--cache',
    type = str,
    metavar = "DIR",
    help = "Cache-Verzeichnis")


commands = parser.add_subparsers(required = True)


command_toc = commands.add_parser(
    'toc',
    description = "Inhaltsverzeichnisse verwalten")

commands_toc = command_toc.add_subparsers(required = True)


commands_toc_fetch = commands_toc.add_parser(
    'fetch',
    description = "Inhaltsverzeichnis herunterladen")

parse_type(commands_toc_fetch)
parse_refresh(commands_toc_fetch)

commands_toc_fetch.set_defaults(func = toc_fetch)


command_toc_list = commands_toc.add_parser(
    'list',
    description = "Inhaltsverzeichnisse anzeigen")

parse_type_multi(command_toc_list)

command_toc_list.set_defaults(func = toc_list)


command_toc_delete = commands_toc.add_parser(
    'delete',
    description = "Inhaltsverzeichnis löschen")

parse_type(command_toc_delete)
parse_airac(command_toc_delete)

command_toc_delete.set_defaults(func = toc_delete)


command_page = commands.add_parser(
    'page',
    description = "Seiten verwalten")

commands_page = command_page.add_subparsers(required = True)


command_page_list = commands_page.add_parser(
    'list',
    description = "Seiten anzeigen")

parse_type(command_page_list)
parse_airac(command_page_list)

command_page_list.add_argument(
    '--folder',
    action = 'store_true',
    help = "Abschnitte anzeigen")

command_page_list.add_argument(
    '--pages',
    action = 'store_true',
    help = "Seiten anzeigen")

command_page_list.add_argument(
    '--num',
    action = 'store_true',
    help = "Interne Seitennummerierung anzeigen")

command_page_list.add_argument(
    '--tree',
    action = 'store_true',
    help = "Baumstruktur anzeigen")

command_page_list.add_argument(
    '--prefix',
    action = 'store_true',
    help = "Präfix anzeigen")

command_page_list.add_argument(
    '--title',
    action = 'store_true',
    help = "Titel anzeigen")

command_page_list.set_defaults(func = page_list)


command_page_filter = commands_page.add_parser(
    'filter',
    description = "Seiten auswählen")

parse_type(command_page_filter)
parse_baseairac(command_page_filter)
parse_airac(command_page_filter)
parse_filter(command_page_filter)
parse_pairs(command_page_filter, "Vorder- und Rückseiten anzeigen")

command_page_filter.set_defaults(func = page_filter)


command_page_fetch = commands_page.add_parser(
    'fetch',
    description = "Seiten herunterladen")

parse_type(command_page_fetch)
parse_refresh(command_page_fetch)
parse_baseairac(command_page_fetch)
parse_airac(command_page_fetch)
parse_filter(command_page_fetch)
parse_pairs(command_page_fetch, "Zugehörige Vorder- bzw. Rückseiten herunterladen")

command_page_fetch.set_defaults(func = page_fetch)


command_page_purge = commands_page.add_parser(
    'purge',
    description = "Überflüssige Seiten löschen")

command_page_purge.set_defaults(func = page_purge)


command_pdf = commands.add_parser(
    'pdf',
    description = "Zusammenfassung als PDF exportieren")

command_pdf.add_argument(
    '--output',
    metavar = 'FILE',
    type = str,
    required = True,
    help = 'Ausgabedatei')

commands_pdf = command_pdf.add_subparsers(required = True)


command_pdf_summary = commands_pdf.add_parser(
    'summary',
    description = "Einfache Zusammenfassung erstellen")

parse_type(command_pdf_summary)
parse_refresh(command_pdf_summary)
parse_baseairac(command_pdf_summary)
parse_airac(command_pdf_summary)
parse_filter(command_pdf_summary)
parse_pairs(command_pdf_summary, "Vorder- und Rückseiten für Duplex-Druck ausgeben")

command_pdf_summary.set_defaults(func = pdf_summary)



args = parser.parse_args()

args.func(args)
