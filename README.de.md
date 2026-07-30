# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
**Deutsch** · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnostizieren Sie, wo ein Agent-Skill-Lauf zuerst auseinanderfiel – und prüfen Sie die Beweise
> hinter jeder Schlussfolgerung.

Agent Skill Runtime Intelligence ist ein schreibgeschütztes Laufzeit-Beweis- und Diagnosesystem für Agent Skills. Es kombiniert Skill-Definitionen, offizielle Agent-Laufzeitereignisse, importierte Ablaufverfolgungen, Sitzungs-Fallback und beobachtbare Arbeitsbereichsergebnisse in einem evidenzbewerteten Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Schnellstart

Installieren und starten Sie die neueste Version auf macOS oder Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Es ist kein Klon, Konto, `sudo` oder GitHub CLI erforderlich. Das Installationsprogramm überprüft die Release-Prüfsumme, erkennt unterstützte Agenten und Skills, erklärt jeden Pfad, den es liest, fragt einmal, bevor es Nur-Beobachtungs-Hooks aktiviert, und öffnet das lokale UI bei [http://127.0.0.1:4317](http://127.0.0.1:4317). Laufzeitdaten bleiben unter `~/.skill-runtime`, es sei denn, Sie konfigurieren explizit einen Export.

Sie können [Überprüfen Sie den Installer](scripts/install.sh), bevor Sie es ausführen.

### Sehen Sie Ihr erstes Live SkillRun

1. Akzeptieren Sie das optionale Fail-Open-Hook-Setup, wenn das Installationsprogramm Sie dazu auffordert.
2. Starten Sie den Agenten neu und beginnen Sie mit einer neuen Aufgabe. Überprüfen Sie in Codex zunächst die verwalteten Befehle in `/hooks`; Vorhandene Aufgaben laden keine neuen Hooks im laufenden Betrieb.
3. Verwenden Sie einen Skill normal, bestätigen Sie dann die Integration und öffnen Sie UI:

```bash
skill-runtime doctor
skill-runtime status
```

Eine Integration ist erst **Live**, nachdem der Collector ein echtes Laufzeitereignis empfängt. Ein konfigurierter, aber unbeobachteter Hook ist **ausstehend** und wird nie als Live-Beweis präsentiert. Öffnen Sie [http://127.0.0.1:4317](http://127.0.0.1:4317) oder lesen Sie [Leitfaden „Erste Schritte“.](docs/getting-started.md) für agentenspezifische Anweisungen und Fehlerbehebung.

So führen Sie den Vorgang direkt von einem Quell-Checkout aus aus:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Produktoberfläche | Was es antwortet |
|---|---|
| Runtime Overview | Welche SkillRuns brauchen Aufmerksamkeit? |
| First Observable Boundary | Wo sind Beweise zum ersten Mal verschwunden oder fehlgeschlagen? |
| Skill Run Panorama | Wie sind Anfrage, Aktivierung, Ressourcen, Tools, Artefakte und Ergebnis miteinander verbunden? |
| Evidence Inspector | Welche Quelle, Qualität, Basis und Adapterfähigkeit stützen diese Behauptung? |
| Vergleichen | Ist ein Unterschied verhaltensbedingt oder nur ein beobachtbarer Unterschied? |
| Inferred Analysis | Welche evidenzbasierte Erklärung oder nächste Untersuchung ist plausibel? |
| Einstellungen / Arzt | Was wird gelesen, gespeichert, exportiert, ausstehend und überprüft? |

## Wie es funktioniert

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime beobachtet den Workflow, den Sie bereits verwenden. Versionierte Adapter verwandeln agentennative Ereignisse in einen stabilen Skill-Lebenszyklus, während rohe Quellumschläge, normalisierte Ereignisse, Beziehungen und Schlussfolgerungen getrennt bleiben. Die Diagnose-Engine identifiziert zunächst die früheste Grenze, an der Beweise fehlen oder fehlschlagen. Es erfindet keine Modellabsicht oder kausale Wirksamkeit.

| Datenquelle | Rolle | Frische | UI-Beschriftung |
|---|---|---|---|
| Offizielle Agent-Hooks/Plugins/SDK-Ereignisse | Primärer Lebenszyklus, Tool, Subagent und Terminalnachweise | Live | `Official hook` / `Native telemetry` |
| Fertigkeitsdateien und beobachtbare Arbeitsbereichsergebnisse | Definition, Ressource, Datei, Artefakt und Testnachweise | Live-Schnappschuss / indiziert | `Observed` |
| Sitzungsprotokolle | Kompatibilitäts-Fallback, wenn der Agent keine ausreichende Laufzeit bereitstellt API | Nah am Leben oder historisch | `Transcript fallback` |
| OTLP und unterstützte Trace-Exporte | Interoperabilität und historische Bedeutung | Live-Export / Batch-Import | Quellprofil angezeigt |
| Deterministische Korrelation | Verbindet Ereignisse mit einem SkillRun, ohne die Quellfakten zu ändern | Bei Einnahme | `Derived` |
| Semantische Hilfe | Nur Erläuterungen und Untersuchungsvorschläge | Auf Anfrage | `Inferred` |

Unterstützte Erstanbieteradapter werden unabhängig voneinander versioniert:

| Agent | Primäre Integration | Zurückgreifen | Sichtbarkeit der Aktivierung |
|---|---|---|---|
| Codex | Offizieller Befehl Hooks | Sitzungsimport | Explizite Aktivierung bei Offenlegung durch das Hook-Ereignis |
| Claude Code | Offizielle Hooks | Sitzungsimport | Es wurden explizite Beweise für das Skill-Tool und den Slash-Command aufgedeckt |
| Qoder | Offizieller Befehl Hooks | Lokale Aufzeichnungen | Explizite Aktivierung, wenn sie durch das Fähigkeitswerkzeug freigelegt wird |
| OpenCode | Globales Nur-Beobachtungs-Plugin | Lokale Aufzeichnungen | Rückrufe von Fertigkeitstools wurden angezeigt |

Genaue Leistungsgrenzen sind im [Adapterfähigkeitsmatrix](docs/adapter-capability-matrix.md) dokumentiert. Nicht unterstützte und nicht beobachtete Phasen bleiben sichtbar und werden nicht in Fehler umgewandelt.

## Das Problem

Die Installation eines Skills beweist nicht, dass ein Agent ihn entdeckt hat. Die Entdeckung beweist keine Aktivierung. Die Aktivierung beweist nicht, dass die vollständigen Anweisungen und Ressourcen geladen wurden. Die Ausführung beweist nicht, dass die Fähigkeit das Ergebnis verbessert hat.

Heutzutage werden diese Misserfolge oft verheimlicht. Entwickler fragen sich:

- War der Skill für diesen Agenten verfügbar?
- Wurde es für diese Anfrage aktiviert?
- Welche Anweisungen, Referenzen, Skripte und Assets wurden geladen?
- Welche Tools, MCP-Aufrufe, Subagenten, Dateien und Artefakte waren beteiligt?
- Wo ist die Ausführung fehlgeschlagen, wurde sie wiederholt oder der Kontext ging verloren?
- Hat der Skill geholfen oder hat er nur zusätzliche Kosten und Latenz verursacht?

## Fähigkeitsspezifische Diagnose

Das primäre Diagnoseobjekt ist ein `SkillRun`, nicht eine gesamte Agentensitzung:

```text
User request
    ↓
Skills discovered
    ↓
Skill selected / not selected
    ↓
SKILL.md activated
    ↓
References and scripts loaded
    ↓
Tools / MCP / subagents executed
    ↓
Files and artifacts produced
    ↓
Observable outcome
```

Der UI hält den Lebenszyklus geordnet, typisiert und evidenzbewertet. Fehlende Aktivierungstelemetrie bedeutet „nicht beobachtet“ oder „nicht unterstützt“; Dies bedeutet nicht, dass der Agent den Skill definitiv übersprungen hat.

## Beweisdisziplin

Der UI darf niemals eine Schlussfolgerung als Laufzeitfakt darstellen:

- **Beobachtet** – explizit in einem Quellereignis oder einer Quelldatei vorhanden.
- **Abgeleitet** – deterministisch verbunden aus beobachteten Beweisen.
- **Abgeleitet** – eine plausible Erklärung mit Unsicherheit.
- **Experimentell** – ein Effekt, der durch kontrollierte paarweise Auswertung gemessen wird.

Eine einzelne Ablaufverfolgung kann die Ausführungszuordnung unterstützen. Eine kausale Wirksamkeit kann nicht nachgewiesen werden. Behauptungen wie „Diese Fähigkeit hat die Erfolgsquote verbessert“ erfordern eine wiederholte Bewertung mit/ohne Fähigkeit.

## Produktprinzipien

- Standardmäßig privat, mit lokaler, hybrider und teamverbundener Bereitstellung.
- Nur-Lese-Beobachtung; Übernehmen Sie niemals die Agentenschleife.
- Kein Modell-Proxy und kein obligatorischer Cloud-Service.
- Keine Blockierung, Genehmigungstür oder Richtliniendurchsetzung im Standardprodukt.
- Explizite Provenienz und Evidenzbewertung.
- Progressive Offenlegung: einfache Erzählung zuerst, rohe Ereignisse auf Anfrage.
- Adapterbasierte Unterstützung für die Änderung von Agent-Transkriptformaten.

## Aktueller Umfang

Die Laufzeit unterstützt Codex, Claude Code, Qoder und OpenCode über unabhängige, versionierte Adapter und bietet:

- installierte Fähigkeitserkennung und -validierung;
- Offizielle Hook/Plugin-Sammlung in Echtzeit plus gekennzeichneter Sitzungs-Fallback;
- Zeitpläne für die Aktivierung von Fertigkeiten, das Laden von Ressourcen und Werkzeugaufrufe;
- Subagenten-, MCP-, Datei- und Artefaktbeziehungen;
- Dauer, Token, Fehler, Wiederholungsversuche und Statuszusammenfassungen, sofern verfügbar;
- Runtime Overview und Erstgrenzdiagnose;
- ein Panorama-DAG, eine Ereigniszeitleiste und ein Beweisinspektor;
- fähigkeitsbewusster Vergleich gleicher und agentenübergreifender Agenten;
- eine separate Inferred Analysis-Oberfläche, die Laufzeitfakten nicht neu schreiben kann;
- Opt-in-OTLP/HTTP-Export und unterstützter Observability-Trace-Import.

Das MVP umfasst **keinen** Marktplatz, Universal Agent Runtime, Sicherheitsdurchsetzung, Enterprise Governance oder Kausalwirkungsansprüche.

## Detaillierte Installation

Für den kürzesten unterstützten Pfad verwenden Sie das einzeilige Release-Installationsprogramm in [Schnellstart](#quick-start). Der vollständige Erstausführungsablauf, agentenspezifische Neustart-/Vertrauensschritte, Datenschutzverhalten und Fehlerbehebung live im [Leitfaden „Erste Schritte“.](docs/getting-started.md).

Für die Entwicklung weist die Basisimplementierung keine Laufzeitabhängigkeiten über Python 3.9+ hinaus auf. Aus dem Repository-Stammverzeichnis:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Öffnen Sie dann [http://127.0.0.1:4317](http://127.0.0.1:4317).

Der einmalige `install`-Befehl:

1. scannt Benutzer-, Projekt- und zwischengespeicherte Plugin-Skill-Standorte;
2. erkennt Codex, Claude Code, Qoder und OpenCode, ohne ihre Konfiguration zu ändern;
3. zeigt an, welche Agenten- und Skillpfade gelesen werden;
4. lädt einen durch Prüfsummen verifizierten nativen Absender mit geringem Startaufwand für die aktuelle Plattform herunter, greift auf einen lokalen C-Build und schließlich auf den Python-Absender zurück und erwärmt einmal während der Installation eine neue native Binärdatei vor;
5. erstellt `~/.skill-runtime/config.json` und den lokalen SQLite-Index.

Wenn es interaktiv ausgeführt wird, fragt es einmal nach, bevor es Fail-Open-Agent-Hooks hinzufügt. `--no-hooks` behält den Transkriptimport als gekennzeichneten Fallback bei, während `--enable-hooks` die ausdrückliche Zustimmung aufzeichnet und nur verwaltete Einträge installiert. Öffnen Sie für Codex `/hooks` nach der Installation, überprüfen Sie die genauen verwalteten Befehle und vertrauen Sie ihnen. Codex erfordert diese explizite Überprüfung absichtlich für Hooks, die außerhalb der verwalteten Unternehmenskonfiguration hinzugefügt werden. Starten Sie eine neue Codex-Aufgabe/Sitzung, nachdem Sie den Hooks vertraut haben, und führen Sie dann Folgendes aus:

```bash
.venv/bin/skill-runtime doctor
```

Qoder lädt die Hook-Konfiguration beim Start, also starten Sie Qoder nach der ersten Installation neu. OpenCode erkennt das verwaltete Nur-Beobachtungs-Plugin aus seinem globalen Plugin-Verzeichnis; Starten Sie OpenCode neu, wenn der aktuelle Prozess vor der Installation durchgeführt wurde. Keine der Integrationen liest oder ändert Modellanforderungen.

Die Integration wird erst **Live**, nachdem die Datenbank ein echtes `official_hook`-Ereignis empfängt. Das bloße Schreiben von `~/.codex/hooks.json` wird als **Ausstehend**, nie Verbunden angezeigt. `start` startet den Collector, den Transkript-Fallback-Watcher, den Retention Worker, den SQLite-Speicher und führt UI als verwalteten Hintergrundprozess aus. Es wird keine Modellanfrage weitergeleitet.

Lebenszyklusbefehle:

```bash
skill-runtime status
skill-runtime doctor
skill-runtime restart
skill-runtime stop
skill-runtime config --set retention_days=30
skill-runtime config --set network_export.endpoint=https://collector.example/v1/traces
skill-runtime config --set network_export.enabled=true
skill-runtime uninstall --keep-data
```

`uninstall` entfernt nur verwaltete Hook-Einträge und Skill Runtime-eigene Dateien. Ohne `--keep-data` ist eine interaktive Bestätigung (oder `--yes`) erforderlich, bevor `~/.skill-runtime` entfernt wird. Agentensitzungen und Fertigkeitsquellen werden niemals entfernt.

So indizieren und separat bereitstellen:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importieren Sie einen vorhandenen Trace-Export aus einem gängigen Observability-System:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Die versionierten Importprofile erkennen derzeit die Formen OTLP/Phoenix, Langfuse, LangSmith, W&B Weave und Datadog JSON. Sie erstellen nur dann ein SkillRun, wenn die Quelle eine explizite Skill-Semantik enthält; generische Span-Namen werden nicht als Aktivierungsnachweis behandelt.

Exportieren Sie normalisierte, Skill-spezifische Laufzeitnachweise an einen beliebigen OTLP/HTTP-Traces-Endpunkt:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Der Export ist deaktiviert, es sei denn, ein Endpunkt wird explizit konfiguriert. Prüfpunkte, Wiederholungsstatus und Zielzustand werden in den Einstellungen angezeigt. Rohe Eingabeaufforderungen, Tool-Payloads, Anmeldeinformationen und Skill-Ressourceninhalte werden nicht exportiert. Stellen Sie für den authentifizierten Hintergrundexport Standard `OTEL_EXPORTER_OTLP_HEADERS` in der Umgebung vor `skill-runtime start` bereit; Header werden niemals in Skill Runtime-Konfigurations- oder Prozessargumente geschrieben.

## Senden Sie Live-Laufzeitbeweise

`skill-runtime start` enthält einen lokalen Collector. Native Telemetrieadapter, offizielle Hooks, leichte Fail-Open-Hooks und SDK-Integrationen können ein einzelnes Ereignis oder einen begrenzten Batch an `POST /api/events` anhängen:

```bash
curl -X POST http://127.0.0.1:4317/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "evt-example-activation",
    "event_type": "skill.activated",
    "occurred_at": "2026-07-29T05:00:00Z",
    "session_id": "agent-session-example",
    "turn_id": "turn-1",
    "activation_mode": "explicit_tool",
    "skill": {"name": "pdf"},
    "source": {
      "adapter": "example-agent",
      "adapter_version": "1.0",
      "collection_mode": "official_hook",
      "source_event_id": "source-event-1"
    },
    "evidence": {
      "grade": "observed",
      "confidence": 1.0,
      "basis": "Official runtime hook"
    },
    "payload": {"tool_name": "Skill"}
  }'
```

Der Endpunkt redigiert allgemeine Anmeldeinformationen vor der Persistenz, dedupliziert sie um `event_id`, behält einen separaten redigierten Rohumschlag bei und gibt den resultierenden `skill_run_ids` zurück. `GET /api/collector/schema` macht das unterstützte Ereignisvokabular und die unterstützten Erfassungsmodi verfügbar. Der UI hört `/api/stream` über SSE ab, wobei die Abfrage nur als Fallback für die erneute Verbindung dient.

Der Quellindikator unterscheidet primäre Laufzeitnachweise von `Transcript fallback` und importierten Spuren. Ein Collector-Endpunkt allein erhebt keinen Anspruch auf native Telemetrie: Jeder Produzent muss angeben, ob sein Ereignis von nativer Telemetrie, einem offiziellen Hook, einem Lightweight-Hook oder einem SDK stammt.

### Optionale Agent-Hooks

Überprüfen Sie zunächst die genauen Pfade und Ereignisse. Dieser Befehl ist schreibgeschützt:

```bash
.venv/bin/skill-runtime setup
```

Die Hook-Installation erfordert ein explizites Flag:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Das Installationsprogramm sichert die Agent-Konfiguration, behält vorhandene Hooks bei und fügt nur Einträge hinzu, die eine Skill Runtime-Verwaltungsmarkierung tragen. Der Hook-Adapter speichert nur minimale Lebenszyklusfelder anstelle vollständiger Eingabeaufforderungen oder Tool-Payloads. Für abgeschlossene Tool-Aufrufe werden nur exakte `SKILL.md`-, Standard-Skill-Ressourcen- und geänderte Dateipfade im Speicher extrahiert. Rohbefehle, Patchkörper, Eingabeaufforderungen und Toolausgaben werden vor der Persistenz verworfen. Während die Laufzeit aktiv ist, ist ein berechtigungsbeschränkter Unix-Socket der schnelle Pfad; Ein optionaler nativer Absender vermeidet den Start von Python. Wenn die Laufzeit nicht aktiv ist, hängt der eigenständige Fail-Open-Pfad geschwärzte Beweise an `~/.skill-runtime/queue/events.jsonl` an. `skill-runtime start` gibt diese Warteschlange mit Ereignis-ID-Deduplizierung wieder.

Codex-Ereignisse verwenden ihre offiziellen Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` und `Stop`). Codex führt derzeit Befehls-Hooks synchron aus, daher verwendet Skill Runtime einen lokalen Unix-Socket/nativen Absender mit einem begrenzten Timeout. Jeder Lieferfehler wird geschluckt und in die Warteschlange gestellt. Es ändert nie die Entscheidung eines Agenten. Siehe [offizielle Codex Hook-Dokumentation](https://developers.openai.com/codex/config-advanced#hooks).

Entfernen Sie nur die verwalteten Einträge mit:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Der Server bindet standardmäßig an `127.0.0.1`. Vollständige Transkriptnachrichten und Tool-Nutzlasten werden nicht in den Index kopiert. Gemeinsame geheime Muster werden geschwärzt, bevor normalisierte Zusammenfassungen beibehalten werden.

Führen Sie die abhängigkeitsfreie Testsuite aus mit:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Release-Engineering

GitHub Actions führt Python 3.9–3.13-Tests, JavaScript-Validierung, native Absenderkompilierung und einen echten Installations-/Start-/Doctor-/Stopp-/Deinstallations-Rauchtest aus. Ein `v*`-Tag erstellt Wheel-/Sdist-Pakete sowie prüfsummengeschützte Linux- und macOS-native Absender. Das CLI-Installationsprogramm lädt das passende Release-Asset herunter, sodass Endbenutzer keinen Compiler benötigen.

Führen Sie das erste produktbezogene Diagnoseexperiment durch:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Es fügt Fehler in den Lebenszyklusnachweisen, expliziten Fehlern, unvollständigen Läufen und nicht überprüften Ergebnissen ein und wertet dann dieselbe deterministische Diagnose-Engine aus, die von API und UI verwendet wird. Siehe [PAI-DSW-Experimentplan](docs/pai-dsw-experiment-plan.md) für die Experimentierleiter, Nichtinterferenztests und den Reproduzierbarkeitsvertrag.

Führen Sie nach dem Erstellen des Rads den isolierten verpackten Lebenszyklusrauch aus mit:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Es wird in einer temporären virtuellen Umgebung und einem temporären Zuhause installiert, führt den gesamten lokalen Lebenszyklus aus, ohne Hooks zu aktivieren, und überprüft, ob Projekt- und Agentenkonfiguration nicht interferierend sind.

## Experimentelles Produktdesign

Das Produktverhalten wird durch das [experimentierorientierte Produktphilosophie](docs/experiment-driven-product-philosophy.md) eingeschränkt: Beweise vor Schlussfolgerungen, die erste beobachtbare Grenze vor dem Schweregrad, typisierte Beziehungen vor flachen Protokollen und deterministische Rekonstruktion vor probabilistischer Unterstützung.

Zu den aktuellen reproduzierbaren lokalen Beweisen gehören:

- 7/7 lokale Experimentstore wurden passiert;
- 2.400/2.400 Collector-Ereignisse werden ohne Input/Output-Mutation akzeptiert;
- 14/14 deterministische Fehler-Korpus-Diagnosen ohne unbegründete Kausalitätsbehauptung;
- relationale Diagnosedarstellung mit einer Genauigkeit von 13/14 und F1 0,963, während die flache Lebenszyklusabfrage eine Genauigkeit von 1/14 und F1 0,080 erreichte;
- In 11/11-Studienmaterialfällen wird die früheste beobachtbare Grenze zuerst gesetzt.

Diese Ergebnisse validieren Mechanismen und Darstellungsoptionen, nicht die Verallgemeinerung der Bereitstellung oder den Nutzen für den Menschen. Echte Second-Agent-Studien, plattformübergreifende Tail-Latenz, echte Fehlerkalibrierung und Studien zur Teilnehmerdiagnose bleiben offene Evidenzlücken.

Die Forschungsrichtung basiert auch auf angrenzenden Primärarbeiten: [SkillsBench](https://arxiv.org/abs/2602.12670) und [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivieren die Diagnose, da die Auswirkungen auf Fähigkeiten variieren und sich zurückbilden können; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiviert einen fähigkeitsbewussten, agentenübergreifenden Vergleich; und das [Untersuchung der Herkunft der Ausführung](https://arxiv.org/abs/2606.04990) motiviert typisierte Beweisbeziehungen, die Rückverfolgung der Herkunft und eine datenschutzbewusste Prüfinfrastruktur.

## Dokumentation

| Beginnen Sie hier | Zweck |
|---|---|
| [Getting Started](docs/getting-started.md) | Installieren Sie einen Agenten, verbinden Sie ihn, überprüfen Sie Live-Beweise und beheben Sie Fehler |
| [Architektur](docs/architecture.md) | Sammlungspipeline, Speichergrenzen, Beweis-Engine und Vertrauensmodell |
| [Adapterfähigkeitsmatrix](docs/adapter-capability-matrix.md) | Genaue Signale und Einschränkungen nach Agent/Version |
| [Einrichtung der Observability-Plattform](docs/observability-platform-setup.md) | Verbinden Sie OTLP-kompatible Plattformen und importieren Sie unterstützte Traces |
| [Laufzeitereignismodell](docs/runtime-event-model.md) | Stabiles Ereignisvokabular, Herkunft, Beziehungen und Evidenzgrade |
| [UI-Informationsarchitektur](docs/ui-information-architecture.md) | Übersicht, erste Grenze, Panorama, Inspektor, Vergleichen und Inferred Analysis |

Produkt- und Forschungsreferenzen: [Produktdefinition](docs/product-definition.md), [MVP-Spezifikation](docs/mvp-specification.md), [Observability-Interoperabilität](docs/observability-interoperability.md), [experimentierorientierte Produktphilosophie](docs/experiment-driven-product-philosophy.md), [Versuchsergebnisse](docs/experiment-results-2026-07-29.md) und [Forschungsagenda](docs/research-paper-agenda.md).

## Roadmap

1. **v0.2.0 – Jetzt verfügbar:** Live-Fail-Open-Sammlung, vier versionierte Agent-Adapter, Runtime Overview, Diagnose der ersten Grenze, Panorama, Evidence Inspector, fähigkeitsbewusster Vergleich, Inferred Analysis und OTLP-Interoperabilität.
2. **Weiter – Adapter- und Diagnosehärtung:** breitere Agenten-/Versionsabdeckung, echte Fehlerkalibrierung, plattformübergreifende Tail-Latenz-Validierung und Teilnehmerdiagnosestudien.
3. **Später – Effektauswertung:** kontrollierte gepaarte Auswertung mit Fertigkeit/ohne Fertigkeit, explizit getrennt von der Einzeldurchlaufdiagnose.

## Projektstatus

Version `v0.2.0` ist veröffentlicht. Die Laufzeit umfasst ein installiertes Definitionsinventar, zustimmungsgesteuerte offizielle Hook-Adapter für Codex, Claude Code und Qoder, ein Nur-Beobachtungs-OpenCode-Plugin, markiertes Transkript-Fallback, Active-Scope-Attribution, genaue Datei-/Artefaktpfade, Schwärzung, separate Quellen-/Beziehungs-/Inferenzebenen, SQLite Speicherung, Aufbewahrung, deterministische Diagnose, Live-UI und Cross-Run-/Cross-Agent-Vergleich. OTLP/Phoenix-, Langfuse-, LangSmith-, W&B Weave- und Datadog-Exporte können importiert werden; Normalisierte Beweise können über Opt-in OTLP/HTTP live exportiert werden.

Die Entdeckung von Kandidaten innerhalb des Modells, modellinterne Auswahlgründe, semantische Wirksamkeit und kausale Ergebnisansprüche werden ausdrücklich nicht unterstützt, es sei denn, eine Quelle oder ein kontrolliertes Experiment liefert diese Beweise.
