# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
**Deutsch** · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->


> Diagnostizieren Sie, wo ein Agent-Skill-Lauf zuerst auseinanderfiel – und prüfen Sie die Beweise
> hinter jeder Schlussfolgerung.

Agent Skill Runtime Intelligenceist ein schreibgeschütztes Laufzeit-Beweis- und Diagnosesystem für Agent Skills. Es kombiniert Skill-Definitionen, offizielle Agenten-Laufzeitereignisse, importierte Ablaufverfolgungen, Sitzungs-Fallbacks und beobachtbare Arbeitsbereichsergebnisse zu einem evidenzbewerteten ErgebnisSkill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Schnellstart

Installieren Sie die eigenständige Version mit einem authentifizierten Benutzer aus dem privaten RepositoryGitHub-CLI:

```bash
install_tmp="$(mktemp -d)"
gh release download --repo hellogxp/skill-runtime-intelligence \
  --pattern install.sh --dir "$install_tmp"
sh "$install_tmp/install.sh"
skill-runtime start
```

Oder führen Sie es direkt von einem Quell-Checkout aus aus:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Offen[http://127.0.0.1:4317](http://127.0.0.1:4317). FürCodexÜberprüfen Sie die verwalteten Befehle und vertrauen Sie ihnen`/hooks`, beginnen Sie einen neuen Agentenzug und überprüfen Sie dann Folgendes:

```bash
.venv/bin/skill-runtime doctor
```

Die Integration wird erst **verifiziert**, nachdem ein echtes offizielles Hook-Ereignis empfangen wurde. Ein konfigurierter Hook wird als **Ausstehend** angezeigt, niemals als Live-Beweis.

| Produktoberfläche | Was es antwortet |
|---|---|
| Laufzeitübersicht | WelcheSkillRunsBrauchen Sie Aufmerksamkeit? |
| Erste beobachtbare Grenze | Wo sind Beweise zum ersten Mal verschwunden oder fehlgeschlagen? |
| Skill Run Panorama | Wie sind Anfrage, Aktivierung, Ressourcen, Tools, Artefakte und Ergebnis miteinander verbunden? |
| Beweisinspektor | Welche Quelle, Qualität, Basis und Adapterfähigkeit stützen diese Behauptung? |
| Vergleichen | Ist ein Unterschied verhaltensbedingt oder nur ein beobachtbarer Unterschied? |
| Einstellungen / Arzt | Was wird gelesen, gespeichert, exportiert, ausstehend und überprüft? |

## Das Problem

Die Installation eines Skills beweist nicht, dass ein Agent ihn entdeckt hat. Die Entdeckung beweist keine Aktivierung. Die Aktivierung beweist nicht, dass die vollständigen Anweisungen und Ressourcen geladen wurden. Die Ausführung beweist nicht, dass die Fähigkeit das Ergebnis verbessert hat.

Heutzutage werden diese Misserfolge oft verheimlicht. Entwickler fragen sich:

- War der Skill für diesen Agenten verfügbar?
- Wurde es für diese Anfrage aktiviert?
- Welche Anweisungen, Referenzen, Skripte und Assets wurden geladen?
- Welche Werkzeuge,MCPAnrufe, Subagenten, Dateien und Artefakte beteiligt waren?
- Wo ist die Ausführung fehlgeschlagen, wurde sie wiederholt oder der Kontext ging verloren?
- Hat der Skill geholfen oder hat er nur zusätzliche Kosten und Latenz verursacht?

## Produktrichtung

Das erste Produkt ist ein **Skill Run Panorama**:

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

Das Panorama basiert auf realen Signalen, nicht auf Modell-Selbstberichten:

| Quelle | Beispiele | Beweis |
|---|---|---|
| Skill-Dateien | Metadaten, Anweisungen, Skripte, Referenzen, Assets | Beobachtet |
| Laufzeitereignisse | Skill-Aufrufe, Tool-Aufrufe, Subagenten, Fehler, Dauer | Beobachtet |
| Sitzungsprotokolle | Eingabeaufforderungen, Meldungen, Werkzeugeingaben und -ausgaben, Bestellung | Beobachtet |
| Ergebnisse des Arbeitsbereichs | Dateiänderungen,GitDiff, Berichte, generierte Artefakte | Beobachtet |
| Korrelation | Beziehungen zwischen Ereignissen, Ressourcen und Ergebnissen | Abgeleitet oder abgeleitet |

## Beweisdisziplin

DerUIdarf niemals eine Schlussfolgerung als Laufzeitfakt darstellen:

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

## Erster Umfang

Der MVP unterstütztClaude CodeUndCodexund bietet:

- installierte Fähigkeitserkennung und -validierung;
- Sitzungsimport und lokale Live-Beobachtung, sofern unterstützt;
- Zeitpläne für die Aktivierung von Fertigkeiten, das Laden von Ressourcen und Werkzeugaufrufe;
- Subagent,MCP, Datei- und Artefaktbeziehungen;
- Dauer, Token, Fehler, Wiederholungsversuche und Statuszusammenfassungen, sofern verfügbar;
- eine Ausführungsliste, Panorama-DAG, Ereigniszeitleiste und Knoteninspektor.

Das MVP umfasst **keinen** Marktplatz, Universal Agent Runtime, Sicherheitsdurchsetzung, Enterprise Governance oder Kausalwirkungsansprüche.

## Detaillierte Installation

Die Basisimplementierung weist darüber hinaus keine Laufzeitabhängigkeiten aufPython3,9+. Aus dem Repository-Stammverzeichnis:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Dann öffnen[http://127.0.0.1:4317](http://127.0.0.1:4317).

Das Einmalige`install`Befehl:

1. scannt Benutzer-, Projekt- und zwischengespeicherte Plugin-Skill-Standorte;
2. erkenntCodexUndClaude Codeohne ihre Konfiguration zu ändern;
3. zeigt an, welche Agenten- und Skillpfade gelesen werden;
4. lädt einen durch Prüfsummen verifizierten nativen Absender mit geringem Startup für die aktuelle Plattform herunter, greift auf einen lokalen C-Build zurück und schließlich auf denPythonAbsender und erwärmt einmal während der Installation eine neue native Binärdatei vor;
5. schafft`~/.skill-runtime/config.json`und das LokaleSQLiteIndex.

Wenn es interaktiv ausgeführt wird, fragt es einmal nach, bevor es Fail-Open-Agent-Hooks hinzufügt.`--no-hooks`Behält den Transkriptimport als markierten Fallback bei, während`--enable-hooks`zeichnet die ausdrückliche Zustimmung auf und installiert nur verwaltete Einträge. FürCodex, offen`/hooks`Überprüfen Sie nach der Installation die genauen verwalteten Befehle und vertrauen Sie ihnen.Codexerfordert diese explizite Überprüfung absichtlich für Hooks, die außerhalb der verwalteten Unternehmenskonfiguration hinzugefügt werden. Starten Sie einen neuen Agentenzug und führen Sie dann Folgendes aus:

```bash
.venv/bin/skill-runtime doctor
```

Die Integration wird erst **Live**, nachdem die Datenbank eine echte Datei erhält`official_hook`Ereignis. Bloß schreiben`~/.codex/hooks.json`wird als **Ausstehend**, nie verbunden angezeigt.`start`startet den Collector, den Transkript-Fallback-Watcher und den Retention Worker.SQLitespeichern und lebenUIals verwalteter Hintergrundprozess. Es wird keine Modellanfrage weitergeleitet.

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

`uninstall`Entfernt nur verwaltete Hook-Einträge undSkill Runtime-eigene Dateien. Ohne`--keep-data`, erfordert es eine interaktive Bestätigung (oder`--yes`), bevor Sie es entfernen`~/.skill-runtime`; Agentensitzungen und Fertigkeitsquellen werden niemals entfernt.

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

Die versionierten Importprofile erkennen derzeit OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, UndDatadog JSONFormen. Sie erstellen nur eineSkillRunwenn die Quelle eine explizite Skill-Semantik enthält; generische Span-Namen werden nicht als Aktivierungsnachweis behandelt.

Exportieren Sie normalisierte, fähigkeitsspezifische Laufzeitnachweise in beliebigeOTLP/HTTPTraces-Endpunkt:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Der Export ist deaktiviert, es sei denn, ein Endpunkt wird explizit konfiguriert. Prüfpunkte, Wiederholungsstatus und Zielzustand werden in den Einstellungen angezeigt. Rohe Eingabeaufforderungen, Tool-Payloads, Anmeldeinformationen und Skill-Ressourceninhalte werden nicht exportiert. Geben Sie für den authentifizierten Hintergrundexport Standard an`OTEL_EXPORTER_OTLP_HEADERS`in der Umgebung vorher`skill-runtime start`; Header werden nie beschriebenSkill RuntimeKonfigurations- oder Prozessargumente.

## Senden Sie Live-Laufzeitbeweise

`skill-runtime start`enthält einen lokalen Collector. Native Telemetrieadapter, offizielle Hooks, leichte Fail-Open-Hooks undSDKIntegrationen können ein einzelnes Ereignis oder einen begrenzten Stapel anhängen`POST /api/events`:

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

Der Endpunkt schwärzt allgemeine Anmeldeinformationen vor der Persistenz und dedupliziert sie`event_id`, behält einen separaten redigierten Rohumschlag bei und gibt das Ergebnis zurück`skill_run_ids`.`GET /api/collector/schema`macht das unterstützte Ereignisvokabular und die unterstützten Erfassungsmodi verfügbar. DerUIhört zu`/api/stream`Verwendung von SSE, wobei die Abfrage nur als Fallback für die erneute Verbindung dient.

Der Quellenindikator unterscheidet primäre Laufzeitbeweise von`Transcript fallback`und importierte Spuren. Ein Collector-Endpunkt allein erhebt keinen Anspruch auf native Telemetrie: Jeder Produzent muss angeben, ob sein Ereignis von nativer Telemetrie, einem offiziellen Hook, einem Lightweight-Hook oder einem anderen stammtSDK.

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

Das Installationsprogramm sichert die Agent-Konfiguration, behält vorhandene Hooks bei und fügt nur Einträge mit a hinzuSkill RuntimeManagement-Marker. Der Hook-Adapter speichert nur minimale Lebenszyklusfelder anstelle vollständiger Eingabeaufforderungen oder Tool-Payloads. Während die Laufzeit aktiv ist, ist die Berechtigung eingeschränktUnixSocket ist der schnelle Weg; ein optionaler nativer Absender vermeidetPythonStart-up. Wenn die Laufzeit nicht aktiv ist, hängt der eigenständige Fail-Open-Pfad geschwärzte Beweise an`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`spielt diese Warteschlange mit Ereignis-ID-Deduplizierung ab.

CodexVeranstaltungen verwenden ihren offiziellen HookAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, Und`Stop`).Codexführt derzeit Befehls-Hooks synchron aus, alsoSkill Runtimeverwendet einen lokalenUnixSocket/nativer Absender mit begrenztem Timeout. Jeder Lieferfehler wird geschluckt und in die Warteschlange gestellt. Es ändert nie die Entscheidung eines Agenten. Siehe die[offizielle Codex Hook-Dokumentation](https://developers.openai.com/codex/config-advanced#hooks).

Entfernen Sie nur die verwalteten Einträge mit:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Der Server bindet an`127.0.0.1`standardmäßig. Vollständige Transkriptnachrichten und Tool-Nutzlasten werden nicht in den Index kopiert. Gemeinsame geheime Muster werden geschwärzt, bevor normalisierte Zusammenfassungen beibehalten werden.

Führen Sie die abhängigkeitsfreie Testsuite aus mit:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Release-Engineering

GitHub-Aktionen werden ausgeführtPython3.9–3.13-Tests, JavaScript-Validierung, native Absenderkompilierung und ein echter Smoke-Test zum Installieren/Starten/Doctor/Stoppen/Deinstallieren. A`v*`Tag erstellt Wheel/Sdist-Pakete sowie prüfsummengeschützte native Linux- und macOS-Sender. Das CLI-Installationsprogramm lädt das passende Release-Asset herunter, sodass Endbenutzer keinen Compiler benötigen.

Führen Sie das erste produktbezogene Diagnoseexperiment durch:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Es fügt Fehler in den Lebenszyklusnachweisen, expliziten Fehlern, unvollständigen Läufen und nicht überprüften Ergebnissen ein und wertet dann dieselbe deterministische Diagnose-Engine aus, die auch von verwendet wirdAPIUndUI. Siehe die[PAI-DSW-Experimentplan](docs/pai-dsw-experiment-plan.md)für die Experimentierleiter, Nichtinterferenztests und den Reproduzierbarkeitsvertrag.

Führen Sie nach dem Erstellen des Rads den isolierten verpackten Lebenszyklusrauch aus mit:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Es wird in einer temporären virtuellen Umgebung und einem temporären Zuhause installiert, führt den gesamten lokalen Lebenszyklus aus, ohne Hooks zu aktivieren, und überprüft, ob Projekt- und Agentenkonfiguration nicht interferierend sind.

## Experimentelles Produktdesign

Das Produktverhalten wird durch die eingeschränkt[experimentierorientierte Produktphilosophie](docs/experiment-driven-product-philosophy.md): Beweise vor Schlussfolgerungen, die erste beobachtbare Grenze vor dem Schweregrad, typisierte Beziehungen vor flachen Protokollen und deterministische Rekonstruktion vor probabilistischer Unterstützung.

Zu den aktuellen reproduzierbaren lokalen Beweisen gehören:

- 7/7 lokale Experimentstore wurden passiert;
- 2.400/2.400 Collector-Ereignisse werden ohne Input/Output-Mutation akzeptiert;
- 14/14 deterministische Fehler-Korpus-Diagnosen ohne unbegründete Kausalitätsbehauptung;
- relationale Diagnosedarstellung mit einer Genauigkeit von 13/14 und F1 0,963, während die flache Lebenszyklusabfrage eine Genauigkeit von 1/14 und F1 0,080 erreichte;
- In 11/11-Studienmaterialfällen wird die früheste beobachtbare Grenze zuerst gesetzt.

Diese Ergebnisse validieren Mechanismen und Darstellungsoptionen, nicht die Verallgemeinerung der Bereitstellung oder den Nutzen für den Menschen. Echte Second-Agent-Studien, plattformübergreifende Tail-Latenz, echte Fehlerkalibrierung und Studien zur Teilnehmerdiagnose bleiben offene Evidenzlücken.

Die Forschungsrichtung basiert auch auf angrenzenden Primärarbeiten:[SkillsBench](https://arxiv.org/abs/2602.12670)Und[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)Motivieren Sie die Diagnose, da die Auswirkungen von Fertigkeiten variieren und sich zurückbilden können.[Harness-Bench](https://arxiv.org/abs/2605.27922)motiviert zum fähigkeitsbewussten, agentenübergreifenden Vergleich; und die[Untersuchung der Herkunft der Ausführung](https://arxiv.org/abs/2606.04990)fördert typisierte Beweisbeziehungen, die Rückverfolgung der Herkunft und eine datenschutzbewusste Prüfinfrastruktur.

## Dokumentation

- [Produktdefinition](docs/product-definition.md)
- [MVP-Spezifikation](docs/mvp-specification.md)
- [Laufzeitereignismodell](docs/runtime-event-model.md)
- [UI-Informationsarchitektur](docs/ui-information-architecture.md)
- [Adapterfähigkeitsmatrix](docs/adapter-capability-matrix.md)
- [Observability-Interoperabilität](docs/observability-interoperability.md)
- [Einrichtung der Observability-Plattform](docs/observability-platform-setup.md)
- [Forschungs- und Wettbewerbslandschaft](docs/research-and-competitive-landscape.md)
- [Agenda für Forschungsarbeiten](docs/research-paper-agenda.md)
- [Experimentelle Produktphilosophie](docs/experiment-driven-product-philosophy.md)
- [Versuchsergebnisse](docs/experiment-results-2026-07-29.md)
- [PAI-DSW-Experimentplan](docs/pai-dsw-experiment-plan.md)

## Roadmap

1. **v0.1 – Laufzeitbeweis und -diagnose:** Live-Sammlung,Skill Run Panorama, Erstgrenzdiagnose, Beweisprüfung, Vergleich und OTLP-Interoperabilität.
2. **v0.2 – Adapterbreite und Diagnosestudien:** zusätzliche Agenten, echte agentenübergreifende Experimente und Teilnehmerbewertung.
3. **v0.3 – Effektauswertung:** kontrollierte gepaarte Auswertung mit Fertigkeit/ohne Fertigkeit, getrennt von der Einzeldurchlaufdiagnose.

## Projektstatus

ASkillRun-erste Laufzeit ist ausführbar: Inventar der installierten Definition,CodexTranskript-Fallback, einwilligungsgesteuertCodexUndClaude CodeOffizielle Hook-Adapter, Active-Scope-Attribution, genaue Datei-/Artefaktpfade, Schwärzung, separate Quell-/Beziehungs-/Inferenzebenen,SQLiteSpeicherung, Aufbewahrung, Cross-Run- und Cross-Agent-Vergleich, deterministische Diagnose und das Live-PanoramaUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, UndDatadogExporte können importiert werden; Normalisierte Beweise können per Opt-in live exportiert werdenOTLP/HTTP. Die aktuelle reproduzierbare Suite verfügt über sieben Durchgangsexperimentstore. Kandidatenfindung, modellinterne Auswahlgründe, semantische Wirksamkeit und kausale Ergebnisansprüche werden weiterhin ausdrücklich nicht unterstützt.
