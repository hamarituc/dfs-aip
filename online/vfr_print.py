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
import sys

from aip import load_pages



parser = argparse.ArgumentParser(
        description = "AIP-PDFs für Druck ausschießen"
    )

parser.add_argument(
    '--output',
    metavar = 'FILE',
    type = str,
    required = True,
    help = 'Ausgabedatei')

parser.add_argument(
    '--cropmark',
    action = 'store_true',
    help = 'Schnitmarken zeichnen')

parser.add_argument(
    '--punchmark',
    action = 'store_true',
    help = 'Lochmarken zeichnen')

parser.add_argument(
    '--foldmark',
    action = 'store_true',
    help = 'Faltmarken zeichnen')

parser.add_argument(
    '--tc-to-a4',
    action = 'store_true',
    help = 'Terminal Charts auf A4 verkleinern')

parser.add_argument(
    '--misc-to-a4',
    action = 'store_true',
    help = 'Unbekannte Formate auf A4 verkleinern')

parser.add_argument(
    'pdfs',
    metavar = 'PDF',
    type = str,
    nargs = '+',
    help = 'PDF-Dateien')

args = parser.parse_args()



PAGES_A5   = []
PAGES_A4N  = []
PAGES_A4   = []
PAGES_TC   = []
PAGES_MISC = []



pdfs = load_pages(args.pdfs)

