#!/usr/bin/env python3
"""Impose a PDF into a saddle-stitch booklet (print duplex, fold, staple).

Pages are re-ordered and placed two-up on landscape sheets so that, printed
double-sided with the sheets nested and folded in half, they read in order.
See README.md for details.
"""

# Copyright (C) 2026 Patrick R. Wallace, Hamilton College.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import re
import sys
from pathlib import Path

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

# Sheet sizes in points (portrait width x height; output is always landscape).
PAPER = {
    "letter": (612, 792),
    "legal": (612, 1008),
    "tabloid": (792, 1224),
    "ledger": (792, 1224),
    "a3": (841.89, 1190.55),
    "a4": (595.28, 841.89),
    "a5": (419.53, 595.28),
    "b4": (708.66, 1000.63),
    "b5": (498.9, 708.66),
}
UNITS = {"pt": 1.0, "in": 72.0, "mm": 72 / 25.4, "cm": 72 / 2.54}


def parse_length(text):
    m = re.fullmatch(r"\s*([\d.]+)\s*(pt|in|mm|cm)?\s*", text)
    if not m:
        raise argparse.ArgumentTypeError(f"bad length: {text!r} (e.g. 0.25in, 6mm, 18pt)")
    return float(m.group(1)) * UNITS[m.group(2) or "pt"]


def parse_paper(text):
    key = text.lower()
    if key in PAPER:
        return PAPER[key]
    m = re.fullmatch(r"([\d.]+)x([\d.]+)(pt|in|mm|cm)?", key)
    if not m:
        raise argparse.ArgumentTypeError(
            f"unknown paper {text!r}; use one of {', '.join(PAPER)} or WxH[unit], e.g. 8.5x11in"
        )
    f = UNITS[m.group(3) or "pt"]
    return float(m.group(1)) * f, float(m.group(2)) * f


def parse_page_ranges(spec, n):
    """'1-5,8,10-' -> list of 0-based indexes, in the order given."""
    out = []
    for part in spec.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d*)(-?)(\d*)", part)
        if not part or not m:
            raise ValueError(f"bad page range: {part!r}")
        a, dash, b = m.groups()
        if not dash:
            lo = hi = int(a)
        else:
            lo, hi = int(a or 1), int(b or n)
        if not (1 <= lo <= hi <= n):
            raise ValueError(f"page range {part!r} outside 1-{n}")
        out.extend(range(lo - 1, hi))
    return out


def build_page_list(indexes, pad, back_cover):
    """Return a list of source indexes with None for blank pages."""
    pages = list(indexes)
    missing = -len(pages) % 4
    if missing and not pad:
        raise SystemExit(
            f"{len(pages)} pages is not a multiple of 4 (need {missing} more); "
            "use --pad or fix the page selection"
        )
    blanks = [None] * missing
    if back_cover and len(pages) > 1:
        return pages[:-1] + blanks + pages[-1:]
    return pages + blanks


