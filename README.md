# arc-skills

Agent Skills von Arslan Chaudhry, Product Owner im Bereich Learning Software. Jeder Skill ist ein Ordner unter `skills/` mit einer `SKILL.md` und optional Skripten und Referenzen. Sie laufen in Claude Code und, soweit in `compatibility` angegeben, in Codex.

## Skills

| Skill | Wofür |
| --- | --- |
| `arc-new-api-stories` | API Design Stories aus Anforderungen, Domänenmodell und API-Standards |
| `arc-create-api-spec` | OpenAPI 3.1.0 aus Stories, mit Offline-Linter und Vorschau |
| `arc-api-spec-review` | OpenAPI-Spezifikation gegen Standards und Best Practices prüfen |
| `arc-design-api` | Ganzer Weg von der Anforderung bis zur geprüften Spezifikation |
| `arc-personal-brand` | Personal-Brand-Strategie für eine Person |
| `arc-brand-identity` | Brief zur visuellen Identität |
| `arc-brand-guidelines` | Brand-Guidelines-Dokument |
| `arc-social-media-strategy` | Social-Media-Strategie auf Basis einer Personal Brand |

## API-Design: Reihenfolge und Rollen

Die vier API-Skills bauen aufeinander auf und denken die Sicht von Produkt, Entwicklung und QA mit.

1. `arc-new-api-stories` macht aus Requirements, Domänenmodell und API-Standards API Stories. PO oder PM prüfen und geben sie frei.
2. `arc-create-api-spec` erzeugt aus den Stories eine OpenAPI-3.1-Spezifikation, lintet sie lokal und zeigt sie als Vorschau. Meist übernimmt hier die Entwicklung.
3. `arc-api-spec-review` prüft eine neue oder bestehende Spezifikation gegen Standards und Best Practices. Der Abweichungsbericht richtet sich an QA und Entwicklung; Korrekturen folgen erst nach deren Freigabe.

`arc-design-api` führt Schritt 1 und 2 samt Review der Stories in einem Aufruf zusammen. Für eine bestehende Spezifikation reicht Schritt 3.

Die Eingaben sind Markdown-Dateien (Requirements, Domänenmodell, API-Standards, Best Practices); Beispiele liegen jedem Skill bei. Bei einem Konflikt gewinnt das Domänenmodell bei Namen und Werten, die Schreibweise kommt aus den Standards. Alles läuft lokal: Linter und Vorschau brauchen nur die Python-Standardbibliothek, ohne Upload und ohne CDN.

Standards und Best Practices sind allgemeine Vorgaben. Einzelne Entscheidungen passen vielleicht nicht zu jeder Organisation; eigene Regelwerke lassen sich statt der Beispiele übergeben.

## Installation

Den gewünschten Ordner nach `~/.claude/skills/` kopieren, zum Beispiel:

```bash
cp -R skills/arc-new-api-stories ~/.claude/skills/
```

Die vier API-Skills bauen aufeinander auf. `arc-api-spec-review` und `arc-design-api` brauchen den Linter aus `arc-create-api-spec`, installiere sie also zusammen. Die Brand-Skills verweisen auf einen Workflow, der nicht Teil dieses Repos ist; einzeln laufen sie trotzdem.

## Herkunft und Lizenz

Alles steht unter der MIT-Lizenz, siehe [LICENSE](LICENSE).

- Die vier API-Skills gehen auf die Methode von Emmanuel Paraskakis (Level 250) zurück. Sein Copyright-Hinweis steht in der `LICENSE` jedes dieser Skills.
- Die vier Brand-Skills sind angepasst nach [arnabbagxd/brand-building-skills](https://github.com/arnabbagxd/brand-building-skills) (MIT).
