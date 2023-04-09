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
import datetime

from aip.cache import AipCache
from aip.toc import AipToc



def prepare_filter(filterarray):
    prefixes = []

    if filterarray is None:
        return None

    for f in filterarray:
        fsplit = f.split('-')
        if len(fsplit) == 1:
            prefixes.append(( fsplit[0].strip(), fsplit[0].strip() ))
        elif len(fsplit) == 2:
            prefixes.append(( fsplit[0].strip(), fsplit[1].strip() ))
        else:
            raise ValueError("Ungültiger Filterausdruck '%s'" % f)

    return prefixes


def page_list_tree(entry, show, indent = []):
    line = ""

    if show['num']:
        if 'folder' in entry:
            line += "%4d - %4d " % ( entry['numfirst'], entry['numlast'] )
        else:
            line += "    %4d    " % ( entry['num'] )

    if show['folder'] and show['tree']:
        for idx, last in enumerate(indent):
            if idx + 1 >= len(indent):
                line += "+- "
            elif last:
                line += "   "
            else:
                line += "|  "

    if show['prefix']:
        if 'prefix' in entry:
            line += entry['prefix']
        if show['title'] and 'title' in entry:
            line += ": "

    if show['title'] and 'title' in entry:
        line += entry['title']

    if (show['prefix'] or show['title']) and \
       'prefix' not in entry and \
       'title' not in entry:
        line += entry['name']

    if show['folder'] and 'folder' in entry or \
       show['pages'] and 'folder' not in entry:
        print(line)

    if 'folder' in entry:
        for idx, e in enumerate(entry['folder']):
            page_list_tree(e, show, indent = indent + [ idx + 1 >= len(entry['folder']) ])



def toc_fetch(args):
    cache = AipCache(basedir = args.cache)
    cache.fetch(args.type, debug = True, refresh = args.refresh)


def toc_list(args):
    if args.vfr == args.ifr:
        filtertype = None
    elif args.vfr:
        filtertype = 'VFR'
    elif args.ifr:
        filtertype = 'IFR'
    else:
        filtertype = None

    cache = AipCache(basedir = args.cache)
    for aiptype, airac, filename in cache.list(filtertype):
        print("%3s  %s  %s" % ( aiptype, airac.isoformat(), filename ))


def toc_delete(args):
    pass


def page_list(args):
    cache = AipCache(basedir = args.cache)
    airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    aiptype, airac, filename = cache.get(args.type, airac)
    toc = AipToc(filename)

    show = \
    {
        'num':    args.num,
        'tree':   args.tree,
        'prefix': args.prefix,
        'title':  args.title,
        'folder': args.folder,
        'pages':  args.pages,
    }

    if not (show['prefix'] or show['title']):
        show['tree']   = True
        show['prefix'] = True
        show['title']  = True

    if not (show['folder'] or show['pages']):
        show['folder'] = True
        show['pages']  = True

    page_list_tree(toc.toc, show)


def page_filter(args):
    prefixes = prepare_filter(args.filter)

    cache = AipCache(basedir = args.cache)
    airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    aiptype, airac, filename = cache.get(args.type, airac)
    toc = AipToc(filename)
    pages = toc.filter(prefixes)

    if args.pairs:
        page_pairs(toc.pairs(pages, pairs = True))
        return

    for p in pages:
        if 'prefix' in p and 'title' in p:
            print("%s:\t%s" % ( p['prefix'], p['title'] ))
        elif 'prefix' in p:
            print(p['prefix'])
        elif 'title' in p:
            print(p['title'])
        else:
            print(p['name'])


def page_pairs(pagepairs):
    for podd, peven in pagepairs:
        if podd is None:
            print("V  ---")
        elif 'prefix' in podd:
            print("V  %s" % podd['prefix'])
        else:
            print("V  %s" % podd['name'])

        if peven is None:
            print("R  ---")
        elif 'prefix' in peven:
            print("R  %s" % peven['prefix'])
        else:
            print("R  %s" % peven['name'])


def page_fetch(args):
    prefixes = prepare_filter(args.filter)

    cache = AipCache(basedir = args.cache)
    airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    aiptype, airac, filename = cache.get(args.type, airac)
    toc = AipToc(filename)
    pages = toc.filter(prefixes)
    pages = toc.pairs(pages)

    for pageodd, pageeven in pages:
        if pageodd is not None:
            toc.fetchpage(pageodd, refresh = args.refresh)
        if pageeven is not None:
            toc.fetchpage(pageeven, refresh = args.refresh)


def page_purge(args):
    pass



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
parse_airac(command_page_filter)
parse_filter(command_page_filter)
parse_pairs(command_page_filter, "Vorder- und Rückseiten anzeigen")

command_page_filter.set_defaults(func = page_filter)


command_page_fetch = commands_page.add_parser(
    'fetch',
    description = "Seiten herunterladen")

parse_type(command_page_fetch)
parse_refresh(command_page_fetch)
parse_airac(command_page_fetch)
parse_filter(command_page_fetch)
parse_pairs(command_page_fetch, "Zugehörige Vorder- bzw. Rückseiten herunterladen")

command_page_fetch.set_defaults(func = page_fetch)


command_page_purge = commands_page.add_parser(
    'purge',
    description = "Überflüssige Seiten löschen")

command_page_purge.set_defaults(func = page_purge)


args = parser.parse_args()

args.func(args)