for filename, pages, _ in pdfs:
    currlist = None
    nextlist = None

    for p in pages:
        if p is None:
            if currlist is not None:
                currlist.append(None)
            continue

        page = pikepdf.Page(p)

        box = [ round(float(x) / 72.0 * 25.4) for x in page.trimbox ]
        box_left   = min(box[0], box[2])
        box_right  = max(box[0], box[2])
        box_bottom = min(box[1], box[3])
        box_top    = max(box[1], box[3])
        box_width  = box_right - box_left
        box_height = box_top   - box_bottom

        width  = box_width
        height = box_height

        rotation = p.Rotate if '/Rotate' in p else 0
        if rotation % 180:
            width, height = height, width

        # Genau genommen gibt es keine reinen A4-Seiten. Stattdessen ist es
        # wahrscheinlicher, dass die Zuschnittsbox der Seite falsch angelegt
        # wurde (z.B. AD-2 EDDC-2). Wir kürzen die Seite ein, sodass eine auf
        # A5 einklappbare Seite entsteht.
        if ( width, height ) == ( 210, 297 ):
            box_height = 277
            box_top = box_bottom + box_height
            box = [ round(float(x) / 25.4 * 72.0) for x in [ box_left, box_bottom, box_right, box_top ] ]
            page.trimbox = box

        pagedict = \
        {
            'page':      p,
            'width':     width,
            'height':    height,
            'rotation':  rotation,
            'landscape': width > height,
            # 'box_left':   box_left,
            # 'box_right':  box_right,
            # 'box_bottom': box_bottom,
            # 'box_top':    box_top,
            # 'box_width':  box_width,
            # 'box_height': box_height,
        }

        if ( box_width, box_height ) in [ ( 148, 210 ), ( 210, 148 ), ( 211, 148 ) ]:
            pagedict['format'] = 'A5'

            if currlist is PAGES_A4N and len(PAGES_A4N) % 2 and width < height:
                # Eine hochformatige A5-Seite, die auf eine kurze, ungerade
                # A4-Seite folgt, wird auf die Rückseite der A4-Seite gedruckt.
                nextlist = PAGES_A4N
            else:
                nextlist = PAGES_A5

        elif ( box_width, box_height ) in [ ( 210, 277 ), ( 277, 210 ) ]:
            pagedict['format'] = 'A4N'

            if currlist is PAGES_A4N and len(PAGES_A4N) % 2 and \
               (
                 width > height and not PAGES_A4N[-1]['landscape'] or
                 width < height and     PAGES_A4N[-1]['landscape']
               ):
                # Folgt eine schmale A4-Seite im Hochformat auf eine schmale,
                # ungerade A4-Seite im Querformat oder umgekehrt (Querformat
                # folgt auf Hochformat), dann wird eine Leerseite eingefügt,
                # weil beide Seiten ungerade sind.
                PAGES_A4N.append(None)

            nextlist = PAGES_A4N

        elif ( box_width, box_height ) in [ ( 210, 297 ), ( 297, 210 ) ]:
            pagedict['format'] = 'A4'
            nextlist = PAGES_A4

        elif ( box_width, box_height ) in [ ( 297, 380 ), ( 380, 297 ) ]:
            pagedict['format'] = 'TC'

            # Terminal Charts sind duplex, der Rest (Rollschemata) wird simplex
            # aufgearbeitet.
            if currlist is not PAGES_TC and len(PAGES_TC) % 2 != 0:
                PAGES_TC.append(None)
            nextlist = PAGES_TC

        elif args.misc_to_a4:
            # Eine Lücke lassen, wenn das Vorgängerformat nicht passt.
            if len(PAGES_MISC) % 2 and PAGES_MISC[-1] is not None:
                lastpage = PAGES_MISC[-1]
                if ( pagedict['width'], pagedict['height'] ) != ( lastpage['width'], lastpage['height'] ) and \
                   ( pagedict['width'], pagedict['height'] ) != ( lastpage['height'], lastpage['width'] ):
                    PAGES_MISC.append(None)

            pagedict['format'] = 'MISC'
            if pagedict['landscape']:
                pagedict['scale'] = min(1.0, 297.0 / pagedict['width'], 210.0 / pagedict['height'])
            else:
                pagedict['scale'] = min(1.0, 210.0 / pagedict['width'], 297.0 / pagedict['height'])
            nextlist = PAGES_MISC

        else:
            sys.stderr.write(
                "Seite %s von '%s' hat ein unbekanntes Format %dmm x %dmm. Seite bitte manuell drucken.\n" %
                (
                    page.label,
                    filename,
                    box_width,
                    box_height,
                )
            )

        # Beim Wechsel des Seitenformats ggf. eine Leerseite einfügen
        if nextlist is not currlist and len(nextlist) % 2 != 0:
            nextlist.append(None)

        nextlist.append(pagedict)
        currlist = nextlist

    # Sicherstellen, dass wir bei jedem neuen Dokument mit einer ungeraden
    # Seite beginnen.
    if len(PAGES_A5) % 2 != 0:
        PAGES_A5.append(None)
    if len(PAGES_A4N) % 2 != 0:
        PAGES_A4N.append(None)
    if len(PAGES_A4) % 2 != 0:
        PAGES_A4.append(None)
    if len(PAGES_TC) % 2 != 0:
        PAGES_TC.append(None)
    if len(PAGES_MISC) % 2 != 0:
        PAGES_MISC.append(None)

PAGES_A5.extend((-len(PAGES_A5) % 4) * [ None ])
PAGES_A4N.extend((-len(PAGES_A4N) % 2) * [ None ])
PAGES_A4.extend((-len(PAGES_A4) % 2) * [ None ])
PAGES_TC.extend((-len(PAGES_TC) % 2) * [ None ])
PAGES_MISC.extend((-len(PAGES_MISC) % 2) * [ None ])



