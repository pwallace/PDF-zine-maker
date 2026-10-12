# PDF zine maker

Turns an ordinary sequential PDF into a **saddle-stitch booklet**: pages are
reordered and placed two-up on landscape sheets so that, printed duplex with
the sheets stacked, folded in half and stapled along the fold, they read in
order. Page 1 is the front cover; the last page is the back cover.

## Setup

    pip install -r requirements.txt     # just pypdf (>= 4)

## Usage

    python pdf_zine_maker.py INPUT.pdf [options]

Output defaults to `INPUT_booklet.pdf` next to the input.

| Option | Default | Meaning |
|---|---|---|
| `-o, --output FILE` | `<input>_booklet.pdf` | Output path |
| `-p, --paper SIZE` | `letter` | Sheet size: `letter legal tabloid ledger a3 a4 a5 b4 b5`, or `WxH[pt\|in\|mm\|cm]` (e.g. `8.5x11in`, `210x297mm`). Output is always landscape. |
| `--back-cover / --no-back-cover` | on | Keep the last page as the back cover; blank padding goes *before* it. If off, padding goes at the end. |
| `--pad / --no-pad` | on | Insert blank pages to reach a multiple of 4. With `--no-pad`, a non-multiple of 4 is an error. |
| `--pages RANGES` | all | Use only these source pages, e.g. `1-12,15` or `3-`. |
| `--scale fit\|shrink\|none` | `fit` | `fit` scales each page to fill its half; `shrink` only scales down; `none` keeps original size, centered. |
| `--margin LEN` | 0 | Outer margin on the sheet (`0.25in`, `6mm`, `18pt`). Use for printers that can't print edge to edge. |
| `--gutter LEN` | 0 | Extra gap at the fold between the halves. |
| `--rtl` | off | Right-to-left binding. |
| `--show-order` | off | Print the imposition order. |
| `-n, --dry-run` | off | Print the order and summary only; write nothing. |
| `-f, --force` | off | Overwrite an existing output file. |

## Examples

    # A4, 24-page zine
    python pdf_zine_maker.py zine.pdf -p a4

    # 22 pages -> 2 blanks inserted before the back cover (pages 21, 22 become blank)
    python pdf_zine_maker.py zine.pdf --dry-run

    # Printer needs a 1/4" unprintable margin and a little fold gap
    python pdf_zine_maker.py zine.pdf --margin 0.25in --gutter 2mm

    # No back cover; blanks appended at the end
    python pdf_zine_maker.py zine.pdf --no-back-cover

## Printing

Print the output **duplex, flip on SHORT edge**, at **actual size / 100%**
(not "fit to page"). Flipping on the long edge leaves the backs upside down.
Nest the sheets in order, fold, and staple along the fold.

## Imposition order

For N booklet pages (multiple of 4), sheet *i* (0-based) has:

- front: `N-2i | 2i+1`
- back: `2i+2 | N-2i-1`

e.g. N=8: `8|1`, `2|7`, `6|3`, `4|5`.

## Notes

- Pages of mixed sizes are each scaled into their half independently; blank
  pages are just empty halves.
- Page rotation and crop boxes in the source are respected.
- Output is a regular PDF; text stays selectable, nothing is rasterized.

## License

Copyright © 2026 Patrick R. Wallace, Hamilton College.

- **Software** (`pdf_zine_maker.py`): GNU General Public License, version 3 or
  later (`SPDX-License-Identifier: GPL-3.0-or-later`). Full text in
  [COPYING](COPYING).
- **Documentation** (this README): GNU Free Documentation License, version 1.3
  or later, with no Invariant Sections, no Front-Cover Texts, and no
  Back-Cover Texts (`SPDX-License-Identifier: GFDL-1.3-or-later`). Full text in
  [COPYING.DOC](COPYING.DOC). Command lines and code fragments quoted in the
  documentation are also available under the GPL, version 3 or later, at your
  option.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See [LICENSE.txt](LICENSE.txt) for the summary.
