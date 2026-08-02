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


> Drehen `SKILL.md` in überprüfbare Laufzeiterwartungen umwandeln. Sehen Sie, was eigentlich
> geschah, wo das Verhalten zunächst auseinanderging, und die Beweise hinter dem Urteil.

Agent Skill Runtime Intelligence ist ein schreibgeschütztes Laufzeit-Beweis- und Diagnosesystem für Agent Skills. Es extrahiert konservative, überprüfbare Einschränkungen aus der aktuellen Skill-Definition, ordnet sie der Laufzeitaktivität zu und rekonstruiert das Ergebnis als evidenzbewertetes Ergebnis Skill Run Panorama. Es kombiniert offizielle Agent-Ereignisse, importierte Ablaufverfolgungen, gekennzeichnete Sitzungs-Fallbacks und beobachtbare Arbeitsbereichsergebnisse, ohne Modellanforderungen weiterzuleiten oder die Agent-Schleife zu übernehmen.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Schnellstart

Installieren und starten Sie die neueste Version auf macOS oder Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Kein Klon, Konto, `sudo`, oder GitHub CLI ist erforderlich. Das Installationsprogramm überprüft die Release-Prüfsumme, erkennt unterstützte Agenten und Skills, erklärt jeden Pfad, den es liest, fragt einmal, bevor es Nur-Beobachtungs-Hooks aktiviert, und öffnet das lokale UI bei [http://127.0.0.1:4317](http://127.0.0.1:4317). Laufzeitdaten bleiben unter `~/.skill-runtime` es sei denn, Sie konfigurieren explizit einen Export.

Du kannst [Überprüfen Sie den Installer](scripts/install.sh) bevor Sie es ausführen.

### Sehen Sie Ihr erstes Live SkillRun

1. Akzeptieren Sie das optionale Fail-Open Hook Setup, wenn das Installationsprogramm dazu fragt.
2. Starten Sie den Agenten neu und beginnen Sie mit einer neuen Aufgabe. In Codex, überprüfen Sie die verwalteten Befehle in `/hooks` Erste; Vorhandene Aufgaben können nicht im laufenden Betrieb neu geladen werden HookS.
3. Verwenden Sie einen Skill normal, bestätigen Sie dann die Integration und öffnen Sie den UI:

```bash
skill-runtime doctor
skill-runtime status
```

Eine Integration ist erst **Live**, nachdem der Collector ein echtes Laufzeitereignis empfängt. Ein konfiguriertes, aber unbeobachtetes Hook ist **ausstehend** – wird nie als Beweismittel präsentiert. Offen [http://127.0.0.1:4317](http://127.0.0.1:4317), oder sehen Sie sich die an [Leitfaden „Erste Schritte“.](docs/getting-started.md) für agentenspezifische Anweisungen und Fehlerbehebung.

So führen Sie den Vorgang direkt von einem Quell-Checkout aus aus:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Produktoberfläche | Was es antwortet |
|---|---|
| Runtime Overview | Welche SkillRuns Brauchen Sie Aufmerksamkeit? |
| Überprüfung des Fähigkeitsverhaltens | Welche überprüfbaren Anweisungen wurden erfüllt, müssen überprüft werden oder können nicht bewertet werden? |
| Was tatsächlich passiert ist | Welche Anweisungen, Ressourcen, Werkzeuge, Artefakte und Ergebnisse wurden beobachtet? |
| First Observable Boundary | Wo fehlen laufspezifische Beweise zum ersten Mal oder sind fehlgeschlagen? |
| Skill Run Panorama | Wie sind Anfrage, Aktivierung, Ressourcen, Tools, Artefakte und Ergebnis miteinander verbunden? |
| Evidence Inspector | Welche Quelle, Qualität, Basis und Adapterfähigkeit stützen diese Behauptung? |
| Vergleichen | Ist ein Unterschied verhaltensbedingt oder nur ein beobachtbarer Unterschied? |
| Inferred Analysis | Welche evidenzbasierte Erklärung oder nächste Untersuchung ist plausibel? |
| Einstellungen / Arzt | Was wird gelesen, gespeichert, exportiert, ausstehend und überprüft? |

## Wie es funktioniert

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime Beachtet den Workflow, den Sie bereits verwenden. Versionierte Adapter verwandeln agentennative Ereignisse in einen stabilen Skill-Lebenszyklus, während rohe Quellumschläge, normalisierte Ereignisse, Beziehungen und Schlussfolgerungen getrennt bleiben. Die Diagnose-Engine prüft explizite Skill-Einschränkungen anhand dieser Beweise, identifiziert die früheste beobachtbare Abweichung und hält systemische Adapter-Blindspots von laufspezifischen Erkenntnissen getrennt. Es erfindet keine Modellabsicht oder kausale Wirksamkeit.

| Datenquelle | Rolle | Frische | UI Etikett |
|---|---|---|---|
| Offizielle Agent-Hooks / Plugins / SDK Ereignisse | Primärer Lebenszyklus, Tool, Subagent und Terminalnachweise | Live | `Official hook` / `Native telemetry` |
| Fertigkeitsdateien und beobachtbare Arbeitsbereichsergebnisse | Definition, Ressource, Datei, Artefakt und Testnachweise | Live-Schnappschuss / indiziert | `Observed` |
| Sitzungsprotokolle | Kompatibilitäts-Fallback, wenn der Agent keine ausreichende Laufzeit zur Verfügung stellt API | Nah am Leben oder historisch | `Transcript fallback` |
| OTLP und unterstützte Trace-Exporte | Interoperabilität und historische Bedeutung | Live-Export / Batch-Import | Quellprofil angezeigt |
| Deterministische Korrelation | Verbindet Ereignisse mit einem SkillRun ohne die Quellenangaben zu ändern | Bei Einnahme | `Derived` |
| Semantische Hilfe | Nur Erläuterungen und Untersuchungsvorschläge | Auf Anfrage | `Inferred` |

Unterstützte Erstanbieteradapter werden unabhängig voneinander versioniert:

| Agent | Primäre Integration | Zurückgreifen | Sichtbarkeit der Aktivierung |
|---|---|---|---|
| Codex | Offizieller Befehl HookS | Sitzungsimport | Explizite Aktivierung bei Offenlegung durch die Hook Ereignis |
| Claude Code | Offiziell HookS | Sitzungsimport | Es wurden explizite Beweise für das Skill-Tool und den Slash-Command aufgedeckt |
| Qoder | Offizieller Befehl HookS | Lokale Aufzeichnungen | Explizite Aktivierung, wenn sie durch das Fähigkeitswerkzeug freigelegt wird |
| OpenCode | Globales Nur-Beobachtungs-Plugin | Lokale Aufzeichnungen | Rückrufe von Fertigkeitstools wurden angezeigt |

Genaue Leistungsgrenzen sind im dokumentiert [Adapterfähigkeitsmatrix](docs/adapter-capability-matrix.md). Nicht unterstützte und nicht beobachtete Phasen bleiben sichtbar und werden nicht in Fehler umgewandelt.

## Das Problem

Die Installation eines Skills beweist nicht, dass ein Agent ihn entdeckt hat. Die Entdeckung beweist keine Aktivierung. Die Aktivierung beweist nicht, dass die vollständigen Anweisungen und Ressourcen geladen wurden. Das Laden von Anweisungen beweist nicht, dass der Agent diese befolgt hat. Die Ausführung beweist nicht, dass die Fähigkeit das Ergebnis verbessert hat.

Heutzutage werden diese Misserfolge oft verheimlicht. Entwickler fragen sich:

- War der Skill für diesen Agenten verfügbar?
- Wurde es für diese Anfrage aktiviert?
- Welche Anweisungen, Referenzen, Skripte und Assets wurden geladen?
- Welche expliziten Qualifikationsanforderungen wurden befolgt, verfehlt oder konnten nicht bewertet werden?
- Welche Werkzeuge, MCP Anrufe, Subagenten, Dateien und Artefakte beteiligt waren?
- Wo ist die Ausführung fehlgeschlagen, wurde sie wiederholt oder der Kontext ging verloren?
- Hat der Skill geholfen oder hat er nur zusätzliche Kosten und Latenz verursacht?

## Fähigkeitsspezifische Diagnose

Das primäre Diagnoseobjekt ist a `SkillRun`, nicht eine ganze Agentensitzung:

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

Der UI sorgt dafür, dass der Lebenszyklus geordnet, typisiert und nach Beweisen bewertet wird. Fehlende Aktivierungstelemetrie bedeutet „nicht beobachtet“ oder „nicht unterstützt“; Dies bedeutet nicht, dass der Agent den Skill definitiv übersprungen hat.

## Beweisdisziplin

Der UI darf niemals eine Schlussfolgerung als Laufzeitfakt darstellen:

- **Beobachtet** – explizit in einem Quellereignis oder einer Quelldatei vorhanden.
- **Abgeleitet** – deterministisch verbunden aus beobachteten Beweisen.
- **Abgeleitet** – eine plausible Erklärung mit Unsicherheit.
- **Experimentell** – ein Effekt, der durch kontrollierte paarweise Auswertung gemessen wird.

Eine einzelne Ablaufverfolgung kann die Ausführungszuordnung unterstützen. Eine kausale Wirksamkeit kann nicht nachgewiesen werden. Behauptungen wie „diese Fähigkeit hat die Erfolgsquote verbessert“ erfordern eine wiederholte Bewertung mit/ohne Fähigkeit.

## Produktprinzipien

- Standardmäßig privat, mit lokaler, hybrider und teamverbundener Bereitstellung.
- Nur-Lese-Beobachtung; Übernehmen Sie niemals die Agentenschleife.
- Kein Modell-Proxy und kein obligatorischer Cloud-Service.
- Keine Blockierung, Genehmigungstür oder Richtliniendurchsetzung im Standardprodukt.
- Explizite Provenienz und Evidenzbewertung.
- Progressive Offenlegung: einfache Erzählung zuerst, rohe Ereignisse auf Anfrage.
- Adapterbasierte Unterstützung für die Änderung von Agent-Transkriptformaten.

## Aktueller Umfang

Die Laufzeit unterstützt Codex, Claude Code, Qoder, Und OpenCode durch unabhängige, versionierte Adapter und bietet:

- installierte Fähigkeitserkennung und -validierung;
- Echtzeit-Beamter Hook/plugin-Sammlung plus gekennzeichneter Sitzungs-Fallback;
- Zeitpläne für die Aktivierung von Fertigkeiten, das Laden von Ressourcen und Werkzeugaufrufe;
- Subagent, MCP, Datei- und Artefaktbeziehungen;
- Dauer, Token, Fehler, Wiederholungsversuche und Statuszusammenfassungen, sofern verfügbar;
- konservative Verhaltensbeschränkungen, die aus dem Strom extrahiert werden `SKILL.md`;
- evidenzbasierte Konformitäts-, Verifizierungs- und Laufzeitfehlerprüfungen;
- konkrete Anleitungs-, Ressourcen-, Werkzeug-, Artefakt- und Ergebnisinventare;
- Runtime Overview mit systemischen Abdeckungsgrenzen, getrennt von den Laufergebnissen;
- Erstgrenzdiagnose;
- ein Panorama-DAG, eine Ereigniszeitleiste und ein Beweisinspektor;
- fähigkeitsbewusster Vergleich gleicher und agentenübergreifender Agenten;
- ein separates Inferred Analysis Oberfläche, die Laufzeitfakten nicht neu schreiben kann;
- Opt-in OTLP/HTTP Export und unterstützter Observability-Trace-Import.

Das MVP umfasst **keinen** Marktplatz, Universal Agent Runtime, Sicherheitsdurchsetzung, Enterprise Governance oder Kausalwirkungsansprüche.

## Detaillierte Installation

Für den kürzesten unterstützten Pfad verwenden Sie das einzeilige Release-Installationsprogramm in [Schnellstart](#quick-start). Der vollständige Erstausführungsablauf, agentenspezifische Neustart-/Vertrauensschritte, Datenschutzverhalten und Fehlerbehebung live im [Leitfaden „Erste Schritte“.](docs/getting-started.md).

Für die Entwicklung weist die Basisimplementierung darüber hinaus keine Laufzeitabhängigkeiten auf Python 3,9+. Aus dem Repository-Stammverzeichnis:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Dann öffnen [http://127.0.0.1:4317](http://127.0.0.1:4317).

Das Einmalige `install` Befehl:

1. scannt Benutzer-, Projekt- und zwischengespeicherte Plugin-Skill-Standorte;
2. erkennt Codex, Claude Code, Qoder, Und OpenCode ohne ihre Konfiguration zu ändern;
3. zeigt an, welche Agenten- und Skillpfade gelesen werden;
4. lädt einen durch Prüfsummen verifizierten nativen Absender mit geringem Startup für die aktuelle Plattform herunter, greift auf einen lokalen C-Build zurück und schließlich auf den Python Absender und erwärmt einmal während der Installation eine neue native Binärdatei vor;
5. schafft `~/.skill-runtime/config.json` und das Lokale SQLite Index.

Der erste Index importiert vorhandene kompatible Agent-Sitzungen. Auf einer langlebigen Workstation kann dies länger dauern als eine Neuinstallation; Spätere Starts sind inkrementell und die UI wird verfügbar, während die Hintergrundaktualisierung ausgeführt wird.

Wenn es interaktiv ausgeführt wird, fragt es einmal nach, bevor es Fail-Open-Agent-Hooks hinzufügt. `--no-hooks` Behält den Transkriptimport als markierten Fallback bei, während `--enable-hooks` zeichnet die ausdrückliche Zustimmung auf und installiert nur verwaltete Einträge. Für Codex, offen `/hooks` Überprüfen Sie nach der Installation die genauen verwalteten Befehle und vertrauen Sie ihnen. Codex erfordert diese explizite Überprüfung absichtlich für Hooks, die außerhalb der verwalteten Unternehmenskonfiguration hinzugefügt werden. Neu starten Codex Aufgabe/Sitzung nach dem Vertrauen Hooks, dann ausführen:

```bash
.venv/bin/skill-runtime doctor
```

Qoder Lasten Hook Konfiguration beim Start, also neu starten Qoder nach der ersten Installation. OpenCode erkennt das verwaltete Nur-Beobachtungs-Plugin aus seinem globalen Plugin-Verzeichnis; neu starten OpenCode wenn der aktuelle Prozess vor der Installation durchgeführt wurde. Keine der Integrationen liest oder ändert Modellanforderungen.

Die Integration wird erst **Live**, nachdem die Datenbank eine echte Datei erhält `official_hook` Ereignis. Bloß schreiben `~/.codex/hooks.json` wird als **Ausstehend**, nie verbunden angezeigt. `start` startet den Collector, den Transkript-Fallback-Watcher und den Retention Worker. SQLite speichern und leben UI als verwalteter Hintergrundprozess. Es wird keine Modellanfrage weitergeleitet.

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

`uninstall` Entfernt nur verwaltet Hook Einträge und Skill Runtime-eigene Dateien. Ohne `--keep-data`, erfordert es eine interaktive Bestätigung (oder `--yes`), bevor Sie es entfernen `~/.skill-runtime`; Agentensitzungen und Fertigkeitsquellen werden niemals entfernt.

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

Die versionierten Importprofile erkennen derzeit OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, Und Datadog JSON Formen. Sie erstellen nur eine SkillRun wenn die Quelle eine explizite Skill-Semantik enthält; Generische Span-Namen werden nicht als Aktivierungsnachweis behandelt.

Exportieren Sie normalisierte, fähigkeitsspezifische Laufzeitnachweise in ein beliebiges OTLP/HTTP Traces-Endpunkt:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Der Export ist deaktiviert, es sei denn, ein Endpunkt wird explizit konfiguriert. Prüfpunkte, Wiederholungsstatus und Zielzustand werden in den Einstellungen angezeigt. Rohe Eingabeaufforderungen, Tool-Payloads, Anmeldeinformationen und Skill-Ressourceninhalte werden nicht exportiert. Geben Sie für den authentifizierten Hintergrundexport Standard an `OTEL_EXPORTER_OTLP_HEADERS` in der Umgebung vorher `skill-runtime start`; Header werden nie beschrieben Skill Runtime Konfigurations- oder Prozessargumente.

## Senden Sie Live-Laufzeitbeweise

`skill-runtime start` Enthält einen lokalen Collector. Native Telemetrieadapter, offizielle Hooks, leichte Fail-Open-Hooks und SDK Integrationen können ein einzelnes Ereignis oder einen begrenzten Stapel anhängen `POST /api/events`:

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

Der Endpunkt schwärzt allgemeine Anmeldeinformationen vor der Persistenz und dedupliziert sie `event_id`, behält einen separaten redigierten Rohumschlag bei und gibt das Ergebnis zurück `skill_run_ids`. `GET /api/collector/schema` macht das unterstützte Ereignisvokabular und die unterstützten Erfassungsmodi verfügbar. Der UI hört zu `/api/stream` Verwendung von SSE, wobei die Abfrage nur als Fallback für die erneute Verbindung dient.

Der Quellenindikator unterscheidet primäre Laufzeitbeweise von `Transcript fallback` und importierte Spuren. Ein Collector-Endpunkt allein erhebt keinen Anspruch auf native Telemetrie: Jeder Produzent muss angeben, ob sein Ereignis von nativer Telemetrie, einem offiziellen Hook, einem Lightweight-Hook oder einem anderen stammt SDK.

### Optionale Agent-Hooks

Überprüfen Sie zunächst die genauen Pfade und Ereignisse. Dieser Befehl ist schreibgeschützt:

```bash
.venv/bin/skill-runtime setup
```

Hook Die Installation erfordert ein explizites Flag:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Das Installationsprogramm sichert die Agent-Konfiguration, behält vorhandene Hooks bei und fügt nur Einträge mit a hinzu Skill Runtime Management-Marker. Der Hook-Adapter speichert nur minimale Lebenszyklusfelder anstelle vollständiger Eingabeaufforderungen oder Tool-Payloads. Bei abgeschlossenen Tool-Aufrufen werden nur exakte Extrahierungen vorgenommen `SKILL.md`, Standard-Skill-Ressource und geänderte Dateipfade im Speicher; Rohbefehle, Patchkörper, Eingabeaufforderungen und Toolausgaben werden vor der Persistenz verworfen. Während die Laufzeit aktiv ist, ist die Berechtigung eingeschränkt Unix Socket ist der schnelle Weg; ein optionaler nativer Absender vermeidet Python Start-up. Wenn die Laufzeit nicht aktiv ist, hängt der eigenständige Fail-Open-Pfad geschwärzte Beweise an `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` spielt diese Warteschlange mit Ereignis-ID-Deduplizierung ab.

Codex Veranstaltungen nutzen seinen Beamten Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, Und `Stop`). Codex führt derzeit Befehls-Hooks synchron aus, also Skill Runtime verwendet einen lokalen Unix Socket/nativer Absender mit begrenztem Timeout. Jeder Lieferfehler wird geschluckt und in die Warteschlange gestellt; Es ändert nie die Entscheidung eines Agenten. Siehe die [offizielle Codex Hook-Dokumentation](https://developers.openai.com/codex/config-advanced#hooks).

Entfernen Sie nur die verwalteten Einträge mit:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Der Server bindet an `127.0.0.1` standardmäßig. Vollständige Transkriptnachrichten und Tool-Nutzlasten werden nicht in den Index kopiert. Gemeinsame geheime Muster werden geschwärzt, bevor normalisierte Zusammenfassungen beibehalten werden.

Führen Sie die abhängigkeitsfreie Testsuite aus mit:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Release-Engineering

GitHub Aktionen werden ausgeführt Python 3.9–3.13-Tests, JavaScript-Validierung, native Absenderkompilierung und ein echter Rauchtest zum Installieren/Starten/Doctor/Stoppen/Deinstallieren. A `v*` Tag erstellt Wheel/Sdist-Pakete plus Prüfsummenschutz Linux Und macOS native Absender. Das CLI-Installationsprogramm lädt das passende Release-Asset herunter, sodass Endbenutzer keinen Compiler benötigen.

Führen Sie das erste produktbezogene Diagnoseexperiment durch:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Es fügt Fehler in den Lebenszyklusnachweisen, expliziten Fehlern, unvollständigen Läufen und nicht überprüften Ergebnissen ein und wertet dann dieselbe deterministische Diagnose-Engine aus, die von verwendet wird API Und UI. Siehe die [PAI-DSW-Experimentplan](docs/pai-dsw-experiment-plan.md) für die Experimentierleiter, Nichtinterferenztests und den Reproduzierbarkeitsvertrag.

Führen Sie nach dem Erstellen des Rads den isolierten verpackten Lebenszyklusrauch aus mit:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Es wird in einer temporären virtuellen Umgebung und einem temporären Zuhause installiert, führt den gesamten lokalen Lebenszyklus aus, ohne Hooks zu aktivieren, und überprüft, ob Projekt- und Agentenkonfiguration nicht interferierend sind.

## Experimentelles Produktdesign

Das Produktverhalten folgt vier experimentellen Einschränkungen: Beweise vor Schlussfolgerungen, die erste beobachtbare Grenze vor dem Schweregrad, typisierte Beziehungen vor flachen Protokollen und deterministische Rekonstruktion vor probabilistischer Unterstützung.

Reproduzierbare Beweise und ihre Grenzen werden in der beibehalten [Experimentbericht](docs/experiment-results-2026-07-29.md). Zu den begrenzten Ergebnissen gehören:

- 2.400/2.400 Collector-Ereignisse werden ohne Input/Output-Mutation akzeptiert;
- 14/14 deterministische Fehler-Korpus-Diagnosen ohne unbegründete Kausalitätsbehauptung;
- relationale Diagnosedarstellung mit einer Genauigkeit von 13/14 und F1 0,963, während die flache Lebenszyklusabfrage eine Genauigkeit von 1/14 und F1 0,080 erreichte;
- ein datenschutzsicheres Real-Run-Audit, das ausdrücklich für bestätigende Produktwirkungsaussagen ungeeignet bleibt, da verifizierte Ergebnisse, eine ausgewogene agentenübergreifende Abdeckung und menschliche Kennzeichnungen fehlen.

Diese Ergebnisse validieren Mechanismen und Darstellungsoptionen, nicht die Verallgemeinerung der Bereitstellung oder den Nutzen für den Menschen. Echte Second-Agent-Studien, plattformübergreifende Tail-Latenz, echte Fehlerkalibrierung und Studien zur Teilnehmerdiagnose bleiben offene Evidenzlücken.

Die Forschungsrichtung basiert auch auf angrenzenden Primärarbeiten: [SkillsBench](https://arxiv.org/abs/2602.12670) Und [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) Motivieren Sie die Diagnose, da die Auswirkungen von Fertigkeiten variieren und sich zurückbilden können. [Harness-Bench](https://arxiv.org/abs/2605.27922) motiviert zum fähigkeitsbewussten, agentenübergreifenden Vergleich; und die [Untersuchung der Herkunft der Ausführung](https://arxiv.org/abs/2606.04990) fördert typisierte Beweisbeziehungen, die Rückverfolgung der Herkunft und eine datenschutzbewusste Prüfinfrastruktur.

## Dokumentation

| Beginnen Sie hier | Zweck |
|---|---|
| [Getting Started](docs/getting-started.md) | Installieren Sie einen Agenten, verbinden Sie ihn, überprüfen Sie Live-Beweise und beheben Sie Fehler |
| [Architektur](docs/architecture.md) | Sammlungspipeline, Speichergrenzen, Beweis-Engine und Vertrauensmodell |
| [Adapterfähigkeitsmatrix](docs/adapter-capability-matrix.md) | Genaue Signale und Einschränkungen nach Agent/Version |
| [Einrichtung der Observability-Plattform](docs/observability-platform-setup.md) | Verbinden Sie OTLP-kompatible Plattformen und importieren Sie unterstützte Traces |
| [Laufzeitereignismodell](docs/runtime-event-model.md) | Stabiles Ereignisvokabular, Herkunft, Beziehungen und Evidenzgrade |
| [UI-Informationsarchitektur](docs/ui-information-architecture.md) | Übersicht, erste Grenze, Panorama, Inspektor, Vergleichen und Inferred Analysis |
| [Änderungsprotokoll](CHANGELOG.md) | Versionierte, für den Benutzer sichtbare Änderungen |
| [Versionshinweise zu v0.3.0](docs/releases/v0.3.0.md) | Upgrade-Anleitungen, Highlights und bekannte Grenzen |

Produkt- und Forschungsreferenzen: [Produktdefinition](docs/product-definition.md), [MVP-Spezifikation](docs/mvp-specification.md), [Observability-Interoperabilität](docs/observability-interoperability.md), [Versuchsergebnisse](docs/experiment-results-2026-07-29.md), und die [Forschungsagenda](docs/research-paper-agenda.md).

## Gemeinschaft und Governance

- Lesen [Mitwirken](CONTRIBUTING.md) bevor Sie die Beweissemantik, Adapter oder das Produktverhalten ändern.
- Folgen Sie dem [Verhaltenskodex](CODE_OF_CONDUCT.md) in allen Projekträumen.
- Melden Sie Schwachstellen privat über die [Sicherheitspolitik](SECURITY.md), keine öffentliche Angelegenheit.
- Nutzen Sie das Strukturierte [Issue-Tracker](https://github.com/hellogxp/skill-runtime-intelligence/issues) für reproduzierbare Fehler und Vorschläge für eingeschränkte Funktionen. Hängen Sie niemals private Laufzeitdatenbanken oder Sitzungsprotokolle an.

## Roadmap

1. **v0.3.0 – Nächste Version:** überprüfbare Skill-Verhaltenseinschränkungen, konkrete Laufzeitaktivität, evidenzbasierte Bewertung, systemische Abdeckungsdiagnose und der bestehende Live-Panorama- und Vergleichs-Workflow.
2. **Weiter – Adapter- und Diagnosehärtung:** breitere Agenten-/Versionsabdeckung, echte Fehlerkalibrierung, plattformübergreifende Tail-Latenz-Validierung und Teilnehmerdiagnosestudien.
3. **Später – Effektauswertung:** kontrollierte gepaarte Auswertung mit Fertigkeit/ohne Fertigkeit, explizit getrennt von der Einzeldurchlaufdiagnose.

## Projektstatus

Die aktuellen Quellbaumziele `v0.3.0`; Verwenden Sie das obige Release-Badge, um den zuletzt veröffentlichten Build zu identifizieren. Die Laufzeit umfasst überprüfbare Skill-Verhaltensbeschränkungen, konkrete Aktivitätszusammenfassungen, installierte Definitionsinventur und zustimmungsgesteuerte Beamte Hook Adapter für Codex, Claude Code, Und Qoder, eine reine Beobachtung OpenCode Plugin, beschriftetes Transkript-Fallback, Zuordnung im aktiven Bereich, genaue Datei-/Artefaktpfade, Schwärzung, separate Quellen-/Beziehungs-/Inferenzebenen, SQLite Speicherung, Aufbewahrung, deterministische Diagnose, live UIund Cross-Run-/Cross-Agent-Vergleich. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, Und Datadog Exporte können importiert werden; Normalisierte Beweise können per Opt-in live exportiert werden OTLP/HTTP.

Die Entdeckung von Kandidaten innerhalb des Modells, modellinterne Auswahlgründe, semantische Wirksamkeit und kausale Ergebnisansprüche werden ausdrücklich nicht unterstützt, es sei denn, eine Quelle oder ein kontrolliertes Experiment liefert diese Beweise.
