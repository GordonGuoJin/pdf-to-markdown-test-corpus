#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify the corpus without a PDF library.

Reads each file, checks the structural invariants a reader depends on, and
extracts the text-showing operators straight out of the content stream. If this
passes, the files are well-formed enough for a conforming parser; if it fails,
you get told which file and which check.

    python3 verify.py
"""

import os
import re
import zlib
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(HERE, "tests")

Tj = re.compile(rb"BT\s+/(F\d)\s+([\d.]+)\s+Tf\s+1 0 0 1 (-?[\d.]+) (-?[\d.]+) Tm\s*\(((?:[^()\\]|\\.)*)\)\s*Tj", re.S)


def parse_objects(data):
    """Return {obj_num: (dict_bytes, stream_bytes_or_None)}."""
    objs = {}
    for m in re.finditer(rb"(\d+) 0 obj\s*(.*?)\s*endobj", data, re.S):
        num = int(m.group(1))
        body = m.group(2)
        sm = re.search(rb"stream\n(.*?)\nendstream", body, re.S)
        if sm:
            dictionary = body[:sm.start()]
            objs[num] = (dictionary, sm.group(1))
        else:
            objs[num] = (body, None)
    return objs


def check(path):
    name = os.path.basename(path)
    problems = []
    data = open(path, "rb").read()

    # --- header and trailer ---
    if not data.startswith(b"%PDF-1.4"):
        problems.append("missing %PDF-1.4 header")
    if not data.rstrip().endswith(b"%%EOF"):
        problems.append("missing %%EOF")

    # --- xref offsets must point at real object headers ---
    m = re.search(rb"startxref\s+(\d+)\s+%%EOF", data)
    if not m:
        problems.append("no startxref")
        return name, problems, []
    xref_pos = int(m.group(1))
    if data[xref_pos:xref_pos + 4] != b"xref":
        problems.append("startxref does not point at the xref table")

    xm = re.search(rb"xref\n0 (\d+)\n(.*?)trailer", data, re.S)
    if not xm:
        problems.append("malformed xref table")
        return name, problems, []

    count = int(xm.group(1))
    entries = xm.group(2).split(b"\n")
    for i, entry in enumerate(entries):
        if i == 0:
            continue  # the free entry
        if not entry.strip():
            continue
        parts = entry.split()
        if len(parts) < 3:
            continue
        off = int(parts[0])
        expect = b"%d 0 obj" % i
        if data[off:off + len(expect)] != expect:
            problems.append("xref entry %d points at %r, expected object %d"
                            % (i, data[off:off + 14], i))

    objs = parse_objects(data)

    # --- every page must reference a content stream that exists ---
    page_count = 0
    for num, (dictionary, stream) in objs.items():
        if b"/Type /Page" in dictionary and b"/Type /Pages" not in dictionary:
            page_count += 1
            cm = re.search(rb"/Contents (\d+) 0 R", dictionary)
            if not cm:
                problems.append("page object %d has no /Contents" % num)
            elif int(cm.group(1)) not in objs:
                problems.append("page object %d references missing stream %s"
                                % (num, cm.group(1).decode()))

    # --- declared /Length must match the actual stream length ---
    for num, (dictionary, stream) in objs.items():
        if stream is None:
            continue
        lm = re.search(rb"/Length (\d+)", dictionary)
        if not lm:
            problems.append("stream object %d has no /Length" % num)
        elif int(lm.group(1)) != len(stream):
            problems.append("stream object %d declares /Length %s but is %d bytes"
                            % (num, lm.group(1).decode(), len(stream)))

    # --- collect the text, decompressing if needed ---
    texts = []
    for num, (dictionary, stream) in objs.items():
        if stream is None:
            continue
        if b"/FlateDecode" in dictionary:
            try:
                stream = zlib.decompress(stream)
            except zlib.error as exc:
                problems.append("stream object %d fails to decompress: %s" % (num, exc))
                continue
        for tm in Tj.finditer(stream):
            font, size, x, y, raw = tm.groups()
            s = raw.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
            texts.append((float(y), float(x), float(size), font.decode(), s.decode("latin-1")))

    # rows top to bottom, then left to right — the reading order a human uses
    texts.sort(key=lambda t: (-t[0], t[1]))
    return name, problems, texts


def main():
    files = sorted(f for f in os.listdir(TESTS) if f.endswith(".pdf"))
    if not files:
        print("no PDFs found in %s — run make_pdfs.py first" % TESTS)
        return 1

    failed = 0
    print("%-38s %5s %5s %6s  %s" % ("file", "pages", "ops", "bytes", "status"))
    print("-" * 74)

    for f in files:
        path = os.path.join(TESTS, f)
        name, problems, texts = check(path)
        size = os.path.getsize(path)
        pages = len(set())  # placeholder, counted below
        # count page objects for display
        data = open(path, "rb").read()
        pages = len(re.findall(rb"/Type /Page[^s]", data))

        status = "ok" if not problems else "FAIL"
        if problems:
            failed += 1
        print("%-38s %5d %5d %6d  %s" % (name, pages, len(texts), size, status))
        for p in problems:
            print("      ! %s" % p)

    print("-" * 74)
    print("%d files, %d failed" % (len(files), failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