def placepage(pdf, target, source,
              landscape = False,
              turn = False,
              offx = 0.0, offy = 0.0,
              scale = None,
              shiftx = 0.0, shifty = 0.0):
    if source is None:
        return

    # Die Quellseiten kopieren und als Ressource in die Zielseiten einfügen
    sourcepage = pikepdf.Page(source['page'])
    targetpage = pikepdf.Page(target)
    obj = pdf.copy_foreign(sourcepage.as_form_xobject())
    name = targetpage.add_resource(obj, pikepdf.Name.XObject)

    m = pikepdf.Matrix()

    # Abmessungen bestimmen.
    box_left   = float(min(sourcepage.trimbox[0], sourcepage.trimbox[2]))
    box_right  = float(max(sourcepage.trimbox[0], sourcepage.trimbox[2]))
    box_bottom = float(min(sourcepage.trimbox[1], sourcepage.trimbox[3]))
    box_top    = float(max(sourcepage.trimbox[1], sourcepage.trimbox[3]))
    box_width  = box_right - box_left
    box_height = box_top   - box_bottom

    # Anzeigeausrichtung der Seite bestimmen.
    rotation = source['page'].Rotate if '/Rotate' in source['page'] else 0

    # Anzeigeausrichtung kompensieren. Karte an unterer linken Ecke ausrichten.
    m = m @ pikepdf.Matrix().rotated(rotation)
    m = m @ pikepdf.Matrix().translated(-box_left, -box_bottom)
    m = m @ pikepdf.Matrix().rotated(-rotation)

    # Kartenmitte in den Ursprung schieben.
    if rotation % 180:
        box_width, box_height = box_height, box_width

    m = m @ pikepdf.Matrix().translated(-box_width / 2.0, -box_height / 2.0)

    # Seiten mit falscher Ausrichtung so drehen, dass man sie von rechts lesen kann.
    if landscape:
        if box_width < box_height:
            m = m @ pikepdf.Matrix().rotated(90)
            box_width, box_height = box_height, box_width
    else:
        if box_width > box_height:
            m = m @ pikepdf.Matrix().rotated(90)
            box_width, box_height = box_height, box_width

    # Seite so drehen, dass der Heftrand in der Mitte liegt, damit die
    # Schnittkante auf den Heftrand fällt.
    if turn:
        m = m @ pikepdf.Matrix().rotated(180)

    # Untere linke Ecke in den Ursprung schieben.
    m = m @ pikepdf.Matrix().translated(box_width / 2.0, box_height / 2.0)

    if scale is not None:
        # Skalierungszentrum in den Ursprung rücken.
        m = m @ pikepdf.Matrix().translated(-offx, -offy)

        # Skalieren.
        m = m @ pikepdf.Matrix().scaled(scale, scale)

    # Seite platzieren.
    m = m @ pikepdf.Matrix().translated(shiftx, shifty)

    commands = []
    commands.append(( [],                         pikepdf.Operator('q')  ))
    commands.append(( pikepdf.Array(m.shorthand), pikepdf.Operator('cm') ))
    commands.append(( [ name ],                   pikepdf.Operator('Do') ))
    commands.append(( [],                         pikepdf.Operator('Q')  ))

    targetpage.contents_add(pikepdf.unparse_content_stream(commands))


def pdfcmds_circle(x, y, r):
    c = 0.551915024494

    commands = []
    commands.append(( [ x +     r, y          ],                                    pikepdf.Operator('m') ))
    commands.append(( [ x +     r, y + c * r, x + c * r, y +     r, x,     y + r ], pikepdf.Operator('c') ))
    commands.append(( [ x - c * r, y +     r, x -     r, y + c * r, x - r, y     ], pikepdf.Operator('c') ))
    commands.append(( [ x -     r, y - c * r, x - c * r, y -     r, x,     y - r ], pikepdf.Operator('c') ))
    commands.append(( [ x + c * r, y -     r, x +     r, y - c * r, x + r, y     ], pikepdf.Operator('c') ))
    commands.append(( [],                                                           pikepdf.Operator('S') ))

    return commands


