# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · **Italiano** · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->


> Diagnostica il punto in cui l'esecuzione di una abilità dell'agente si è discostata per la prima volta e esamina le prove
> dietro ogni conclusione.

Agent Skill Runtime Intelligenceè un sistema di prova e diagnosi runtime di sola lettura per le competenze dell'agente. Combina le definizioni delle competenze, gli eventi ufficiali di runtime dell'agente, le tracce importate, il fallback della sessione e i risultati osservabili dell'area di lavoro in un elenco con valutazione delle proveSkill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Avvio rapido

Installa la versione autonoma dal repository privato con un file autenticatoGitCLI dell'hub:

```bash
install_tmp="$(mktemp -d)"
gh release download --repo hellogxp/skill-runtime-intelligence \
  --pattern install.sh --dir "$install_tmp"
sh "$install_tmp/install.sh"
skill-runtime start
```

Oppure esegui direttamente da un checkout di origine:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Aprire[http://127.0.0.1:4317](http://127.0.0.1:4317). PerCodex, rivedi e attendi con fiducia i comandi gestiti`/hooks`, inizia un nuovo turno di Agente, quindi verifica:

```bash
.venv/bin/skill-runtime doctor
```

L'integrazione diventa **Verificata** solo dopo aver ricevuto un vero evento ufficiale. Un hook configurato viene mostrato come **In sospeso**, mai come prova dal vivo.

| Superficie del prodotto | Cosa risponde |
|---|---|
| Panoramica sull'esecuzione | QualeSkillRunsbisogno di attenzione? |
| Primo confine osservabile | Dove sono andate perdute o fallite le prove? |
| Skill Run Panorama | Come si collegavano richiesta, attivazione, risorse, strumenti, artefatti e risultati? |
| Ispettore delle prove | Quale origine, grado, base e capacità dell'adattatore supportano questa affermazione? |
| Confrontare | Una differenza è comportamentale o è solo una differenza di osservabilità? |
| Impostazioni/Dottore | Cosa viene letto, archiviato, esportato, in sospeso e verificato? |

## Il problema

L'installazione di una Skill non prova che un agente l'abbia scoperta. La scoperta non dimostra l'attivazione. L'attivazione non prova che siano state caricate le istruzioni e le risorse complete. L'esecuzione non dimostra che l'Abilità abbia migliorato il risultato.

Oggi questi fallimenti sono spesso silenziosi. Gli sviluppatori si chiedono:

- L'abilità era disponibile per questo agente?
- Si è attivato per questa richiesta?
- Quali istruzioni, riferimenti, script e risorse sono stati caricati?
- Quali strumenti,MCPerano coinvolti chiamate, agenti secondari, file e artefatti?
- Dove l'esecuzione non è riuscita, è stata riprovata o ha perso il contesto?
- La Skill è stata d'aiuto o ha solo aggiunto costi e latenza?

## Direzione del prodotto

Il primo prodotto è un **Skill Run Panorama**:

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

Il panorama è costruito a partire da segnali reali, non da modelli di auto-report:

| Fonte | Esempi | Prova |
|---|---|---|
| File di abilità | metadati, istruzioni, script, riferimenti, risorse | Osservato |
| Eventi in fase di esecuzione | Chiamate a competenze, chiamate a strumenti, subagenti, guasti, durata | Osservato |
| Trascrizioni delle sessioni | richieste, messaggi, input e output dello strumento, ordinamento | Osservato |
| Risultati dello spazio di lavoro | modifiche ai file,Gitdiff, report, artefatti generati | Osservato |
| Correlazione | relazioni tra eventi, risorse e risultati | Derivato o dedotto |

## Disciplina della prova

ILUInon deve mai presentare un'inferenza come fatto di runtime:

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

## Ambito iniziale

L'MVP supportaClaude CodeECodexe prevede:

- rilevamento e convalida delle competenze installate;
- importazione di sessioni e osservazione locale dal vivo, ove supportato;
- Attivazione delle competenze, caricamento delle risorse e tempistiche delle chiamate agli strumenti;
- subagente,MCPrelazioni , file e artefatti;
- riepiloghi di durata, token, errori, tentativi e stato, se disponibili;
- un elenco di esecuzioni, DAG panoramico, sequenza temporale degli eventi e ispettore del nodo.

L'MVP **non** include marketplace, runtime dell'agente universale, applicazione della sicurezza, governance aziendale o affermazioni sull'effetto causale.

## Installazione dettagliata

L'implementazione di base non ha dipendenze di runtime oltrePython3.9+. Dalla radice del repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Quindi apri[http://127.0.0.1:4317](http://127.0.0.1:4317).

Quella di una volta`install`comando:

1. esegue la scansione delle posizioni delle competenze di utenti, progetti e plug-in memorizzati nella cache;
2. rilevaCodexEClaude Codesenza modificarne la configurazione;
3. mostra quali percorsi Agente e Competenza verranno letti;
4. scarica un mittente nativo a basso avvio verificato con checksum per la piattaforma corrente, ricorrendo a una build C locale e infine alPythonmittente e preriscalda un nuovo binario nativo una volta durante l'installazione;
5. crea`~/.skill-runtime/config.json`e il localeSQLiteindice.

Quando viene eseguito in modo interattivo, richiede una volta prima di aggiungere hook dell'agente di apertura non riuscita.`--no-hooks`mantiene l'importazione della trascrizione come fallback etichettato, mentre`--enable-hooks`registra il consenso esplicito e installa solo le voci gestite. PerCodex, aprire`/hooks`dopo l'installazione, esamina gli esatti comandi gestiti e fidati di loro.Codexrichiede intenzionalmente questa revisione esplicita per gli hook aggiunti all'esterno della configurazione aziendale gestita. Inizia un nuovo turno di Agente, quindi esegui:

```bash
.venv/bin/skill-runtime doctor
```

L'integrazione diventa **Live** solo dopo che il database riceve un real`official_hook`evento. Semplicemente scrivere`~/.codex/hooks.json`viene visualizzato come **In sospeso**, mai Connesso.`start`avvia il servizio di raccolta, l'osservatore di fallback delle trascrizioni, l'addetto alla conservazione,SQLiteconservare e vivereUIcome processo in background gestito. Nessuna richiesta di modello è delegata.

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

`uninstall`rimuove solo le voci Hook gestite eSkill Runtimefile di proprietà. Senza`--keep-data`, richiede una conferma interattiva (o`--yes`) prima di rimuoverlo`~/.skill-runtime`; Le sessioni dell'agente e le origini delle competenze non vengono mai rimosse.

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

I profili di importazione con versione attualmente riconoscono OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, EDatadog JSONforme. Creano solo aSkillRunquando la fonte porta con sé una semantica esplicita delle competenze; i nomi di span generici non vengono trattati come prova di attivazione.

Esporta prove di runtime normalizzate e specifiche per ogni abilitàOTLP/HTTPendpoint delle tracce:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

L'esportazione è disabilitata a meno che un endpoint non sia configurato in modo esplicito. I checkpoint, lo stato dei nuovi tentativi e lo stato della destinazione vengono visualizzati in Impostazioni. I prompt non elaborati, i payload degli strumenti, le credenziali e i contenuti delle risorse delle competenze non vengono esportati. Per l'esportazione in background autenticata, fornire standard`OTEL_EXPORTER_OTLP_HEADERS`nell'ambiente prima`skill-runtime start`; le intestazioni non vengono mai scritteSkill Runtimeargomenti di configurazione o di processo.

## Invia prove di runtime in tempo reale

`skill-runtime start`include un collezionista locale. Adattatori di telemetria nativi, hook ufficiali, hook fail-open leggeri eSDKle integrazioni possono aggiungere un singolo evento o un batch limitato a`POST /api/events`:

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

L'endpoint redige le credenziali comuni prima della persistenza, deduplica entro`event_id`, conserva una busta grezza redatta separata e restituisce il risultato`skill_run_ids`.`GET /api/collector/schema`espone il vocabolario degli eventi supportato e le modalità di raccolta. ILUIascolta`/api/stream`utilizzando SSE, con il polling solo come fallback di riconnessione.

L'indicatore di origine distingue l'evidenza di runtime primaria da`Transcript fallback`e tracce importate. Un endpoint di raccolta da solo non rivendica la telemetria nativa: ogni produttore deve dichiarare se il suo evento proviene dalla telemetria nativa, da un hook ufficiale, da un hook leggero o da unSDK.

### Hook dell'agente opzionali

Ispezionare prima i percorsi e gli eventi esatti. Questo comando è di sola lettura:

```bash
.venv/bin/skill-runtime setup
```

L'installazione dell'hook richiede un flag esplicito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Il programma di installazione esegue il backup della configurazione dell'agente, conserva gli hook esistenti e aggiunge solo le voci che contengono un fileSkill Runtimeindicatore di gestione. L'adattatore hook memorizza campi minimi del ciclo di vita anziché prompt completi o payload dello strumento. Mentre il runtime è attivo, un'autorizzazione limitataUnixsocket è il percorso veloce; un mittente nativo opzionale evitaPythonavvio. Quando il runtime non è attivo, il percorso autonomo di apertura in caso di errore accoda prove oscurate`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`riproduce la coda con la deduplicazione dell'ID evento.

Codexgli eventi utilizzano il suo Hook ufficialeAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, E`Stop`).Codexattualmente esegue gli hook di comando in modo sincrono, quindiSkill Runtimeusa un localeUnixsocket/mittente nativo con un timeout limitato. Qualsiasi errore di consegna viene inghiottito e messo in coda; non cambia mai la decisione dell'Agente. Vedi il[documentazione ufficiale del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Rimuovi solo le voci gestite con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Il server si lega a`127.0.0.1`per impostazione predefinita. I messaggi di trascrizione completa e i payload dello strumento non vengono copiati nell'indice. I modelli segreti comuni vengono redatti prima che i riepiloghi normalizzati vengano mantenuti.

