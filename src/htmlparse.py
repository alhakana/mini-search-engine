"""
Visible-text extraction from raw ClueWeb (WARC) documents.

Each corpus document is a WARC record: WARC headers first, then HTTP headers,
then the HTML payload. The extraction procedure is:

  1) skip all headers by starting at the first line that begins with '<'
     (the start of the HTML, e.g. <!DOCTYPE ...> or <html>),
  2) parse the HTML and keep only the visible body text
     (excluding <head>, <script>, <style> and <noscript> content).

Only the standard library (html.parser) is used, so no installation is required.
"""

from html.parser import HTMLParser

# Tags whose textual content is not part of the visible text.
_SKIP_TAGS = {"script", "style", "noscript", "head"}


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts = []
        self._skip_depth = 0
        self._seen_body = False

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "body":
            self._seen_body = True

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0:
            # A separator between fragments prevents words from merging across tags.
            self._parts.append(data)
            self._parts.append(" ")

    def get_text(self):
        return "".join(self._parts)


def extract_html_body(raw_text):
    """Return the portion of the raw WARC text starting at the first '<' line."""
    lines = raw_text.split("\n")
    collected = []
    started = False
    for line in lines:
        if line.startswith("<"):
            started = True
        if started:
            collected.append(line)
    return "\n".join(collected)


def document_to_text(raw_text):
    """Extract the clean visible text from a raw WARC document."""
    html = extract_html_body(raw_text)
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Malformed HTML must not abort processing of the whole corpus.
        pass
    return parser.get_text()
