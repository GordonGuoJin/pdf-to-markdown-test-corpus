# PDF-to-Markdown Test Corpus

18 small PDFs, each built to break a PDF-to-Markdown converter in one specific
way, plus the measured output of one converter against all of them.

If you are writing a converter, or choosing one, the hard part is not the happy
path. It is knowing what happens when a document has two columns, or a heading
that is only bold, or a scanned page in the middle. This corpus is meant to make
that testable in about a minute, and to give you somewhere to point when you find
a bug.

```bash
git clone https://github.com/GordonGuoJin/pdf-to-markdown-test-corpus
cd pdf-to-markdown-test-corpus
python3 verify.py          # structural check + text extraction, no dependencies
```

Then open your converter, drop in the files from `tests/`, and compare against
`results.json`.

## What is in here

| File | What it isolates |
| --- | --- |
| `01-single-column.pdf` | The case everything is built for — a baseline to compare against |
| `02-two-column-shared-baseline.pdf` | Two columns on identical baselines |
| `03-table.pdf` | Table cells sharing a baseline |
| `04-no-text-layer.pdf` | A page with no text operators at all |
| `05-two-column-offset.pdf` | Two columns that overlap for only part of the page |
| `06-three-column.pdf` | Three columns sharing baselines |
| `07-bold-headings-body-size.pdf` | Headings marked out only by weight, not size |
| `08-running-header-2-pages.pdf` | The same header and footer repeated on every page |
| `09-hyphenated-breaks.pdf` | Words split across lines with a trailing hyphen |
| `10-toc-wide-gap.pdf` | A wide horizontal gap inside one visual line |
| `11-scan-styled.pdf` | Bars standing in for a scanned page |
| `12-mixed-worst-case.pdf` | Title, two-column paragraph and table on one page |
| `13-heading-thresholds.pdf` | One line at each of six font sizes around the usual thresholds |
| `14a-row-major.pdf` | Identical geometry to 14b, text written row by row |
| `14b-column-major.pdf` | Identical geometry to 14a, text written column by column |
| `15-mixed-first-page-text.pdf` | Page 1 has text, page 2 is a scan |
| `16-mixed-middle-page-text.pdf` | Scan, text, scan |
| `17-compressed-stream.pdf` | A FlateDecode-compressed content stream |

Two rules apply to all of them. Each file isolates **one** behaviour, so a
surprising result points at a single cause. And where two files are compared they
differ in one variable only — `14a`/`14b` are the clearest case: same page size,
same font, same coordinates, the same four left-column and four right-column
strings, and the same nine text items in total. The only difference is the order
those text operators appear in the content stream. (Each file does carry its own
heading, `Row Major` and `Column Major`, so that you can tell at a glance which
one produced a given result; that heading is the one string that differs.)

## The pair worth looking at first

`14a-row-major.pdf` and `14b-column-major.pdf` are visually indistinguishable.
Open them side by side and you cannot tell which is which.

Yet one converter (the one whose results are in `results.json`) produced:

```
Left column, line one. Right column, line one.
```

for `14a`, and

```
Left column, line one.Right column, line one.
```

for `14b` — no space at all between the columns.

Both are wrong, but the second is far more dangerous, because
`line one.Right column` reads as a typo rather than as two columns that have been
fused together. Nobody proofreading the output catches that.

The cause is not the geometry. It is that PDF.js emits the spacing between two
text runs as its own synthetic text item when the runs are written consecutively,
and omits it otherwise. Same page, same coordinates, different outcome — a
property of the file's internal byte order that no amount of looking at the page
will reveal.

## Measured results

`results.json` holds the verbatim output of one converter against every file,
measured 2026-09-17. Structure:

```json
{
  "converter": { "name": "...", "engine": "...", "measured": "..." },
  "results": [
    {
      "file": "01-single-column.pdf",
      "intent": "what the file is built to test",
      "status": "the string the tool reported",
      "output": "verbatim Markdown, or null if it errored"
    }
  ]
}
```

Your converter's results will differ. That is the point — the value is in having a
fixed set of inputs you can compare over time, and in the entries like
`heading_measured` in `13-heading-thresholds.pdf`, which records which font sizes
became which heading levels.

## Rebuilding the corpus

```bash
python3 make_pdfs.py    # regenerates tests/ — byte-identical when run twice
python3 verify.py       # checks xref offsets, /Length, page and stream references
```

No dependencies. Both scripts are standard library only, and the PDFs are written
byte by byte rather than generated with a library, so you can read the exact
content stream behind any result. When a converter does something surprising it
matters that the input is not a black box.

`verify.py` is deliberately not a PDF parser. It checks the invariants a reader
depends on — that `startxref` points at the xref table, that every xref entry
points at a real object header, that declared `/Length` matches the actual stream
length, that every page's `/Contents` resolves — and then pulls the text back out
with a regular expression. If it passes, the files are well-formed enough for a
conforming parser.

## Contributing

A new file is welcome if it isolates one behaviour and comes with its measured
output. The most useful contributions are the ones that are currently *not*
covered: forms and annotations, rotated pages, right-to-left text, embedded
fonts with unusual encodings, incremental updates, and PDFs from the awkward
corners of the format.

Please keep the naming convention `NN-what-it-tests.pdf`, keep the file small
(under about 5 KB), and add the entry to `results.json`.

## Licence

The PDFs and scripts are released under [CC0 1.0](LICENSE) — public domain. Use
them for anything, including commercially, with no attribution required.

They are synthetic documents built for testing and contain no third-party
content.

---

Built while testing [pdfmdtools.com](https://pdfmdtools.com), a browser-side
PDF-to-Markdown converter, and published so the test cases do not have to be
rebuilt by everyone who needs them.