Esegui la suite di test senza dipendenze con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingegneria del rilascio

GitViene eseguito Azioni hubPython3.9–3.13, convalida JavaScript, compilazione del mittente nativo e un vero test del fumo di installazione/avvio/medico/arresto/disinstallazione. UN`v*`tag crea pacchetti wheel/sdist oltre a mittenti nativi Linux e macOS protetti da checksum. Il programma di installazione della CLI scarica la risorsa di rilascio corrispondente, quindi gli utenti finali non hanno bisogno di un compilatore.

Esegui il primo esperimento di diagnostica collegata al prodotto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inserisce lacune nelle prove del ciclo di vita, guasti espliciti, esecuzioni incomplete e risultati non verificati, quindi valuta lo stesso motore di diagnosi deterministica utilizzato dalAPIEUI. Vedi il[Piano dell'esperimento PAI-DSW](docs/pai-dsw-experiment-plan.md)per la scala sperimentale, i test di non interferenza e il contratto di riproducibilità.

Dopo aver costruito la ruota, esegui il fumo del ciclo di vita del pacchetto isolato con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Si installa in un ambiente virtuale temporaneo e in una casa temporanea, esercita l'intero ciclo di vita locale senza abilitare gli hook e verifica la non interferenza della configurazione del progetto e dell'agente.

## Progettazione del prodotto basata sugli esperimenti

Il comportamento del prodotto è vincolato da[filosofia di prodotto guidata dalla sperimentazione](docs/experiment-driven-product-philosophy.md): prove prima delle conclusioni, primo confine osservabile prima della gravità, relazioni tipizzate prima dei log piatti e ricostruzione deterministica prima dell'assistenza probabilistica.

Le attuali prove locali riproducibili includono:

- 7/7 cancelli dell'esperimento locale superati;
- 2.400/2.400 eventi del Collector accettati senza mutazione di input/output;
- 14/14 diagnosi deterministiche del corpo degli errori senza alcuna affermazione causale non supportata;
- rappresentazione della diagnosi relazionale a 13/14 esatto e F1 0,963, mentre il recupero del ciclo di vita piatto ha raggiunto 1/14 esatto e F1 0,080;
- I casi di materiale di studio 11/11 collocano per primo il primo confine osservabile.

Questi risultati convalidano i meccanismi e le scelte di rappresentanza, non la generalizzazione dell’implementazione o il vantaggio umano. Gli studi sul secondo agente reale, la latenza della coda multipiattaforma, la calibrazione dei guasti reali e gli studi sulla diagnosi dei partecipanti rimangono lacune di prove aperte.

La direzione della ricerca si basa anche sul lavoro primario adiacente:[SkillsBench](https://arxiv.org/abs/2602.12670)E[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motivare la diagnosi perché gli effetti delle Abilità variano e possono regredire;[Harness-Bench](https://arxiv.org/abs/2605.27922)motiva il confronto tra agenti consapevole delle capacità; e il[indagine sulla provenienza dell'esecuzione](https://arxiv.org/abs/2606.04990)motiva le relazioni con le prove digitate, la tracciabilità della provenienza e l'infrastruttura di controllo attenta alla privacy.

## Documentazione

- [Definizione del prodotto](docs/product-definition.md)
- [Specifica MVP](docs/mvp-specification.md)
- [Modello di eventi di runtime](docs/runtime-event-model.md)
- [Architettura delle informazioni dell'interfaccia utente](docs/ui-information-architecture.md)
- [Matrice delle capacità dell'adattatore](docs/adapter-capability-matrix.md)
- [Interoperabilità dell'osservabilità](docs/observability-interoperability.md)
- [Configurazione della piattaforma di osservabilità](docs/observability-platform-setup.md)
- [Ricerca e panorama competitivo](docs/research-and-competitive-landscape.md)
- [Agenda del documento di ricerca](docs/research-paper-agenda.md)
- [Filosofia del prodotto basata sulla sperimentazione](docs/experiment-driven-product-philosophy.md)
- [Risultati dell'esperimento](docs/experiment-results-2026-07-29.md)
- [Piano dell'esperimento PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Tabella di marcia

1. **v0.1 — Evidenze e diagnosi in fase di esecuzione:** raccolta in tempo reale,Skill Run Panorama, diagnosi del primo limite, ispezione delle prove, confronto e interoperabilità OTLP.
2. **v0.2 — Studi diagnostici e sull'ampiezza dell'adattatore:** agenti aggiuntivi, esperimenti reali tra agenti e valutazione dei partecipanti.
3. **v0.3 — Valutazione degli effetti:** valutazione abbinata controllata con/senza abilità, tenuta separata dalla diagnosi a ciclo singolo.

## Stato del progetto

UNSkillRun-il primo runtime è eseguibile: inventario con definizione installata,Codexfallback della trascrizione, basato sul consensoCodexEClaude Codeadattatori hook ufficiali, attribuzione di ambito attivo, percorsi esatti di file/artefatti, redazione, livelli di origine/relazione/inferenza separati,SQLitearchiviazione, conservazione, confronto tra più esecuzioni e tra agenti, diagnosi deterministica e panorama in tempo realeUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, EDatadogle esportazioni possono essere importate; le prove normalizzate possono essere esportate in tempo reale tramite l'opt-inOTLP/HTTP. L'attuale suite riproducibile ha sette porte sperimentali di passaggio. La scoperta del candidato, le ragioni della selezione interna del modello, l’efficacia semantica e le affermazioni sui risultati causali rimangono esplicitamente non supportati.
