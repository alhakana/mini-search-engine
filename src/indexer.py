#!/usr/bin/env python3
"""
Indexer
=======

Builds the delta-encoded inverted index from the forward index (doc_index.txt)
produced by the Tokenizer.

Input:
    - a folder with the Tokenizer results (doc_index.txt is used)
    - an output folder

Output files:
    term_index.txt - inverted index; for each term, its occurrence list encoded
                     with the delta technique
    term_info.txt  - per-term metadata:
                     TERMID <tab> file_offset <tab> corpus_frequency
                     <tab> document_count

Delta encoding:
    A term's occurrence list is a sequence of (DOCID, position) pairs, ordered by
    DOCID then by position. Starting from prev_doc = 0, prev_pos = 0, each pair
    (doc, pos) is written as "gap:value":
      - if doc != prev_doc (a new document):
        (doc - prev_doc) : pos
        (the position is absolute, being the first one in that document)
      - otherwise (same document):
        0 : (pos - prev_pos)
        (the position delta within the same document)
    document_count = number of "gap != 0" entries; corpus_frequency = total
    number of occurrences.

The offset in term_info.txt is the byte position where the corresponding line
starts in term_index.txt, enabling random-access reads of a single list without
loading the whole file.

Usage:
    python3 indexer.py <tokenizer_results_folder> <output_folder>

Memory note: postings are grouped by TERMID. Since doc_index.txt is already
ordered by DOCID, each term's occurrences end up ordered automatically.
"""

import os
import sys


def read_doc_index(path):
    """
    Read doc_index.txt and return a dictionary  TERMID -> [(docid, pos), ...].

    Because doc_index is ordered by (docid, termid) and positions within a line
    are ascending, each term's list is already ordered by docid then position.
    """
    postings = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            docid = int(parts[0])
            termid = int(parts[1])
            lst = postings.get(termid)
            if lst is None:
                lst = []
                postings[termid] = lst
            for p in parts[2:]:
                lst.append((docid, int(p)))
    return postings


def encode_delta(pairs):
    """
    Delta-encode a list of (docid, pos) pairs.
    Return (text_groups, corpus_frequency, document_count).
    """
    groups = []
    prev_doc = 0
    prev_pos = 0
    doc_count = 0
    for doc_id, pos in pairs:
        if doc_id != prev_doc:
            groups.append("%d:%d" % (doc_id - prev_doc, pos))
            doc_count += 1
        else:
            groups.append("0:%d" % (pos - prev_pos))
        prev_doc = doc_id
        prev_pos = pos
    return groups, len(pairs), doc_count


def main(argv):
    if len(argv) != 3:
        prog = os.path.basename(argv[0]) if argv else "indexer.py"
        sys.stderr.write(
            "Usage: python3 %s <tokenizer_results_folder> <output_folder>\n" % prog
        )
        return 1

    in_dir, out_dir = argv[1], argv[2]
    doc_index_path = os.path.join(in_dir, "doc_index.txt")
    if not os.path.isfile(doc_index_path):
        sys.stderr.write("Error: %s not found\n" % doc_index_path)
        return 1
    os.makedirs(out_dir, exist_ok=True)

    sys.stderr.write("Loading forward index...\n")
    postings = read_doc_index(doc_index_path)

    term_index_path = os.path.join(out_dir, "term_index.txt")
    term_info_path = os.path.join(out_dir, "term_info.txt")

    sys.stderr.write("Building inverted index...\n")
    offset = 0
    with open(term_index_path, "w", encoding="utf-8") as ti_f, \
         open(term_info_path, "w", encoding="utf-8") as info_f:

        for termid in sorted(postings.keys()):
            groups, freq, doc_count = encode_delta(postings[termid])
            line = "%d\t%s\n" % (termid, "\t".join(groups))
            ti_f.write(line)
            # term_info: TERMID  offset  corpus_frequency  document_count
            info_f.write("%d\t%d\t%d\t%d\n" % (termid, offset, freq, doc_count))
            # Offset is measured in bytes, so encode the line to count its length.
            offset += len(line.encode("utf-8"))

    sys.stderr.write(
        "Done: %d terms indexed.\nResults written to: %s\n"
        % (len(postings), out_dir)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
