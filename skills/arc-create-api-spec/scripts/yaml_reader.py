"""Reads YAML as it appears in OpenAPI files, using only the Python standard library.

Covered: block mappings and sequences (also compact, as in "- name: x"), flow collections
([...] and {...}, also across several lines), single and double quotes, block scalars
(| and > with chomping and indentation indicator), multi-line plain scalars, comments,
anchors, aliases, merge keys (<<), the tag !!str and the other !!-tags (ignored), one document
with optional --- and ... .

Types follow the YAML 1.2 Core Schema: null, true/false, integers, floats, otherwise string.
"yes", "on" or a date stay strings, unlike in PyYAML. Keys always stay strings exactly as
written ("200" stays "200"), so the result matches what JSON gives. Not supported: several
documents, complex keys (?), tabs for indentation.

load(text, make_object=dict) returns the value or raises YamlError with a line number.
make_object receives the pairs of a mapping, like object_pairs_hook in json.loads.
"""

from __future__ import annotations

import re


class YamlError(ValueError):
    def __init__(self, message: str, line: int):
        super().__init__(f"{message} (line {line})")
        self.message = message
        self.line = line


NULL = re.compile(r"^(~|null|Null|NULL|)$")
TRUE = re.compile(r"^(true|True|TRUE)$")
FALSE = re.compile(r"^(false|False|FALSE)$")
INT = re.compile(r"^[-+]?[0-9]+$")
OCTAL = re.compile(r"^0o[0-7]+$")
HEX = re.compile(r"^0x[0-9a-fA-F]+$")
FLOAT = re.compile(r"^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$")
INFINITY = re.compile(r"^([-+]?)\.(inf|Inf|INF)$")
NAN = re.compile(r"^\.(nan|NaN|NAN)$")
BLOCK_HEADER = re.compile(r"^([|>])([+-]?)([1-9]?)([+-]?)\s*(#.*)?$")
ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "t": "\t", "\t": "\t", "n": "\n", "v": "\v", "f": "\f",
           "r": "\r", "e": "\x1b", " ": " ", '"': '"', "/": "/", "\\": "\\", "N": "\x85",
           "_": "\xa0", "L": " ", "P": " "}


def resolve_scalar(text: str):
    """Resolves a plain scalar per the YAML 1.2 Core Schema."""
    if NULL.match(text):
        return None
    if TRUE.match(text):
        return True
    if FALSE.match(text):
        return False
    if INT.match(text):
        return int(text)
    if OCTAL.match(text):
        return int(text[2:], 8)
    if HEX.match(text):
        return int(text[2:], 16)
    if FLOAT.match(text) and any(c.isdigit() for c in text):
        return float(text)
    m = INFINITY.match(text)
    if m:
        return float("-inf") if m.group(1) == "-" else float("inf")
    if NAN.match(text):
        return float("nan")
    return text


def _strip_comment(text: str) -> str:
    """Cuts off a comment after a plain scalar."""
    if text.startswith("#"):
        return ""
    m = re.search(r"[ \t]#", text)
    return (text[: m.start()] if m else text).rstrip()


def _fold(raw: str) -> str:
    """Line breaks in quoted scalars: a single one becomes a space, empty lines become \\n."""
    lines = raw.split("\n")
    if len(lines) == 1:
        return raw
    parts = [lines[0].rstrip(" \t")]
    blank = 0
    for idx, line in enumerate(lines[1:], 1):
        line = line.strip(" \t") if idx < len(lines) - 1 else line.lstrip(" \t")
        if line == "" and idx < len(lines) - 1:
            blank += 1
            continue
        if parts[-1].endswith("\\") and not parts[-1].endswith("\\\\"):
            parts[-1] = parts[-1][:-1]
            parts.append(line)
        else:
            parts.append(("\n" * blank if blank else " ") + line)
        blank = 0
    return "".join(parts)


def _decode_double_quoted(raw: str, line: int) -> str:
    text = _fold(raw)
    out = []
    j = 0
    while j < len(text):
        char = text[j]
        if char != "\\":
            out.append(char)
            j += 1
            continue
        if j + 1 >= len(text):
            raise YamlError("Backslash at the end of a quoted string", line)
        code = text[j + 1]
        if code in ESCAPES:
            out.append(ESCAPES[code])
            j += 2
        elif code in "xuU":
            length = {"x": 2, "u": 4, "U": 8}[code]
            digits = text[j + 2: j + 2 + length]
            if len(digits) != length or not re.fullmatch(r"[0-9a-fA-F]+", digits):
                raise YamlError(f"Invalid escape \\{code}{digits}", line)
            out.append(chr(int(digits, 16)))
            j += 2 + length
        else:
            raise YamlError(f"Unknown escape \\{code}", line)
    return "".join(out)


