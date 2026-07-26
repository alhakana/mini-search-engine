#!/usr/bin/env python3
"""
Reader
======

Interactive command-line interface over the index built by the Tokenizer and
Indexer. Expects a folder containing:
    docids.txt, termids.txt        (Tokenizer output)
    term_index.txt, term_info.txt  (Indexer output)

Commands:
    --doc DOCNAME
        Document statistics: DOCID, distinct term count, total term count.

    --term TERM
        Term statistics: TERMID, document count, corpus frequency, and the
        offset of the inverted list in the index file.

    --term TERM --doc DOCNAME
        The exact positions at which the term occurs in the given document.

Other commands: "exit" or "quit" to leave.

Usage:
    python3 reader.py [index_folder]
(if no folder is given, the current directory is used)

Memory note: only the compact maps (docids, termids, term_info) are loaded into
memory. The large term_index.txt file is never loaded in full:
    - for --term TERM --doc: the offset is used to read a single line
      (random access),
    - for --doc: the file is processed line by line (streamed).
"""

import os
import sys

from porter import PorterStemmer


class Index:
    def __init__(self, folder):
        self.folder = folder
        self.term_index_path = os.path.join(folder, "term_index.txt")

        self.docname_to_id = {}
        self.docid_to_name = {}
        self.term_to_id = {}
        self.termid_to_name = {}
        # TERMID -> (offset, corpus_frequency, document_count)
        self.term_info = {}
        self._stemmer = PorterStemmer()

        self._load_docids(os.path.join(folder, "docids.txt"))
        self._load_termids(os.path.join(folder, "termids.txt"))
        self._load_term_info(os.path.join(folder, "term_info.txt"))

    def _load_docids(self, path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                docid = int(parts[0])
                name = parts[1]
                self.docname_to_id[name] = docid
                self.docid_to_name[docid] = name

    def _load_termids(self, path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 2:
                    continue
                termid = int(parts[0])
                term = parts[1]
                self.term_to_id[term] = termid
                self.termid_to_name[termid] = term

    def _load_term_info(self, path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                termid = int(parts[0])
                offset = int(parts[1])
                freq = int(parts[2])
                docs = int(parts[3])
                self.term_info[termid] = (offset, freq, docs)

    # --------------------------------------------------------------------- term

    def resolve_term(self, term):
        """
        Return the TERMID for the given term, or None.
        A direct match is tried first (the term may already be in stemmed form),
        then a match after applying Porter stemming to the query term.
        """
        t = term.lower()
        if t in self.term_to_id:
            return self.term_to_id[t]
        stemmed = self._stemmer.stem(t)
        if stemmed in self.term_to_id:
            return self.term_to_id[stemmed]
        return None

    def read_inverted_list(self, termid):
        """
        Read (via random access) the inverted list for termid and return an
        ordered dictionary  docid -> [positions].  Decodes the delta encoding.
        """
        offset = self.term_info[termid][0]
        with open(self.term_index_path, "rb") as f:
            f.seek(offset)
            raw = f.readline()
        line = raw.decode("utf-8").rstrip("\n")
        parts = line.split("\t")
        result = {}
        cur_doc = 0
        cur_pos = 0
        for group in parts[1:]:
            d_str, p_str = group.split(":")
            d = int(d_str)
            p = int(p_str)
            if d != 0:
                cur_doc += d
                cur_pos = p
                result[cur_doc] = [cur_pos]
            else:
                cur_pos += p
                result[cur_doc].append(cur_pos)
        return result

    def doc_stats(self, docid):
        """
        Compute (distinct_term_count, total_term_count) for a document by
        streaming term_index.txt (without loading the whole file).
        """
        distinct = 0
        total = 0
        with open(self.term_index_path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                cur_doc = 0
                for group in parts[1:]:
                    d_str = group.split(":", 1)[0]
                    d = int(d_str)
                    cur_doc += d
                    if cur_doc > docid:
                        break
                    if cur_doc == docid:
                        if d > 0:
                            distinct += 1
                        total += 1
        return distinct, total


# ------------------------------------------------------------------- commands

def cmd_doc(index, docname):
    docid = index.docname_to_id.get(docname)
    if docid is None:
        return "Document not found: %s" % docname
    distinct, total = index.doc_stats(docid)
    return ("Listing for document: %s\n"
            "DOCID: %d\n"
            "Distinct terms: %d\n"
            "Total terms: %d") % (docname, docid, distinct, total)


def cmd_term(index, term):
    termid = index.resolve_term(term)
    if termid is None:
        return "Term not found: %s" % term
    offset, freq, docs = index.term_info[termid]
    display = index.termid_to_name[termid]
    return ("Listing for term: %s\n"
            "TERMID: %d\n"
            "Number of documents containing term: %d\n"
            "Term frequency in corpus: %d\n"
            "Inverted list offset: %d") % (display, termid, docs, freq, offset)


def cmd_term_doc(index, term, docname):
    termid = index.resolve_term(term)
    if termid is None:
        return "Term not found: %s" % term
    docid = index.docname_to_id.get(docname)
    if docid is None:
        return "Document not found: %s" % docname
    display = index.termid_to_name[termid]
    postings = index.read_inverted_list(termid)
    positions = postings.get(docid)
    if not positions:
        return ("Inverted list for term: %s\n"
                "In document: %s\n"
                "TERMID: %d\n"
                "DOCID: %d\n"
                "Term frequency in document: 0\n"
                "Positions: ") % (display, docname, termid, docid)
    return ("Inverted list for term: %s\n"
            "In document: %s\n"
            "TERMID: %d\n"
            "DOCID: %d\n"
            "Term frequency in document: %d\n"
            "Positions: %s") % (
        display, docname, termid, docid, len(positions),
        ", ".join(str(p) for p in positions),
    )


def parse_and_run(index, line):
    """Parse a command line (--doc / --term) and return the response text."""
    tokens = line.split()
    doc = None
    term = None
    i = 0
    while i < len(tokens):
        if tokens[i] == "--doc":
            if i + 1 >= len(tokens):
                return "Missing document name after --doc"
            if doc is not None:
                return "There cannot be two --doc arguments"
            doc = tokens[i + 1]
            i += 2
        elif tokens[i] == "--term":
            if i + 1 >= len(tokens):
                return "Missing term after --term"
            if term is not None:
                return "There cannot be two --term arguments"
            term = tokens[i + 1]
            i += 2
        else:
            i += 1

    if term is not None and doc is not None:
        return cmd_term_doc(index, term, doc)
    if doc is not None:
        return cmd_doc(index, doc)
    if term is not None:
        return cmd_term(index, term)
    return "Unknown command. Use: --doc DOCNAME | --term TERM | --term TERM --doc DOCNAME"


def main(argv):
    folder = argv[1] if len(argv) > 1 else "."
    for required in ("docids.txt", "termids.txt", "term_index.txt", "term_info.txt"):
        if not os.path.isfile(os.path.join(folder, required)):
            sys.stderr.write(
                "Error: file %s is missing in folder '%s'\n" % (required, folder)
            )
            return 1

    sys.stderr.write("Loading index from: %s\n" % folder)
    index = Index(folder)
    sys.stderr.write(
        "Index loaded: %d documents, %d terms.\n"
        % (len(index.docid_to_name), len(index.termid_to_name))
    )

    while True:
        try:
            line = input("Enter command: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        print(parse_and_run(index, line))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
