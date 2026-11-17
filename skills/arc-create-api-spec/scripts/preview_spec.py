#!/usr/bin/env python3
"""Writes a self-contained HTML preview of an OpenAPI file (JSON or YAML).

Usage:
  python3 preview_spec.py SPEC [--output FILE.html] [--open]

Standard library only. The page loads nothing: no font, no script, no CDN, no request to the
API. Its design is neutral, with the system font and light or dark mode per system setting.
Labels are English. Exit 0 on success, 2 on wrong usage or an unreadable spec.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_spec import METHODS, read  # noqa: E402

STYLE = """
:root {
  --bg: #fafafa; --surface: #ffffff; --sunken: #f2f2f3; --line: #e2e2e5;
  --text: #1d1d1f; --muted: #5c5c66; --accent: #1f5fbf;
  --get: #e3eefc; --get-text: #174a91; --post: #e3f4e8; --post-text: #1d6b37;
  --put: #fdf0dc; --put-text: #7a4e05; --delete: #fbe4e4; --delete-text: #8f2323;
  --other: #ececef; --other-text: #3f3f46;
  --ok: #e3f4e8; --ok-text: #1d6b37; --warn: #fdf0dc; --warn-text: #7a4e05;
  --err: #fbe4e4; --err-text: #8f2323;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #161618; --surface: #1f1f22; --sunken: #19191b; --line: #34343a;
    --text: #ececef; --muted: #a1a1aa; --accent: #7fb0ff;
    --get: #17304f; --get-text: #a9cbff; --post: #163a24; --post-text: #9fe0b4;
    --put: #3d2e10; --put-text: #f2cf8a; --delete: #3f1a1a; --delete-text: #f4a9a9;
    --other: #2c2c31; --other-text: #d4d4d8;
    --ok: #163a24; --ok-text: #9fe0b4; --warn: #3d2e10; --warn-text: #f2cf8a;
    --err: #3f1a1a; --err-text: #f4a9a9;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); font: 14px/1.5 var(--sans); }
.wrap { max-width: 1200px; margin: 0 auto; padding: 32px 24px 56px; }
header { border-bottom: 1px solid var(--line); padding-bottom: 20px; }
.label { font: 11px/1.4 var(--mono); text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }
h1 { font-size: 28px; line-height: 1.2; margin: 8px 0 0; }
h2 { font-size: 20px; margin: 8px 0; }
h3 { font-size: 17px; margin: 4px 0; }
h4 { font-size: 14px; margin: 16px 0 8px; }
p { margin: 0 0 8px; max-width: 75ch; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
code, .mono { font-family: var(--mono); font-size: 12px; }
.muted { color: var(--muted); }
.layout { display: grid; grid-template-columns: 240px 1fr; gap: 32px; margin-top: 24px; }
nav { position: sticky; top: 16px; align-self: start; max-height: calc(100vh - 32px); overflow-y: auto; font-size: 13px; }
nav ul { list-style: none; margin: 4px 0 16px; padding: 0; }
nav li { padding: 3px 0; }
nav a { color: var(--text); display: flex; gap: 8px; align-items: baseline; }
section { border-top: 1px solid var(--line); padding-top: 24px; margin-top: 40px; }
section:first-child { border-top: 0; margin-top: 0; padding-top: 0; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px; margin-top: 16px; }
.row { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
.path { font-family: var(--mono); font-size: 14px; word-break: break-all; }
.chip { font: 11px/1.6 var(--mono); text-transform: uppercase; border-radius: 3px; padding: 0 5px; white-space: nowrap; }
.m-get { background: var(--get); color: var(--get-text); }
.m-post { background: var(--post); color: var(--post-text); }
.m-put, .m-patch { background: var(--put); color: var(--put-text); }
.m-delete { background: var(--delete); color: var(--delete-text); }
.m-other, .s-1, .s-3 { background: var(--other); color: var(--other-text); }
.s-2 { background: var(--ok); color: var(--ok-text); }
.s-4 { background: var(--warn); color: var(--warn-text); }
.s-5 { background: var(--err); color: var(--err-text); }
.table { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th { text-align: left; font-weight: normal; }
th, td { padding: 6px 12px 6px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
.response { border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }
pre { background: var(--sunken); border: 1px solid var(--line); border-radius: 4px; padding: 12px; overflow-x: auto;
      font: 12px/1.45 var(--mono); margin: 8px 0; }
details summary { cursor: pointer; color: var(--muted); font-size: 13px; margin-top: 8px; }
@media (max-width: 760px) { .layout { grid-template-columns: 1fr; } nav { position: static; max-height: none; } }
@media print { nav { display: none; } .layout { grid-template-columns: 1fr; } .card { break-inside: avoid; } }
"""


def e(text) -> str:
    return html.escape("" if text is None else str(text), quote=True)


def anchor_id(*parts) -> str:
    return "-".join(re.sub(r"[^A-Za-z0-9_-]+", "-", str(t)).strip("-") for t in parts)


def to_json(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, default=str)


class Preview:
    def __init__(self, doc: dict):
        self.doc = doc

    def deref(self, obj):
        """Follows local $ref chains; returns the object or {}."""
        for _ in range(20):
            if not (isinstance(obj, dict) and isinstance(obj.get("$ref"), str) and obj["$ref"].startswith("#/")):
                return obj if isinstance(obj, dict) else {}
            node = self.doc
            for part in obj["$ref"][2:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                node = node.get(part) if isinstance(node, dict) else None
            obj = node
        return {}

    def components(self) -> dict:
        return self.doc.get("components") if isinstance(self.doc.get("components"), dict) else {}

    # -- Building blocks

    def text(self, value, css_class="") -> str:
        if not isinstance(value, str) or not value.strip():
            return ""
        attr = f' class="{css_class}"' if css_class else ""
        return "".join(f"<p{attr}>{e(paragraph).replace(chr(10), '<br>')}</p>"
                       for paragraph in re.split(r"\n\s*\n", value.strip()))

    def render_type(self, schema) -> str:
        if not isinstance(schema, dict):
            return ""
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", 1)[-1]
            return f'<a href="#{anchor_id("schema", name)}"><code>{e(name)}</code></a>'
        type_value = schema.get("type")
        types = type_value if isinstance(type_value, list) else [type_value] if type_value else []
        if "array" in types:
            inner = self.render_type(schema.get("items")) or "<code>any</code>"
            rest = [t for t in types if t != "array"]
            return f"<code>array</code> of {inner}" + "".join(f" | <code>{e(t)}</code>" for t in rest)
        for key in ("oneOf", "anyOf", "allOf"):
            if isinstance(schema.get(key), list):
                parts = [self.render_type(s) for s in schema[key]]
                return f"{e(key)}(" + ", ".join(t for t in parts if t) + ")"
        text = " | ".join(f"<code>{e(t)}</code>" for t in types) or "<code>any</code>"
        if schema.get("format"):
            text += f' <span class="muted">({e(schema["format"])})</span>'
        if isinstance(schema.get("enum"), list):
            text += '<br><span class="muted">' + ", ".join(f"<code>{e(json.dumps(w, ensure_ascii=False))}</code>"
                                                          for w in schema["enum"]) + "</span>"
        return text

    def example_of(self, obj, schema=None):
        for source in (obj, self.deref(schema) if schema is not None else None):
            if not isinstance(source, dict):
                continue
            if "example" in source:
                return True, source["example"]
            examples = source.get("examples")
            if isinstance(examples, list) and examples:
                return True, examples[0]
            if isinstance(examples, dict) and examples:
                first_entry = self.deref(next(iter(examples.values())))
                if "value" in first_entry:
                    return True, first_entry["value"]
        return False, None

    def example_block(self, value, title="Example") -> str:
        return f'<details><summary>{e(title)}</summary><pre>{e(to_json(value))}</pre></details>'

    # -- Page

    def page(self) -> str:
        info = self.doc.get("info") if isinstance(self.doc.get("info"), dict) else {}
        title = info.get("title") or "API"
        groups = self.groups()
        schemas = self.components().get("schemas")
        schemas = schemas if isinstance(schemas, dict) else {}
        parts = [
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{e(title)}: preview</title>",
            f"<style>{STYLE}</style>\n</head>\n<body>\n<div class=\"wrap\">",
            f'<header><div class="label">OpenAPI {e(self.doc.get("openapi", ""))} · version {e(info.get("version", ""))}</div>',
            f"<h1>{e(title)}</h1></header>",
            '<div class="layout">',
            self.navigation(groups, schemas),
            "<main>",
            self.overview(info),
        ]
        for tag, description, ops in groups:
            parts.append(f'<section id="{anchor_id("tag", tag)}"><div class="label">Tag</div><h2>{e(tag)}</h2>')
            parts.append(self.text(description))
            parts.extend(self.operation(path, method, op) for path, method, op in ops)
            parts.append("</section>")
        if schemas:
            parts.append('<section id="schemas"><div class="label">Components</div><h2>Schemas</h2>')
            parts.extend(self.schema_card(name, schema) for name, schema in schemas.items())
            parts.append("</section>")
        parts.append("</main></div></div>\n</body>\n</html>\n")
        return "\n".join(t for t in parts if t)

    def groups(self):
        """[(tag, description, [(path, method, op)])] in the order of the global tags."""
        tags = self.doc.get("tags") if isinstance(self.doc.get("tags"), list) else []
        tag_descriptions = {t.get("name"): t.get("description", "") for t in tags if isinstance(t, dict)}
        ops: dict = {name: [] for name in tag_descriptions}
        paths = self.doc.get("paths") if isinstance(self.doc.get("paths"), dict) else {}
        for path, item in paths.items():
            item = self.deref(item)
            for method in METHODS:
                op = item.get(method)
                if not isinstance(op, dict):
                    continue
                op_tags = op.get("tags") if isinstance(op.get("tags"), list) and op.get("tags") else ["Untagged"]
                # An operation appears under its first tag so that every anchor stays unique.
                ops.setdefault(op_tags[0], []).append((path, method, op))
        return [(tag, tag_descriptions.get(tag, ""), entries) for tag, entries in ops.items() if entries]

    def navigation(self, groups, schemas) -> str:
        parts = ['<nav aria-label="Contents">']
        for tag, _, ops in groups:
            parts.append(f'<div class="label">{e(tag)}</div><ul>')
            for path, method, op in ops:
                parts.append(f'<li><a href="#{anchor_id("op", method, path)}">{self.method_chip(method)}'
                             f'<span>{e(op.get("summary") or path)}</span></a></li>')
            parts.append("</ul>")
        if schemas:
            parts.append('<div class="label">Schemas</div><ul>')
            parts.extend(f'<li><a href="#{anchor_id("schema", n)}"><code>{e(n)}</code></a></li>' for n in schemas)
            parts.append("</ul>")
        parts.append("</nav>")
        return "".join(parts)

    @staticmethod
    def method_chip(method: str) -> str:
        css_class = f"m-{method}" if method in ("get", "post", "put", "patch", "delete") else "m-other"
        return f'<span class="chip {css_class}">{e(method.upper())}</span>'

    def overview(self, info) -> str:
        parts = ['<section id="overview"><div class="label">Overview</div>', self.text(info.get("description"))]
        lines = []
        for server in self.doc.get("servers", []) if isinstance(self.doc.get("servers"), list) else []:
            if isinstance(server, dict):
                lines.append(("Server", f'<code>{e(server.get("url"))}</code> {e(server.get("description", ""))}'))
        contact = info.get("contact") if isinstance(info.get("contact"), dict) else {}
        if contact:
            details = [e(contact.get("name", ""))] + [f"<code>{e(contact[k])}</code>" for k in ("email", "url") if contact.get(k)]
            lines.append(("Contact", ", ".join(a for a in details if a)))
        license_info = info.get("license") if isinstance(info.get("license"), dict) else {}
        if license_info:
            lines.append(("License", e(license_info.get("name", "")) + (f' <code>{e(license_info["url"])}</code>' if license_info.get("url") else "")))
        schemes = self.components().get("securitySchemes")
        if isinstance(schemes, dict) and schemes:
            for name, schema in schemes.items():
                schema = self.deref(schema)
                kind = " ".join(str(schema.get(k)) for k in ("type", "scheme", "in", "name") if schema.get(k))
                lines.append(("Security", f"<code>{e(name)}</code> {e(kind)}"))
        else:
            lines.append(("Security", "no authentication described"))
        parts.append('<div class="table"><table><tbody>')
        parts.extend(f'<tr><th class="label">{e(k)}</th><td>{v}</td></tr>' for k, v in lines)
        parts.append("</tbody></table></div></section>")
        return "".join(parts)

    def operation(self, path, method, op) -> str:
        parts = [f'<article class="card" id="{anchor_id("op", method, path)}">',
                 f'<div class="row">{self.method_chip(method)}<span class="path">{e(path)}</span>'
                 f'<span class="muted mono">{e(op.get("operationId", ""))}</span></div>',
                 f'<h3>{e(op.get("summary", ""))}</h3>' if op.get("summary") else "",
                 self.text(op.get("description"), "muted")]
        item = self.deref((self.doc.get("paths") or {}).get(path))
        raw = (item.get("parameters") or []) + (op.get("parameters") or [])
        parameter = [self.deref(p) for p in raw if isinstance(p, dict)]
        if parameter:
            parts.append("<h4>Parameters</h4>" + self.parameter_table(parameter))
        if "requestBody" in op:
            body = self.deref(op["requestBody"])
            parts.append("<h4>Request body" + (' <span class="muted">required</span>' if body.get("required") else "") + "</h4>")
            parts.append(self.text(body.get("description"), "muted"))
            parts.append(self.render_content(body.get("content")))
        responses = op.get("responses") if isinstance(op.get("responses"), dict) else {}
        if responses:
            parts.append("<h4>Responses</h4>")
            parts.extend(self.render_response(code, response) for code, response in responses.items())
        parts.append("</article>")
        return "".join(t for t in parts if t)

    def parameter_table(self, parameter) -> str:
        lines = ['<div class="table"><table><thead><tr><th class="label">Name</th><th class="label">In</th>'
                  '<th class="label">Type</th><th class="label">Description</th><th class="label">Example</th>'
                  "</tr></thead><tbody>"]
        for p in parameter:
            found, value = self.example_of(p, p.get("schema"))
            required = ' <span class="muted">required</span>' if p.get("required") else ""
            lines.append(f'<tr><td class="mono">{e(p.get("name"))}{required}</td><td class="mono">{e(p.get("in"))}</td>'
                          f'<td>{self.render_type(p.get("schema"))}</td><td>{e(p.get("description", ""))}</td>'
                          f'<td class="mono">{e(json.dumps(value, ensure_ascii=False, default=str)) if found else ""}</td></tr>')
        lines.append("</tbody></table></div>")
        return "".join(lines)

    def render_response(self, code, raw) -> str:
        response = self.deref(raw)
        css_class = f"s-{str(code)[:1]}" if str(code)[:1] in "12345" else "s-3"
        parts = [f'<div class="response"><div class="row"><span class="chip {css_class}">{e(code)}</span>'
                 f'<span>{e(response.get("description", ""))}</span></div>']
        header = response.get("headers") if isinstance(response.get("headers"), dict) else {}
        if header:
            parts.append('<div class="muted">Headers: ' + ", ".join(f"<code>{e(h)}</code>" for h in header) + "</div>")
        parts.append(self.render_content(response.get("content")))
        parts.append("</div>")
        return "".join(parts)

    def render_content(self, content) -> str:
        if not isinstance(content, dict):
            return ""
        parts = []
        for media_type, medium in content.items():
            medium = medium if isinstance(medium, dict) else {}
            parts.append(f'<div class="muted"><code>{e(media_type)}</code> {self.render_type(medium.get("schema"))}</div>')
            found, value = self.example_of(medium, medium.get("schema"))
            if found:
                parts.append(self.example_block(value, f"Example ({media_type})"))
        return "".join(parts)

    def schema_card(self, name, schema) -> str:
        schema = schema if isinstance(schema, dict) else {}
        parts = [f'<article class="card" id="{anchor_id("schema", name)}">',
                 f'<div class="row"><h3><code>{e(name)}</code></h3><span class="muted">{self.render_type(schema)}</span></div>',
                 self.text(schema.get("description"), "muted")]
        props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
        required = set(schema.get("required") or []) if isinstance(schema.get("required"), list) else set()
        if props:
            parts.append('<div class="table"><table><thead><tr><th class="label">Property</th><th class="label">Type</th>'
                         '<th class="label">Description</th></tr></thead><tbody>')
            for prop, sub in props.items():
                sub = sub if isinstance(sub, dict) else {}
                marker = ' <span class="muted">required</span>' if prop in required else ""
                description = sub.get("description") or self.deref(sub).get("description", "")
                parts.append(f'<tr><td class="mono">{e(prop)}{marker}</td><td>{self.render_type(sub)}</td>'
                             f"<td>{e(description)}</td></tr>")
            parts.append("</tbody></table></div>")
        found, value = self.example_of(schema)
        if found:
            parts.append(self.example_block(value))
        parts.append("</article>")
        return "".join(t for t in parts if t)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(description="Write a self-contained HTML preview of an OpenAPI file (JSON or YAML).")
    parser.add_argument("spec", help="path to the OpenAPI file (JSON or YAML)")
    parser.add_argument("--output", metavar="FILE", help="target file; default <spec>.preview.html next to the spec")
    parser.add_argument("--open", action="store_true", help="open the preview with the system's default program")
    args = parser.parse_args(argv)

    spec = Path(args.spec).expanduser()
    if not spec.is_file():
        print(f"Spec not found: {spec}", file=sys.stderr)
        return 2
    doc, problem = read(spec)
    if problem:
        print(f"Spec cannot be read: {problem}", file=sys.stderr)
        return 2
    target = Path(args.output).expanduser() if args.output else spec.with_name(spec.stem + ".preview.html")
    target.write_text(Preview(doc).page(), encoding="utf-8")
    print(f"Preview written: {target.resolve()}")
    if args.open:
        if webbrowser.open(target.resolve().as_uri()):
            print("Opened with the default program.")
        else:
            print("No program found to open it; open the file by hand.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
