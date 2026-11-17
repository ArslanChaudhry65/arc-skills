#!/usr/bin/env python3
"""Lints an OpenAPI 3.x file (JSON or YAML) locally and gives scores in the style of Rate My OpenAPI.

Usage:
  python3 lint_spec.py SPEC [--standards API-standards.md]
                            [--best-practices OpenAPI-best-practices.md]
                            [--ignore CODE[,CODE...]] [--json]

Standard library only, no network. Exit 0 without errors, 1 as soon as there is an error,
2 on wrong usage or a missing file. Warnings do not change the exit code.

The weighting follows the public source code of Rate My OpenAPI
(github.com/zuplo/rate-my-openapi, MIT): deduction of 75 per error, 25 per warning, 10 and 5 per
minor warning; areas info 0.1, servers 0.05, tags 0.05, security 0.05, paths 0.6,
components 0.15. Only rules and weights are taken over, no code.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yaml_reader import YamlError, load as yaml_load  # noqa: E402

DOCS, COMPLETENESS, SDK, SECURITY = "docs", "completeness", "sdkGeneration", "security"
CATEGORIES = (DOCS, COMPLETENESS, SDK, SECURITY)
CATEGORY_NAMES = {DOCS: "Docs", COMPLETENESS: "Completeness", SDK: "SDK Generation", SECURITY: "Security"}
AREA_WEIGHTS = {"info": 0.1, "servers": 0.05, "tags": 0.05, "security": 0.05, "paths": 0.6, "components": 0.15}
METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")
COMPONENT_TYPES = ("schemas", "responses", "parameters", "examples", "requestBodies", "headers",
                     "securitySchemes", "links", "callbacks", "pathItems")

BASE, STANDARDS, BEST_PRACTICES = "base", "standards", "best-practices"
OAS = "OpenAPI 3.x"
GOTCHAS = "SKILL.md, Common Gotchas"
SKILL_RULES = "SKILL.md, Step 2"
BP = "OpenAPI-best-practices.md"
STD = "API-standards.md"


def _rmoa(code: str) -> str:
    return f"Rate My OpenAPI: {code}"


@dataclass(frozen=True)
class Rule:
    code: str
    severity: str          # "error" or "warning"
    weight: int              # deduction per finding, as in RMOA 75, 25, 10 or 5
    categories: tuple
    source: str
    text: str                 # the rule in one sentence
    fix: str
    ruleset: str = BASE         # base, standards or best-practices
    anchor: str | None = None  # text the rule file must contain for the rule to apply


ALL_CATEGORIES = CATEGORIES
RULES: dict[str, Rule] = {}


def _rule(code, severity, weight, categories, source, text, fix, ruleset=BASE, anchor=None):
    RULES[code] = Rule(code, severity, weight, tuple(categories), source, text, fix, ruleset, anchor)


F, W = "error", "warning"

# --- Structure per OpenAPI 3.x; every violation counts in all four categories, like oas3-schema in RMOA.
_rule("syntax-valid", F, 75, ALL_CATEGORIES, OAS, "The file is valid JSON or YAML with an object at the root.",
       "Fix the syntax at the reported line, for example a missing comma, quote or wrong indentation.")
_rule("duplicate-key", F, 75, ALL_CATEGORIES, f"{BP}, Format 6; {OAS}", "No key appears twice in the same object.",
       "Merge or remove the duplicate key.")
_rule("openapi-version", F, 75, ALL_CATEGORIES, OAS, "The openapi field names a version 3.0.x or 3.1.x.",
       'Set "openapi": "3.1.0" at the top; convert Swagger 2.0 to OpenAPI 3 first.')
_rule("info-object", F, 75, ALL_CATEGORIES, OAS, "info exists and has a title and a version.", "Add info with title and version.")
_rule("paths-object", F, 75, ALL_CATEGORIES, OAS, "paths exists (3.0), or one of paths, components, webhooks (3.1).",
       "Add paths with the endpoints from the stories.")
_rule("path-key", F, 75, ALL_CATEGORIES, OAS, "Every path starts with /.", "Start the path with /.")
_rule("ref-resolvable", F, 75, ALL_CATEGORIES, OAS, "Every $ref points to a target that exists.",
       "Create the component or point the $ref to the right name.")
_rule("ref-external", W, 10, (COMPLETENESS,), OAS, "External $refs are not checked.",
       "Pull the component into the file for a complete check.")
_rule("map-ref", F, 75, ALL_CATEGORIES, f"{BP}, Format 16; {OAS}",
       "headers, responses, content, links and callbacks are maps; the whole map is never a $ref.",
       "Write out the keys and put one $ref per entry.")
_rule("operation-responses", F, 75, ALL_CATEGORIES, OAS, "Every operation has responses.",
       "Add responses with at least one success response.")
_rule("response-description", F, 75, ALL_CATEGORIES, OAS, "Every response has a non-empty description.",
       "Add a description that says when this response is returned.")
_rule("parameter-structure", F, 75, ALL_CATEGORIES, OAS,
       "Every parameter has a name, a valid in, and schema or content; path parameters are required.",
       "Add the missing fields; path parameters need required: true.")
_rule("path-params", F, 75, ALL_CATEGORIES, f"{_rmoa('path-params')}; {OAS}",
       "Every placeholder in the path is defined as a path parameter, and the other way round.",
       "Add the parameter with in: path and required: true, or align the placeholder.")
_rule("header-schema", F, 75, ALL_CATEGORIES, f"{BP}, Format 3; {OAS}", "Every header has schema or content.",
       "Add a schema, for example a $ref to a schema with type integer.")
_rule("request-body-content", F, 75, ALL_CATEGORIES, OAS, "A requestBody has content.",
       'Add content with "application/json" and a schema.')
_rule("security-scheme-structure", F, 75, ALL_CATEGORIES, OAS, "Every securityScheme has a valid type and its required fields.",
       "Add the required fields: apiKey name and in, http scheme, oauth2 flows, openIdConnect openIdConnectUrl.")
_rule("security-defined", F, 75, ALL_CATEGORIES, _rmoa("oas3-operation-security-defined"),
       "Every security requirement names a scheme from components.securitySchemes.",
       "Create the scheme under components.securitySchemes or fix the name.")
_rule("operation-id-unique", F, 75, (DOCS, SDK), _rmoa("operation-operationId-unique"),
       "Every operationId is unique.", "Give the second operation its own operationId.")
_rule("component-name", F, 75, (SDK,), _rmoa("redocly-components-invalid-map-name"),
       "Component names use only A-Z a-z 0-9 . _ -.", "Rename the component and update every $ref.")
_rule("nullable-3-1", F, 75, (COMPLETENESS, SDK), f"{GOTCHAS}; {BP}, Format 7", "OpenAPI 3.1 has no nullable keyword.",
       'Remove nullable and write "type": ["string", "null"].')
_rule("type-list-3-0", F, 75, (COMPLETENESS, SDK), OAS, "In OpenAPI 3.0, type is a single string.",
       "Pick one type and set nullable: true, or switch to openapi 3.1.0.")

# --- As in Rate My OpenAPI (Spectral rules and weights from its source code).
_rule("servers", W, 25, ALL_CATEGORIES, _rmoa("oas3-api-servers"), "servers is a non-empty list.",
       'Add servers with at least one entry, for example {"url": "https://api.example.org", "description": "..."}.')
_rule("server-not-example", W, 25, (DOCS, COMPLETENESS), _rmoa("oas3-host-not-example"),
       "The server URL does not point to example.com.",
       "Ask for the real or planned host. If there is none yet, keep the placeholder and ignore this rule.")
_rule("server-trailing-slash", W, 25, (DOCS,), _rmoa("oas3-host-trailing-slash"), "The server URL does not end with /.",
       "Remove the trailing slash.")
_rule("server-https", W, 25, (SECURITY,), _rmoa("owasp:api7:2019-security-hosts-https-oas3"),
       "Every server URL starts with https://.", "Change the URL to https://.")
_rule("server-variables-defined", W, 25, (DOCS, COMPLETENESS), _rmoa("redocly-no-undefined-server-variable"),
       "Every variable in the server URL is described under variables.", "Describe the variable with default and enum.")
_rule("server-variables-enum", W, 25, (DOCS, COMPLETENESS), _rmoa("redocly-no-server-variables-empty-enum"),
       "Every server variable has an enum.", "List the allowed values as enum.")
_rule("info-description", W, 25, (DOCS, COMPLETENESS), _rmoa("info-description"), "info has a non-empty description.",
       "Describe what the API is for and who uses it.")
_rule("info-contact", W, 10, (COMPLETENESS,), f"{_rmoa('info-contact')}; {BP}, Format 8", "info has a contact object.",
       "Add info.contact with name, url and email.")
_rule("contact-properties", W, 10, (DOCS, COMPLETENESS), f"{_rmoa('contact-properties')}; {BP}, Format 12",
       "contact has name, url and email.", "Add the missing fields to info.contact.")
_rule("info-license", W, 10, (COMPLETENESS,), _rmoa("info-license"), "info has a license object.",
       "Add info.license with name and url.")
_rule("license-url", W, 10, (COMPLETENESS,), f"{_rmoa('license-url')}; {BP}, Format 8", "license has a url.",
       "Add info.license.url.")
_rule("tags", W, 25, (DOCS, COMPLETENESS), f"{_rmoa('openapi-tags')}; {BP}, Format 5", "The document has a non-empty tags array.",
       "Add one tag with a description per theme of the stories.")
_rule("tag-description", W, 10, (DOCS, COMPLETENESS), _rmoa("tag-description"), "Every tag has a description.",
       "Give the tag a description.")
_rule("tag-unique", W, 25, (DOCS,), _rmoa("openapi-tags-uniqueness"), "Every tag name is unique.", "Remove the duplicate tag.")
_rule("operation-tags", W, 5, (DOCS, COMPLETENESS, SDK), _rmoa("operation-tags"), "Every operation has at least one tag.",
       "Give the operation the tag of its theme.")
_rule("operation-tag-defined", W, 25, (DOCS, COMPLETENESS), _rmoa("operation-tag-defined"),
       "Every tag of an operation is defined in the top-level tags.", "Add the tag with a description to the top-level tags.")
_rule("operation-summary", W, 25, (DOCS, COMPLETENESS), f"{_rmoa('redocly-operation-summary')}; {BP}, Format 9",
       "Every operation has a summary.", "Add a short summary, for example the title of the story.")
_rule("operation-description", W, 25, (DOCS, COMPLETENESS), f"{_rmoa('operation-description')}; {GOTCHAS}",
       "Every operation has a description.", "Describe what the operation does, which inputs it takes and what it returns.")
_rule("operation-id", W, 25, (DOCS, COMPLETENESS, SDK), f"{_rmoa('operation-operationId')}; {GOTCHAS}",
       "Every operation has an operationId.", "Add a camelCase operationId, for example listTalks.")
_rule("operation-id-url", W, 25, (DOCS, SDK), _rmoa("operation-operationId-valid-in-url"),
       "The operationId contains only characters allowed in a URL.", "Remove spaces and special characters from the operationId.")
_rule("operation-id-casing", W, 10, (SDK,), f"{SKILL_RULES}, Naming Rules", "The operationId is camelCase.",
       "Write the operationId as a camelCase verb, for example getTalk.")
_rule("name-length", W, 10, (SDK,), _rmoa("apimatic-*-max-length"),
       "operationIds and parameter, header and component names have at most 50 characters.", "Shorten the name.")
_rule("operation-success-response", W, 25, (DOCS, COMPLETENESS, SDK), _rmoa("operation-success-response"),
       "Every operation has a 2xx or 3xx response.", "Add the success response.")
_rule("operation-4xx-response", W, 10, (DOCS, COMPLETENESS, SECURITY), f"{_rmoa('operation-4xx-response')}; {GOTCHAS}",
       "Every operation has at least one 4xx response.", "Add the fitting error responses, for example 400 or 404.")
_rule("response-401", W, 25, (SECURITY,), _rmoa("owasp:api3:2019-define-error-responses-401"),
       "Every operation has a 401 response with content.",
       "Add 401 as a $ref to a shared error response. If the API intentionally has no authentication, ask the user and ignore response-401.")
_rule("response-500", W, 25, (SECURITY,), _rmoa("owasp:api3:2019-define-error-responses-500"),
       "Every operation has a 500 response with content.", "Add 500 as a $ref to a shared error response.")
_rule("response-429", W, 10, (SECURITY,), _rmoa("owasp:api4:2019-rate-limit-responses-429"),
       "Every operation has a 429 response with content.", "Add 429 as a $ref to a shared error response with Retry-After.")
_rule("rate-limit-headers", W, 10, (SECURITY,), _rmoa("owasp:api4:2019-rate-limit"),
       "Every 2xx and 4xx response has a rate limit header (X-RateLimit-Limit or RateLimit-Limit).",
       "Add X-RateLimit-Limit as a $ref to components/headers.")
_rule("retry-after", W, 10, (SECURITY,), _rmoa("owasp:api4:2019-rate-limit-retry-after"),
       "Every 429 response has a Retry-After header.", "Add Retry-After as a $ref to components/headers.")
_rule("security-global", W, 25, (SECURITY,), _rmoa("apimatic-security-defined"),
       "security is a non-empty list at the top level.",
       "Apply the scheme from components.securitySchemes globally. If the API is intentionally public, ask the user and ignore this rule.")
_rule("security-schemes", W, 25, (SECURITY,), GOTCHAS, "components.securitySchemes exists and is not empty.",
       "Add the method from the API standards as a securityScheme.")
_rule("no-http-basic", W, 25, (SECURITY,), _rmoa("owasp:api2:2019-no-http-basic"), "No securityScheme uses HTTP Basic.",
       "Use another method, for example Bearer or OAuth 2.0.")
_rule("id-numeric", W, 25, (SECURITY,), _rmoa("owasp:api1:2019-no-numeric-ids"),
       "ID parameters are not integers; a format is uuid.", 'Set the schema to "type": "string", "format": "uuid".')
_rule("parameter-description", W, 25, (DOCS, COMPLETENESS), f"{_rmoa('oas3-parameter-description')}; {GOTCHAS}",
       "Every parameter has a description.", "Add a description that names the effect and the allowed values.")
_rule("parameter-name", W, 25, ALL_CATEGORIES, _rmoa("speakeasy-parameter-name-nonempty"), "No parameter name is empty.",
       "Give the parameter a name.")
_rule("inline-schema", W, 10, (SDK,), f"{_rmoa('apimatic-no-inline-*-schema')}; {GOTCHAS}",
       "Schemas in parameters, requestBody and responses under paths are not inline.",
       "Move the schema to components/schemas and reference it with $ref.")
_rule("unused-component", W, 25, (SDK,), f"{_rmoa('oas3-unused-component')}; {GOTCHAS}",
       "Every component is referenced at least once.", "Reference the component or remove it.")
_rule("example-valid", W, 25, (DOCS, COMPLETENESS), _rmoa("oas3-valid-schema-example"), "Every example matches its schema.",
       "Align the example with type, format, enum and required fields of the schema.")
_rule("typed-enum", W, 25, (DOCS, SDK), _rmoa("typed-enum"), "Every enum value has the type of the schema.",
       "Align the values with type or fix type.")
_rule("enum-unique", W, 25, (DOCS,), _rmoa("duplicated-entry-in-enum"), "No enum value appears twice.",
       "Remove the duplicate value.")
_rule("path-trailing-slash", W, 25, (DOCS,), _rmoa("path-keys-no-trailing-slash"), "No path ends with /.",
       "Remove the trailing slash.")
_rule("path-query", W, 25, (DOCS,), _rmoa("path-not-include-query"), "No path contains a query string.",
       "Describe the query part as a parameter with in: query.")
_rule("path-ambiguous", W, 25, (DOCS, SDK), _rmoa("no-ambiguous-paths"),
       "No two paths differ only in the name of a placeholder.", "Merge the paths or make them distinct.")
_rule("path-without-operation", W, 25, (DOCS, COMPLETENESS), OAS, "Every path has at least one operation.",
       "Add the operation or remove the path.")
_rule("markdown-script", W, 25, ALL_CATEGORIES, _rmoa("no-script-tags-in-markdown / no-eval-in-markdown"),
       "No description contains <script> or eval(.", "Remove the code from the description.")

# --- From SKILL.md and the gotchas: what RMOA does not check but the best practices require.
_rule("schema-description", W, 25, (DOCS, COMPLETENESS), f"{GOTCHAS}; {BP}, Format 1",
       "Every schema under components has a description.", "Describe what the schema stands for.")
_rule("property-description", W, 25, (DOCS, COMPLETENESS), f"{GOTCHAS}; {BP}, Format 1", "Every property has a description.",
       "Add a description, taken from the domain model.")
_rule("header-description", W, 25, (DOCS, COMPLETENESS), GOTCHAS, "Every header has a description.", "Add a description.")
_rule("request-body-description", W, 10, (DOCS,), f"{BP}, Format 1", "Every requestBody has a description.",
       "Add a description.")
_rule("server-description", W, 10, (DOCS,), f"{SKILL_RULES}, Structure", "Every server has a description.",
       "Add a description, for example Production.")
_rule("schema-example", W, 25, (DOCS, COMPLETENESS), f"{GOTCHAS}; {BP}, Format 2",
       "Every schema and property has an example, unless an example higher up covers it.",
       "Add a realistic example from the domain model.")
_rule("parameter-example", W, 25, (DOCS, COMPLETENESS), f"{GOTCHAS}; {BP}, Format 2",
       "Every parameter has an example, on the parameter or on its schema.", "Add a realistic example.")
_rule("inline-enum", W, 10, (SDK,), f"{SKILL_RULES}, Schema Generation Rules; {BP}, Format 17",
       "An enum is its own schema under components/schemas, not inline in a property.",
       "Create the enum as a schema and reference it with $ref.")

# --- From API-standards.md; apply only with --standards and when the anchor is in the file.
_rule("path-prefix", W, 25, (DOCS,), f"{STD}, Paths 1", "Paths do not start with /api.",
       "Remove the prefix from the paths; it belongs in the server URL.", STANDARDS, "/api")
_rule("path-version", W, 25, (DOCS,), f"{STD}, Paths 2", "Paths contain no version number such as /v1.",
       "Remove the version from the path unless it is required.", STANDARDS, "/v1")
_rule("path-casing", W, 25, (DOCS, SDK), f"{STD}, Casing", "Path segments are lowercase, multi-word ones in kebab-case.",
       "Rename the segment, for example /line-items.", STANDARDS, "kebab-case")
_rule("parameter-casing", W, 25, (DOCS, SDK), f"{STD}, Casing", "Path and query parameters are camelCase, acronyms as words.",
       "Rename the parameter, for example talkId instead of talk_id or talkID.", STANDARDS, "camelCase")
_rule("property-casing", W, 25, (DOCS, SDK), f"{STD}, Casing", "Property names are camelCase, acronyms as words.",
       "Rename the property, for example trackId instead of trackID.", STANDARDS, "camelCase")
_rule("enum-casing", W, 25, (DOCS,), f"{STD}, Casing", "Enum values are lowercase words.",
       "Write the values in lowercase, for example keynote instead of Keynote.", STANDARDS, "lowercase words")
_rule("boolean-naming", W, 10, (DOCS,), f"{STD}, Naming Conventions 5", "Boolean properties have no is or has prefix.",
       "Rename, for example completed instead of isCompleted.", STANDARDS, "isComplete")
_rule("id-uuid", W, 25, (SECURITY, COMPLETENESS), f"{STD}, IDs", "ID parameters have format uuid.",
       'Set the schema to "type": "string", "format": "uuid".', STANDARDS, "UUID")
_rule("error-media-type", W, 25, (DOCS, COMPLETENESS), f"{STD}, Errors", "4xx and 5xx responses use application/problem+json.",
       "Set the media type of the error response to application/problem+json.", STANDARDS, "application/problem+json")
_rule("collection-wrapper", W, 25, (COMPLETENESS, SDK), f"{STD}, Collections & Pagination 1",
       "A list comes in a wrapper object, never as a bare array.", "Create a collection schema with data and meta.",
       STANDARDS, "bare arrays")
_rule("collection-total-count", W, 25, (COMPLETENESS,), f"{STD}, Collections & Pagination 2",
       "A collection wrapper has meta.totalCount.", "Add meta with totalCount, limit and offset.", STANDARDS, "totalCount")
_rule("collection-pagination", W, 25, (COMPLETENESS,), f"{STD}, Collections & Pagination 3", "A list takes offset and limit.",
       "Add offset and limit as $refs to components/parameters.", STANDARDS, "offset")
_rule("rate-limit-headers-standard", W, 25, (SECURITY,), f"{STD}, Rate Limiting 1",
       "Every 2xx and 4xx response has X-RateLimit-Limit, X-RateLimit-Remaining and Retry-After.",
       "Add the missing headers as $refs to components/headers.", STANDARDS, "X-RateLimit-Remaining")
_rule("post-created", W, 25, (COMPLETENESS,), f"{STD}, Methods 2", "POST answers with 201 and a Location header, or with 202.",
       "Add 201 with a Location header.", STANDARDS, "Location")
_rule("delete-no-content", W, 25, (COMPLETENESS,), f"{STD}, Methods 4", "DELETE answers with 204.",
       "Add 204 without content.", STANDARDS, "DELETE returns 204")
_rule("patch-merge", W, 25, (COMPLETENESS,), f"{STD}, Methods 1", "PATCH takes application/merge-patch+json.",
       "Use PUT, or set the media type to application/merge-patch+json.", STANDARDS, "merge-patch")
_rule("api-key-in-url", W, 25, (SECURITY,), f"{STD}, Security 5", "No key or token is passed in the URL.",
       "Send the key in the Authorization header.", STANDARDS, "in URLs")
_rule("api-key-header", W, 25, (SECURITY,), f"{STD}, Security 3", "An API key goes in the Authorization header, not in X-Api-Key.",
       "Change the scheme to type http, scheme bearer.", STANDARDS, "X-Api-Key")

# --- From OpenAPI-best-practices.md; apply only with --best-practices and when the anchor is in the file.
_rule("response-403", W, 25, (SECURITY,), f"{BP}, Format 19", "Every secured operation has 401 and 403.",
       "Add 403 as a $ref to a shared error response.", BEST_PRACTICES, "403")
_rule("operation-description-agent", W, 25, (DOCS,), f"{BP}, Format 21",
       "The description of an operation says more than the summary and names its filters.",
       "Add what the operation does, which filters exist and what it returns.", BEST_PRACTICES, "Agent-readiness")

# --- Helpers -----------------------------------------------------------------------------------


class JsonObject(dict):
    """A JSON or YAML object that remembers duplicate keys."""

    duplicates: list


def _make_object(pairs):
    obj = JsonObject()
    obj.duplicates = []
    for key, value in pairs:
        if key in obj:
            obj.duplicates.append(key)
        obj[key] = value
    return obj


def pointer(*parts) -> str:
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in parts)


def segments(ptr: str) -> list[str]:
    if not ptr:
        return []
    return [s.replace("~1", "/").replace("~0", "~") for s in ptr.split("/")[1:]]


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def short(value, length=40) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text if len(text) <= length else text[: length - 3] + "..."


UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:\S+$")
CAMEL = re.compile(r"^[a-z][a-zA-Z0-9]*$")
OPID_URL = re.compile(r"^[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=]*$")
COMPONENT_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")


@dataclass
class Finding:
    rule: Rule
    location: str
    message: str


class Linter:
    def __init__(self, doc, rule_texts: dict[str, str | None]):
        self.doc = doc
        self.rule_texts = rule_texts  # ruleset -> content of the rule file, or None
        self.findings: list[Finding] = []
        self._seen: set[tuple[str, str]] = set()
        self.referenced: set[str] = set()
        self.version = ""

    # -- Reporting

    def is_active(self, rule: Rule) -> bool:
        if rule.ruleset == BASE:
            return True
        text = self.rule_texts.get(rule.ruleset)
        if text is None:
            return False
        return rule.anchor is None or rule.anchor.lower() in text.lower()

    def report(self, code: str, location: str, message: str) -> None:
        rule = RULES[code]
        if not self.is_active(rule) or (code, location) in self._seen:
            return
        self._seen.add((code, location))
        self.findings.append(Finding(rule, location, message))

    # -- References

    def resolve_ref(self, ref: str):
        if not isinstance(ref, str) or not ref.startswith("#"):
            return None
        node = self.doc
        for part in segments(ref[1:]):
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
                node = node[int(part)]
            else:
                return None
        return node

    def resolve(self, obj, ptr: str):
        """Follows $ref chains; returns (object, pointer), or (None, ptr) for a broken reference."""
        for _ in range(20):
            if not (isinstance(obj, dict) and isinstance(obj.get("$ref"), str)):
                return obj, ptr
            ref = obj["$ref"]
            target = self.resolve_ref(ref)
            if target is None:
                return None, ptr
            obj, ptr = target, ref[1:]
        return None, ptr

    def components(self) -> dict:
        return self.doc.get("components") if isinstance(self.doc.get("components"), dict) else {}

    # -- Run

    def check(self) -> None:
        self.walk_all(self.doc, "")
        if not self.check_version():
            return
        self.check_info()
        self.check_servers()
        self.check_tags()
        self.check_security()
        self.check_components()
        self.check_paths()
        self.check_unused()

    def walk_all(self, node, ptr: str, parent: str = "") -> None:
        if isinstance(node, dict):
            for key in getattr(node, "duplicates", []):
                self.report("duplicate-key", ptr, f'The key "{key}" appears more than once in this object.')
            ref = node.get("$ref")
            if isinstance(ref, str):
                if ref.startswith("#"):
                    if self.resolve_ref(ref) is None:
                        self.report("ref-resolvable", pointer(*segments(ptr), "$ref"), f"{ref} points nowhere.")
                    else:
                        self.referenced.add(ref[1:])
                else:
                    self.report("ref-external", pointer(*segments(ptr), "$ref"), f"{ref} is external and was not checked.")
            discriminator = node.get("discriminator")
            mapping = discriminator.get("mapping") if isinstance(discriminator, dict) else None
            if isinstance(mapping, dict):
                for value in mapping.values():
                    if isinstance(value, str) and value.startswith("#"):
                        self.referenced.add(value[1:])
            for key, value in node.items():
                if key in ("example", "default", "const", "enum") or key.startswith("x-"):
                    continue
                if key == "value" and parent == "examples-entry":
                    continue
                child_ptr = pointer(*segments(ptr), key)
                if key in ("headers", "responses", "content", "links", "callbacks") \
                        and isinstance(value, dict) and "$ref" in value and parent != "properties":
                    self.report("map-ref", child_ptr, f"{key} is a map but is included as a whole with $ref.")
                if key == "description" and isinstance(value, str) and parent != "properties":
                    if re.search(r"<script|eval\(", value, re.IGNORECASE):
                        self.report("markdown-script", child_ptr, "The description contains <script> or eval(.")
                self.walk_all(value, child_ptr, key if parent != "examples" else "examples-entry")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                if parent == "examples":
                    continue
                self.walk_all(value, pointer(*segments(ptr), i), parent)

    def check_version(self) -> bool:
        doc = self.doc
        if "swagger" in doc:
            self.report("openapi-version", "/swagger", f"Swagger {doc['swagger']} is not checked, only OpenAPI 3.x.")
            return False
        version = doc.get("openapi")
        if not isinstance(version, str) or not re.match(r"^3\.[01]\.\d+", version):
            hint = " In YAML, quote the version or write it with three parts, such as 3.1.0." \
                if isinstance(version, float) else ""
            self.report("openapi-version", "/openapi", f"openapi is {short(version)}, expected 3.0.x or 3.1.x.{hint}")
            return False
        self.version = "3.1" if version.startswith("3.1") else "3.0"
        if self.version == "3.0" and not isinstance(doc.get("paths"), dict):
            self.report("paths-object", "/paths", "paths is missing; OpenAPI 3.0 requires it.")
        if self.version == "3.1" and not any(isinstance(doc.get(k), dict) for k in ("paths", "components", "webhooks")):
            self.report("paths-object", "/paths", "There are no paths, components or webhooks.")
        return True

    # -- Areas

    def check_info(self) -> None:
        info = self.doc.get("info")
        if not isinstance(info, dict):
            self.report("info-object", "/info", "info is missing.")
            return
        for field in ("title", "version"):
            if not _text(info.get(field)):
                self.report("info-object", pointer("info", field), f"info.{field} is missing or empty.")
        if not _text(info.get("description")):
            self.report("info-description", "/info/description", "info has no description.")
        contact = info.get("contact")
        if not isinstance(contact, dict):
            self.report("info-contact", "/info/contact", "info.contact is missing.")
        else:
            missing = [f for f in ("name", "url", "email") if not _text(contact.get(f))]
            if missing:
                self.report("contact-properties", "/info/contact", f"info.contact lacks: {', '.join(missing)}.")
        license_info = info.get("license")
        if not isinstance(license_info, dict):
            self.report("info-license", "/info/license", "info.license is missing.")
        elif not _text(license_info.get("url")):
            self.report("license-url", "/info/license/url", "info.license has no url.")

    def check_servers(self) -> None:
        server = self.doc.get("servers")
        if not isinstance(server, list) or not server:
            self.report("servers", "/servers", "servers is missing or empty.")
            return
        for i, entry in enumerate(server):
            ptr = pointer("servers", i)
            if not isinstance(entry, dict) or not _text(entry.get("url")):
                self.report("servers", ptr, "The server has no url.")
                continue
            url = entry["url"]
            url_ptr = pointer("servers", i, "url")
            if re.search(r"(^|[/.])example\.com", url):
                self.report("server-not-example", url_ptr, f"{url} is a placeholder.")
            if url.endswith("/"):
                self.report("server-trailing-slash", url_ptr, f"{url} ends with /.")
            if not url.startswith("https:"):
                self.report("server-https", url_ptr, f"{url} does not start with https://.")
            if not _text(entry.get("description")):
                self.report("server-description", ptr, "The server has no description.")
            variables = entry.get("variables") if isinstance(entry.get("variables"), dict) else {}
            for name in re.findall(r"\{([^}]+)\}", url):
                if name not in variables:
                    self.report("server-variables-defined", ptr, f"The variable {{{name}}} is not described.")
            for name, var in variables.items():
                if not isinstance(var, dict) or "enum" not in var:
                    self.report("server-variables-enum", pointer("servers", i, "variables", name),
                               f"The variable {name} has no enum.")

    def check_tags(self) -> None:
        tags = self.doc.get("tags")
        if not isinstance(tags, list) or not tags:
            self.report("tags", "/tags", "tags is missing or empty.")
            return
        names = set()
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                continue
            name = tag.get("name")
            if name in names:
                self.report("tag-unique", pointer("tags", i), f"The tag {name} appears twice.")
            names.add(name)
            if not _text(tag.get("description")):
                self.report("tag-description", pointer("tags", i), f"The tag {name} has no description.")

    def check_security(self) -> None:
        schemes = self.components().get("securitySchemes")
        schemes = schemes if isinstance(schemes, dict) else {}
        top_level = self.doc.get("security")
        if not isinstance(top_level, list) or not top_level or all(isinstance(a, dict) and not a for a in top_level):
            self.report("security-global", "/security", "No security is set at the top level.")
        if not schemes:
            self.report("security-schemes", "/components/securitySchemes", "There are no securitySchemes.")
        required = {"apiKey": ("name", "in"), "http": ("scheme",), "oauth2": ("flows",),
                   "openIdConnect": ("openIdConnectUrl",), "mutualTLS": ()}
        for name, schema in schemes.items():
            schema, ptr = self.resolve(schema, pointer("components", "securitySchemes", name))
            if not isinstance(schema, dict):
                continue
            type_name = schema.get("type")
            if type_name not in required:
                self.report("security-scheme-structure", ptr, f"type {short(type_name)} is not a valid type.")
                continue
            for field in required[type_name]:
                if field not in schema:
                    self.report("security-scheme-structure", ptr, f"Type {type_name} lacks {field}.")
            if type_name == "http" and str(schema.get("scheme", "")).lower() == "basic":
                self.report("no-http-basic", ptr, f"{name} uses HTTP Basic.")
            if type_name == "apiKey" and schema.get("in") == "query":
                self.report("api-key-in-url", ptr, f"{name} expects the key in the query.")
            if type_name == "apiKey" and schema.get("in") == "header" and str(schema.get("name", "")).lower() != "authorization":
                self.report("api-key-header", ptr, f"{name} expects the key in the header {schema.get('name')}.")
        requirements = [("/security", top_level)]
        for path, _, method, op in self.operations():
            requirements.append((pointer("paths", path, method, "security"), op.get("security")))
        for ptr, entries in requirements:
            if not isinstance(entries, list):
                continue
            for i, requirement in enumerate(entries):
                if isinstance(requirement, dict):
                    for name in requirement:
                        if name not in schemes:
                            self.report("security-defined", pointer(*segments(ptr), i), f"The scheme {name} is not defined.")
                        else:
                            self.referenced.add(pointer("components", "securitySchemes", name))

    def check_components(self) -> None:
        components = self.components()
        for kind in COMPONENT_TYPES:
            entries = components.get(kind)
            if not isinstance(entries, dict):
                continue
            for name, value in entries.items():
                ptr = pointer("components", kind, name)
                if not COMPONENT_NAME.match(name):
                    self.report("component-name", ptr, f"The name {name} contains characters that are not allowed.")
                if len(name) > 50:
                    self.report("name-length", ptr, f"The name {name} has {len(name)} characters.")
                if isinstance(value, dict) and "$ref" in value:
                    continue
                if kind == "schemas":
                    self.check_schema_root(value, ptr, covered=False, is_component=True)
                elif kind == "parameters":
                    self.check_parameter(value, ptr, under_paths=False)
                elif kind == "headers":
                    self.check_header(name, value, ptr)
                elif kind == "responses":
                    self.check_response(value, ptr, under_paths=False)
                elif kind == "requestBodies":
                    self.check_request_body(value, ptr, under_paths=False)

    def operations(self):
        paths = self.doc.get("paths")
        if not isinstance(paths, dict):
            return
        for path, item in paths.items():
            if not isinstance(item, dict):
                continue
            for method in METHODS:
                if isinstance(item.get(method), dict):
                    yield path, item, method, item[method]

    def check_paths(self) -> None:
        paths = self.doc.get("paths")
        if not isinstance(paths, dict):
            return
        normalized: dict[str, str] = {}
        operation_ids: dict[str, str] = {}
        for path, item in paths.items():
            ptr = pointer("paths", path)
            if not path.startswith("/"):
                self.report("path-key", ptr, f"{path} does not start with /.")
            if len(path) > 1 and path.endswith("/"):
                self.report("path-trailing-slash", ptr, f"{path} ends with /.")
            if "?" in path:
                self.report("path-query", ptr, f"{path} contains a query string.")
            template = re.sub(r"\{[^}]+\}", "{}", path)
            if template in normalized:
                self.report("path-ambiguous", ptr, f"{path} cannot be told apart from {normalized[template]}.")
            normalized.setdefault(template, path)
            self.check_path_names(path, ptr)
            if not isinstance(item, dict):
                continue
            if "$ref" in item:
                item, _ = self.resolve(item, ptr)
                if not isinstance(item, dict):
                    continue
            path_params = self.resolve_parameters(item.get("parameters"), pointer("paths", path, "parameters"))
            methods = [m for m in METHODS if isinstance(item.get(m), dict)]
            if not methods:
                self.report("path-without-operation", ptr, f"{path} has no operation.")
            for method in methods:
                op_ptr = pointer("paths", path, method)
                op = item[method]
                op_params = self.resolve_parameters(op.get("parameters"), pointer("paths", path, method, "parameters"))
                parameter = {(p.get("name"), p.get("in")): (p, pp) for p, pp in path_params}
                parameter.update({(p.get("name"), p.get("in")): (p, pp) for p, pp in op_params})
                self.check_path_params(path, op_ptr, parameter)
                self.check_operation(path, method, op, op_ptr, list(parameter.values()), operation_ids)

    def check_path_names(self, path: str, ptr: str) -> None:
        parts = [t for t in path.split("/") if t]
        if parts and parts[0].lower() == "api":
            self.report("path-prefix", ptr, f"{path} starts with /api.")
        for part in parts:
            if re.fullmatch(r"[vV]\d+", part):
                self.report("path-version", ptr, f"{path} contains the version /{part}.")
            elif part.startswith("{"):
                name = part.strip("{}")
                if not CAMEL.match(name) or re.search(r"[A-Z]{2}", name):
                    self.report("parameter-casing", ptr, f"The placeholder {{{name}}} is not camelCase.")
            elif not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", part):
                self.report("path-casing", ptr, f"The segment {part} is not lowercase kebab-case.")

    def resolve_parameters(self, entries, ptr: str):
        """Resolves the parameters of a list and checks each; returns [(parameter, pointer)]."""
        result = []
        if not isinstance(entries, list):
            return result
        for i, raw in enumerate(entries):
            is_ref = isinstance(raw, dict) and "$ref" in raw
            param, param_ptr = self.resolve(raw, pointer(*segments(ptr), i))
            if not isinstance(param, dict):
                continue
            if not is_ref:
                self.check_parameter(param, param_ptr, under_paths=True)
            result.append((param, param_ptr))
        return result

    def check_parameter(self, param, ptr: str, under_paths: bool) -> None:
        if not isinstance(param, dict):
            return
        name = param.get("name")
        location = param.get("in")
        if not isinstance(name, str):
            self.report("parameter-structure", ptr, "The parameter has no name.")
            name = ""
        elif not name:
            self.report("parameter-name", ptr, "The parameter name is empty.")
        if location not in ("query", "header", "path", "cookie"):
            self.report("parameter-structure", ptr, f"in is {short(location)}; allowed are query, header, path, cookie.")
        if location == "path" and param.get("required") is not True:
            self.report("parameter-structure", ptr, f"The path parameter {name} lacks required: true.")
        if "schema" not in param and "content" not in param:
            self.report("parameter-structure", ptr, f"The parameter {name} has neither schema nor content.")
        if len(name) > 50:
            self.report("name-length", ptr, f"The parameter name {name} has {len(name)} characters.")
        if not _text(param.get("description")):
            self.report("parameter-description", ptr, f"The parameter {name} has no description.")
        if location in ("query", "path") and name and (not CAMEL.match(name) or re.search(r"[A-Z]{2}", name)):
            self.report("parameter-casing", ptr, f"The parameter {name} is not camelCase.")
        schema = param.get("schema")
        resolved, _ = self.resolve(schema, ptr)
        if not _has_example(param) and not (isinstance(resolved, dict) and _has_example(resolved)):
            self.report("parameter-example", ptr, f"The parameter {name} has no example.")
        if isinstance(schema, dict):
            schema_ptr = pointer(*segments(ptr), "schema")
            if under_paths and "$ref" not in schema:
                self.report("inline-schema", schema_ptr, f"The schema of the parameter {name} is inline.")
            if "$ref" not in schema:
                # A missing example is reported by parameter-example, not again by schema-example.
                self.check_schema_root(schema, schema_ptr, covered=True, is_component=False)
            if re.fullmatch(r"id|.*(_id|Id|-id)", name or "") and isinstance(resolved, dict):
                if resolved.get("type") == "integer" or resolved.get("format") not in (None, "uuid"):
                    self.report("id-numeric", schema_ptr, f"The ID parameter {name} is not described as a UUID.")
                if resolved.get("format") != "uuid":
                    self.report("id-uuid", schema_ptr, f"The ID parameter {name} does not have format uuid.")
            if "example" in param:
                self.validate_example(param["example"], schema, pointer(*segments(ptr), "example"))
        self.validate_examples(param.get("examples"), schema, pointer(*segments(ptr), "examples"))
        self.check_content(param.get("content"), pointer(*segments(ptr), "content"), under_paths, "parameter")

    def check_path_params(self, path: str, op_ptr: str, parameter: dict) -> None:
        placeholders = re.findall(r"\{([^}]+)\}", path)
        defined = {name: pp for (name, location), (p, pp) in parameter.items() if location == "path"}
        for name in placeholders:
            if name not in defined:
                self.report("path-params", op_ptr, f"{{{name}}} is in the path but is not a path parameter.")
        for name, pp in defined.items():
            if name not in placeholders:
                self.report("path-params", pp, f"The path parameter {name} does not appear in {path}.")

    def check_operation(self, path, method, op, ptr, parameter, operation_ids) -> None:
        name = f"{method.upper()} {path}"
        if not _text(op.get("summary")):
            self.report("operation-summary", ptr, f"{name} has no summary.")
        if not _text(op.get("description")):
            self.report("operation-description", ptr, f"{name} has no description.")
        else:
            self.check_agent_description(name, op, ptr, parameter)
        op_id = op.get("operationId")
        if not _text(op_id):
            self.report("operation-id", ptr, f"{name} has no operationId.")
        else:
            id_ptr = pointer(*segments(ptr), "operationId")
            if op_id in operation_ids:
                self.report("operation-id-unique", id_ptr, f"{op_id} is already used by {operation_ids[op_id]}.")
            operation_ids.setdefault(op_id, name)
            if not OPID_URL.match(op_id):
                self.report("operation-id-url", id_ptr, f"{op_id} contains characters not allowed in a URL.")
            if not CAMEL.match(op_id):
                self.report("operation-id-casing", id_ptr, f"{op_id} is not camelCase.")
            if len(op_id) > 50:
                self.report("name-length", id_ptr, f"{op_id} has {len(op_id)} characters.")
        tags = op.get("tags")
        if not isinstance(tags, list) or not tags:
            self.report("operation-tags", ptr, f"{name} has no tag.")
        else:
            defined = {t.get("name") for t in self.doc.get("tags", []) if isinstance(t, dict)} \
                if isinstance(self.doc.get("tags"), list) else set()
            for i, tag in enumerate(tags):
                if tag not in defined:
                    self.report("operation-tag-defined", pointer(*segments(ptr), "tags", i),
                               f"The tag {tag} is not defined at the top level.")
        if "requestBody" in op:
            raw = op["requestBody"]
            body, body_ptr = self.resolve(raw, pointer(*segments(ptr), "requestBody"))
            if isinstance(raw, dict) and "$ref" not in raw:
                self.check_request_body(body, body_ptr, under_paths=True)
            if method == "patch" and isinstance(body, dict) and isinstance(body.get("content"), dict) \
                    and "application/merge-patch+json" not in body["content"]:
                self.report("patch-merge", body_ptr, f"{name} does not take application/merge-patch+json.")
        responses = op.get("responses")
        if not isinstance(responses, dict) or not responses:
            self.report("operation-responses", ptr, f"{name} has no responses.")
            return
        self.check_responses(name, method, op, ptr, responses, parameter)

    def check_agent_description(self, name, op, ptr, parameter) -> None:
        description = op.get("description", "").strip()
        summary = str(op.get("summary") or "").strip()
        if summary and (description.rstrip(".").lower() == summary.rstrip(".").lower() or len(description) <= len(summary)):
            self.report("operation-description-agent", ptr, f"The description of {name} says no more than the summary.")
            return
        filter_names = [p.get("name") for p, _ in parameter
                        if p.get("in") == "query" and p.get("name") not in ("offset", "limit", "cursor")]
        if filter_names and not any(n and str(n).lower() in description.lower() for n in filter_names):
            self.report("operation-description-agent", ptr,
                       f"The description of {name} names none of its filters ({', '.join(map(str, filter_names))}).")

    def check_responses(self, name, method, op, ptr, responses, parameter) -> None:
        codes = [str(c) for c in responses]
        resp_ptr = pointer(*segments(ptr), "responses")
        if not any(c[:1] in ("2", "3") for c in codes):
            self.report("operation-success-response", resp_ptr, f"{name} has no 2xx or 3xx response.")
        if not any(c.startswith("4") for c in codes):
            self.report("operation-4xx-response", resp_ptr, f"{name} has no 4xx response.")
        unsecured = not self.doc.get("security") and not self.components().get("securitySchemes")
        for code, rule in (("401", "response-401"), ("500", "response-500"), ("429", "response-429")):
            response, _ = self.resolve(responses.get(code), resp_ptr)
            if not isinstance(response, dict) or not response.get("content"):
                extra = " The API has no authentication; check with the user whether that is intended." \
                    if code == "401" and unsecured else ""
                self.report(rule, resp_ptr, f"{name} has no {code} response with content.{extra}")
        security = op.get("security", self.doc.get("security"))
        secured = isinstance(security, list) and any(isinstance(a, dict) and a for a in security)
        if secured and "403" not in codes:
            self.report("response-403", resp_ptr, f"{name} is secured but has no 403 response.")
        if method == "post":
            created, _ = self.resolve(responses.get("201"), resp_ptr)
            if "202" not in codes and not (isinstance(created, dict) and _has_header(created, "Location")):
                self.report("post-created", resp_ptr, f"{name} has no 201 response with a Location header.")
        if method == "delete" and "204" not in codes:
            self.report("delete-no-content", resp_ptr, f"{name} has no 204 response.")
        for code in codes:
            raw = responses[code]
            response, response_ptr = self.resolve(raw, pointer(*segments(resp_ptr), code))
            if not isinstance(response, dict):
                continue
            if isinstance(raw, dict) and "$ref" not in raw:
                self.check_response(response, response_ptr, under_paths=True)
            self.check_response_rules(code, response, response_ptr)
            if method == "get" and code.startswith("2"):
                self.check_collection(name, response, response_ptr, ptr, parameter)

    def check_response_rules(self, code: str, response: dict, ptr: str) -> None:
        if code[:1] in ("2", "4"):
            if not any(_has_header(response, h) for h in ("X-RateLimit-Limit", "X-Rate-Limit-Limit", "RateLimit-Limit")):
                self.report("rate-limit-headers", ptr, f"The {code} response has no rate limit header.")
            missing = [h for h in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After") if not _has_header(response, h)]
            if missing:
                self.report("rate-limit-headers-standard", ptr, f"The {code} response lacks: {', '.join(missing)}.")
        if code == "429" and not _has_header(response, "Retry-After"):
            self.report("retry-after", ptr, "The 429 response has no Retry-After header.")
        if code[:1] in ("4", "5") and isinstance(response.get("content"), dict) and response["content"] \
                and "application/problem+json" not in response["content"]:
            self.report("error-media-type", pointer(*segments(ptr), "content"),
                       f"The {code} response uses {', '.join(response['content'])} instead of application/problem+json.")

    def check_collection(self, name, response, ptr, op_ptr, parameter) -> None:
        content = response.get("content")
        if not isinstance(content, dict):
            return
        for media_type, medium in content.items():
            if not isinstance(medium, dict):
                continue
            schema, schema_ptr = self.resolve(medium.get("schema"), pointer(*segments(ptr), "content", media_type, "schema"))
            if not isinstance(schema, dict):
                continue
            if _types(schema) == {"array"}:
                self.report("collection-wrapper", schema_ptr, f"{name} returns a bare array.")
                continue
            props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            data, _ = self.resolve(props.get("data"), schema_ptr)
            if not (isinstance(data, dict) and "array" in _types(data)):
                continue
            meta, meta_ptr = self.resolve(props.get("meta"), pointer(*segments(schema_ptr), "properties", "meta"))
            meta_props = meta.get("properties") if isinstance(meta, dict) and isinstance(meta.get("properties"), dict) else {}
            if "totalCount" not in meta_props:
                self.report("collection-total-count", meta_ptr if isinstance(meta, dict) else schema_ptr,
                           "The collection wrapper has no meta.totalCount.")
            names = {p.get("name") for p, _ in parameter if p.get("in") == "query"}
            missing = [n for n in ("offset", "limit") if n not in names]
            if missing:
                self.report("collection-pagination", op_ptr, f"{name} does not take {' or '.join(missing)}.")

    def check_response(self, response, ptr: str, under_paths: bool) -> None:
        if not isinstance(response, dict):
            return
        if not _text(response.get("description")):
            self.report("response-description", ptr, "The response has no description.")
        header = response.get("headers")
        if isinstance(header, dict) and "$ref" not in header:
            for name, raw in header.items():
                h_ptr = pointer(*segments(ptr), "headers", name)
                if len(name) > 50:
                    self.report("name-length", h_ptr, f"The header {name} has {len(name)} characters.")
                if isinstance(raw, dict) and "$ref" not in raw:
                    self.check_header(name, raw, h_ptr)
        self.check_content(response.get("content"), pointer(*segments(ptr), "content"), under_paths, "response")

    def check_header(self, name, header, ptr: str) -> None:
        if not isinstance(header, dict):
            return
        if not _text(header.get("description")):
            self.report("header-description", ptr, f"The header {name} has no description.")
        if "schema" not in header and "content" not in header:
            self.report("header-schema", ptr, f"The header {name} has neither schema nor content.")
        schema = header.get("schema")
        if isinstance(schema, dict) and "$ref" not in schema:
            self.check_schema_root(schema, pointer(*segments(ptr), "schema"), covered=_has_example(header), is_component=False)
        if "example" in header:
            self.validate_example(header["example"], schema, pointer(*segments(ptr), "example"))

    def check_request_body(self, body, ptr: str, under_paths: bool) -> None:
        if not isinstance(body, dict):
            return
        if not _text(body.get("description")):
            self.report("request-body-description", ptr, "The requestBody has no description.")
        if not isinstance(body.get("content"), dict) or not body["content"]:
            self.report("request-body-content", ptr, "The requestBody has no content.")
            return
        self.check_content(body["content"], pointer(*segments(ptr), "content"), under_paths, "requestBody")

    def check_content(self, content, ptr: str, under_paths: bool, owner: str) -> None:
        if not isinstance(content, dict) or "$ref" in content:
            return
        for media_type, medium in content.items():
            if not isinstance(medium, dict):
                continue
            m_ptr = pointer(*segments(ptr), media_type)
            schema = medium.get("schema")
            if isinstance(schema, dict):
                if "$ref" not in schema:
                    if under_paths:
                        self.report("inline-schema", pointer(*segments(m_ptr), "schema"),
                                   f"The {media_type} schema of this {owner} is inline.")
                    self.check_schema_root(schema, pointer(*segments(m_ptr), "schema"), covered=_has_example(medium), is_component=False)
                if "example" in medium:
                    self.validate_example(medium["example"], schema, pointer(*segments(m_ptr), "example"))
                self.validate_examples(medium.get("examples"), schema, pointer(*segments(m_ptr), "examples"))

    # -- Schemas

    def check_schema_root(self, schema, ptr: str, covered: bool, is_component: bool) -> None:
        if not isinstance(schema, dict):
            return
        if is_component and "$ref" not in schema and not _text(schema.get("description")):
            self.report("schema-description", ptr, f"The schema {segments(ptr)[-1]} has no description.")
        self.check_schema_node(schema, ptr, role="root", depth=0)
        if not covered:
            self.check_missing_example(schema, ptr)

    def check_schema_node(self, schema, ptr: str, role: str, depth: int) -> None:
        if not isinstance(schema, dict) or depth > 40:
            return
        if "$ref" in schema and self.version == "3.0":
            return
        if "nullable" in schema and self.version == "3.1":
            self.report("nullable-3-1", pointer(*segments(ptr), "nullable"), "nullable does not exist in OpenAPI 3.1.")
        if isinstance(schema.get("type"), list) and self.version == "3.0":
            self.report("type-list-3-0", pointer(*segments(ptr), "type"), "In OpenAPI 3.0, type is a single string.")
        if role == "property" and "$ref" not in schema and not _text(schema.get("description")):
            self.report("property-description", ptr, f"The property {segments(ptr)[-1]} has no description.")
        if isinstance(schema.get("enum"), list):
            self.check_enum(schema, schema["enum"], ptr, role)
        if "example" in schema:
            self.validate_example(schema["example"], schema, pointer(*segments(ptr), "example"))
        if isinstance(schema.get("examples"), list):
            for i, value in enumerate(schema["examples"]):
                self.validate_example(value, schema, pointer(*segments(ptr), "examples", i))
        props = schema.get("properties")
        if isinstance(props, dict):
            for name, sub in props.items():
                sub_ptr = pointer(*segments(ptr), "properties", name)
                if not CAMEL.match(name) or re.search(r"[A-Z]{2}", name):
                    self.report("property-casing", sub_ptr, f"The property {name} is not camelCase.")
                if isinstance(sub, dict) and "boolean" in _types(sub) and re.match(r"^(is|has)[A-Z]", name):
                    self.report("boolean-naming", sub_ptr, f"The boolean property {name} has an is or has prefix.")
                self.check_schema_node(sub, sub_ptr, "property", depth + 1)
        for key in ("items", "not", "additionalProperties", "contains", "if", "then", "else"):
            if isinstance(schema.get(key), dict):
                self.check_schema_node(schema[key], pointer(*segments(ptr), key), "part", depth + 1)
        for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
            if isinstance(schema.get(key), list):
                for i, sub in enumerate(schema[key]):
                    self.check_schema_node(sub, pointer(*segments(ptr), key, i), "part", depth + 1)
        for key in ("patternProperties", "$defs", "dependentSchemas"):
            if isinstance(schema.get(key), dict):
                for name, sub in schema[key].items():
                    self.check_schema_node(sub, pointer(*segments(ptr), key, name), "part", depth + 1)

    def check_enum(self, schema, enum, ptr, role) -> None:
        e_ptr = pointer(*segments(ptr), "enum")
        seen = []
        for value in enum:
            if any(_equal(value, g) for g in seen):
                self.report("enum-unique", e_ptr, f"{short(value)} appears twice in the enum.")
            seen.append(value)
        types = _types(schema)
        if types:
            wrong = [w for w in enum if not any(_matches_type(w, t) for t in types)]
            if wrong:
                self.report("typed-enum", e_ptr,
                           f"{', '.join(short(w) for w in wrong)} does not match type {'/'.join(sorted(types))}.")
        not_lowercase = [w for w in enum if isinstance(w, str) and w != w.lower()]
        if not_lowercase:
            self.report("enum-casing", e_ptr, f"Not lowercase: {', '.join(not_lowercase)}.")
        if role != "root" or segments(ptr)[:2] != ["components", "schemas"]:
            self.report("inline-enum", ptr, "The enum is inline instead of its own schema.")

    def check_missing_example(self, schema, ptr: str, depth: int = 0) -> None:
        """Reports the deepest schemas without an example; an example higher up covers everything below."""
        if not isinstance(schema, dict) or depth > 40 or _has_example(schema) or "$ref" in schema:
            return
        props = schema.get("properties")
        if isinstance(props, dict) and props:
            for name, sub in props.items():
                self.check_missing_example(sub, pointer(*segments(ptr), "properties", name), depth + 1)
            return
        items = schema.get("items")
        if isinstance(items, dict):
            target, _ = self.resolve(items, ptr)
            if isinstance(target, dict) and (_has_example(target) or "$ref" in items):
                return
        name = segments(ptr)[-1] if segments(ptr) else ptr
        self.report("schema-example", ptr, f"{name} has no example.")

    # -- Examples

    def validate_examples(self, examples, schema, ptr: str) -> None:
        if not isinstance(examples, dict) or schema is None:
            return
        for name, entry in examples.items():
            entry, e_ptr = self.resolve(entry, pointer(*segments(ptr), name))
            if isinstance(entry, dict) and "value" in entry:
                self.validate_example(entry["value"], schema, pointer(*segments(e_ptr), "value"))

    def validate_example(self, value, schema, ptr: str) -> None:
        if not isinstance(schema, dict):
            return
        problems = self.validate(value, schema, "", 0)
        if problems:
            more = f" (and {len(problems) - 3} more)" if len(problems) > 3 else ""
            self.report("example-valid", ptr, "; ".join(problems[:3]) + more)

    def validate(self, value, schema, location: str, depth: int) -> list[str]:
        if not isinstance(schema, dict) or depth > 30:
            return []
        where = location or "example"
        if isinstance(schema.get("$ref"), str):
            target = self.resolve_ref(schema["$ref"])
            problems = self.validate(value, target, location, depth + 1) if isinstance(target, dict) else []
            if self.version == "3.1":
                rest = {k: v for k, v in schema.items() if k not in ("$ref", "description", "example", "examples")}
                problems += self.validate(value, rest, location, depth + 1)
            return problems
        problems: list[str] = []
        types = set(_types(schema))
        if schema.get("nullable") is True:
            types.add("null")
        if types and not any(_matches_type(value, t) for t in types):
            return [f"{where}: {short(value)} is not {' or '.join(sorted(types))}"]
        if isinstance(schema.get("enum"), list) and not any(_equal(value, e) for e in schema["enum"]):
            problems.append(f"{where}: {short(value)} is not in the enum")
        if "const" in schema and not _equal(value, schema["const"]):
            problems.append(f"{where}: {short(value)} is not {short(schema['const'])}")
        for part_schema in schema.get("allOf", []) if isinstance(schema.get("allOf"), list) else []:
            problems += self.validate(value, part_schema, location, depth + 1)
        for key in ("anyOf", "oneOf"):
            variants = schema.get(key)
            if isinstance(variants, list) and variants:
                if all(self.validate(value, v, location, depth + 1) for v in variants):
                    problems.append(f"{where}: matches no variant of {key}")
        if isinstance(value, str):
            problems += _string_problems(value, schema, where)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            problems += _number_problems(value, schema, where, self.version)
        elif isinstance(value, list):
            if isinstance(schema.get("minItems"), int) and len(value) < schema["minItems"]:
                problems.append(f"{where}: fewer than {schema['minItems']} items")
            if isinstance(schema.get("maxItems"), int) and len(value) > schema["maxItems"]:
                problems.append(f"{where}: more than {schema['maxItems']} items")
            if isinstance(schema.get("items"), dict):
                for i, entry in enumerate(value):
                    problems += self.validate(entry, schema["items"], f"{where}[{i}]", depth + 1)
        elif isinstance(value, dict):
            required = schema.get("required") if isinstance(schema.get("required"), list) else []
            for field in required:
                if field not in value:
                    problems.append(f"{where}: required field {field} is missing")
            props = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
            for field, sub_value in value.items():
                if field in props:
                    problems += self.validate(sub_value, props[field], f"{location + '.' if location else ''}{field}", depth + 1)
                elif schema.get("additionalProperties") is False:
                    problems.append(f"{where}: field {field} is not allowed")
        return problems

    # -- Unused components

    def check_unused(self) -> None:
        components = self.components()
        for kind in COMPONENT_TYPES:
            entries = components.get(kind)
            if not isinstance(entries, dict):
                continue
            for name in entries:
                ptr = pointer("components", kind, name)
                if not any(r == ptr or r.startswith(ptr + "/") for r in self.referenced):
                    self.report("unused-component", ptr, f"{kind}/{name} is never referenced.")


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_example(obj) -> bool:
    if not isinstance(obj, dict):
        return False
    return "example" in obj or (isinstance(obj.get("examples"), (list, dict)) and bool(obj["examples"]))


def _has_header(response: dict, name: str) -> bool:
    header = response.get("headers")
    return isinstance(header, dict) and any(str(k).lower() == name.lower() for k in header)


def _types(schema) -> set:
    type_name = schema.get("type") if isinstance(schema, dict) else None
    if isinstance(type_name, str):
        return {type_name}
    if isinstance(type_name, list):
        return {t for t in type_name if isinstance(t, str)}
    return set()


def _matches_type(value, type_name: str) -> bool:
    return {
        "null": value is None,
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool)
        or isinstance(value, float) and value.is_integer(),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "string": isinstance(value, str),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(type_name, True)


def _equal(a, b) -> bool:
    return type(a) is type(b) and a == b or (
        isinstance(a, (int, float)) and isinstance(b, (int, float))
        and not isinstance(a, bool) and not isinstance(b, bool) and a == b)


def _string_problems(value: str, schema: dict, where: str) -> list[str]:
    problems = []
    if isinstance(schema.get("minLength"), int) and len(value) < schema["minLength"]:
        problems.append(f"{where}: shorter than {schema['minLength']} characters")
    if isinstance(schema.get("maxLength"), int) and len(value) > schema["maxLength"]:
        problems.append(f"{where}: longer than {schema['maxLength']} characters")
    if isinstance(schema.get("pattern"), str):
        try:
            if not re.search(schema["pattern"], value):
                problems.append(f"{where}: {short(value)} does not match the pattern {schema['pattern']}")
        except re.error:
            pass
    formats = {"uuid": UUID, "date-time": DATE_TIME, "email": EMAIL, "uri": URI, "url": URI}
    fmt = schema.get("format")
    if fmt == "date":
        try:
            if not DATE.match(value):
                raise ValueError
            dt.date.fromisoformat(value)
        except ValueError:
            problems.append(f"{where}: {short(value)} is not an RFC 3339 date")
    elif fmt in formats and not formats[fmt].match(value):
        hint = "; an absolute URI starts with a scheme such as https://" if fmt in ("uri", "url") else ""
        problems.append(f"{where}: {short(value)} does not have format {fmt}{hint}")
    return problems


def _number_problems(value, schema: dict, where: str, version: str) -> list[str]:
    problems = []
    for key, compare, text in (("minimum", lambda a, b: a < b, "less than"),
                                        ("maximum", lambda a, b: a > b, "greater than")):
        limit = schema.get(key)
        if isinstance(limit, (int, float)) and not isinstance(limit, bool):
            exclusive = schema.get("exclusive" + key.capitalize()) is True and version == "3.0"
            if compare(value, limit) or (exclusive and value == limit):
                problems.append(f"{where}: {value} is {text} {limit}")
    for key, compare, text in (("exclusiveMinimum", lambda a, b: a <= b, "not greater than"),
                                        ("exclusiveMaximum", lambda a, b: a >= b, "not less than")):
        limit = schema.get(key)
        if isinstance(limit, (int, float)) and not isinstance(limit, bool) and compare(value, limit):
            problems.append(f"{where}: {value} is {text} {limit}")
    return problems


# --- Scoring -------------------------------------------------------------------------------------


def _deduction(findings, category, divisor=1.0) -> float:
    return sum(b.rule.weight for b in findings if category in b.rule.categories) / divisor


def _area_scores(findings, length=1) -> dict:
    return {k: max(0.0, 100 - _deduction(findings, k, length)) for k in CATEGORIES}


def _fixed(docs, completeness, sdk, security) -> dict:
    return {DOCS: docs, COMPLETENESS: completeness, SDK: sdk, SECURITY: security}


def _area_of(finding: Finding) -> str:
    parts = segments(finding.location)
    if parts and parts[0] in AREA_WEIGHTS:
        return parts[0]
    for key, area in (("info", "info"), ("server", "servers"), ("path", "paths"),
                                ("component", "components"), ("security", "security"), ("tag", "tags")):
        if key in finding.rule.code:
            return area
    return "info"


def compute_score(doc, findings: list[Finding], intentionally_open: bool = False) -> dict:
    """Score as in Rate My OpenAPI: each area scored on its own, then averaged by AREA_WEIGHTS.

    intentionally_open: the user ignored security-global, so the API is open on purpose.
    The missing global security then no longer costs the area all its points at once.
    """
    doc = doc if isinstance(doc, dict) else {}
    by_area = defaultdict(list)
    for finding in findings:
        by_area[_area_of(finding)].append(finding)

    areas = {"info": _area_scores(by_area["info"])}
    tags, server, security = doc.get("tags"), doc.get("servers"), doc.get("security")
    areas["tags"] = _area_scores(by_area["tags"], len(tags)) if isinstance(tags, list) and tags \
        else _fixed(25, 25, 100, 100)
    areas["servers"] = _area_scores(by_area["servers"], len(server)) if isinstance(server, list) and server \
        else _fixed(0, 0, 0, 0)
    areas["security"] = _area_scores(by_area["security"], len(security)) \
        if isinstance(security, list) and security \
        else _area_scores(by_area["security"]) if intentionally_open else _fixed(0, 0, 100, 0)
    areas["components"] = _score_components(doc, by_area["components"])
    areas["paths"] = _score_paths(doc, by_area["paths"])

    result = {k: round_half_up(sum(areas[b][k] * g for b, g in AREA_WEIGHTS.items())) for k in CATEGORIES}
    area_score = {b: round_half_up(sum(scores.values()) / 4) for b, scores in areas.items()}
    result["overall"] = round_half_up(sum(area_score[b] * g for b, g in AREA_WEIGHTS.items()))
    result["areas"] = {b: {"score": area_score[b], **{k: round_half_up(v) for k, v in scores.items()}}
                         for b, scores in areas.items()}
    return result


def _score_components(doc, findings) -> dict:
    components = doc.get("components")
    if not isinstance(components, dict):
        return _fixed(100, 100, 0, 100)
    by_component = defaultdict(list)
    for finding in findings:
        parts = segments(finding.location)
        if len(parts) >= 3:
            by_component[(parts[1], parts[2])].append(finding)
    kind_scores = []
    for kind in COMPONENT_TYPES:
        entries = components.get(kind)
        if not isinstance(entries, dict) or not entries:
            continue
        scores = [_area_scores(by_component[(kind, name)]) for name in entries]
        kind_scores.append({k: round_half_up(sum(w[k] for w in scores) / len(scores)) for k in CATEGORIES})
    if not kind_scores:
        return _fixed(100, 100, 100, 100)
    return {k: round_half_up(sum(a[k] for a in kind_scores) / len(kind_scores)) for k in CATEGORIES}


def _score_paths(doc, findings) -> dict:
    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        return _fixed(0, 0, 0, 0)
    by_path = defaultdict(lambda: defaultdict(list))
    for finding in findings:
        parts = segments(finding.location)
        if len(parts) < 2:
            continue
        operation = parts[2] if len(parts) > 2 and parts[2] in METHODS else "path"
        by_path[parts[1]][operation].append(finding)
    scores = []
    for path, item in paths.items():
        methods = [m for m in METHODS if isinstance(item, dict) and isinstance(item.get(m), dict)]
        if not methods:
            scores.append(_fixed(0, 0, 0, 0))
            continue
        ops = [_score_operation(item[m], by_path[path][m]) for m in methods]
        path_findings = by_path[path]["path"]
        scores.append({k: max(0, round_half_up(sum(o[k] for o in ops) / len(ops) - _deduction(path_findings, k))) for k in CATEGORIES})
    return {k: round_half_up(sum(w[k] for w in scores) / len(scores)) for k in CATEGORIES}


def _score_operation(op: dict, findings) -> dict:
    """Deductions on parameters, single responses and tags are divided by their count (as in RMOA)."""
    result = {}
    for category in CATEGORIES:
        score = 100.0
        for finding in findings:
            if category not in finding.rule.categories:
                continue
            parts = segments(finding.location)
            field = parts[3] if len(parts) > 3 else None
            divisor = 1
            if field == "parameters":
                divisor = len(op.get("parameters") or []) or 1
            elif field == "responses" and len(parts) > 4:
                divisor = len(op.get("responses") or {}) or 1
            elif field == "tags":
                divisor = len(op.get("tags") or []) or 1
            score = max(0.0, score - finding.rule.weight / divisor)
        result[category] = round_half_up(score)
    return result


# --- Input and output --------------------------------------------------------------------------


def read(path: Path):
    """Reads JSON or YAML; returns (doc, problem), where problem is a message on broken syntax."""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        return None, f"The file is not UTF-8: {error}."
    suffix = path.suffix.lower()
    is_json = suffix == ".json" or (suffix not in (".yaml", ".yml") and text.lstrip()[:1] in ("{", "["))
    try:
        if is_json:
            doc = json.loads(text, object_pairs_hook=_make_object)
        else:
            doc = yaml_load(text, make_object=_make_object)
    except json.JSONDecodeError as error:
        return None, f"Invalid JSON: {error.msg} (line {error.lineno}, column {error.colno})."
    except YamlError as error:
        return None, f"Invalid YAML: {error}."
    if not isinstance(doc, dict):
        return None, "The root is not an object."
    return doc, None


def finding_to_dict(b: Finding) -> dict:
    return {"severity": b.rule.severity, "rule": b.rule.code, "location": b.location, "message": b.message,
            "fix": b.rule.fix, "description": b.rule.text, "source": b.rule.source,
            "weight": b.rule.weight, "categories": list(b.rule.categories)}


def sort_findings(findings):
    return sorted(findings, key=lambda b: (b.rule.severity != "error", -b.rule.weight, b.location, b.rule.code))


def report_text(file_name, version, score, findings, ignored, rulesets) -> str:
    lines = [f"OpenAPI lint: {file_name}" + (f" (OpenAPI {version})" if version else "")]
    ruleset_labels = ["base"] + [f"{s['file']} ({s['active']} of {s['total']} rules active)" for s in rulesets.values()]
    lines.append("Rules: " + " + ".join(ruleset_labels))
    lines.append("")
    lines.append(f"Score: {score['overall']} / 100")
    for k in CATEGORIES:
        lines.append(f"  {CATEGORY_NAMES[k] + ':':<16}{score[k]:>4}")
    errors = sum(1 for b in findings if b.rule.severity == "error")
    lines.append("")
    lines.append(f"Findings: {errors} errors, {len(findings) - errors} warnings"
                  + (f", {len(ignored)} ignored" if ignored else ""))
    # One block per rule: rule and fix once, then every location with its finding.
    groups: dict[str, list[Finding]] = {}
    for b in sort_findings(findings):
        groups.setdefault(b.rule.code, []).append(b)
    for i, (code, group) in enumerate(groups.items(), 1):
        rule = group[0].rule
        lines.append("")
        lines.append(f"{i}. [{rule.severity.upper()}] {code}, {len(group)}x, weight {rule.weight}")
        lines.append(f"   Rule: {rule.text} ({rule.source})")
        lines.append(f"   Fix:  {rule.fix}")
        for b in group:
            lines.append(f"   - {b.location or '/'}")
            lines.append(f"     {b.message}")
    if ignored:
        lines.append("")
        lines.append("Ignored (with --ignore, not in the score):")
        for b in sort_findings(ignored):
            lines.append(f"  - {b.rule.code} {b.location or '/'}: {b.message}")
    return "\n".join(lines)


def read_ruleset(path: str | None, ruleset: str):
    if path is None:
        return None, None
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise FileNotFoundError(f"Rule file not found: {file_path}")
    text = file_path.read_text(encoding="utf-8", errors="replace")
    rules = [r for r in RULES.values() if r.ruleset == ruleset]
    active = [r.code for r in rules if r.anchor is None or r.anchor.lower() in text.lower()]
    info = {"file": file_path.name, "active": len(active), "total": len(rules), "activeRules": active,
            "inactiveRules": [r.code for r in rules if r.code not in active]}
    return text, info


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    parser = argparse.ArgumentParser(
        description="Lint an OpenAPI 3.x file (JSON or YAML) locally, without network, with Rate My OpenAPI style scores.")
    parser.add_argument("spec", nargs="?", help="path to the OpenAPI file (JSON or YAML)")
    parser.add_argument("--standards", metavar="FILE", help="API standards (Markdown); enables the standards rules")
    parser.add_argument("--best-practices", metavar="FILE", help="OpenAPI best practices (Markdown); enables those rules")
    parser.add_argument("--ignore", metavar="CODE[,CODE]", action="append", default=[],
                        help="rules the user accepts on purpose; they count neither in the score nor in the exit code")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--list-rules", action="store_true", help="list all rules and exit")
    args = parser.parse_args(argv)

    if args.list_rules:
        for r in RULES.values():
            print(f"{r.code:<30} {r.severity:<8} {r.weight:>3}  {r.ruleset:<15} {r.text}")
        return 0
    if args.spec is None:
        parser.error("the path to the spec is missing")

    ignored_codes = {c.strip() for entry in args.ignore for c in entry.split(",") if c.strip()}
    unknown = sorted(ignored_codes - RULES.keys())
    if unknown:
        print(f"Unknown rule in --ignore: {', '.join(unknown)}. See --list-rules.", file=sys.stderr)
        return 2
    spec = Path(args.spec).expanduser()
    if not spec.is_file():
        print(f"Spec not found: {spec}", file=sys.stderr)
        return 2
    try:
        standards, standards_info = read_ruleset(args.standards, STANDARDS)
        best_practices, best_practices_info = read_ruleset(args.best_practices, BEST_PRACTICES)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 2
    rulesets = {k: v for k, v in ((STANDARDS, standards_info), (BEST_PRACTICES, best_practices_info)) if v}

    doc, problem = read(spec)
    linter = Linter(doc if doc is not None else {}, {STANDARDS: standards, BEST_PRACTICES: best_practices})
    if problem:
        linter.report("syntax-valid", "", problem)
    else:
        linter.check()
    findings = [b for b in linter.findings if b.rule.code not in ignored_codes]
    ignored = [b for b in linter.findings if b.rule.code in ignored_codes]
    score = compute_score(doc, findings, intentionally_open="security-global" in ignored_codes) if doc is not None else \
        {**{k: 0 for k in CATEGORIES}, "overall": 0, "areas": {}}
    errors = sum(1 for b in findings if b.rule.severity == "error")
    version = doc.get("openapi") if isinstance(doc, dict) else None

    if args.json:
        output = {
            "file": str(spec), "openapi": version,
            "score": {k: score[k] for k in ("overall", *CATEGORIES)}, "areas": score["areas"],
            "summary": {"errors": errors, "warnings": len(findings) - errors, "ignored": len(ignored)},
            "rulesets": rulesets,
            "findings": [finding_to_dict(b) for b in sort_findings(findings)],
            "ignored": [finding_to_dict(b) for b in sort_findings(ignored)],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    else:
        print(report_text(spec.name, version, score, findings, ignored, rulesets))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