def marks_a5(pdf, page, cropmark = False, punchmark = False, foldmark = False):
    commands = []

    # Schnittmarke
    if cropmark:
        commands.append(( [],                                           pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ],                                      pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ],                                      pikepdf.Operator('w') ))
        commands.append(( [ 0 ],                                        pikepdf.Operator('J') ))
        commands.append(( [ 297 / 2 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 297 / 2 / 25.4 * 72.0,  10 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 297 / 2 / 25.4 * 72.0, 200 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 297 / 2 / 25.4 * 72.0, 210 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [],                                           pikepdf.Operator('S') ))
        commands.append(( [],                                           pikepdf.Operator('Q') ))

    # Lochmarke
    if punchmark:
        commands.append(( [],      pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ], pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ], pikepdf.Operator('w') ))
        commands.append(( [ 0 ],   pikepdf.Operator('J') ))
        commands.extend(pdfcmds_circle((297 / 2 - 12) / 25.4 * 72.0,  25.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 - 12) / 25.4 * 72.0,  65.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 - 12) / 25.4 * 72.0, 145.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 - 12) / 25.4 * 72.0, 185.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 + 12) / 25.4 * 72.0,  25.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 + 12) / 25.4 * 72.0,  65.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 + 12) / 25.4 * 72.0, 145.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle((297 / 2 + 12) / 25.4 * 72.0, 185.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.append(( [],      pikepdf.Operator('Q') ))

    pikepdf.Page(page).contents_add(pikepdf.unparse_content_stream(commands))


def marks_a4(pdf, page, cropmark = False, punchmark = False, foldmark = False):
    commands = []

    # Schnittmarke
    if cropmark:
        commands.append(( [],                                       pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ],                                  pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ],                                  pikepdf.Operator('w') ))
        commands.append(( [ 0 ],                                    pikepdf.Operator('J') ))
        commands.append(( [ 277 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 277 / 25.4 * 72.0,  10 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 277 / 25.4 * 72.0, 200 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 277 / 25.4 * 72.0, 210 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [],                                       pikepdf.Operator('S') ))
        commands.append(( [],                                       pikepdf.Operator('Q') ))

    # Lochmarke
    if punchmark:
        commands.append(( [],      pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ], pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ], pikepdf.Operator('w') ))
        commands.append(( [ 0 ],   pikepdf.Operator('J') ))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0,  25.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0,  65.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 145.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 185.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.append(( [],      pikepdf.Operator('Q') ))

    # Faltmarke
    if foldmark:
        commands.append(( [],                                      pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ],                                 pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ],                                 pikepdf.Operator('w') ))
        commands.append(( [ pikepdf.Array([ 5, 5 ]), 0 ],          pikepdf.Operator('d') ))
        commands.append(( [ 0 ],                                   pikepdf.Operator('J') ))
        commands.append(( [ 17 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 17 / 25.4 * 72.0,  10 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 17 / 25.4 * 72.0, 200 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 17 / 25.4 * 72.0, 210 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [],                                      pikepdf.Operator('S') ))
        commands.append(( [],                                      pikepdf.Operator('Q') ))

    pikepdf.Page(page).contents_add(pikepdf.unparse_content_stream(commands))


def marks_a3(pdf, page, cropmark = False, punchmark = False, foldmark = False):
    commands = []

    if cropmark:
        # Schnittmarke
        commands.append(( [],                                       pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ],                                  pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ],                                  pikepdf.Operator('w') ))
        commands.append(( [ 0 ],                                    pikepdf.Operator('J') ))
        commands.append(( [ 380 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 380 / 25.4 * 72.0,  10 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 380 / 25.4 * 72.0, 287 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 380 / 25.4 * 72.0, 297 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [   0 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [  25 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [  25 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [],                                       pikepdf.Operator('S') ))
        commands.append(( [],                                       pikepdf.Operator('Q') ))

    # Lochmarke
    if punchmark:
        commands.append(( [],      pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ], pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ], pikepdf.Operator('w') ))
        commands.append(( [ 0 ],   pikepdf.Operator('J') ))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 112.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 152.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 232.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.extend(pdfcmds_circle(12 / 25.4 * 72.0, 272.0 / 25.4 * 72.0, 2 / 25.4 * 72.0))
        commands.append(( [],      pikepdf.Operator('Q') ))

    # Faltmarke
    if foldmark:
        commands.append(( [],                                       pikepdf.Operator('q') ))
        commands.append(( [ 0.5 ],                                  pikepdf.Operator('G') ))
        commands.append(( [ 0.4 ],                                  pikepdf.Operator('w') ))
        commands.append(( [ pikepdf.Array([ 5, 5 ]), 0 ],           pikepdf.Operator('d') ))
        commands.append(( [ 0 ],                                    pikepdf.Operator('J') ))
        commands.append(( [ 140 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 140 / 25.4 * 72.0,   5 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 140 / 25.4 * 72.0, 292 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 140 / 25.4 * 72.0, 297 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 255 / 25.4 * 72.0,   0 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 255 / 25.4 * 72.0,   5 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 255 / 25.4 * 72.0, 292 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 255 / 25.4 * 72.0, 297 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [  15 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [  25 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [ 380 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('m') ))
        commands.append(( [ 390 / 25.4 * 72.0,  87 / 25.4 * 72.0 ], pikepdf.Operator('l') ))
        commands.append(( [],                                       pikepdf.Operator('S') ))
        commands.append(( [],                                       pikepdf.Operator('Q') ))

    pikepdf.Page(page).contents_add(pikepdf.unparse_content_stream(commands))



OUT = pikepdf.Pdf.new()

for i in range(0, len(PAGES_A5), 4):
    # Zwei leere A4-Zielseiten anlegen.
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))

    placepage(OUT, OUT.pages[-2], PAGES_A5[i + 0], turn = True)
    placepage(OUT, OUT.pages[-1], PAGES_A5[i + 1], turn = False)
    placepage(OUT, OUT.pages[-1], PAGES_A5[i + 2], turn = False, shiftx = 148 / 25.4 * 72.0)
    placepage(OUT, OUT.pages[-2], PAGES_A5[i + 3], turn = True,  shiftx = 148 / 25.4 * 72.0)

    marks_a5(OUT, OUT.pages[-2], cropmark = args.cropmark, punchmark = args.punchmark, foldmark = args.foldmark)

    p1 = pikepdf.Page(OUT.pages[-2])
    p2 = pikepdf.Page(OUT.pages[-1])
    p1.contents_coalesce()
    p2.contents_coalesce()
    p1.remove_unreferenced_resources()
    p2.remove_unreferenced_resources()

for i in range(0, len(PAGES_A4N), 2):
    # Zwei leere A4-Zielseiten anlegen.
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))

    # A5-Seiten auf der Rückseite einer A4-Seite im Hochformat belassen.
    pg2 = PAGES_A4N[i + 1]
    landscape = pg2 is None or pg2['format'] != 'A5'

    placepage(OUT, OUT.pages[-2], PAGES_A4N[i + 0], landscape = True,      turn = False)
    placepage(OUT, OUT.pages[-1], PAGES_A4N[i + 1], landscape = landscape, turn = True)

    marks_a4(OUT, OUT.pages[-2], cropmark = args.cropmark, punchmark = args.punchmark, foldmark = args.foldmark)

    p1 = pikepdf.Page(OUT.pages[-2])
    p2 = pikepdf.Page(OUT.pages[-1])
    p1.contents_coalesce()
    p2.contents_coalesce()
    p1.remove_unreferenced_resources()
    p2.remove_unreferenced_resources()


for i in range(0, len(PAGES_A4), 2):
    # Zwei leere A4-Zielseiten anlegen.
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))

    placepage(OUT, OUT.pages[-2], PAGES_A4[i + 0], landscape = True, turn = False)
    placepage(OUT, OUT.pages[-1], PAGES_A4[i + 1], landscape = True, turn = True)

    marks_a4(OUT, OUT.pages[-2], cropmark = args.cropmark, punchmark = args.punchmark, foldmark = args.foldmark)

    p1 = pikepdf.Page(OUT.pages[-2])
    p2 = pikepdf.Page(OUT.pages[-1])
    p1.contents_coalesce()
    p2.contents_coalesce()
    p1.remove_unreferenced_resources()
    p2.remove_unreferenced_resources()


