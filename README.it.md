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


> Giro `SKILL.md` in aspettative di runtime verificabili. Guarda cosa in realtà
> accaduto, dove il comportamento inizialmente divergeva, e le prove alla base della sentenza.

Agent Skill Runtime Intelligence è un sistema di prova e diagnosi runtime di sola lettura per le competenze dell'agente. Estrae vincoli conservativi e ispezionabili dall'attuale definizione di abilità, li abbina all'attività di runtime e ricostruisce il risultato come un risultato classificato in base all'evidenza Skill Run Panorama. Combina eventi ufficiali dell'agente, tracce importate, fallback della sessione etichettata e risultati osservabili dell'area di lavoro senza inoltrare richieste di modelli tramite proxy o assumere il controllo del ciclo dell'agente.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Avvio rapido

Installa e avvia l'ultima versione su macOS O Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nessun clone, account, `sudo`, O GitHub CLI è obbligatorio. Il programma di installazione verifica il checksum del rilascio, rileva gli agenti e le competenze supportati, spiega ogni percorso che leggerà, chiede una volta prima di abilitare gli hook di sola osservazione e apre la finestra locale UI A [http://127.0.0.1:4317](http://127.0.0.1:4317). I dati di runtime rimangono sotto `~/.skill-runtime` a meno che non si configuri esplicitamente un'esportazione.

