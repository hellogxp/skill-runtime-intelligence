# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · **Italiano** · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnostica il punto in cui l'esecuzione di una abilità dell'agente si è discostata per la prima volta e esamina le prove
> dietro ogni conclusione.

Agent Skill Runtime Intelligence è un sistema di prova e diagnosi runtime di sola lettura per le competenze dell'agente. Combina le definizioni delle competenze, gli eventi ufficiali di runtime dell'agente, le tracce importate, il fallback della sessione e i risultati osservabili dell'area di lavoro in un livello di prova Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Avvio rapido

Installa e avvia l'ultima versione su macOS o Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Non è richiesto alcun clone, account, `sudo` o GitHub CLI. Il programma di installazione verifica il checksum del rilascio, rileva gli agenti e le competenze supportati, spiega ogni percorso che leggerà, chiede una volta prima di abilitare gli hook di sola osservazione e apre il UI locale su [http://127.0.0.1:4317](http://127.0.0.1:4317). I dati di runtime rimangono in `~/.skill-runtime` a meno che non si configuri esplicitamente un'esportazione.

Puoi [ispezionare l'installatore](scripts/install.sh) prima di eseguirlo.

### Guarda il tuo primo live SkillRun

1. Accettare la configurazione facoltativa opzionale di apertura Hook quando richiesto dal programma di installazione.
2. Riavviare l'agente e iniziare una nuova attività. In Codex, rivedere prima i comandi gestiti in `/hooks`; le attività esistenti non caricano a caldo i nuovi Hook.
3. Usa normalmente un'abilità, quindi conferma l'integrazione e apri UI:

```bash
skill-runtime doctor
skill-runtime status
```

Un'integrazione è **Live** solo dopo che il Collector riceve un evento di runtime reale. Un Hook configurato ma non osservato è **In sospeso**: mai presentato come prova dal vivo. Apri [http://127.0.0.1:4317](http://127.0.0.1:4317) o consulta [Guida introduttiva](docs/getting-started.md) per istruzioni specifiche dell'agente e risoluzione dei problemi.

Per eseguire direttamente da un checkout di origine:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Superficie del prodotto | Cosa risponde |
|---|---|
| Runtime Overview | Quali SkillRuns necessitano di attenzione? |
| First Observable Boundary | Dove sono andate perdute o fallite le prove? |
| Skill Run Panorama | Come si collegavano richiesta, attivazione, risorse, strumenti, artefatti e risultati? |
| Evidence Inspector | Quale origine, grado, base e capacità dell'adattatore supportano questa affermazione? |
| Confrontare | Una differenza è comportamentale o è solo una differenza di osservabilità? |
| Inferred Analysis | Quale spiegazione basata sull’evidenza o prossima indagine è plausibile? |
| Impostazioni/Dottore | Cosa viene letto, archiviato, esportato, in sospeso e verificato? |

## Come funziona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime osserva il flusso di lavoro che già utilizzi. Gli adattatori con versione trasformano gli eventi nativi dell'agente in un ciclo di vita stabile delle competenze, mentre gli inviluppi di origine grezza, gli eventi normalizzati, le relazioni e le inferenze rimangono separati. Il motore di diagnosi identifica innanzitutto il primo confine in cui le prove diventano mancanti o fallite; non inventa l’intento del modello o l’efficacia causale.

| Origine dati | Ruolo | Freschezza | Etichetta UI |
|---|---|---|---|
| Hook/plug-in/eventi SDK ufficiali dell'agente | Ciclo di vita primario, strumento, agente secondario ed evidenza terminale | Vivere | `Official hook` / `Native telemetry` |
| File di competenze e risultati osservabili dello spazio di lavoro | Definizione, risorsa, file, artefatto e prova del test | Istantanea dal vivo/indicizzata | `Observed` |
| Trascrizioni delle sessioni | Fallback di compatibilità quando l'agente non espone un runtime sufficiente API | Quasi dal vivo o storico | `Transcript fallback` |
| OTLP e esportazioni di tracce supportate | Interoperabilità e importanza storica | Esportazione in tempo reale/importazione batch | Profilo di origine mostrato |
| Correlazione deterministica | Collega gli eventi a SkillRun senza modificare i fatti di origine | All'ingestione | `Derived` |
| Assistenza semantica | Solo spiegazioni e suggerimenti per l'indagine | Su richiesta | `Inferred` |

Gli adattatori originali supportati hanno una versione indipendente:

| Agente | Integrazione primaria | Ricaderci | Visibilità dell'attivazione |
|---|---|---|---|
| Codex | Comando ufficiale Hooks | Importazione della sessione | Attivazione esplicita quando esposta dall'evento Hook |
| Claude Code | Hook ufficiali | Importazione della sessione | Strumento di abilità esplicita e prova del comando barra dove esposti |
| Qoder | Comando ufficiale Hooks | Registri locali | Attivazione esplicita quando esposta dal suo strumento Abilità |
| OpenCode | Plugin globale di sola osservazione | Registri locali | Richiami degli strumenti di abilità dove esposti |

I limiti esatti di capacità sono documentati nel [matrice di capacità dell'adattatore](docs/adapter-capability-matrix.md). Le fasi non supportate e non osservate rimangono visibili invece di essere convertite in fallimenti.

## Il problema

L'installazione di una Skill non prova che un agente l'abbia scoperta. La scoperta non dimostra l'attivazione. L'attivazione non prova che siano state caricate le istruzioni e le risorse complete. L'esecuzione non dimostra che l'Abilità abbia migliorato il risultato.

Oggi questi fallimenti sono spesso silenziosi. Gli sviluppatori si chiedono:

- L'abilità era disponibile per questo agente?
- Si è attivato per questa richiesta?
- Quali istruzioni, riferimenti, script e risorse sono stati caricati?
- Quali strumenti, chiamate MCP, agenti secondari, file e artefatti sono stati coinvolti?
- Dove l'esecuzione non è riuscita, è stata riprovata o ha perso il contesto?
- La Skill è stata d'aiuto o ha solo aggiunto costi e latenza?

## Diagnosi specifica per abilità

L'oggetto diagnostico principale è un `SkillRun`, non un'intera sessione dell'agente:

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

Il UI mantiene il ciclo di vita ordinato, tipizzato e classificato in base alle prove. La telemetria di attivazione mancante significa "non osservato" o "non supportato"; ciò non significa che l'Agente abbia definitivamente saltato l'Abilità.

## Disciplina della prova

Il UI non deve mai presentare un'inferenza come fatto di runtime:

- **Osservato**: presente esplicitamente in un evento o file di origine.
- **Derivato**: connesso in modo deterministico dalle prove osservate.
- **Dedotto**: una spiegazione plausibile con incertezza.
- **Sperimentale**: un effetto misurato attraverso una valutazione abbinata controllata.

Una singola traccia può supportare l'attribuzione dell'esecuzione. Non può dimostrare l’efficacia causale. Affermazioni come "questa abilità ha migliorato il tasso di successo" richiedono una valutazione ripetuta con/senza abilità.

## Principi del prodotto

- Privato per impostazione predefinita, con distribuzione locale, ibrida e connessa al team.
- Osservazione di sola lettura; non assumere mai il controllo del ciclo dell'agente.
- Nessun modello proxy e nessun servizio cloud obbligatorio.
- Nessun blocco, blocco dell'approvazione o applicazione di policy nel prodotto predefinito.
- Provenienza esplicita e classificazione delle prove.
- Divulgazione progressiva: prima la narrazione semplice, eventi grezzi su richiesta.
- Supporto basato su adattatore per la modifica dei formati di trascrizione dell'agente.

## Ambito attuale

Il runtime supporta Codex, Claude Code, Qoder e OpenCode tramite adattatori indipendenti e con versione e fornisce:

- rilevamento e convalida delle competenze installate;
- raccolta ufficiale Hook/plugin in tempo reale più fallback della sessione etichettata;
- Attivazione delle competenze, caricamento delle risorse e tempistiche delle chiamate agli strumenti;
- relazioni tra agente secondario, MCP, file e artefatto;
- riepiloghi di durata, token, errori, tentativi e stato, se disponibili;
- Runtime Overview e diagnosi di primo confine;
- un DAG panoramico, una cronologia degli eventi e un ispettore delle prove;
- confronto tra lo stesso agente e tra agenti in base alle funzionalità;
- una superficie Inferred Analysis separata che non può riscrivere i fatti di runtime;
- attivazione esplicita dell'esportazione OTLP/HTTP e importazione supportata della traccia di osservabilità.

L'MVP **non** include marketplace, runtime dell'agente universale, applicazione della sicurezza, governance aziendale o affermazioni sull'effetto causale.

## Installazione dettagliata

Per il percorso supportato più breve, utilizzare il programma di installazione della versione a una riga in [Avvio rapido](#quick-start). Il flusso completo di prima esecuzione, i passaggi di riavvio/attendibilità specifici dell'agente, il comportamento in materia di privacy e la risoluzione dei problemi sono disponibili in [Guida introduttiva](docs/getting-started.md).

Per lo sviluppo, l'implementazione di base non ha dipendenze di runtime oltre Python 3.9+. Dalla radice del repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Quindi apri [http://127.0.0.1:4317](http://127.0.0.1:4317).

Il comando `install` una tantum:

1. esegue la scansione delle posizioni delle competenze di utenti, progetti e plug-in memorizzati nella cache;
2. rileva Codex, Claude Code, Qoder e OpenCode senza modificarne la configurazione;
3. mostra quali percorsi Agente e Competenza verranno letti;
4. scarica un mittente nativo a basso avvio verificato con checksum per la piattaforma corrente, ricorrendo a una build C locale e infine al mittente Python e preriscalda un nuovo binario nativo una volta durante l'installazione;
5. crea `~/.skill-runtime/config.json` e l'indice locale SQLite.

Quando viene eseguito in modo interattivo, richiede una volta prima di aggiungere hook dell'agente di apertura non riuscita. `--no-hooks` mantiene l'importazione della trascrizione come fallback etichettato, mentre `--enable-hooks` registra il consenso esplicito e installa solo le voci gestite. Per Codex, apri `/hooks` dopo l'installazione, esamina gli esatti comandi gestiti e fidati di loro. Codex richiede intenzionalmente questa revisione esplicita per gli hook aggiunti all'esterno della configurazione aziendale gestita. Avvia una nuova attività/sessione Codex dopo aver dato fiducia agli Hook, quindi esegui:

```bash
.venv/bin/skill-runtime doctor
```

Qoder carica la configurazione di Hook all'avvio, quindi riavvia Qoder dopo la prima installazione. OpenCode scopre il plugin di sola osservazione gestito dalla sua directory globale dei plugin; riavviare OpenCode se il processo corrente è precedente all'installazione. Nessuna delle due integrazioni legge o modifica le richieste del modello.

L'integrazione diventa **Live** solo dopo che il database riceve un evento `official_hook` reale. La semplice scrittura di `~/.codex/hooks.json` viene visualizzata come **In sospeso**, mai Connesso. `start` avvia il servizio di raccolta, l'osservatore di fallback della trascrizione, l'addetto alla conservazione, l'archivio SQLite e UI attivo come processo in background gestito. Nessuna richiesta di modello è delegata.

Comandi del ciclo di vita:

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

`uninstall` rimuove solo le voci gestite Hook e i file di proprietà di Skill Runtime. Senza `--keep-data`, richiede conferma interattiva (o `--yes`) prima di rimuovere `~/.skill-runtime`; Le sessioni dell'agente e le origini delle competenze non vengono mai rimosse.

Per indicizzare e pubblicare separatamente:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importa un'esportazione di traccia esistente da un sistema di osservabilità tradizionale:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

I profili di importazione con versione attualmente riconoscono le forme OTLP/Phoenix, Langfuse, LangSmith, W&B Weave e Datadog JSON. Creano un SkillRun solo quando la fonte porta una semantica Abilità esplicita; i nomi di span generici non vengono trattati come prova di attivazione.

Esporta prove di runtime normalizzate e specifiche della competenza su qualsiasi endpoint di tracce OTLP/HTTP:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

L'esportazione è disabilitata a meno che un endpoint non sia configurato in modo esplicito. I checkpoint, lo stato dei nuovi tentativi e lo stato della destinazione vengono visualizzati in Impostazioni. I prompt non elaborati, i payload degli strumenti, le credenziali e i contenuti delle risorse delle competenze non vengono esportati. Per l'esportazione in background autenticata, fornire lo standard `OTEL_EXPORTER_OTLP_HEADERS` nell'ambiente prima di `skill-runtime start`; le intestazioni non vengono mai scritte nella configurazione Skill Runtime o negli argomenti del processo.

## Invia prove di runtime in tempo reale

`skill-runtime start` include un raccoglitore locale. Gli adattatori di telemetria nativi, gli hook ufficiali, gli hook fail-open leggeri e le integrazioni SDK possono aggiungere un singolo evento o un batch limitato a `POST /api/events`:

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

L'endpoint oscura le credenziali comuni prima della persistenza, deduplica per `event_id`, conserva una busta grezza oscurata separata e restituisce il risultante `skill_run_ids`. `GET /api/collector/schema` espone il vocabolario degli eventi supportati e le modalità di raccolta. L'UI ascolta `/api/stream` utilizzando SSE, con il polling solo come fallback di riconnessione.

L'indicatore di origine distingue le prove di runtime primarie da `Transcript fallback` e le tracce importate. Un endpoint Collector da solo non rivendica la telemetria nativa: ogni produttore deve dichiarare se il suo evento proviene dalla telemetria nativa, da un hook ufficiale, da un hook leggero o da un SDK.

### Hook dell'agente opzionali

Ispezionare prima i percorsi e gli eventi esatti. Questo comando è di sola lettura:

```bash
.venv/bin/skill-runtime setup
```

L'installazione Hook richiede un flag esplicito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Il programma di installazione esegue il backup della configurazione dell'agente, preserva gli hook esistenti e aggiunge solo le voci che portano un indicatore di gestione Skill Runtime. L'adattatore hook memorizza campi minimi del ciclo di vita anziché prompt completi o payload dello strumento. Per le chiamate allo strumento completate, estrae solo l'esatto `SKILL.md`, la risorsa abilità standard e i percorsi dei file modificati in memoria; i comandi grezzi, i corpi delle patch, i prompt e gli output degli strumenti vengono eliminati prima della persistenza. Mentre il runtime è attivo, un socket Unix con autorizzazioni limitate è il percorso veloce; un mittente nativo opzionale evita l'avvio di Python. Quando il runtime non è attivo, il percorso fail-open autonomo aggiunge prove oscurate a `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` riproduce la coda con la deduplicazione dell'ID evento.

Gli eventi Codex utilizzano il suo ufficiale Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` e `Stop`). Codex attualmente esegue gli hook di comando in modo sincrono, quindi Skill Runtime utilizza un socket Unix locale/mittente nativo con un timeout limitato. Qualsiasi errore di consegna viene inghiottito e messo in coda; non cambia mai la decisione dell'Agente. Vedi [documentazione ufficiale del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Rimuovi solo le voci gestite con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Il server si collega a `127.0.0.1` per impostazione predefinita. I messaggi di trascrizione completa e i payload dello strumento non vengono copiati nell'indice. I modelli segreti comuni vengono redatti prima che i riepiloghi normalizzati vengano mantenuti.

Esegui la suite di test senza dipendenze con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingegneria del rilascio

GitHub Le azioni eseguono test Python 3.9–3.13, convalida JavaScript, compilazione del mittente nativo e un vero test del fumo di installazione/avvio/medico/arresto/disinstallazione. Un tag `v*` crea pacchetti wheel/sdist più mittenti nativi Linux e macOS protetti da checksum. Il programma di installazione della CLI scarica la risorsa di rilascio corrispondente, quindi gli utenti finali non hanno bisogno di un compilatore.

Esegui il primo esperimento di diagnostica collegata al prodotto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inserisce lacune nelle prove del ciclo di vita, guasti espliciti, esecuzioni incomplete e risultati non verificati, quindi valuta lo stesso motore di diagnosi deterministica utilizzato da API e UI. Vedere [Piano dell'esperimento PAI-DSW](docs/pai-dsw-experiment-plan.md) per la scala degli esperimenti, i test di non interferenza e il contratto di riproducibilità.

Dopo aver costruito la ruota, esegui il fumo del ciclo di vita del pacchetto isolato con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Si installa in un ambiente virtuale temporaneo e in una casa temporanea, esercita l'intero ciclo di vita locale senza abilitare gli hook e verifica la non interferenza della configurazione del progetto e dell'agente.

## Progettazione del prodotto basata sugli esperimenti

Il comportamento del prodotto è vincolato da [filosofia di prodotto guidata dalla sperimentazione](docs/experiment-driven-product-philosophy.md): prove prima delle conclusioni, primo confine osservabile prima della gravità, relazioni tipizzate prima dei log piatti e ricostruzione deterministica prima dell'assistenza probabilistica.

Le attuali prove locali riproducibili includono:

- 7/7 cancelli dell'esperimento locale superati;
- 2.400/2.400 eventi del Collector accettati senza mutazione di input/output;
- 14/14 diagnosi deterministiche del corpo degli errori senza alcuna affermazione causale non supportata;
- rappresentazione della diagnosi relazionale a 13/14 esatto e F1 0,963, mentre il recupero del ciclo di vita piatto ha raggiunto 1/14 esatto e F1 0,080;
- I casi di materiale di studio 11/11 collocano per primo il primo confine osservabile.

Questi risultati convalidano i meccanismi e le scelte di rappresentanza, non la generalizzazione dell’implementazione o il vantaggio umano. Gli studi sul secondo agente reale, la latenza della coda multipiattaforma, la calibrazione dei guasti reali e gli studi sulla diagnosi dei partecipanti rimangono lacune di prove aperte.

La direzione della ricerca si basa anche sul lavoro primario adiacente: [SkillsBench](https://arxiv.org/abs/2602.12670) e [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivano la diagnosi perché gli effetti delle Abilità variano e possono regredire; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva il confronto tra agenti consapevole delle capacità; e la [indagine sulla provenienza dell'esecuzione](https://arxiv.org/abs/2606.04990) motiva le relazioni con le prove digitate, la provenienza delle tracce e l'infrastruttura di controllo attenta alla privacy.

## Documentazione

| Inizia qui | Scopo |
|---|---|
| [Getting Started](docs/getting-started.md) | Installa, collega un agente, verifica prove dal vivo e risolvi i problemi |
| [Architettura](docs/architecture.md) | Pipeline di raccolta, limiti di archiviazione, motore delle prove e modello di fiducia |
| [Matrice delle capacità dell'adattatore](docs/adapter-capability-matrix.md) | Segnali esatti e limitazioni per agente/versione |
| [Configurazione della piattaforma di osservabilità](docs/observability-platform-setup.md) | Connetti piattaforme compatibili con OTLP e importa tracce supportate |
| [Modello di eventi di runtime](docs/runtime-event-model.md) | Vocabolario stabile degli eventi, provenienza, relazioni e gradi di prova |
| [Architettura delle informazioni dell'interfaccia utente](docs/ui-information-architecture.md) | Panoramica, primo confine, Panorama, Ispettore, Confronta e Inferred Analysis |

Riferimenti di prodotti e ricerche: [definizione del prodotto](docs/product-definition.md), [Specifica MVP](docs/mvp-specification.md), [interoperabilità osservabile](docs/observability-interoperability.md), [filosofia di prodotto guidata dalla sperimentazione](docs/experiment-driven-product-philosophy.md), [risultati dell'esperimento](docs/experiment-results-2026-07-29.md) e [agenda di ricerca](docs/research-paper-agenda.md).

## Tabella di marcia

1. **v0.2.0 — Disponibile ora:** raccolta live fail-open, quattro adattatori per agenti con versione, Runtime Overview, diagnosi del primo limite, Panorama, Evidence Inspector, confronto con funzionalità, Inferred Analysis e interoperabilità OTLP.
2. **Avanti: Rafforzamento dell'adattatore e della diagnosi:** copertura più ampia di agenti/versioni, calibrazione degli errori reali, convalida della latenza di coda multipiattaforma e studi sulla diagnosi dei partecipanti.
3. **Successivo — Valutazione degli effetti:** valutazione accoppiata controllata con/senza abilità, mantenuta esplicitamente separata dalla diagnosi a ciclo singolo.

## Stato del progetto

Pubblicata la versione `v0.2.0`. Il runtime include inventario delle definizioni installate, adattatori Hook ufficiali basati sul consenso per Codex, Claude Code e Qoder, un plug-in OpenCode di sola osservazione, fallback di trascrizione etichettato, attribuzione di ambito attivo, percorsi esatti di file/artefatti, redazione, livelli di origine/relazione/inferenza separati, SQLite archiviazione, conservazione, diagnosi deterministica, UI in tempo reale e confronto tra analisi incrociate/tra agenti. È possibile importare esportazioni OTLP/Phoenix, Langfuse, LangSmith, W&B Weave e Datadog; le prove normalizzate possono essere esportate in tempo reale tramite l'opt-in OTLP/HTTP.

La scoperta dei candidati all'interno del modello, le ragioni della selezione interna del modello, l'efficacia semantica e le affermazioni sui risultati causali rimangono esplicitamente non supportate a meno che una fonte o un esperimento controllato non forniscano tale prova.
