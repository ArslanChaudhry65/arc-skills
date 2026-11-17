"""Tests for lint_spec.py, yaml_reader.py and preview_spec.py on the conference specs. Standard library only.

Usage: python3 -m unittest discover -s ~/.claude/skills/arc-create-api-spec/scripts/tests -v

conference-clean.json is the conference API from references/examples/ with no finding except
the intentionally missing authentication and one naming decision: the enum TalkFormat keeps the
domain values (Keynote, Talk, ...) although the standards require lowercase.
conference-clean.yaml is the same content as YAML.
conference-faulty.json is the same spec with planted errors, one rule per error; the list is in
EXPECTED_FAULTY.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent
LINTER = SCRIPTS / "lint_spec.py"
PREVIEW = SCRIPTS / "preview_spec.py"
EXAMPLES = SCRIPTS.parent / "references" / "examples"
RULE_FILES = ["--standards", str(EXAMPLES / "API-standards.md"),
                "--best-practices", str(EXAMPLES / "OpenAPI-best-practices.md")]
NO_AUTH = ["--ignore", "security-global,security-schemes,response-401"]
# Naming decision: the domain wins over the naming rules of the standards.
DOMAIN_WINS = ["--ignore", "enum-casing"]

sys.path.insert(0, str(SCRIPTS))
from yaml_reader import YamlError, load  # noqa: E402

EXPECTED_FAULTY = {
    # Errors
    "duplicate-key", "nullable-3-1", "path-params", "operation-id-unique", "ref-resolvable",
    # Base warnings
    "servers", "contact-properties", "license-url", "schema-example", "property-description",
    "inline-enum", "example-valid", "unused-component", "operation-description", "inline-schema",
    "operation-id", "operation-summary", "operation-tag-defined", "rate-limit-headers",
    "response-429", "response-500",
    # Warnings from API-standards.md
    "enum-casing", "collection-wrapper", "parameter-casing", "error-media-type", "rate-limit-headers-standard",
}
STANDARDS_ONLY = {"enum-casing", "collection-wrapper", "parameter-casing", "error-media-type",
                     "rate-limit-headers-standard"}


def lint(*args):
    proc = subprocess.run([sys.executable, str(LINTER), *args, "--json"],
                          capture_output=True, text=True, encoding="utf-8")
    report = json.loads(proc.stdout) if proc.stdout.strip() else None
    return proc.returncode, report, proc.stderr


def codes(report):
    return {b["rule"] for b in report["findings"]}


class CleanSpec(unittest.TestCase):
    def test_full_score_when_open_api_is_intended(self):
        exit_code, report, _ = lint(str(HERE / "conference-clean.json"), *RULE_FILES, *NO_AUTH, *DOMAIN_WINS)
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["score"], {"overall": 100, "docs": 100, "completeness": 100,
                                            "sdkGeneration": 100, "security": 100})
        self.assertEqual(report["summary"]["ignored"], 11)

    def test_without_ignores_only_auth_and_naming_decision(self):
        exit_code, report, _ = lint(str(HERE / "conference-clean.json"), *RULE_FILES)
        self.assertEqual(exit_code, 0, "warnings alone do not change the exit code")
        self.assertEqual(codes(report), {"security-global", "security-schemes", "response-401", "enum-casing"})
        enum = next(b for b in report["findings"] if b["rule"] == "enum-casing")
        self.assertEqual(enum["location"], "/components/schemas/TalkFormat/enum")

    def test_without_standards_no_naming_decision(self):
        _, report, _ = lint(str(HERE / "conference-clean.json"))
        self.assertNotIn("enum-casing", codes(report))
        self.assertLess(report["score"]["security"], 100)

    def test_yaml_gives_same_report_as_json(self):
        _, from_json, _ = lint(str(HERE / "conference-clean.json"), *RULE_FILES)
        exit_code, from_yaml, _ = lint(str(HERE / "conference-clean.yaml"), *RULE_FILES)
        self.assertEqual(exit_code, 0)
        self.assertEqual(from_yaml["score"], from_json["score"])
        self.assertEqual(from_yaml["findings"], from_json["findings"])


class FaultySpec(unittest.TestCase):
    def test_every_planted_error_is_found(self):
        exit_code, report, _ = lint(str(HERE / "conference-faulty.json"), *RULE_FILES, *NO_AUTH)
        self.assertEqual(exit_code, 1)
        self.assertEqual(EXPECTED_FAULTY - codes(report), set())
        self.assertEqual(report["summary"]["errors"], 5)
        self.assertLess(report["score"]["overall"], 90)

    def test_finding_has_all_fields(self):
        _, report, _ = lint(str(HERE / "conference-faulty.json"))
        for finding in report["findings"]:
            self.assertIn(finding["severity"], ("error", "warning"))
            self.assertTrue(finding["location"] == "" or finding["location"].startswith("/"))
            for field in ("rule", "message", "fix", "source"):
                self.assertTrue(finding[field], f"{field} is missing in {finding}")

    def test_standards_rules_only_with_rule_file(self):
        _, report, _ = lint(str(HERE / "conference-faulty.json"))
        self.assertEqual(codes(report) & STANDARDS_ONLY, set())


class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def write_file(self, name, content):
        path = Path(self.tmpdir.name) / name
        path.write_text(content, encoding="utf-8")
        return str(path)

    def test_broken_json_is_an_error(self):
        exit_code, report, _ = lint(self.write_file("broken.json", '{"openapi": "3.1.0",}'))
        self.assertEqual(exit_code, 1)
        self.assertEqual(codes(report), {"syntax-valid"})
        self.assertEqual(report["score"]["overall"], 0)

    def test_broken_yaml_names_the_line(self):
        exit_code, report, _ = lint(self.write_file("broken.yaml", "openapi: 3.1.0\ninfo:\n  title: x\n   version: 1\n"))
        self.assertEqual(exit_code, 1)
        self.assertEqual(codes(report), {"syntax-valid"})
        self.assertIn("line 4", report["findings"][0]["message"])

    def test_duplicate_key_in_yaml(self):
        _, report, _ = lint(self.write_file("duplicate.yaml", "openapi: 3.1.0\ninfo:\n  title: a\n  title: b\n  version: '1'\n"))
        self.assertIn("duplicate-key", codes(report))

    def test_yaml_version_as_number(self):
        _, report, _ = lint(self.write_file("number.yml", "openapi: 3.1\ninfo: {title: x, version: '1'}\npaths: {}\n"))
        finding = next(b for b in report["findings"] if b["rule"] == "openapi-version")
        self.assertIn("quote the version", finding["message"])

    def test_missing_file(self):
        exit_code, _, _ = lint(str(Path(self.tmpdir.name) / "does-not-exist.json"))
        self.assertEqual(exit_code, 2)

    def test_unknown_rule_in_ignore(self):
        exit_code, _, stderr = lint(str(HERE / "conference-clean.json"), "--ignore", "does-not-exist")
        self.assertEqual(exit_code, 2)
        self.assertIn("does-not-exist", stderr)

    def test_swagger_2_is_not_checked(self):
        exit_code, report, _ = lint(self.write_file("old.json", '{"swagger": "2.0", "info": {}, "paths": {}}'))
        self.assertEqual(exit_code, 1)
        self.assertEqual(codes(report), {"openapi-version"})

    def test_preview_from_yaml_without_external_resources(self):
        target = Path(self.tmpdir.name) / "preview.html"
        proc = subprocess.run([sys.executable, str(PREVIEW), str(HERE / "conference-clean.yaml"), "--output", str(target)],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        page = target.read_text(encoding="utf-8")
        self.assertIn("listSpeakerTalks", page)
        for external in ("http://", "https://", "<script", "<link", "@import", "url("):
            hits = [z for z in page.splitlines() if external in z and "<code>" not in z and "<pre>" not in z]
            if external.startswith("http"):
                # Addresses from the spec appear only as text in <code> or <pre>, never as a resource.
                self.assertFalse([z for z in hits if 'src="http' in z or 'href="http' in z], external)
            else:
                self.assertEqual(hits, [], external)


class YamlReader(unittest.TestCase):
    def test_types_per_yaml_1_2(self):
        value = load("a: 1\nb: true\nc: ~\nd: 1.5\ne: 3.1.0\nf: 2026-02-20\ng: yes\n200: ok\n")
        self.assertEqual(value, {"a": 1, "b": True, "c": None, "d": 1.5, "e": "3.1.0", "f": "2026-02-20",
                                "g": "yes", "200": "ok"})

    def test_block_and_flow(self):
        text = ("lit: |\n  a\n  b\nfold: >-\n  c\n  d\nseq:\n- name: x\n  in: query\n- [1, 'two', {k: v}]\n"
                "q: \"tab\\tend\"\ns: 'it''s'\nanchor: &a {x: 1}\nalias: *a\n")
        self.assertEqual(load(text), {"lit": "a\nb\n", "fold": "c d", "seq": [{"name": "x", "in": "query"}, [1, "two", {"k": "v"}]],
                                       "q": "tab\tend", "s": "it's", "anchor": {"x": 1}, "alias": {"x": 1}})

    def test_error_with_line(self):
        for text, line in (("a:\n\tb: 1\n", 2), ("a: 1\n---\nb: 2\n", 2), ("a: \"open\n", 1)):
            with self.assertRaises(YamlError) as ctx:
                load(text)
            self.assertEqual(ctx.exception.line, line, text)


if __name__ == "__main__":
    unittest.main()
