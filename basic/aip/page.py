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



def page_amdt(pages_base, pages_target):
    index_page = { p['prefix']: p for p in pages_base }
    index_idx  = { p['prefix']: i for i, p in enumerate(pages_base) }

    result = []

    lastidx_base = 0
    for page_target in pages_target:
        prefix = page_target['prefix']

        if prefix not in index_page:
            # neue Seite
            result.append(( None, page_target ))
            continue

        page_base = index_page[prefix]

        curridx_base = index_idx[prefix]
        for i in range(lastidx_base, curridx_base):
            # gelöschte Seite
            result.append(( pages_base[i], None ))
        lastidx_base = curridx_base + 1

        if page_target['pageid'] != page_base['pageid']:
            # geänderte Seite
            result.append(( page_base, page_target ))
            continue

    return result
