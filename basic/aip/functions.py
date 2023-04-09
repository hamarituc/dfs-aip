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

import datetime

from .cache import AipCache
from .toc import AipToc



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


def prepare_pagepairs(args, pairs):
    prefixes = prepare_filter(args.filter)

    cache = AipCache(basedir = args.cache)
    airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    aiptype, airac, filename = cache.get(args.type, airac)
    toc = AipToc(filename)
    pages = toc.filter(prefixes)
    pagepairs = toc.pairs(pages, pairs = pairs)

    return toc, pagepairs


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


def page_show_filter(args, page, odd):
    line = ""

    if args.pairs:
        line += "V  " if odd else "H  "

    if page is None:
        line += "---"
    elif 'prefix' in page and 'title' in page:
        line += "%s:\t%s" % ( page['prefix'], page['title'] )
    elif 'prefix' in page:
        line += page['prefix']
    elif 'title' in page:
        line += page['title']
    else:
        line += page['name']

    if page is not None or args.pairs:
        print(line)


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
    toc, pagepairs = prepare_pagepairs(args, args.pairs)

    for pageodd, pageeven in pagepairs:
        page_show_filter(args, pageodd,  True)
        page_show_filter(args, pageeven, False)


def page_fetch(args):
    toc, pagepairs = prepare_pagepairs(args, args.pairs)

    for pageodd, pageeven in pagepairs:
        if pageodd is not None:
            toc.fetchpage(pageodd, refresh = args.refresh)
        if pageeven is not None:
            toc.fetchpage(pageeven, refresh = args.refresh)


def page_purge(args):
    pass