def sheet_order(pages, rtl=False):
    """Yield (left, right) page pairs for each printed side, front/back alternating."""
    n = len(pages)
    for i in range(n // 4):
        sides = [(pages[n - 1 - 2 * i], pages[2 * i]),
                 (pages[2 * i + 1], pages[n - 2 - 2 * i])]
        for left, right in sides:
            yield (right, left) if rtl else (left, right)


def place(sheet, src_page, x, y, w, h, scale_mode):
    """Draw src_page centered in the cell (x, y, w, h)."""
    if src_page is None:
        return
    src_page.transfer_rotation_to_content()
    box = src_page.cropbox
    pw, ph = float(box.width), float(box.height)
    s = min(w / pw, h / ph)
    if scale_mode == "shrink":
        s = min(s, 1.0)
    elif scale_mode == "none":
        s = 1.0
    tx = x + (w - pw * s) / 2 - float(box.left) * s
    ty = y + (h - ph * s) / 2 - float(box.bottom) * s
    sheet.merge_transformed_page(src_page, Transformation().scale(s).translate(tx, ty))


def make_booklet(args):
    reader = PdfReader(args.input)
    if reader.is_encrypted:
        reader.decrypt("")
    total = len(reader.pages)
    indexes = parse_page_ranges(args.pages, total) if args.pages else list(range(total))
    if not indexes:
        raise SystemExit("no pages to impose")
    pages = build_page_list(indexes, args.pad, args.back_cover)

    pw, ph = args.paper
    W, H = (ph, pw) if pw < ph else (pw, ph)  # landscape
    m, g = args.margin, args.gutter
    cell_w, cell_h = (W - 2 * m - g) / 2, H - 2 * m

    writer = PdfWriter()
    for side, (left, right) in enumerate(sheet_order(pages, args.rtl), 1):
        sheet = PageObject.create_blank_page(width=W, height=H)
        for idx, x in ((left, m), (right, m + cell_w + g)):
            src = None if idx is None else reader.pages[idx]
            place(sheet, src, x, m, cell_w, cell_h, args.scale)
        writer.add_page(sheet)

    if args.show_order or args.dry_run:
        label = lambda i: "blank" if i is None else str(i + 1)
        for side, (l, r) in enumerate(sheet_order(pages, args.rtl)):
            print(f"sheet {side // 2 + 1} {'front' if side % 2 == 0 else 'back '}: "
                  f"{label(l):>5} | {label(r)}")
    summary = (f"{len(indexes)} source pages -> {len(pages)} booklet pages "
               f"({len(pages) - len(indexes)} blank) on {len(pages) // 4} sheets, "
               f"{W / 72:.2f}x{H / 72:.2f} in landscape")
    if args.dry_run:
        print(summary)
        return
    out = Path(args.output) if args.output else Path(args.input).with_name(
        Path(args.input).stem + "_booklet.pdf")
    if out.exists() and not args.force:
        raise SystemExit(f"{out} exists; use --force to overwrite")
    writer.add_metadata({"/Title": (reader.metadata.title if reader.metadata and reader.metadata.title
                                    else Path(args.input).stem) + " (booklet imposition)"})
    writer.write(out)
    print(summary)
    print(f"wrote {out}")
    print("Print duplex, flip on SHORT edge, actual size (100%).")


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Reorder a PDF into a duplex saddle-stitch booklet (2-up, fold & staple).")
    p.add_argument("input", help="source PDF")
    p.add_argument("-o", "--output", help="output PDF (default: <input>_booklet.pdf)")
    p.add_argument("-p", "--paper", type=parse_paper, default="letter",
                   help=f"sheet size: {', '.join(PAPER)} or WxH[pt|in|mm|cm] (default: letter)")
    p.add_argument("--back-cover", action=argparse.BooleanOptionalAction, default=True,
                   help="treat the last page as the back cover; padding goes before it (default: on)")
    p.add_argument("--pad", action=argparse.BooleanOptionalAction, default=True,
                   help="insert blank pages to reach a multiple of 4 (default: on)")
    p.add_argument("--pages", help="only use these source pages, e.g. '1-12,15' (default: all)")
    p.add_argument("--scale", choices=["fit", "shrink", "none"], default="fit",
                   help="fit: scale up/down to fill each half; shrink: only scale down; "
                        "none: keep original size, centered (default: fit)")
    p.add_argument("--margin", type=parse_length, default=0,
                   help="outer margin on the sheet, e.g. 0.25in (default: 0)")
    p.add_argument("--gutter", type=parse_length, default=0,
                   help="extra gap at the fold between the two halves (default: 0)")
    p.add_argument("--rtl", action="store_true",
                   help="right-to-left binding (manga, Arabic, Hebrew)")
    p.add_argument("--show-order", action="store_true", help="print the page imposition order")
    p.add_argument("-n", "--dry-run", action="store_true",
                   help="print the order and summary without writing a file")
    p.add_argument("-f", "--force", action="store_true", help="overwrite existing output")
    args = p.parse_args(argv)
    if isinstance(args.paper, str):
        args.paper = parse_paper(args.paper)
    make_booklet(args)


if __name__ == "__main__":
    sys.exit(main())