def _quote_end(text: str, start: int) -> int:
    """Index of the closing quote for the quote at start, otherwise -1."""
    quote = text[start]
    j = start + 1
    while j < len(text):
        if quote == '"' and text[j] == "\\":
            j += 2
            continue
        if text[j] == quote:
            if quote == "'" and j + 1 < len(text) and text[j + 1] == "'":
                j += 2
                continue
            return j
        j += 1
    return -1


def _quote_value(text: str, start: int, end: int, line: int) -> str:
    inner = text[start + 1: end]
    if text[start] == '"':
        return _decode_double_quoted(inner, line)
    return _fold(inner).replace("''", "'")


class _Flow:
    """Parser for flow collections: [a, b], {a: 1, b: [2]}."""

    def __init__(self, text: str, line: int, reader: "_Reader"):
        self.text, self.pos, self.line, self.reader = text, 0, line, reader

    def fail(self, message):
        raise YamlError(message, self.line)

    def skip_space(self):
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char in " \t\n":
                self.pos += 1
            elif char == "#" and (self.pos == 0 or self.text[self.pos - 1] in " \t\n"):
                while self.pos < len(self.text) and self.text[self.pos] != "\n":
                    self.pos += 1
            else:
                break

    def parse_value(self, as_key=False):
        self.skip_space()
        if self.pos >= len(self.text):
            self.fail("Unexpected end inside a flow collection")
        char = self.text[self.pos]
        if char == "[" and not as_key:
            return self.sequence()
        if char == "{" and not as_key:
            return self.mapping()
        if char in "\"'":
            end = _quote_end(self.text, self.pos)
            if end < 0:
                self.fail("Unclosed quote in a flow collection")
            value = _quote_value(self.text, self.pos, end, self.line)
            self.pos = end + 1
            return value
        if char == "*" and not as_key:
            m = re.match(r"\*([^\s,\[\]{}]+)", self.text[self.pos:])
            if not m:
                self.fail("Alias without a name")
            self.pos += m.end()
            return self.reader.alias(m.group(1), self.line)
        start = self.pos
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char in ",[]{}":
                break
            if char == ":" and (self.pos + 1 >= len(self.text) or self.text[self.pos + 1] in " \t\n,[]{}"):
                break
            if char == "#" and self.text[self.pos - 1] in " \t\n":
                break
            self.pos += 1
        raw = " ".join(self.text[start:self.pos].split())
        return raw if as_key else resolve_scalar(raw)

    def sequence(self):
        self.pos += 1
        items = []
        while True:
            self.skip_space()
            if self.pos < len(self.text) and self.text[self.pos] == "]":
                self.pos += 1
                return items
            items.append(self.parse_value())
            self.skip_space()
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
            elif self.pos >= len(self.text) or self.text[self.pos] != "]":
                self.fail("Expected , or ] in a flow sequence")

    def mapping(self):
        self.pos += 1
        pairs = []
        while True:
            self.skip_space()
            if self.pos < len(self.text) and self.text[self.pos] == "}":
                self.pos += 1
                return self.reader.make_object(pairs)
            key = self.parse_value(as_key=True)
            self.skip_space()
            value = None
            if self.pos < len(self.text) and self.text[self.pos] == ":":
                self.pos += 1
                value = self.parse_value()
                self.skip_space()
            pairs.append((str(key), value))
            if self.pos < len(self.text) and self.text[self.pos] == ",":
                self.pos += 1
            elif self.pos >= len(self.text) or self.text[self.pos] != "}":
                self.fail("Expected , or } in a flow mapping")


