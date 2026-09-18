#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build the test corpus for pdf-to-markdown-test-corpus.

Every PDF here is written byte by byte from scratch — no reportlab, no
dependencies. That is deliberate: you can read the exact content stream that
produced each result, which is the whole point of a corpus like this. When a
converter does something surprising, the input is not a black box.

Run:

    python3 make_pdfs.py

It writes into ./tests/ and is idempotent — running it twice gives byte-identical
files, so you can diff a regenerated corpus against the committed one.
"""

import os
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tests")

W, H = 612, 792  # US Letter, points


# --------------------------------------------------------------------------
# PDF writer
# --------------------------------------------------------------------------

def build_pdf(path, pages, compress=False):
    """Write a minimal but valid PDF.

    pages: list of (content_stream_bytes, extra_page_dict_bytes_or_None)

    The xref table records real byte offsets, which matters: some parsers
    (including PDF.js in certain modes) will recover from a wrong offset rather
    than fail, and you would never notice the file was malformed.
    """
    n = len(pages)
    catalog_id = 1
    pages_id = 2
    page_ids = [3 + i for i in range(n)]
    f1_id = 3 + n          # Helvetica
    f2_id = 4 + n          # Helvetica-Bold
    content_ids = [5 + n + i for i in range(n)]

    objs = [None] * (4 + 2 * n)
    objs[catalog_id - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id

    kids = b" ".join(b"%d 0 R" % i for i in page_ids)
    objs[pages_id - 1] = (b"<< /Type /Pages /Kids [" + kids +
                          b"] /Count " + str(n).encode() + b" >>")

    for i in range(n):
        stream, extra = pages[i]
        pid = page_ids[i]
        cid = content_ids[i]

        if compress:
            packed = zlib.compress(stream)
            filters = b"/Filter /FlateDecode "
            body = packed
        else:
            filters = b""
            body = stream

        o = (b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] " % (pages_id, W, H) +
             b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> /Contents %d 0 R"
             % (f1_id, f2_id, cid))
        if extra:
            o += b" " + extra
        o += b" >>"
        objs[pid - 1] = o

        objs[cid - 1] = (b"<< " + filters + b"/Length " + str(len(body)).encode() +
                         b" >>\nstream\n" + body + b"\nendstream")

    objs[f1_id - 1] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
                       b"/Encoding /WinAnsiEncoding >>")
    objs[f2_id - 1] = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold "
                       b"/Encoding /WinAnsiEncoding >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(out))
        out += str(i).encode() + b" 0 obj\n" + o + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objs) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()

    out += (b"trailer\n<< /Size " + str(len(objs) + 1).encode() + b" /Root 1 0 R >>\n"
            b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF\n")

    with open(path, "wb") as f:
        f.write(bytes(out))
    return len(out)


def T(x, y, s, size=12, font="F1"):
    """One text-showing operation: put string s at (x, y) at the given size."""
    s = s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return "BT /%s %s Tf 1 0 0 1 %d %d Tm (%s) Tj ET\n" % (
        font, _num(size), x, y, s)


def _num(v):
    """PDF numbers: 21.6 not 21.600000000000001, 12 not 12.0."""
    if float(v) == int(v):
        return str(int(v))
    return ("%.4f" % v).rstrip("0").rstrip(".")


def scan_page(lines=20, y0=700, step=28):
    """A page that looks like a scan: grey bars, no text operators at all."""
    s = "0.9 0.9 0.9 rg\n30 60 552 680 re f\n0.7 0.7 0.7 rg\n"
    y = y0
    for _ in range(lines):
        s += "60 %d 460 6 re f\n" % y
        y -= step
    return s


def write(name, pages, compress=False):
    p = os.path.join(OUT, name)
    size = build_pdf(p, [(s.encode("latin-1"), e) for s, e in pages], compress=compress)
    print("  %-40s %7d B  %d page(s)" % (name, size, len(pages)))
    return size


# --------------------------------------------------------------------------
# The corpus
# --------------------------------------------------------------------------
#
# Two rules, applied to every file:
#
#   1. One behaviour per file. If a result is surprising you should be able to
#      point at the single thing that caused it.
#
#   2. Where two files are compared, they are identical except for one variable.
#      t14a/t14b are the clearest example: same page size, same fonts, same
#      coordinates, same strings — only the order the text is written in the
#      content stream differs. That single variable changes the output.

def build():
    os.makedirs(OUT, exist_ok=True)
    print("Building corpus into %s\n" % OUT)

    results = []

    # -- 01: the case everything is built for -------------------------------
    s = ""
    s += T(50, 740, "Quarterly Report", 24, "F2")
    s += T(50, 705, "This document is laid out in a single column, which is the", 12)
    s += T(50, 688, "simplest case for any PDF-to-Markdown converter to handle.", 12)
    s += T(50, 650, "Key findings", 18, "F2")
    s += T(50, 618, "- Revenue grew across all three regions.", 12)
    s += T(50, 600, "- Headcount stayed flat for the second quarter.", 12)
    s += T(50, 582, "- Support ticket volume dropped by a fifth.", 12)
    s += T(50, 544, "Next steps", 18, "F2")
    s += T(50, 512, "The team will publish the full breakdown next month.", 12)
    results.append(write("01-single-column.pdf", [(s, None)]))

    # -- 02: two columns sharing baselines ----------------------------------
    s = T(50, 740, "Two Column Layout", 20, "F2")
    left = ["Left column, line one.", "Left column, line two.",
            "Left column, line three.", "Left column, line four."]
    right = ["Right column, line one.", "Right column, line two.",
             "Right column, line three.", "Right column, line four."]
    y = 700
    for i in range(4):
        s += T(50, y, left[i], 12)
        s += T(320, y, right[i], 12)
        y -= 20
    results.append(write("02-two-column-shared-baseline.pdf", [(s, None)]))

    # -- 03: table, cells sharing baselines ---------------------------------
    s = T(50, 740, "Price List", 20, "F2")
    rows = [("Item", "Qty", "Unit price"), ("Widget", "10", "1.50"),
            ("Gadget", "5", "9.99"), ("Bracket", "22", "0.75")]
    y = 700
    for r in rows:
        s += T(50, y, r[0], 12)
        s += T(220, y, r[1], 12)
        s += T(340, y, r[2], 12)
        y -= 20
    results.append(write("03-table.pdf", [(s, None)]))

    # -- 04: no text operators at all ---------------------------------------
    s = "0.85 0.85 0.85 rg\n40 400 530 320 re f\n"
    results.append(write("04-no-text-layer.pdf", [(s, None)]))

    # -- 05: two columns, right column starts lower -------------------------
    s = T(50, 740, "Offset Two Column Layout", 20, "F2")
    y = 700
    for t in ["Left column, line one.", "Left column, line two.",
              "Left column, line three.", "Left column, line four.",
              "Left column, line five."]:
        s += T(50, y, t, 12)
        y -= 20
    y = 660
    for t in ["Right column, line one.", "Right column, line two.",
              "Right column, line three."]:
        s += T(320, y, t, 12)
        y -= 20
    results.append(write("05-two-column-offset.pdf", [(s, None)]))

    # -- 06: three columns, shared baselines --------------------------------
    s = T(50, 740, "Three Column Layout", 20, "F2")
    cols = [["Alpha one.", "Alpha two.", "Alpha three."],
            ["Beta one.", "Beta two.", "Beta three."],
            ["Gamma one.", "Gamma two.", "Gamma three."]]
    y = 700
    for i in range(3):
        for c in range(3):
            s += T(50 + c * 190, y, cols[c][i], 11)
        y -= 20
    results.append(write("06-three-column.pdf", [(s, None)]))

    # -- 07: headings distinguished only by font weight ---------------------
    # The heading strings are the same size as the body. Nothing in the
    # coordinates or the size marks them out; only the font resource differs.
    s = ""
    s += T(50, 740, "Bold Headings At Body Size", 12, "F2")
    s += T(50, 712, "This paragraph is body text set in the regular weight.", 12)
    s += T(50, 694, "It exists to establish what the body size of this page is.", 12)
    s += T(50, 660, "Section One", 12, "F2")
    s += T(50, 632, "The heading above is bold but exactly the same size as the", 12)
    s += T(50, 614, "body text, which is the case this test is built to measure.", 12)
    s += T(50, 580, "Section Two", 12, "F2")
    s += T(50, 552, "A second bold heading, again at the body font size, to see", 12)
    s += T(50, 534, "whether either of them is recognised as a heading at all.", 12)
    results.append(write("07-bold-headings-body-size.pdf", [(s, None)]))

    # -- 08: running header and footer repeated across pages ----------------
    def page_with_running_header(body_lines, page_no):
        s = T(50, 760, "CONFIDENTIAL - INTERNAL DRAFT", 9)
        y = 720
        for line in body_lines:
            s += T(50, y, line, 12)
            y -= 20
        s += T(50, 60, "Page %d of 2" % page_no, 9)
        return s

    p1 = page_with_running_header([
        "This is the first page of a two page document.",
        "It carries a running header at the top of every page.",
        "It also carries a page number in the footer.",
    ], 1)
    p2 = page_with_running_header([
        "This is the second page of the same document.",
        "The header and footer repeat here, exactly as before.",
        "In Markdown output they arrive as ordinary paragraphs.",
    ], 2)
    results.append(write("08-running-header-2-pages.pdf", [(p1, None), (p2, None)]))

    # -- 09: hyphenated line breaks -----------------------------------------
    s = T(50, 740, "Hyphenated Line Breaks", 20, "F2")
    y = 700
    for line in ["The configuration file is stored in the applica-",
                 "tion directory, which is created on first launch",
                 "and can be relocated by setting the environ-",
                 "ment variable before the service starts."]:
        s += T(50, y, line, 12)
        y -= 20
    results.append(write("09-hyphenated-breaks.pdf", [(s, None)]))

    # -- 10: one line with a large horizontal gap (table of contents) -------
    s = T(50, 740, "Table Of Contents", 20, "F2")
    y = 700
    for a, b in [("Introduction", "3"), ("Installation", "11"),
                 ("Configuration", "24"), ("Troubleshooting", "48")]:
        s += T(50, y, a, 12)
        s += T(480, y, b, 12)
        y -= 22
    results.append(write("10-toc-wide-gap.pdf", [(s, None)]))

    # -- 11: scan-styled page, no text --------------------------------------
    results.append(write("11-scan-styled.pdf", [(scan_page(22), None)]))

    # -- 12: everything wrong on one page -----------------------------------
    s = ""
    s += T(50, 750, "Mixed Layout Page", 22, "F2")
    s += T(50, 715, "Left paragraph, line one.", 12)
    s += T(320, 715, "Right paragraph, line one.", 12)
    s += T(50, 697, "Left paragraph, line two.", 12)
    s += T(320, 697, "Right paragraph, line two.", 12)
    s += T(50, 655, "Summary Table", 15, "F2")
    y = 625
    for r in [("Region", "Revenue", "Growth"), ("North", "1,200", "8%"),
              ("South", "980", "-2%"), ("East", "1,540", "12%")]:
        s += T(50, y, r[0], 11)
        s += T(230, y, r[1], 11)
        s += T(360, y, r[2], 11)
        y -= 18
    s += T(50, 520, "Closing paragraph under the table.", 12)
    results.append(write("12-mixed-worst-case.pdf", [(s, None)]))

    # -- 13: heading level thresholds ---------------------------------------
    # Nine 12pt lines fix the median body size at 12. Then one line at each of
    # six sizes, chosen to straddle the 1.15 / 1.4 / 1.8 boundaries.
    s = ""
    s += T(50, 760, "Threshold Test", 22, "F2")                 # 1.8333
    for i, word in enumerate(["one", "two", "three", "four", "five",
                              "six", "seven", "eight", "nine"]):
        s += T(50, 735 - i * 18, "Body line %s at twelve point." % word, 12)
    s += T(50, 555, "Heading at thirteen point", 13)            # 1.0833
    s += T(50, 525, "Heading at fifteen point", 15)             # 1.25
    s += T(50, 495, "Heading at eighteen point", 18)            # 1.5
    s += T(50, 465, "Heading at twenty-one point", 21)          # 1.75
    s += T(50, 433, "Heading at twenty-one point six", 21.6)    # 1.8 exactly
    s += T(50, 401, "Heading at twenty-two point", 22)          # 1.8333
    results.append(write("13-heading-thresholds.pdf", [(s, None)]))

    # -- 14: the single-variable pair ---------------------------------------
    # Identical geometry. Identical strings. Identical fonts. The only
    # difference is the order the text operators appear in the content stream.
    left = ["Left column, line one.", "Left column, line two.",
            "Left column, line three.", "Left column, line four."]
    right = ["Right column, line one.", "Right column, line two.",
             "Right column, line three.", "Right column, line four."]
    ys = [700, 680, 660, 640]

    a = T(50, 740, "Row Major", 20, "F2")
    for i in range(4):
        a += T(50, ys[i], left[i], 12)
        a += T(320, ys[i], right[i], 12)

    b = T(50, 740, "Column Major", 20, "F2")
    for i in range(4):
        b += T(50, ys[i], left[i], 12)
    for i in range(4):
        b += T(320, ys[i], right[i], 12)

    results.append(write("14a-row-major.pdf", [(a, None)]))
    results.append(write("14b-column-major.pdf", [(b, None)]))

    # -- 15: first page has text, second is a scan --------------------------
    def text_page(lines, title=None):
        s = ""
        y = 730
        if title:
            s += T(50, y, title, 20, "F2")
            y -= 40
        for line in lines:
            s += T(50, y, line, 12)
            y -= 20
        return s

    t15_p1 = text_page(["This page has a real text layer.",
                        "It is the first page of a two page document.",
                        "The second page is a scan with no text at all."],
                       "Mixed Document")
    results.append(write("15-mixed-first-page-text.pdf",
                         [(t15_p1, None), (scan_page(), None)]))

    # -- 16: only the middle page has text ----------------------------------
    t16_p2 = text_page(["Only the middle page of this document has text.",
                        "The first and third pages are scans.",
                        "Nothing in the output tells you that."], "Page Two")
    results.append(write("16-mixed-middle-page-text.pdf",
                         [(scan_page(), None), (t16_p2, None), (scan_page(), None)]))

    # -- 17: FlateDecode-compressed content stream --------------------------
    # Same text as 01, compressed. A corpus that only ever uses uncompressed
    # streams will not catch a parser bug in the filter path.
    s = ""
    s += T(50, 740, "Compressed Stream Document", 24, "F2")
    s += T(50, 705, "The content stream of this page is FlateDecode-compressed,", 12)
    s += T(50, 688, "which is what almost every real PDF in the world uses.", 12)
    s += T(50, 650, "Key findings", 18, "F2")
    s += T(50, 618, "- Expansion happens before parsing, so results should match.", 12)
    s += T(50, 600, "- A parser that mishandles the filter fails here and nowhere else.", 12)
    results.append(write("17-compressed-stream.pdf", [(s, None)], compress=True))

    total = sum(results)
    print("\n%d files, %d bytes total (%.1f KB)"
          % (len(results), total, total / 1024.0))


if __name__ == "__main__":
    build()
