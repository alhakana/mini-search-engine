#!/usr/bin/env bash
#
# Helper script that runs the full pipeline:
#   1) extract corpus.tgz (if not already extracted)
#   2) run the Tokenizer
#   3) run the Indexer
#   4) run the Reader (interactive)
#
# Usage:  ./run.sh
#
set -e

# Directory containing this script (the "src" folder).
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root (the folder above "src").
ROOT="$(cd "$HERE/.." && pwd)"

CORPUS_TGZ="$ROOT/corpus.tgz"
STOPWORDS="$ROOT/stopwords.txt"
WORK="$ROOT/work"
CORPUS_DIR="$WORK/corpus"
OUTPUT="$ROOT/output"

echo ">> 1/4  Extracting the corpus"
if [ ! -d "$CORPUS_DIR" ]; then
    mkdir -p "$WORK"
    tar xzf "$CORPUS_TGZ" -C "$WORK"
fi
echo "   documents: $(ls "$CORPUS_DIR" | wc -l | tr -d ' ')"

echo ">> 2/4  Tokenizer"
python3 "$HERE/tokenizer.py" "$CORPUS_DIR" "$STOPWORDS" "$OUTPUT"

echo ">> 3/4  Indexer"
python3 "$HERE/indexer.py" "$OUTPUT" "$OUTPUT"

echo ">> 4/4  Reader (type a command, 'exit' to quit)"
python3 "$HERE/reader.py" "$OUTPUT"
