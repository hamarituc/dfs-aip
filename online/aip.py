#!/bin/env python

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

import pikepdf



def load_pages(pdfs):
    pdfs = list(pdfs)
    result = []

    expectpdf = True

    while pdfs:
        pdfname = pdfs.pop(0)
        if not pdfname.endswith(".pdf"):
            raise ValueError("'%s' ist kein gültiger Dateiname." % pdfname)

        pdf = pikepdf.Pdf.open(pdfname)

        if len(pdfs) == 0 or pdfs[0].endswith(".pdf"):
            result.append(( pdfname, list(pdf.pages) ))
            continue

        resultpages = []

        pagespec = pdfs.pop(0)
        for ps in pagespec.split(","):
            if ps == "{}":
                resultpages.append(None)
                continue

            prange = ps.split("-")

            if len(prange) > 2:
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. '%s' ist keine Bereichsangabe." %
                    (
                        pagespec,
                        pdfname,
                        ps,
                    )
                )

            if prange[0].isnumeric():
                pfrom = int(prange[0])
            elif prange[0] == '':
                pfrom = None
            else:
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. '%s' ist keine Seiten-/Bereichsangabe." %
                    (
                        pagespec,
                        pdfname,
                        ps,
                    )
                )

            if len(prange) < 2:
                pto = None
            elif prange[1].isnumeric():
                pto = int(prange[1])
            elif prange[1] == '':
                pto = None
            else:
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. '%s' ist keine Bereichsangabe." %
                    (
                        pagespec,
                        pdfname,
                        ps,
                    )
                )

            if pfrom is not None and (pfrom < 1 or pfrom > len(pdf.pages)):
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. Seitenangabe '%d' außerhalb des Bereichs. Das PDF enthält %d Seiten." %
                    (
                        pagespec,
                        pdfname,
                        pfrom,
                        len(pdf.pages),
                    )
                )

            if pto is not None and (pto < 1 or pto > len(pdf.pages)):
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. Seitenangabe '%d' außerhalb des Bereichs. Das PDF enthält %d Seiten." %
                    (
                        pagespec,
                        pdfname,
                        pto,
                        len(pdf.pages),
                    )
                )

            if pfrom is not None and pto is not None and pfrom > pto:
                raise ValueError(
                    "Ungültiger Bereich '%s' für '%s'. Bereichsangabe '%s' ist nicht aufsteigend." %
                    (
                        pagespec,
                        pdfname,
                        ps,
                    )
                )

            if len(prange) == 1:
                if pfrom is None:
                    raise ValueError(
                        "Ungültiger Bereich '%s' für '%s'. Bereich enthält leere Seiten-/Bereichsangabe." %
                        (
                            pagespec,
                            pdfname,
                        )
                    )

                resultpages.append(pdf.pages[pfrom - 1])
                continue

            if pfrom is None:
                pfrom = 1
            if pto is None:
                pto = len(pdf.pages)

            for p in pdf.pages[pfrom - 1 : pto]:
                resultpages.append(p)

        result.append(( pdfname, resultpages ))

    return result

