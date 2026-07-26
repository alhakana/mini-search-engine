#!/usr/bin/env python3
"""
Tokenizer
=========

Input:
    - a folder of HTML/WARC corpus documents
    - a stop-words file
    - an output folder

Each document goes through the following lexical pipeline:
    HTML parsing  ->  tokenization  ->  lowercasing
    ->  stop-word removal  ->  Porter stemming

Output files (written to the output folder):
    docids.txt    - mapping DOCID  -> file name
    termids.txt   - mapping TERMID -> stemmed term
    doc_index.txt - forward index: term positions for each (document, term)

Usage:
    python3 tokenizer.py <corpus_folder> <stopwords.txt> <output_folder>

Memory note: documents are processed one at a time (streamed); only the compact
identifier maps are kept in memory, never the document texts themselves.
"""

import os
import re
import sys

from porter import PorterStemmer
from htmlparse import document_to_text

# A token is a maximal run of "word" characters [A-Za-z0-9_].
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def load_stopwords(path):
    """Load the stop words into a set (lowercased, blank lines skipped)."""
    stops = set()
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().lower()
            if w:
                stops.add(w)
    return stops


def read_document(path):
    """Read the raw content of a file as text (tolerant of bad encoding)."""
    with open(path, "rb") as f:
        data = f.read()
    return data.decode("utf-8", errors="ignore")


def process_document(path, stopwords, stemmer):
    """
    Return a dictionary  stem -> [positions]  for a single document.

    Positions are 1-based and counted only over tokens that survive stop-word
    removal (i.e. the order of the words that remain after filtering).
    """
    text = document_to_text(read_document(path))
    positions = {}
    pos = 0
    for match in _TOKEN_RE.finditer(text):
        token = match.group().lower()
        if token in stopwords:
            continue
        stem = stemmer.stem(token)
        if not stem:
            continue
        pos += 1
        positions.setdefault(stem, []).append(pos)
    return positions


def main(argv):
    if len(argv) != 4:
        prog = os.path.basename(argv[0]) if argv else "tokenizer.py"
        sys.stderr.write(
            "Usage: python3 %s <corpus_folder> <stopwords.txt> <output_folder>\n" % prog
        )
        return 1

    corpus_dir, stopwords_path, out_dir = argv[1], argv[2], argv[3]

    if not os.path.isdir(corpus_dir):
        sys.stderr.write("Error: corpus folder does not exist: %s\n" % corpus_dir)
        return 1
    if not os.path.isfile(stopwords_path):
        sys.stderr.write("Error: stop-words file does not exist: %s\n" % stopwords_path)
        return 1
    os.makedirs(out_dir, exist_ok=True)

    stopwords = load_stopwords(stopwords_path)
    stemmer = PorterStemmer()

    # Deterministic document order -> deterministic DOCIDs across runs.
    files = sorted(
        name for name in os.listdir(corpus_dir)
        if os.path.isfile(os.path.join(corpus_dir, name))
    )

    term_ids = {}          # stem -> TERMID (assigned on first occurrence)
    next_term_id = 1

    docids_path = os.path.join(out_dir, "docids.txt")
    doc_index_path = os.path.join(out_dir, "doc_index.txt")
    termids_path = os.path.join(out_dir, "termids.txt")

    total = len(files)
    with open(docids_path, "w", encoding="utf-8") as docids_f, \
         open(doc_index_path, "w", encoding="utf-8") as doc_index_f:

        for docid, name in enumerate(files, start=1):
            path = os.path.join(corpus_dir, name)
            docids_f.write("%d\t%s\n" % (docid, name))

            positions = process_document(path, stopwords, stemmer)

            # Assign TERMIDs to newly seen terms (first-occurrence order).
            for stem in positions:
                if stem not in term_ids:
                    term_ids[stem] = next_term_id
                    next_term_id += 1

            # Forward index: lines sorted by TERMID within each document.
            rows = sorted(
                (term_ids[stem], poss) for stem, poss in positions.items()
            )
            for termid, poss in rows:
                doc_index_f.write(
                    "%d\t%d\t%s\n" % (docid, termid, "\t".join(str(p) for p in poss))
                )

            if docid % 250 == 0 or docid == total:
                sys.stderr.write("  processed %d/%d documents\r" % (docid, total))
                sys.stderr.flush()

    sys.stderr.write("\n")

    # termids.txt: sorted by TERMID in ascending order.
    with open(termids_path, "w", encoding="utf-8") as termids_f:
        for stem, termid in sorted(term_ids.items(), key=lambda kv: kv[1]):
            termids_f.write("%d\t%s\n" % (termid, stem))

    sys.stderr.write(
        "Done: %d documents, %d distinct terms.\n" % (total, len(term_ids))
    )
    sys.stderr.write("Results written to: %s\n" % out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
