# mini-search-engine

A compact document indexing and retrieval system for a collection of HTML
(ClueWeb/WARC) documents. It builds an inverted index over the corpus and
provides an interactive interface to query term and document statistics.

The project is written in **pure Python 3** and uses **only the standard
library** — no `pip` install is required.

The system has three stages, run in order:

```
   corpus/                                                        
  (HTML/WARC                                                      
   documents)                                                                     queries    
      │                                                                              │
      ▼                                                                              ▼
 ┌──────────┐       docids.txt          ┌──────────┐                            ┌───────────┐
 │TOKENIZER │       termids.txt         │ INDEXER  │       term_index.txt       │  READER   │
 │          │  ──►  doc_index.txt  ──►  │          │  ──►  term_info.txt   ──►  │           │                  
 └──────────┘                           └──────────┘                            └───────────┘
   lexical           forward              inverting           inverted
   processing        index                index               index
```

---

## Contents

| File | Role |
|---|---|
| `tokenizer.py` | Lexical processing and forward index construction |
| `indexer.py` | Delta-encoded inverted index construction |
| `reader.py` | Interactive query interface over the index |
| `porter.py` | Porter stemming algorithm |
| `htmlparse.py` | Visible-text extraction from WARC/HTML documents |
| `run.sh` | Convenience script that runs the whole pipeline |

---

## Requirements

- Python 3.6+
- No external dependencies

---

## Quick start

From the project root (the folder containing `corpus.tgz` and `stopwords.txt`):

```bash
cd src
chmod +x run.sh
./run.sh
```

The script extracts the corpus, runs the Tokenizer and Indexer, then opens the
Reader.

### Running the stages manually

```bash
# 1) Extract the corpus
mkdir -p work && tar xzf corpus.tgz -C work        # creates work/corpus/...

# 2) Tokenizer:  <corpus_folder>  <stopwords>  <output_folder>
python3 src/tokenizer.py work/corpus stopwords.txt output

# 3) Indexer:  <tokenizer_results_folder>  <output_folder>
python3 src/indexer.py output output

# 4) Reader:  <index_folder>
python3 src/reader.py output
```

---

## Stage 1 — Tokenizer

**Input:** a document folder, a stop-words file, an output folder.
**Output:** `docids.txt`, `termids.txt`, `doc_index.txt`.

Each document is processed through the following lexical pipeline:

1. **Read** the raw WARC record.
2. **Extract the HTML** — WARC and HTTP headers are skipped by starting at the
   first line that begins with `<`.
3. **Parse the HTML** and keep only the visible text (excluding `<head>`,
   `<script>`, `<style>` and `<noscript>` content).
4. **Tokenize** — a token is a maximal run of `[A-Za-z0-9_]` characters.
5. **Lowercase.**
6. **Remove stop words** (case-insensitive comparison).
7. **Stem** with the Porter algorithm.

**Positions** are 1-based and counted *after* stop-word removal (the order of
the words that remain in the document).

Output file formats (tab-separated columns):

```
docids.txt      DOCID  <tab>  file_name
termids.txt     TERMID <tab>  stemmed_term
doc_index.txt   DOCID  <tab>  TERMID  <tab>  pos1  <tab>  pos2 ...
```

## Stage 2 — Indexer

**Input:** the Tokenizer output folder (`doc_index.txt`), an output folder.
**Output:** `term_index.txt`, `term_info.txt`.

For each term, the occurrence list is a sequence of `(DOCID, position)` pairs,
ordered by DOCID then by position, encoded with the **delta technique**. Starting
from `prev_doc = 0`, `prev_pos = 0`, each pair `(doc, pos)` is written as a
`gap:value` group:

- if `doc` is **new** (differs from the previous one): `(doc - prev_doc) : pos`
  — the position is absolute, being the first one in that document;
- if it is the **same** document: `0 : (pos - prev_pos)`
  — the position delta within the document.

Output file formats:

```
term_index.txt  TERMID <tab> gap:pos <tab> gap:pos ...
term_info.txt   TERMID <tab> offset <tab> corpus_frequency <tab> document_count
```

The **offset** is the byte position where the term's line starts in
`term_index.txt`. It lets the Reader read a single inverted list via random
access, without loading the whole file.

## Stage 3 — Reader

An interactive interface over the index. Expects a folder containing
`docids.txt`, `termids.txt`, `term_index.txt`, `term_info.txt`.

### Commands

**`--doc DOCNAME`** — document statistics:

```
Enter command: --doc clueweb12-0000tw-13-04988
Listing for document: clueweb12-0000tw-13-04988
DOCID: 1
Distinct terms: 153
Total terms: 257
```

**`--term TERM`** — term statistics:

```
Enter command: --term chocol
Listing for term: chocol
TERMID: 1
Number of documents containing term: 323
Term frequency in corpus: 25590
Inverted list offset: 0
```

**`--term TERM --doc DOCNAME`** — the term's positions in a document:

```
Enter command: --term chocol --doc clueweb12-0000tw-13-04988
Inverted list for term: chocol
In document: clueweb12-0000tw-13-04988
TERMID: 1
DOCID: 1
Term frequency in document: 24
Positions: 1, 8, 13, 16, 25, 34, 51, 64, 92, 101, 120, 131, 152, 157, 161, 164, 169, 178, 190, 207, 211, 215, 226, 228
```

A term may also be entered in unstemmed form (e.g. `--term chocolate`) — the
Reader stems it and resolves the matching term (`chocol`).

Type `exit` or `quit` to leave.

---

## Memory efficiency

- **Tokenizer** streams documents one at a time and writes results immediately;
  only the compact identifier maps are kept in memory.
- **Indexer** relies on `doc_index.txt` already being ordered by DOCID, so each
  term's occurrences are ordered without an extra sort.
- **Reader** loads only the small maps (`docids`, `termids`, `term_info`) into
  memory. The large `term_index.txt` file is **not** loaded in full:
  - for `--term ... --doc ...` a single line is read via the offset (random
    access),
  - for `--doc` the file is processed line by line (streamed).

---

## Implementation notes

- Documents are processed in a deterministic order (sorted by name), so DOCIDs
  are reproducible across runs.
- The Porter stemmer is a faithful implementation of the classic algorithm,
  verified against the standard test cases.
- HTML is parsed with the built-in `html.parser`, tolerant of malformed markup —
  an error in a single document does not abort processing of the corpus.

