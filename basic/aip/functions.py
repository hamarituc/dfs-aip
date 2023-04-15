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
import pikepdf

from .cache import AipCache
from .toc import AipToc
from .page import page_amdt



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

    if args.base_airac is not None:
        base_airac = datetime.date.fromisoformat(args.base_airac)
        _, base_airac, base_filename = cache.get(args.type, base_airac)
        base_toc = AipToc(base_filename)
        base_pages = base_toc.filter(prefixes)

        pagesdiff = page_amdt(base_pages, pages)
        pages = [ ptarget for pbase, ptarget in pagesdiff if ptarget is not None ]

    pagepairs = toc.pairs(pages, pairs = pairs)

    return toc, pagepairs


def page_tree_show(entry, show, indent = []):
    if not ('folder' in entry or show['pages']):
        return

    line = ""

    if show['num']:
        if 'folder' in entry:
            line += "%4d - %4d " % ( entry['numfirst'], entry['numlast'] )
        else:
            line += "    %4d    " % ( entry['num'] )

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

    print(line)

    if 'folder' in entry:
        for idx, e in enumerate(entry['folder']):
            page_tree_show(e, show, indent = indent + [ idx + 1 >= len(entry['folder']) ])


def page_list_show(args, page, odd):
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


def page_tree(args):
    cache = AipCache(basedir = args.cache)
    airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    aiptype, airac, filename = cache.get(args.type, airac)
    toc = AipToc(filename)

    show = \
    {
        'num':    args.num,
        'prefix': args.prefix,
        'title':  args.title,
        'pages':  not args.only_folder,
    }

    if not (show['prefix'] or show['title']):
        show['prefix'] = True
        show['title']  = True

    page_tree_show(toc.toc, show)


def page_list(args):
    toc, pagepairs = prepare_pagepairs(args, args.pairs)

    for pageodd, pageeven in pagepairs:
        page_list_show(args, pageodd,  True)
        page_list_show(args, pageeven, False)


def page_fetch(args):
    toc, pagepairs = prepare_pagepairs(args, args.pairs)

    for pageodd, pageeven in pagepairs:
        if pageodd is not None:
            toc.fetchpage(pageodd, refresh = args.refresh)
        if pageeven is not None:
            toc.fetchpage(pageeven, refresh = args.refresh)


def page_diff(args):
    prefixes = prepare_filter(args.filter)

    cache = AipCache(basedir = args.cache)

    target_airac = None if args.airac is None else datetime.date.fromisoformat(args.airac)
    _, target_airac, target_filename = cache.get(args.type, target_airac)
    target_toc = AipToc(target_filename)
    target_pages = target_toc.filter(prefixes)

    base_airac = datetime.date.fromisoformat(args.base_airac)
    _, base_airac, base_filename = cache.get(args.type, base_airac)
    base_toc = AipToc(base_filename)
    base_pages = base_toc.filter(prefixes)

    pagesdiff = page_amdt(base_pages, target_pages)

    for pbase, ptarget in pagesdiff:
        if pbase is None:
            line = "++ hinzugefügt  %s" % ptarget['prefix']
        elif ptarget is None:
            line = "-- gelöscht     %s" % pbase['prefix']
        else:
            line = "** geändert     %s" % ptarget['prefix']

        print(line)


def page_purge(args):
    pass


def pdf_summary(args):
    toc, pagepairs = prepare_pagepairs(args, args.pairs)

    out = pikepdf.Pdf.new()

    for pageodd, pageeven in pagepairs:
        if pageodd is None:
            pdfodd = None
            boxodd = None
        else:
            fileodd = toc.fetchpage(pageodd, refresh = args.refresh)
            pdfodd = pikepdf.Pdf.open(fileodd)
            boxodd = pdfodd.pages[0].trimbox

        if pageeven is None:
            pdfeven = None
            boxeven = None
        else:
            fileeven = toc.fetchpage(pageeven, refresh = args.refresh)
            pdfeven = pikepdf.Pdf.open(fileeven)
            boxeven = pdfeven.pages[0].mediabox

        if pageodd is not None:
            out.pages.append(pdfodd.pages[0])
        elif args.pairs:
            out.add_blank_page(page_size = ( abs(boxeven[2] - boxeven[0]), abs(boxeven[3] - boxeven[1]) ))

        if pageeven is not None:
            out.pages.append(pdfeven.pages[0])
        elif args.pairs:
            out.add_blank_page(page_size = ( abs(boxodd[2] - boxodd[0]), abs(boxodd[3] - boxodd[1]) ))

    out.save(args.output)