class _Reader:
    def __init__(self, text: str, make_object):
        self.lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        self.i = 0
        self.anchors: dict = {}
        self.make_object = make_object

    # -- Helpers

    def fail(self, message, line=None):
        raise YamlError(message, (self.i if line is None else line) + 1)

    def at_end(self) -> bool:
        return self.i >= len(self.lines)

    def skip_blank(self):
        while not self.at_end():
            content = self.lines[self.i].strip()
            if content and not content.startswith("#"):
                break
            self.i += 1

    def indentation(self, line: str) -> int:
        n = len(line) - len(line.lstrip(" "))
        if line[n:n + 1] == "\t":
            self.fail("Tabs are not allowed for indentation in YAML")
        return n

    @staticmethod
    def is_sequence(content: str) -> bool:
        return content == "-" or content.startswith("- ") or content.startswith("-\t")

    def alias(self, name, line):
        if name not in self.anchors:
            raise YamlError(f"Unknown alias *{name}", line)
        return self.anchors[name]

    def split_key(self, content: str):
        """Returns (key, rest) for "key: rest", otherwise None."""
        if content[:1] in "\"'":
            end = _quote_end(content, 0)
            if end < 0:
                return None
            after = content[end + 1:].lstrip(" \t")
            if after == ":" or after.startswith(": ") or after.startswith(":\t"):
                return _quote_value(content, 0, end, self.i + 1), after[1:].strip()
            return None
        if content.startswith("? "):
            self.fail("Complex mapping keys (?) are not supported")
        if content[:1] in "[{#&*!|>" or self.is_sequence(content):
            return None
        for j, char in enumerate(content):
            if char == "#" and j > 0 and content[j - 1] in " \t":
                return None
            if char == ":" and (j + 1 == len(content) or content[j + 1] in " \t"):
                return content[:j].rstrip(), content[j + 1:].strip()
        return None

    # -- Structure

    def document(self):
        self.skip_blank()
        while not self.at_end() and self.lines[self.i].startswith("%"):
            self.i += 1
            self.skip_blank()
        if not self.at_end() and re.match(r"^---(\s|$)", self.lines[self.i]):
            rest = self.lines[self.i][3:].strip()
            if rest and not rest.startswith("#"):
                self.lines[self.i] = rest
            else:
                self.i += 1
        value = self.node(0)
        self.skip_blank()
        if not self.at_end():
            line = self.lines[self.i]
            if re.match(r"^---(\s|$)", line):
                self.fail("Several YAML documents in one file are not supported")
            if not re.match(r"^\.\.\.(\s|$)", line):
                self.fail("Unexpected content or indentation")
        return value

    def node(self, min_indent: int):
        self.skip_blank()
        if self.at_end():
            return None
        line = self.lines[self.i]
        indent = self.indentation(line)
        if indent < min_indent:
            return None
        content = line[indent:]
        if indent == 0 and re.match(r"^(---|\.\.\.)(\s|$)", content):
            return None
        if self.is_sequence(content):
            return self.sequence(indent)
        if self.split_key(content) is not None:
            return self.mapping(indent)
        return self.parse_value(content, indent - 1, own_line=True)

    def mapping(self, indent: int):
        pairs = []
        merges = []
        while True:
            self.skip_blank()
            if self.at_end():
                break
            line = self.lines[self.i]
            e = self.indentation(line)
            if e < indent:
                break
            if e > indent:
                self.fail("Unexpected indentation")
            content = line[e:]
            if re.match(r"^(---|\.\.\.)(\s|$)", content) and e == 0:
                break
            if self.is_sequence(content):
                break
            part = self.split_key(content)
            if part is None:
                self.fail("Expected 'key: value'")
            key, rest = part
            value = self.parse_value(rest, indent)
            if key == "<<":
                merges.extend(value if isinstance(value, list) else [value])
            else:
                pairs.append((key, value))
        present = {k for k, _ in pairs}
        for source in merges:
            if isinstance(source, dict):
                for k, v in source.items():
                    if k not in present:
                        pairs.append((k, v))
                        present.add(k)
        return self.make_object(pairs)

    def sequence(self, indent: int):
        items = []
        while True:
            self.skip_blank()
            if self.at_end():
                break
            line = self.lines[self.i]
            e = self.indentation(line)
            if e < indent:
                break
            if e > indent:
                self.fail("Unexpected indentation")
            content = line[e:]
            if not self.is_sequence(content):
                break
            rest = content[1:].lstrip(" \t")
            column = len(line) - len(rest)
            if rest and not rest.startswith("#") and (self.is_sequence(rest) or self.split_key(rest) is not None):
                # Compact form "- name: x" or "- - a": re-indent the line and read it there.
                self.lines[self.i] = " " * column + rest
                items.append(self.node(column))
            else:
                items.append(self.parse_value(rest, indent, in_sequence=True))
        return items

    def parse_value(self, rest: str, indent: int, own_line: bool = False, in_sequence: bool = False):
        """Reads the value that starts with rest on line self.i; indent belongs to the key or dash."""
        line_idx = self.i
        anchor, tag = None, None
        while True:
            m = re.match(r"^&([^\s,\[\]{}]+)\s*", rest)
            if m:
                anchor, rest = m.group(1), rest[m.end():]
                continue
            m = re.match(r"^(![^\s]*)\s*", rest)
            if m:
                tag, rest = m.group(1), rest[m.end():]
                continue
            break
        if rest == "" or rest.startswith("#"):
            self.i += 1
            self.skip_blank()
            value = None
            if not self.at_end():
                next_line = self.lines[self.i]
                e = self.indentation(next_line)
                if e == indent and not (own_line or in_sequence) and self.is_sequence(next_line[e:]):
                    value = self.sequence(indent)
                else:
                    value = self.node(indent + 1)
        elif rest[0] in "|>":
            value = self.block_scalar(rest, indent)
        else:
            value = self.inline(rest, indent, raw=(tag == "!!str"))
        if tag == "!!str" and value is not None and not isinstance(value, str):
            value = str(value)
        if anchor:
            self.anchors[anchor] = value
        if self.i == line_idx:
            self.i += 1
        return value

    def inline(self, rest: str, indent: int, raw: bool = False):
        start_line = self.i
        if rest[0] in "\"'":
            text = rest
            while _quote_end(text, 0) < 0:
                self.i += 1
                if self.at_end():
                    self.fail("Unclosed quote", start_line)
                text += "\n" + self.lines[self.i]
            end = _quote_end(text, 0)
            after = text[end + 1:].strip()
            if after and not after.startswith("#"):
                self.fail("Unexpected text after a quoted string")
            self.i += 1
            return _quote_value(text, 0, end, start_line + 1)
        if rest[0] in "[{":
            text = rest
            while not self._flow_closed(text):
                self.i += 1
                if self.at_end():
                    self.fail("Unclosed flow collection", start_line)
                text += "\n" + self.lines[self.i]
            flow = _Flow(text, start_line + 1, self)
            value = flow.parse_value()
            flow.skip_space()
            if flow.pos < len(text):
                self.fail("Unexpected text after a flow collection")
            self.i += 1
            return value
        if rest[0] == "*":
            name = _strip_comment(rest)[1:]
            self.i += 1
            return self.alias(name, start_line + 1)
        parts = [_strip_comment(rest)]
        self.i += 1
        if not rest.lstrip().startswith("#") and " #" not in rest:
            # Multi-line plain scalar: lines indented further belong to it.
            blank = 0
            while not self.at_end():
                line = self.lines[self.i]
                if line.strip() == "":
                    blank += 1
                    self.i += 1
                    continue
                if self.indentation(line) <= indent or line.strip().startswith("#"):
                    break
                if self.split_key(line.strip()) is not None:
                    self.fail("Unexpected indentation: a 'key: value' line inside a plain scalar")
                parts.append(("\n" * blank if blank else " ") + _strip_comment(line.strip()))
                blank = 0
                self.i += 1
            if blank:
                # Trailing empty lines were not part of the scalar; step back so nothing is lost.
                self.i -= blank
        text = "".join(parts)
        return text if raw else resolve_scalar(text)

    @staticmethod
    def _flow_closed(text: str) -> bool:
        depth, j = 0, 0
        while j < len(text):
            char = text[j]
            if char in "\"'":
                end = _quote_end(text, j)
                if end < 0:
                    return False
                j = end + 1
                continue
            if char == "#" and j > 0 and text[j - 1] in " \t":
                while j < len(text) and text[j] != "\n":
                    j += 1
                continue
            if char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
                if depth == 0:
                    return True
            j += 1
        return False

    def block_scalar(self, header_line: str, indent: int):
        m = BLOCK_HEADER.match(header_line)
        if not m:
            self.fail("Invalid block scalar header")
        style = m.group(1)
        chomping = m.group(2) or m.group(4)
        indent_indicator = int(m.group(3)) if m.group(3) else None
        self.i += 1
        block_indent = max(indent, 0) + indent_indicator if indent_indicator else None
        lines = []
        while not self.at_end():
            line = self.lines[self.i]
            if line.strip() == "":
                lines.append(line[block_indent:] if block_indent and len(line) > block_indent else "")
                self.i += 1
                continue
            e = len(line) - len(line.lstrip(" "))
            if block_indent is None:
                if e <= indent:
                    break
                block_indent = e
            if e < block_indent:
                break
            lines.append(line[block_indent:])
            self.i += 1
        end = len(lines)
        while end and lines[end - 1].strip() == "":
            end -= 1
        trailing = len(lines) - end
        core = lines[:end]
        # Trailing empty lines belong to the block; the caller reads the next line.
        if style == "|":
            text = "\n".join(core)
        else:
            text, blank, prev_more_indented, first = "", 0, False, True
            for line in core:
                if line == "":
                    blank += 1
                    continue
                more_indented = line[:1] in (" ", "\t")
                if not first:
                    if more_indented or prev_more_indented:
                        text += "\n" * (blank + 1)
                    else:
                        text += "\n" * blank if blank else " "
                text += line
                first, blank, prev_more_indented = False, 0, more_indented
        if not core:
            return "\n" * trailing if chomping == "+" else ""
        if chomping == "-":
            return text
        if chomping == "+":
            return text + "\n" * (trailing + 1)
        return text + "\n"


def load(text: str, make_object=dict):
    """Reads one YAML document; mappings are built with make_object(pairs)."""
    if text.startswith("﻿"):
        text = text[1:]
    return _Reader(text, make_object).document()