Puoi [ispezionare l'installatore](scripts/install.sh) prima di eseguirlo.

### Guarda il tuo primo live SkillRun

1. Accettare il fail-open opzionale Hook configurazione quando richiesto dal programma di installazione.
2. Riavviare l'agente e iniziare una nuova attività. In Codex, rivedere i comandi gestiti in `/hooks` Primo; le attività esistenti non vengono caricate a caldo nuove HookS.
3. Utilizza normalmente una Skill, quindi conferma l'integrazione e apri il file UI:

```bash
skill-runtime doctor
skill-runtime status
```

Un'integrazione è **Live** solo dopo che il Collector riceve un evento di runtime reale. Un configurato ma inosservato Hook è **In sospeso**: non è mai stato presentato come prova reale. Aprire [http://127.0.0.1:4317](http://127.0.0.1:4317)o vedere il [Guida introduttiva](docs/getting-started.md) per istruzioni specifiche dell'agente e risoluzione dei problemi.

Per eseguire direttamente da un checkout di origine:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Superficie del prodotto | Cosa risponde |
|---|---|
| Runtime Overview | Quale SkillRuns bisogno di attenzione? |
| Controllo del comportamento delle abilità | Quali istruzioni verificabili sono state soddisfatte, necessitano di revisione o non possono essere valutate? |
| Cosa è realmente successo | Quali istruzioni, risorse, strumenti, artefatti e risultati sono stati osservati? |
| First Observable Boundary | Dove vengono per la prima volta mancanti o fallite le prove specifiche dell'esecuzione? |
| Skill Run Panorama | Come si collegavano richiesta, attivazione, risorse, strumenti, artefatti e risultati? |
| Evidence Inspector | Quale origine, grado, base e capacità dell'adattatore supportano questa affermazione? |
| Confrontare | Una differenza è comportamentale o è solo una differenza di osservabilità? |
| Inferred Analysis | Quale spiegazione basata sull’evidenza o prossima indagine è plausibile? |
| Impostazioni/Dottore | Cosa viene letto, archiviato, esportato, in sospeso e verificato? |

## Come funziona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime osserva il flusso di lavoro che già utilizzi. Gli adattatori con versione trasformano gli eventi nativi dell'agente in un ciclo di vita stabile delle competenze, mentre gli inviluppi di origine grezza, gli eventi normalizzati, le relazioni e le inferenze rimangono separati. Il motore di diagnosi confronta i vincoli di abilità espliciti con tali prove, identifica la prima deviazione osservabile e mantiene i punti ciechi dell'adattatore sistemico separati dai risultati specifici dell'esecuzione. Non inventa l’intento del modello o l’efficacia causale.

| Origine dati | Ruolo | Freschezza | UI etichetta |
|---|---|---|---|
| Hook / plugin ufficiali dell'agente / SDK eventi | Ciclo di vita primario, strumento, agente secondario ed evidenza terminale | Vivere | `Official hook` / `Native telemetry` |
| File di competenze e risultati osservabili dello spazio di lavoro | Definizione, risorsa, file, artefatto e prova del test | Istantanea dal vivo/indicizzata | `Observed` |
| Trascrizioni delle sessioni | Fallback di compatibilità quando l'agente non espone un runtime sufficiente API | Quasi dal vivo o storico | `Transcript fallback` |
| OTLP e esportazioni di tracce supportate | Interoperabilità e importanza storica | Esportazione in tempo reale/importazione batch | Profilo di origine mostrato |
| Correlazione deterministica | Collega gli eventi a a SkillRun senza modificare i fatti di origine | All'ingestione | `Derived` |
| Assistenza semantica | Solo spiegazioni e suggerimenti per l'indagine | Su richiesta | `Inferred` |

Gli adattatori originali supportati hanno una versione indipendente:

| Agente | Integrazione primaria | Ricaderci | Visibilità dell'attivazione |
|---|---|---|---|
| Codex | Comando ufficiale HookS | Importazione della sessione | Attivazione esplicita quando esposta dal Hook evento |
| Claude Code | Ufficiale HookS | Importazione della sessione | Strumento di abilità esplicita e prova del comando barra dove esposti |
| Qoder | Comando ufficiale HookS | Registri locali | Attivazione esplicita quando esposta dal suo strumento Abilità |
| OpenCode | Plugin globale di sola osservazione | Registri locali | Richiami degli strumenti di abilità dove esposti |

I limiti esatti di capacità sono documentati nel [matrice di capacità dell'adattatore](docs/adapter-capability-matrix.md). Le fasi non supportate e non osservate rimangono visibili invece di essere convertite in fallimenti.

## Il problema

L'installazione di una Skill non prova che un agente l'abbia scoperta. La scoperta non dimostra l'attivazione. L'attivazione non dimostra che siano state caricate le istruzioni e le risorse complete. Le istruzioni di caricamento non dimostrano che l'agente le abbia seguite. L'esecuzione non dimostra che l'Abilità abbia migliorato il risultato.

Oggi questi fallimenti sono spesso silenziosi. Gli sviluppatori si chiedono:

- L'abilità era disponibile per questo agente?
- Si è attivato per questa richiesta?
- Quali istruzioni, riferimenti, script e risorse sono stati caricati?
- Quali requisiti espliciti di abilità sono stati seguiti, mancati o impossibili da valutare?
- Quali strumenti, MCP erano coinvolti chiamate, agenti secondari, file e artefatti?
- Dove l'esecuzione non è riuscita, è stata riprovata o ha perso il contesto?
- La Skill è stata d'aiuto o ha solo aggiunto costi e latenza?

## Diagnosi specifica per abilità

L'oggetto diagnostico principale è a `SkillRun`, non un'intera sessione dell'agente:

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

IL UI mantiene il ciclo di vita ordinato, tipizzato e classificato in base alle prove. La telemetria di attivazione mancante significa "non osservato" o "non supportato"; ciò non significa che l'Agente abbia definitivamente saltato l'Abilità.

## Disciplina della prova

IL UI non deve mai presentare un'inferenza come fatto di runtime:

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

Il runtime supporta Codex, Claude Code, Qoder, E OpenCode attraverso adattatori indipendenti e con più versioni e fornisce:

- rilevamento e convalida delle competenze installate;
- ufficiale in tempo reale Hookraccolta /plugin più fallback della sessione etichettata;
- Attivazione delle competenze, caricamento delle risorse e tempistiche delle chiamate agli strumenti;
- subagente, MCPrelazioni , file e artefatti;
- riepiloghi di durata, token, errori, tentativi e stato, se disponibili;
- vincoli di comportamento conservativo estratti dalla corrente `SKILL.md`;
- controlli di conformità, verifica e errori di runtime basati sull'evidenza;
- inventari concreti di istruzioni, risorse, strumenti, artefatti e risultati;
- Runtime Overview con limiti di copertura sistemica separati dai risultati della corsa;
- diagnosi di primo confine;
- un DAG panoramico, una cronologia degli eventi e un ispettore delle prove;
- confronto tra lo stesso agente e tra agenti in base alle funzionalità;
- un separato Inferred Analysis superficie che non può riscrivere i fatti di runtime;
- opt-in OTLP/HTTP esportazione e importazione di tracce di osservabilità supportata.

L'MVP **non** include marketplace, runtime dell'agente universale, applicazione della sicurezza, governance aziendale o affermazioni sull'effetto causale.

## Installazione dettagliata

Per il percorso supportato più breve, utilizzare il programma di installazione della versione a riga singola in [Avvio rapido](#quick-start). Il flusso completo di prima esecuzione, i passaggi di riavvio/attendibilità specifici dell'agente, il comportamento in materia di privacy e la risoluzione dei problemi sono disponibili nel file [Guida introduttiva](docs/getting-started.md).

Per lo sviluppo, l'implementazione di base non ha dipendenze di runtime oltre Python 3.9+. Dalla radice del repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Quindi apri [http://127.0.0.1:4317](http://127.0.0.1:4317).

Quella di una volta `install` comando:

1. esegue la scansione delle posizioni delle competenze di utenti, progetti e plug-in memorizzati nella cache;
2. rileva Codex, Claude Code, Qoder, E OpenCode senza modificarne la configurazione;
3. mostra quali percorsi di Agente e Competenza verranno letti;
4. scarica un mittente nativo a basso avvio verificato con checksum per la piattaforma corrente, ricorrendo a una build C locale e infine al Python mittente e preriscalda un nuovo binario nativo una volta durante l'installazione;
5. crea `~/.skill-runtime/config.json` e il locale SQLite indice.

Il primo indice importa le sessioni dell'agente compatibili esistenti. Su una workstation di lunga durata ciò può richiedere più tempo di una nuova installazione; gli avvii successivi sono incrementali e il UI diventa disponibile mentre viene eseguito l'aggiornamento in background.

Quando viene eseguito in modo interattivo, richiede una volta prima di aggiungere hook dell'agente con apertura in caso di errore. `--no-hooks` mantiene l'importazione della trascrizione come fallback etichettato, mentre `--enable-hooks` registra il consenso esplicito e installa solo le voci gestite. Per Codex, aprire `/hooks` dopo l'installazione, esamina gli esatti comandi gestiti e fidati di loro. Codex richiede intenzionalmente questa revisione esplicita per gli hook aggiunti all'esterno della configurazione aziendale gestita. Iniziarne uno nuovo Codex attività/sessione dopo aver considerato attendibile il file Hooks, quindi esegui:

```bash
.venv/bin/skill-runtime doctor
```

Qoder carichi Hook configurazione all'avvio, quindi riavviare Qoder dopo la prima installazione. OpenCode rileva il plugin di sola osservazione gestito dalla sua directory globale dei plugin; ricomincia OpenCode se il processo corrente è precedente all'installazione. Nessuna delle due integrazioni legge o modifica le richieste del modello.

L'integrazione diventa **Live** solo dopo che il database riceve un real `official_hook` evento. Semplicemente scrivere `~/.codex/hooks.json` viene visualizzato come **In sospeso**, mai Connesso. `start` avvia il servizio di raccolta, l'osservatore di fallback delle trascrizioni, l'addetto alla conservazione, SQLite conservare e vivere UI come processo in background gestito. Nessuna richiesta di modello è delegata.

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

`uninstall` rimuove solo quelli gestiti Hook voci e Skill Runtimefile di proprietà. Senza `--keep-data`, richiede una conferma interattiva (o `--yes`) prima di rimuoverlo `~/.skill-runtime`; Le sessioni dell'agente e le origini delle competenze non vengono mai rimosse.

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

I profili di importazione con versione attualmente riconoscono OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, E Datadog JSON forme. Creano solo a SkillRun quando la fonte porta con sé una semantica esplicita delle competenze; i nomi di span generici non vengono trattati come prova di attivazione.

Esporta prove di runtime normalizzate e specifiche per ogni abilità OTLP/HTTP endpoint delle tracce:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

L'esportazione è disabilitata a meno che un endpoint non sia configurato in modo esplicito. I checkpoint, lo stato dei nuovi tentativi e lo stato della destinazione vengono visualizzati in Impostazioni. I prompt non elaborati, i payload degli strumenti, le credenziali e i contenuti delle risorse delle competenze non vengono esportati. Per l'esportazione in background autenticata, fornire standard `OTEL_EXPORTER_OTLP_HEADERS` nell'ambiente prima `skill-runtime start`; le intestazioni non vengono mai scritte Skill Runtime argomenti di configurazione o di processo.

## Invia prove di runtime in tempo reale

`skill-runtime start` include un collezionista locale. Adattatori di telemetria nativi, hook ufficiali, hook fail-open leggeri e SDK le integrazioni possono aggiungere un singolo evento o un batch limitato a `POST /api/events`:

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

L'endpoint redige le credenziali comuni prima della persistenza, deduplica entro `event_id`, conserva una busta grezza redatta separata e restituisce il risultato `skill_run_ids`. `GET /api/collector/schema` espone il vocabolario degli eventi supportato e le modalità di raccolta. IL UI ascolta `/api/stream` utilizzando SSE, con il polling solo come fallback di riconnessione.

L'indicatore di origine distingue l'evidenza di runtime primaria da `Transcript fallback` e tracce importate. Un endpoint Collector da solo non rivendica la telemetria nativa: ogni produttore deve dichiarare se il suo evento proviene dalla telemetria nativa, da un hook ufficiale, da un hook leggero o da un SDK.

### Hook dell'agente facoltativi

Ispeziona prima i percorsi e gli eventi esatti. Questo comando è di sola lettura:

```bash
.venv/bin/skill-runtime setup
```

Hook l'installazione richiede un flag esplicito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Il programma di installazione esegue il backup della configurazione dell'agente, conserva gli hook esistenti e aggiunge solo le voci che contengono un file Skill Runtime indicatore di gestione. L'adattatore hook memorizza campi minimi del ciclo di vita anziché prompt completi o payload dello strumento. Per le chiamate dello strumento completate si estrae solo l'esatto `SKILL.md`, risorsa abilità standard e percorsi di file modificati in memoria; i comandi grezzi, i corpi delle patch, i prompt e gli output degli strumenti vengono eliminati prima della persistenza. Mentre il runtime è attivo, un'autorizzazione limitata Unix socket è il percorso veloce; un mittente nativo opzionale evita Python avvio. Quando il runtime non è attivo, il percorso autonomo di apertura in caso di errore accoda prove oscurate `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` riproduce la coda con la deduplicazione dell'ID evento.

Codex gli eventi usano il suo ufficiale Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, E `Stop`). Codex attualmente esegue gli hook di comando in modo sincrono, quindi Skill Runtime usa un locale Unix socket/mittente nativo con un timeout limitato. Qualsiasi errore di consegna viene inghiottito e messo in coda; non cambia mai la decisione dell'Agente. Vedi il [documentazione ufficiale del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Rimuovi solo le voci gestite con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Il server si lega a `127.0.0.1` per impostazione predefinita. I messaggi di trascrizione completa e i payload dello strumento non vengono copiati nell'indice. I modelli segreti comuni vengono redatti prima che i riepiloghi normalizzati vengano mantenuti.

Esegui la suite di test senza dipendenze con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingegneria del rilascio

GitHub Le azioni vengono eseguite Python 3.9–3.13, convalida JavaScript, compilazione del mittente nativo e un vero test del fumo di installazione/avvio/medico/arresto/disinstallazione. UN `v*` il tag crea pacchetti wheel/sdist più protetti da checksum Linux E macOS mittenti nativi. Il programma di installazione della CLI scarica la risorsa di rilascio corrispondente, quindi gli utenti finali non hanno bisogno di un compilatore.

Esegui il primo esperimento di diagnostica collegata al prodotto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inserisce lacune nelle prove del ciclo di vita, guasti espliciti, esecuzioni incomplete e risultati non verificati, quindi valuta lo stesso motore di diagnosi deterministica utilizzato dal API E UI. Vedi il [Piano dell'esperimento PAI-DSW](docs/pai-dsw-experiment-plan.md) per la scala sperimentale, i test di non interferenza e il contratto di riproducibilità.

Dopo aver costruito la ruota, esegui il fumo del ciclo di vita del pacchetto isolato con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Si installa in un ambiente virtuale temporaneo e in una casa temporanea, esercita l'intero ciclo di vita locale senza abilitare gli hook e verifica la non interferenza della configurazione del progetto e dell'agente.

## Progettazione del prodotto basata sugli esperimenti

Il comportamento del prodotto segue quattro vincoli guidati dall'esperimento: l'evidenza prima delle conclusioni, il primo confine osservabile prima della gravità, le relazioni tipizzate prima dei log piatti e la ricostruzione deterministica prima dell'assistenza probabilistica.

Le prove riproducibili e le sue limitazioni sono mantenute nel [rapporto sull'esperimento](docs/experiment-results-2026-07-29.md). I risultati delimitati includono:

- 2.400/2.400 eventi del Collector accettati senza mutazione di input/output;
- 14/14 diagnosi deterministiche del corpo degli errori senza alcuna affermazione causale non supportata;
- rappresentazione della diagnosi relazionale a 13/14 esatto e F1 0,963, mentre il recupero del ciclo di vita piatto ha raggiunto 1/14 esatto e F1 0,080;
- un audit reale rispettoso della privacy che rimane esplicitamente inadatto per affermazioni confermative sull'effetto del prodotto perché mancano risultati verificati, copertura equilibrata tra agenti ed etichette umane.

Questi risultati convalidano i meccanismi e le scelte di rappresentazione, non la generalizzazione dell’implementazione o il vantaggio umano. Gli studi sul secondo agente reale, la latenza della coda multipiattaforma, la calibrazione dei guasti reali e gli studi sulla diagnosi dei partecipanti rimangono lacune di evidenza aperte.

La direzione della ricerca si basa anche sul lavoro primario adiacente: [SkillsBench](https://arxiv.org/abs/2602.12670) E [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivare la diagnosi perché gli effetti delle Abilità variano e possono regredire; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva il confronto tra agenti consapevole delle capacità; e il [indagine sulla provenienza dell'esecuzione](https://arxiv.org/abs/2606.04990) motiva le relazioni con le prove digitate, la tracciabilità della provenienza e l'infrastruttura di controllo attenta alla privacy.

## Documentazione

| Inizia qui | Scopo |
|---|---|
| [Getting Started](docs/getting-started.md) | Installa, collega un agente, verifica prove dal vivo e risolvi i problemi |
| [Architettura](docs/architecture.md) | Pipeline di raccolta, limiti di archiviazione, motore delle prove e modello di fiducia |
| [Matrice delle capacità dell'adattatore](docs/adapter-capability-matrix.md) | Segnali esatti e limitazioni per agente/versione |
| [Configurazione della piattaforma di osservabilità](docs/observability-platform-setup.md) | Connetti piattaforme compatibili con OTLP e importa tracce supportate |
| [Modello di eventi di runtime](docs/runtime-event-model.md) | Vocabolario stabile degli eventi, provenienza, relazioni e gradi di prova |
| [Architettura delle informazioni dell'interfaccia utente](docs/ui-information-architecture.md) | Panoramica, primo confine, Panorama, Ispettore, Confronta e Inferred Analysis |
| [Registro delle modifiche](CHANGELOG.md) | Modifiche visibili all'utente con versione |
| [Note sulla versione v0.3.0](docs/releases/v0.3.0.md) | Linee guida per l'aggiornamento, punti salienti e limiti noti |

Riferimenti di prodotti e ricerche: [definizione del prodotto](docs/product-definition.md), [Specifica MVP](docs/mvp-specification.md), [interoperabilità osservabile](docs/observability-interoperability.md), [risultati dell'esperimento](docs/experiment-results-2026-07-29.md), e il [agenda di ricerca](docs/research-paper-agenda.md).

## Comunità e governance

- Leggere [Contribuire](CONTRIBUTING.md) prima di modificare la semantica delle prove, gli adattatori o il comportamento del prodotto.
- Segui il [Codice di comportamento](CODE_OF_CONDUCT.md) in tutti gli spazi del progetto.
- Segnala le vulnerabilità in privato attraverso il [Politica di sicurezza](SECURITY.md), non è una questione pubblica.
- Usa il strutturato [tracker dei problemi](https://github.com/hellogxp/skill-runtime-intelligence/issues) per bug riproducibili e proposte di funzionalità con ambito. Non allegare mai database di runtime privati ​​o trascrizioni di sessioni.

## Tabella di marcia

1. **v0.3.0 — Prossima versione:** vincoli di comportamento delle competenze verificabili, attività di runtime concreta, valutazione basata sull'evidenza, diagnosi di copertura sistemica e il flusso di lavoro Panorama e Confronto in tempo reale esistente.
2. **Avanti: Rafforzamento dell'adattatore e della diagnosi:** copertura più ampia di agenti/versioni, calibrazione degli errori reali, convalida della latenza di coda multipiattaforma e studi sulla diagnosi dei partecipanti.
3. **Successivo — Valutazione degli effetti:** valutazione accoppiata controllata con/senza abilità, mantenuta esplicitamente separata dalla diagnosi a ciclo singolo.

## Stato del progetto

L'albero di origine corrente è destinato `v0.3.0`; utilizzare il badge di rilascio sopra per identificare l'ultima build pubblicata. Il runtime include vincoli controllabili di comportamento delle competenze, riepiloghi di attività concrete, inventario delle definizioni installate, funzionari basati sul consenso Hook adattatori per Codex, Claude Code, E Qoder, una sola osservazione OpenCode plug-in, fallback della trascrizione etichettata, attribuzione con ambito attivo, percorsi esatti di file/artefatto, redazione, livelli di origine/relazione/inferenza separati, SQLite archiviazione, conservazione, diagnosi deterministica, live UIe confronto tra più esecuzioni/tra agenti. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, E Datadog le esportazioni possono essere importate; le prove normalizzate possono essere esportate in tempo reale tramite l'opt-in OTLP/HTTP.

La scoperta dei candidati all'interno del modello, le ragioni della selezione interna del modello, l'efficacia semantica e le affermazioni sui risultati causali rimangono esplicitamente non supportate a meno che una fonte o un esperimento controllato non forniscano tale prova.
