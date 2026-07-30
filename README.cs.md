# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · **Čeština** · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-inteligence/akce/pracovní postupy/ci.yml)[![Uvolnění](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime– inteligence/vydání/nejnovější)[![Licence](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENCE)[![Krajta](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnostikujte, kde se poprvé rozcházel běh agenta Skill – a prohlédněte si důkazy
> za každým závěrem.

Agent Skill Runtime Intelligenceje runtime evidence a diagnostický systém pro dovednosti agentů pouze pro čtení. Kombinuje definice dovedností, oficiální běhové události agenta, importovaná trasování, záložní relace a pozorovatelné výsledky pracovního prostoru do evidenčního hodnocení.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Rychlý start

Nainstalujte nejnovější samostatnou verzi na macOS nebo Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Žádný klon,GitHub účet,`sudo`neboGitJe vyžadován rozbočovač CLI. Instalační program stáhne odpovídající užitečné zatížení podepsaného vydání, ověří kontrolní součty SHA-256, jednou se zeptá, než povolí háky agenta otevřít při selhání, a uloží všechna data za běhu pod`~/.skill-runtime`. Poté spustí místní runtime a otevře se[http://127.0.0.1:4317](http://127.0.0.1:4317).

Můžete[zkontrolovat instalačního technika](scripts/install.sh)než jej spustíte.

Nebo spusťte přímo z pokladny zdroje:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

OTEVŘENO[http://127.0.0.1:4317](http://127.0.0.1:4317). ProCodex, kontrolovat a důvěřovat spravovaným příkazům`/hooks`, začněte jedno nové kolo agenta a poté ověřte:

```bash
skill-runtime doctor
```

Integrace se stane **Ověřenou** až po obdržení skutečné oficiální události. Nakonfigurovaný hák je zobrazen jako **Nevyřízeno**, nikdy jako živý důkaz.

| Povrch produktu | Co to odpovídá |
|---|---|
| Přehled běhového prostředí | KterýSkillRunspotřebují pozornost? |
| První pozorovatelná hranice | Kde důkazy poprvé chyběly nebo selhaly? |
| Skill Run Panorama | Jak se propojila žádost, aktivace, zdroje, nástroje, artefakty a výsledek? |
| Inspektor důkazů | Jaký zdroj, stupeň, základ a schopnost adaptéru toto tvrzení podporují? |
| Porovnejte | Je rozdíl v chování nebo pouze rozdíl ve pozorovatelnosti? |
| Nastavení / Doktor | Co se čte, ukládá, exportuje, čeká na vyřízení a ověřuje? |

## Problém

Instalace dovednosti nedokazuje, že ji objevil agent. Discovery neprokazuje aktivaci. Aktivace neprokazuje, že byly načteny úplné pokyny a zdroje. Provedení nedokazuje, že dovednost zlepšila výsledek.

Dnes se o těchto selháních často mlčí. Vývojáři se ptají:

- Byla dovednost dostupná tomuto agentovi?
- Aktivoval se pro tento požadavek?
- Které pokyny, odkazy, skripty a prostředky byly načteny?
- Jaké nástroje,MCPbyly zapojeny hovory, podagenti, soubory a artefakty?
- Kde se běh nezdařil, opakoval nebo ztratil kontext?
- Pomohla dovednost, nebo jen zvýšila náklady a latenci?

## Směr produktu

První produkt je **Skill Run Panorama**:

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

Panoráma je vytvořena ze skutečných signálů, nikoli z modelové vlastní zprávy:

| Zdroj | Příklady | Důkaz |
|---|---|---|
| Soubory dovedností | metadata, instrukce, skripty, reference, aktiva | Pozorováno |
| Runtime události | Volání dovedností, volání nástrojů, podagenti, selhání, trvání | Pozorováno |
| Přepisy relace | výzvy, zprávy, vstupy a výstupy nástrojů, objednávání | Pozorováno |
| Výsledky pracovního prostoru | změny souborů,Gitrozdíl, zprávy, generované artefakty | Pozorováno |
| Korelace | vztahy mezi událostmi, zdroji a výsledky | Odvozené nebo odvozené |

## Důkazní disciplína

TheUInikdy nesmí představovat závěr jako běhový fakt:

- **Observed** – explicitně přítomno ve zdrojové události nebo souboru.
- **Odvozeno** — deterministicky spojeno z pozorovaných důkazů.
- **Odvozeno** — věrohodné vysvětlení s nejistotou.
- **Experimentální** — účinek měřený pomocí kontrolovaného párového hodnocení.

Jedno trasování může podporovat atribuci provedení. Nemůže prokázat kauzální účinnost. Tvrzení jako „úspěšnost s touto dovedností se zlepšila“ vyžadují opakované hodnocení s dovednostmi/bez dovedností.

## Principy produktu

- Soukromé ve výchozím nastavení s místním, hybridním a týmovým nasazením.
- Pozorování pouze pro čtení; nikdy nepřevezměte smyčku agentů.
- Žádný model proxy a žádná povinná cloudová služba.
- Žádné blokování, schvalovací brána nebo vynucování zásad ve výchozím produktu.
- Explicitní provenience a klasifikace důkazů.
- Postupné odhalování: nejprve jednoduchý příběh, surové události na vyžádání.
- Podpora založená na adaptéru pro změnu formátů přepisu agentů.

## Počáteční rozsah

Runtime podporujeCodex,Claude Code,QoderaOpenCodeprostřednictvím nezávislých verzovaných adaptérů a poskytuje:

- nainstalované zjišťování a ověřování dovedností;
- import relace a živé místní pozorování tam, kde je podporováno;
- Časové osy aktivace dovedností, načítání zdrojů a volání nástrojů;
- zástupce,MCPvztahy mezi soubory a artefakty;
- trvání, token, chyba, opakování a souhrny stavu, pokud jsou k dispozici;
- seznam běhů, panorama DAG, časovou osu události a inspektor uzlů.

MVP **nezahrnuje** tržiště, běhové prostředí univerzálního agenta, vynucování zabezpečení, podnikové řízení ani tvrzení o kauzálním účinku.

## Detailní instalace

Základní implementace nemá žádné další závislosti na běhovém prostředíPython3,9+. Z kořenového adresáře úložiště:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Poté otevřete[http://127.0.0.1:4317](http://127.0.0.1:4317).

Jednorázový`install`příkaz:

1. prohledá umístění dovedností uživatelů, projektů a pluginů v mezipaměti;
2. zjistíCodex,Claude Code,QoderaOpenCodebeze změny jejich konfigurace;
3. ukazuje, které cesty agenta a dovednosti budou načteny;
4. stáhne nativního odesílatele s nízkým spuštěním ověřeného kontrolním součtem pro aktuální platformu, vrátí se k místnímu sestavení C a nakonecPythonodesílatel a během instalace jednou předehřeje čerstvý nativní binární soubor;
5. vytváří`~/.skill-runtime/config.json`a místníSQLiteindex.

Když je spuštěn interaktivně, zeptá se jednou před přidáním háčků agenta otevřeného při selhání.`--no-hooks`zachová import přepisu jako označenou záložní, zatímco`--enable-hooks`zaznamená výslovný souhlas a nainstaluje pouze spravované položky. ProCodex, OTEVŘENO`/hooks`po instalaci si prohlédněte přesně spravované příkazy a důvěřujte jim.Codexzáměrně vyžaduje tuto explicitní kontrolu pro háky přidané mimo konfiguraci spravovaného podniku. Začněte nový tah agenta a poté spusťte:

```bash
.venv/bin/skill-runtime doctor
```

Qodernačte konfiguraci háku při spuštění, takže restartujteQoderpo první instalaci.OpenCodeobjeví spravovaný plugin pouze pro pozorování ze svého globálního adresáře pluginů; restartovatOpenCodepokud aktuální proces předchází instalaci. Integrace nečte ani nemění požadavky modelu.

Integrace se stane **Live** až poté, co databáze obdrží real`official_hook`událost. Pouze psaní`~/.codex/hooks.json`se zobrazí jako **Nevyřízeno**, nikdy nepřipojeno.`start`spouští Collector, záložního sledování přepisů, retenčního pracovníka,SQLiteskladovat a žítUIjako řízený proces na pozadí. Žádný požadavek na model není zadán proxy.

Příkazy životního cyklu:

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

`uninstall`odstraní pouze spravované položky Hook aSkill Runtime-vlastněné soubory. Bez`--keep-data`, vyžaduje interaktivní potvrzení (příp`--yes`) před odstraněním`~/.skill-runtime`; Relace agenta a zdroje dovedností nejsou nikdy odstraněny.

Chcete-li indexovat a poskytovat samostatně:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importujte existující export trasování z běžného systému pozorovatelnosti:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Verzované profily importu aktuálně rozpoznávají OTLP/Phoenix,Langfuse,LangSmith,W&B WeaveaDatadog JSONtvary. Vytvářejí pouze aSkillRunkdyž zdroj nese explicitní sémantiku dovedností; generické názvy span nejsou považovány za důkaz aktivace.

Exportujte normalizované, pro dovednosti specifické runtime důkazy do libovolnéhoOTLP/HTTPtrasování koncového bodu:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Export je zakázán, pokud není explicitně nakonfigurován koncový bod. Kontrolní body, stav opakování a stav cíle se zobrazují v Nastavení. Nezpracované výzvy, užitečné zatížení nástrojů, pověření a obsah zdrojů dovedností se neexportují. Pro ověřený export na pozadí poskytněte standard`OTEL_EXPORTER_OTLP_HEADERS`v prostředí předtím`skill-runtime start`; do hlaviček se nikdy nezapisujeSkill Runtimekonfigurační nebo procesní argumenty.

## Odešlete živé běhové důkazy

`skill-runtime start`zahrnuje místní kolektor. Nativní telemetrické adaptéry, oficiální háky, lehké háky pro otevírání při selhání aSDKintegrace mohou připojit jednu událost nebo ohraničenou dávku`POST /api/events`:

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

Koncový bod rediguje běžná pověření před persistencí, deduplikuje pomocí`event_id`, zachová samostatnou redigovanou nezpracovanou obálku a vrátí výsledek`skill_run_ids`.`GET /api/collector/schema`odhaluje podporovaný slovník událostí a režimy shromažďování. TheUIposlouchá`/api/stream`pomocí SSE, s dotazováním pouze jako záložním řešením pro opětovné připojení.

Zdrojový indikátor odlišuje primární runtime evidence od`Transcript fallback`a importované stopy. Samotný koncový bod Collector si nenárokuje nativní telemetrii: každý výrobce musí deklarovat, zda jeho událost pochází z nativní telemetrie, oficiálního háku, lehkého háčku neboSDK.

### Volitelné háky agentů

Nejprve zkontrolujte přesné cesty a události. Tento příkaz je pouze pro čtení:

```bash
.venv/bin/skill-runtime setup
```

Instalace háku vyžaduje explicitní příznak:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Instalační program zazálohuje konfiguraci agenta, zachová existující háky a přidá pouze položky nesoucí aSkill Runtimemanažerská značka. Adaptér háku ukládá pole minimálního životního cyklu spíše než úplné výzvy nebo užitečné zatížení nástrojů. Když je běhové prostředí aktivní, je omezeno oprávněníUnixzásuvka je rychlá cesta; nepovinný nativní odesílatel se vyhýbáPythonspuštění. Když není běhové prostředí aktivní, samostatná cesta otevření při selhání připojí redigované důkazy`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`přehraje tuto frontu s deduplikací ID události.

Codexudálosti používají svůj oficiální HookAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`a`Stop`).Codexaktuálně provádí zavěšení příkazů synchronně, takžeSkill Runtimepoužívá místníUnixsocket/nativní odesílatel s omezeným časovým limitem. Jakékoli selhání doručení je spolknuto a zařazeno do fronty; nikdy to nezmění rozhodnutí agenta. Viz[oficiální dokumentace Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Odstraňte pouze spravované položky pomocí:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Server se váže na`127.0.0.1`standardně. Zprávy s úplným přepisem a užitečné zatížení nástrojů se do indexu nezkopírují. Běžné tajné vzory jsou redigovány předtím, než jsou normalizované souhrny zachovány.

Spusťte nezávislou testovací sadu pomocí:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Uvolňovací technika

GitAkce rozbočovače běžíPython3.9–3.13 testy, ověření JavaScriptu, kompilace nativního odesílatele a skutečný kouřový test instalace/spuštění/doktor/zastavení/odinstalace. A`v*`tag vytváří balíčky wheel/sdist plus nativní odesílatele Linux a macOS chráněné kontrolním součtem. Instalační program CLI stáhne odpovídající aktivum vydání, takže koncoví uživatelé nepotřebují kompilátor.

Spusťte první diagnostický experiment spojený s produktem:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Vkládá chyby v důkazech o životním cyklu, explicitní selhání, nedokončené běhy a neověřené výsledky a poté vyhodnocuje stejný deterministický diagnostický engine, jaký používáAPIaUI. Viz[Plán experimentu PAI-DSW](docs/pai-dsw-experiment-plan.md)pro žebříček experimentů, testy nerušení a smlouvu reprodukovatelnosti.

Po sestavení kola spusťte izolovaný zabalený kouř životního cyklu s:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Instaluje se do dočasného virtuálního prostředí a dočasného domova, provádí celý místní životní cyklus bez povolení háčků a ověřuje, že projekt a konfigurace agenta neinterferují.

## Design produktu řízený experimenty

Chování produktu je omezeno[filozofie produktu řízená experimenty](docs/experiment-driven-product-philosophy.md): důkazy před závěry, první pozorovatelná hranice před závažností, typizované vztahy před plochými logy a deterministická rekonstrukce před pravděpodobnostní pomocí.

Současné reprodukovatelné místní důkazy zahrnují:

- 7/7 prošlo branami místního experimentu;
- 2 400/2 400 Kolektorové události přijaté bez vstupní/výstupní mutace;
- 14/14 deterministické diagnózy korpusu chyb bez nepodloženého kauzálního tvrzení;
- reprezentace relační diagnózy s přesností 13/14 a F1 0,963, zatímco ploché vyhledávání životního cyklu dosáhlo přesnosti 1/14 a F1 0,080;
- Případy studijního materiálu 11/11 umisťují nejdříve pozorovatelnou hranici jako první.

Tyto výsledky ověřují mechanismy a volby reprezentace, nikoli generalizaci nasazení nebo lidský prospěch. Skutečné studie druhého agenta, latence ocasu napříč platformami, kalibrace skutečné chyby a studie diagnózy účastníků zůstávají otevřené mezery v důkazech.

Směr výzkumu je také založen na sousední primární práci:[SkillsBench](https://arxiv.org/abs/2602.12670)a[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motivovat k diagnóze, protože účinky dovedností se liší a mohou ustoupit;[Harness-Bench](https://arxiv.org/abs/2605.27922)motivuje porovnávání mezi agenty na základě schopností; a[průzkum provenience provedení](https://arxiv.org/abs/2606.04990)motivuje vztahy s typizovanými důkazy, původ původu a infrastrukturu auditu s ohledem na soukromí.

## Dokumentace

- [Definice produktu](docs/product-definition.md)
- [Specifikace MVP](docs/mvp-specification.md)
- [Model událostí za běhu](docs/runtime-event-model.md)
- [Informační architektura uživatelského rozhraní](docs/ui-information-architecture.md)
- [Matice schopností adaptéru](docs/adapter-capability-matrix.md)
- [Pozorovatelnost interoperabilita](docs/observability-interoperability.md)
- [Nastavení platformy pozorovatelnosti](docs/observability-platform-setup.md)
- [Výzkum a konkurenční prostředí](docs/research-and-competitive-landscape.md)
- [Agenda výzkumných prací](docs/research-paper-agenda.md)
- [Produktová filozofie založená na experimentech](docs/experiment-driven-product-philosophy.md)
- [Výsledky experimentu](docs/experiment-results-2026-07-29.md)
- [Plán experimentu PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Cestovní mapa

1. **v0.1 — Průkaz a diagnostika běhu:** živý sběr,Skill Run Panorama, diagnostika první hranice, kontrola důkazů, porovnání a interoperabilita OTLP.
2. **v0.2 — Adaptér hardening a diagnostické studie:** další verze agentů, skutečné experimenty mezi agenty a hodnocení účastníků.
3. **v0.3 — Vyhodnocení efektu:** řízené s párovým hodnocením s dovednostmi/bez dovedností, oddělené od diagnostiky jednoho cyklu.

## Stav projektu

ASkillRun-první runtime je spustitelné: inventář nainstalované definice,Codexpřepis záložní, souhlasem řízené oficiální adaptéry háku proCodex,Claude CodeaQoder, pouze pozorováníOpenCodeadaptér pluginu, atribuce aktivního rozsahu, přesné cesty k souboru/artefaktu, redakce, samostatné vrstvy zdroje/vztahu/odvozování,SQLiteukládání, uchovávání, porovnávání mezi běhy a agenty, deterministická diagnóza a živé panoramaUI. OTLP/Phoenix,Langfuse,LangSmith,W&B WeaveaDatadogexport lze dovážet; normalizované důkazy lze živě exportovat prostřednictvím přihlášeníOTLP/HTTP. Zjištění kandidátů, důvody interního výběru modelu, sémantická účinnost a tvrzení o kauzálních výsledcích zůstávají výslovně nepodporovány.
