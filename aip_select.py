#!/bin/env python3

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
for pdfname, ps in pdfs:
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
