#!/bin/env python3

#
# Copyright (C) 2021 Mario Haustein, mario@mariohaustein.de
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
import pikepdf

from aip import load_pages



parser = argparse.ArgumentParser(
        description = "Seiten aus PDFs extrahieren"
    )

parser.add_argument(
    '--output',
    metavar = 'FILE',
    type = str,
    required = True,
    help = 'Ausgabedatei')

parser.add_argument(
    '--modulus',
    metavar = 'N',
    type = int,
    default = 1,
    help = 'Zwischen einzelnen PDF-Dateien auf nächstes Vielfaches von N auffüllen')

parser.add_argument(
    'pdfs',
    metavar = 'PDF [PAGESPEC]',
    type = str,
    nargs = '+',
    help = 'PDF-Dateien')

args = parser.parse_args()



outpdf = pikepdf.Pdf.new()

pdfs = load_pages(args.pdfs)
for pdfname, ps, _ in pdfs:
    lastpage = None
    blankpages = 0

    ps.extend((-len(ps) % args.modulus) * [ None ])

    for p in ps:
        if p is None:
            if lastpage is None:
                blankpages += 1
            else:
                width  = abs(lastpage.trimbox[2] - lastpage.trimbox[0])
                height = abs(lastpage.trimbox[3] - lastpage.trimbox[1])
                outpdf.add_blank_page(page_size = ( width, height ))

            continue

        lastpage = pikepdf.Page(p)

        if blankpages:
            for i in range(blankpages):
                width  = abs(lastpage.trimbox[2] - lastpage.trimbox[0])
                height = abs(lastpage.trimbox[3] - lastpage.trimbox[1])
                outpdf.add_blank_page(page_size = ( width, height ))
            blankpages = 0

        outpdf.pages.append(p)

outpdf.save(args.output)