for i in range(0, len(PAGES_TC), 2):
    if args.tc_to_a4:
        # Zwei leere A4-Zielseiten anlegen.
        OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))
        OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))

        #
        # Format der TC-Seite
        # - Lochrand:         25mm
        # - nutzbare Breite: 355mm
        # - nutzbare Höhe:   297mm
        #
        # Format der A4-Seite
        # - Lochrand:         17mm
        # - nutzbare Breite: 260mm
        # - nutzbare Höhe:   210mm
        #
        # Skalierung:
        # - Breite 260mm / 355mm = 0.732
        # - Höhe   210mm / 297mm = 0.707 = 1 / sqrt(2)
        #
        # Die Höhe ist bschränkend. Es ist keine Verschiebung in y-Richtung
        # notwendig.
        #
        placepage(OUT, OUT.pages[-2], PAGES_TC[i + 0], landscape = True, turn = False,
            offx = 25 / 25.4 * 72.0, offy = 297 / 2 / 25.4 * 72.0,
            scale = 0.68,
            shiftx = 20 / 25.4 * 72.0, shifty = 210 / 2 / 25.4 * 72.0)
        placepage(OUT, OUT.pages[-1], PAGES_TC[i + 1], landscape = True, turn = True,
            offx = 25 / 25.4 * 72.0, offy = 297 / 2 / 25.4 * 72.0,
            scale = 0.68,
            shiftx = 20 / 25.4 * 72.0, shifty = 210 / 2 / 25.4 * 72.0)

        marks_a4(OUT, OUT.pages[-2], cropmark = args.cropmark, punchmark = args.punchmark, foldmark = args.foldmark)

    else:
        # Zwei leere A3-Zielseiten anlegen.
        OUT.add_blank_page(page_size = ( 420 / 25.4 * 72.0, 297 / 25.4 * 72.0 ))
        OUT.add_blank_page(page_size = ( 420 / 25.4 * 72.0, 297 / 25.4 * 72.0 ))

        placepage(OUT, OUT.pages[-2], PAGES_TC[i + 0], landscape = True, turn = False)
        placepage(OUT, OUT.pages[-1], PAGES_TC[i + 1], landscape = True, turn = True)

        marks_a3(OUT, OUT.pages[-2], cropmark = args.cropmark, punchmark = args.punchmark, foldmark = args.foldmark)

    p1 = pikepdf.Page(OUT.pages[-2])
    p2 = pikepdf.Page(OUT.pages[-1])
    p1.contents_coalesce()
    p2.contents_coalesce()
    p1.remove_unreferenced_resources()
    p2.remove_unreferenced_resources()


for i in range(0, len(PAGES_MISC), 2):
    # Zwei leere A4-Zielseiten anlegen.
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))
    OUT.add_blank_page(page_size = ( 297 / 25.4 * 72.0, 210 / 25.4 * 72.0 ))

    pg1 = PAGES_MISC[i + 0]
    pg2 = PAGES_MISC[i + 1]
    placepage(OUT, OUT.pages[-2], pg1, landscape = True if pg1 is None else pg1['landscape'], turn = False, scale = 1.0 if pg1 is None else pg1['scale'])
    placepage(OUT, OUT.pages[-1], pg2, landscape = True if pg1 is None else pg1['landscape'], turn = True,  scale = 1.0 if pg2 is None else pg2['scale'])

    p1 = pikepdf.Page(OUT.pages[-2])
    p2 = pikepdf.Page(OUT.pages[-1])
    p1.contents_coalesce()
    p2.contents_coalesce()
    p1.remove_unreferenced_resources()
    p2.remove_unreferenced_resources()


if len(OUT.pages):
    OUT.save(args.output)
