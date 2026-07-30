# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · **Čeština** · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnostikujte, kde se poprvé rozcházel běh agenta Skill – a prohlédněte si důkazy
> za každým závěrem.

Agent Skill Runtime Intelligence je runtime evidence a diagnostický systém pouze pro čtení pro dovednosti agentů. Kombinuje definice dovedností, oficiální běhové události agenta, importovaná trasování, záložní relace a pozorovatelné výsledky pracovního prostoru do Skill Run Panorama s hodnocením podle důkazů.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Rychlý start

Nainstalujte a spusťte nejnovější verzi na macOS nebo Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Není vyžadován žádný klon, účet, `sudo` nebo GitHub CLI. Instalační program ověří kontrolní součet vydání, zjistí podporované agenty a dovednosti, vysvětlí každou cestu, kterou bude číst, před povolením háčků pouze pro pozorování se jednou zeptá a otevře místní UI na [http://127.0.0.1:4317](http://127.0.0.1:4317). Data za běhu zůstanou pod `~/.skill-runtime`, pokud explicitně nenakonfigurujete export.

Před spuštěním můžete [zkontrolovat instalačního technika](scripts/install.sh).

### Podívejte se na svůj první živý přenos SkillRun

1. Přijměte volitelné nastavení při selhání Hook, když vás instalační program požádá.
2. Restartujte agenta a začněte s novou úlohou. V Codex si nejprve projděte spravované příkazy v `/hooks`; existující úlohy nenačítají nové Hook za provozu.
3. Normálně použijte dovednost, poté potvrďte integraci a otevřete UI:

```bash
skill-runtime doctor
skill-runtime status
```

Integrace je **Live** až poté, co Collector obdrží skutečnou událost za běhu. Nakonfigurovaný, ale nepozorovaný Hook je **Čeká** – nikdy není prezentován jako živý důkaz. Otevřete [http://127.0.0.1:4317](http://127.0.0.1:4317) nebo se podívejte na [Průvodce Začínáme](docs/getting-started.md) pro specifické pokyny pro agenty a řešení problémů.

Spuštění přímo ze zdroje:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Povrch produktu | Co to odpovídá |
|---|---|
| Runtime Overview | Které SkillRuns vyžadují pozornost? |
| First Observable Boundary | Kde důkazy poprvé chyběly nebo selhaly? |
| Skill Run Panorama | Jak se propojila žádost, aktivace, zdroje, nástroje, artefakty a výsledek? |
| Evidence Inspector | Jaký zdroj, stupeň, základ a schopnost adaptéru toto tvrzení podporují? |
| Porovnejte | Je rozdíl v chování nebo pouze rozdíl ve pozorovatelnosti? |
| Inferred Analysis | Jaké důkazy ohraničené vysvětlení nebo další vyšetřování je přijatelné? |
| Nastavení / Doktor | Co se čte, ukládá, exportuje, čeká na vyřízení a ověřuje? |

## Jak to funguje

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime sleduje pracovní postup, který již používáte. Verzované adaptéry přeměňují události nativního agenta na stabilní životní cyklus dovedností, zatímco nezpracované zdrojové obálky, normalizované události, vztahy a odvození zůstávají odděleny. Diagnostický modul nejprve identifikuje nejčasnější hranici, kde důkazy chybí nebo selhaly; nevymýšlí modelový záměr nebo kauzální účinnost.

| Zdroj dat | Role | Svěžest | štítek UI |
|---|---|---|---|
| Oficiální háky / pluginy / události SDK | Primární životní cyklus, nástroj, subagent a evidence terminálu | Žít | `Official hook` / `Native telemetry` |
| Soubory dovedností a pozorovatelné výsledky pracovního prostoru | Definice, zdroj, soubor, artefakt a důkazy testu | Živý snímek / indexovaný | `Observed` |
| Přepisy relace | Záchrana kompatibility, když Agent nevystaví dostatek času běhu API | Téměř živé nebo historické | `Transcript fallback` |
| OTLP a podporované exporty trasování | Interoperabilita a historický import | Živý export / dávkový import | Zobrazen profil zdroje |
| Deterministická korelace | Připojuje události k SkillRun beze změny zdrojových faktů | Při požití | `Derived` |
| Sémantická pomoc | Pouze vysvětlení a návrhy vyšetřování | Na požádání | `Inferred` |

Podporované adaptéry první strany jsou verzovány nezávisle:

| Činidlo | Primární integrace | Záložní | Viditelnost aktivace |
|---|---|---|---|
| Codex | Oficiální příkaz Hooks | Import relace | Explicitní aktivace při odhalení událostí Hook |
| Claude Code | Oficiální Hooks | Import relace | Explicitní nástroj dovedností a důkazy příkazů lomítka, pokud jsou odhaleny |
| Qoder | Oficiální příkaz Hooks | Místní záznamy | Explicitní aktivace při odhalení nástrojem dovedností |
| OpenCode | Globální plugin pouze pro pozorování | Místní záznamy | Zpětná volání nástrojů dovedností byla odhalena |

Přesné limity schopností jsou zdokumentovány v [matice schopností adaptéru](docs/adapter-capability-matrix.md). Nepodporované a nepozorované fáze zůstávají viditelné místo toho, aby byly převedeny na selhání.

## Problém

Instalace dovednosti nedokazuje, že ji objevil agent. Discovery neprokazuje aktivaci. Aktivace neprokazuje, že byly načteny úplné pokyny a zdroje. Provedení nedokazuje, že dovednost zlepšila výsledek.

Dnes se o těchto selháních často mlčí. Vývojáři se ptají:

- Byla dovednost dostupná tomuto agentovi?
- Aktivoval se pro tento požadavek?
- Které pokyny, odkazy, skripty a prostředky byly načteny?
- O jaké nástroje, volání MCP, podagenti, soubory a artefakty šlo?
- Kde se běh nezdařil, opakoval nebo ztratil kontext?
- Pomohla dovednost, nebo jen zvýšila náklady a latenci?

## Diagnostika specifická pro dovednosti

Primárním diagnostickým objektem je `SkillRun`, nikoli celá relace agenta:

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

UI udržuje životní cyklus uspořádaný, napsaný a klasifikovaný podle důkazů. Chybějící aktivační telemetrie znamená „nepozorováno“ nebo „nepodporováno“; neznamená to, že agent definitivně přeskočil dovednost.

## Důkazní disciplína

UI nikdy nesmí představovat závěr jako běhový fakt:

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

## Aktuální rozsah

Runtime podporuje Codex, Claude Code, Qoder a OpenCode prostřednictvím nezávislých verzovaných adaptérů a poskytuje:

- nainstalované zjišťování a ověřování dovedností;
- oficiální kolekce Hook/pluginů v reálném čase plus označená záložní relace;
- Časové osy aktivace dovedností, načítání zdrojů a volání nástrojů;
- vztahy subagenta, MCP, souborů a artefaktů;
- trvání, token, chyba, opakování a souhrny stavu, pokud jsou k dispozici;
- Runtime Overview a prvohraniční diagnóza;
- panoramatický DAG, časový plán události a inspektor důkazů;
- porovnání mezi stejnými agenty a mezi agenty;
- samostatný povrch Inferred Analysis, který nemůže přepisovat fakta za běhu;
- opt-in export OTLP/HTTP a podporovaný import sledovatelnosti.

MVP **nezahrnuje** tržiště, běhové prostředí univerzálního agenta, vynucování zabezpečení, podnikové řízení ani tvrzení o kauzálním účinku.

## Detailní instalace

Pro nejkratší podporovanou cestu použijte jednořádkový instalační program v [Rychlý start](#quick-start). Kompletní postup prvního spuštění, kroky restartování/důvěry agenta, chování v oblasti ochrany soukromí a odstraňování problémů jsou k dispozici v [Průvodce Začínáme](docs/getting-started.md).

Pro vývoj nemá základní implementace žádné závislosti na běhovém prostředí nad rámec Python 3.9+. Z kořenového adresáře úložiště:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Poté otevřete [http://127.0.0.1:4317](http://127.0.0.1:4317).

Jednorázový příkaz `install`:

1. prohledá umístění dovedností uživatelů, projektů a pluginů v mezipaměti;
2. detekuje Codex, Claude Code, Qoder a OpenCode bez změny jejich konfigurace;
3. ukazuje, které cesty agenta a dovednosti budou načteny;
4. stáhne nativního odesílatele s nízkým startem pro aktuální platformu s ověřeným kontrolním součtem, vrátí se k místnímu sestavení C a nakonec k odesílateli Python a jednou během instalace předehřeje čerstvý nativní binární soubor;
5. vytvoří `~/.skill-runtime/config.json` a místní index SQLite.

Když je spuštěn interaktivně, zeptá se jednou před přidáním háčků agenta otevřeného při selhání. `--no-hooks` uchovává import přepisu jako označený záložní zdroj, zatímco `--enable-hooks` zaznamenává výslovný souhlas a instaluje pouze spravované položky. Pro Codex otevřete `/hooks` po instalaci, prohlédněte si přesně spravované příkazy a důvěřujte jim. Codex záměrně vyžaduje tuto explicitní kontrolu pro háčky přidané mimo konfiguraci spravovaného podniku. Spusťte nový úkol/relaci Codex poté, co důvěřujete Hook, poté spusťte:

```bash
.venv/bin/skill-runtime doctor
```

Qoder načte konfiguraci Hook při spuštění, takže po první instalaci restartujte Qoder. OpenCode objeví spravovaný plugin pouze pro pozorování ze svého globálního adresáře pluginů; restartujte OpenCode, pokud aktuální proces předchází instalaci. Integrace nečte ani nemění požadavky modelu.

Integrace se stane **Live** až poté, co databáze přijme skutečnou událost `official_hook`. Pouhé psaní `~/.codex/hooks.json` se zobrazí jako **Čeká**, nikdy není připojeno. `start` spouští Collector, záložní sledování přepisů, retenčního pracovníka, úložiště SQLite a živé UI jako spravovaný proces na pozadí. Žádný požadavek na model není zadán proxy.

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

`uninstall` odstraní pouze spravované položky Hook a vlastněné soubory Skill Runtime. Bez `--keep-data` vyžaduje interaktivní potvrzení (nebo `--yes`) před odstraněním `~/.skill-runtime`; Relace agenta a zdroje dovedností nejsou nikdy odstraněny.

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

Verzované profily importu aktuálně rozpoznávají tvary OTLP/Phoenix, Langfuse, LangSmith, W&B Weave a Datadog JSON. Vytvářejí pouze SkillRun, když zdroj nese explicitní sémantiku dovedností; generické názvy span nejsou považovány za důkaz aktivace.

Exportujte normalizované, pro dovednosti specifické runtime důkazy do libovolného koncového bodu trasování OTLP/HTTP:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Export je zakázán, pokud není explicitně nakonfigurován koncový bod. Kontrolní body, stav opakování a stav cíle se zobrazují v Nastavení. Nezpracované výzvy, užitečné zatížení nástrojů, pověření a obsah zdrojů dovedností se neexportují. Pro ověřený export na pozadí poskytněte standardní `OTEL_EXPORTER_OTLP_HEADERS` v prostředí před `skill-runtime start`; hlavičky se nikdy nezapisují do konfiguračních nebo procesních argumentů Skill Runtime.

## Odešlete živé běhové důkazy

`skill-runtime start` zahrnuje místní kolektor. Nativní telemetrické adaptéry, oficiální háky, lehké háky s otevřeným selháním a integrace SDK mohou připojit jednu událost nebo ohraničenou dávku k `POST /api/events`:

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

Koncový bod rediguje běžná pověření před persistencí, deduplikuje pomocí `event_id`, zachovává samostatnou redigovanou nezpracovanou obálku a vrací výslednou `skill_run_ids`. `GET /api/collector/schema` odhaluje podporovaný slovník událostí a režimy shromažďování. UI poslouchá `/api/stream` pomocí SSE, s dotazováním pouze jako záložním řešením pro opětovné připojení.

Zdrojový indikátor rozlišuje primární runtime evidence od `Transcript fallback` a importovaných tras. Samotný koncový bod Collector si nečiní nárok na nativní telemetrii: každý výrobce musí deklarovat, zda jeho událost pochází z nativní telemetrie, oficiálního háku, lehkého háku nebo SDK.

### Volitelné háky agentů

Nejprve zkontrolujte přesné cesty a události. Tento příkaz je pouze pro čtení:

```bash
.venv/bin/skill-runtime setup
```

Instalace Hook vyžaduje explicitní příznak:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Instalační program zazálohuje konfiguraci agenta, zachová existující háky a přidá pouze položky nesoucí značku správy Skill Runtime. Adaptér háku ukládá pole minimálního životního cyklu spíše než úplné výzvy nebo užitečné zatížení nástrojů. Pro dokončená volání nástrojů extrahuje pouze přesné `SKILL.md`, standardní prostředek dovedností a změněné cesty k souborům v paměti; raw příkazy, těla záplat, výzvy a výstupy nástrojů jsou před persistencí zahozeny. Když je běhové prostředí aktivní, rychlou cestou je soket Unix s omezeným oprávněním; volitelný nativní odesílatel zabraňuje spuštění Python. Když běhové prostředí není aktivní, samostatná cesta k otevření při selhání připojí redigovaný důkaz k `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` přehraje tuto frontu s deduplikací ID události.

Události Codex používají oficiální Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`⟧,`PreCompact`⟧,`PostCompact`, ⟦109 `SubagentStop` a `Stop`). Codex aktuálně provádí zavěšení příkazů synchronně, takže Skill Runtime používá místní soket Unix/nativního odesílatele s omezeným časovým limitem. Jakékoli selhání doručení je spolknuto a zařazeno do fronty; nikdy to nezmění rozhodnutí agenta. Viz [oficiální dokumentace Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Odstraňte pouze spravované položky pomocí:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Server se standardně váže na `127.0.0.1`. Zprávy s úplným přepisem a užitečné zatížení nástrojů se do indexu nezkopírují. Běžné tajné vzory jsou redigovány předtím, než jsou normalizované souhrny zachovány.

Spusťte nezávislou testovací sadu pomocí:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Uvolňovací technika

GitHub Actions spouští testy Python 3.9–3.13, ověření JavaScriptu, kompilaci nativního odesílatele a skutečný kouřový test instalace/spuštění/doktor/zastavení/odinstalace. Značka `v*` vytváří balíčky wheel/sdist plus nativní odesílatele Linux a macOS chráněné kontrolním součtem. Instalační program CLI stáhne odpovídající aktivum vydání, takže koncoví uživatelé nepotřebují kompilátor.

Spusťte první diagnostický experiment spojený s produktem:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Vkládá chyby v důkazech o životním cyklu, explicitní selhání, neúplné běhy a neověřené výsledky a poté vyhodnocuje stejný deterministický diagnostický engine, jaký používají API a UI. Viz [Plán experimentu PAI-DSW](docs/pai-dsw-experiment-plan.md) pro žebříček experimentů, testy nerušení a smlouvu o reprodukovatelnosti.

Po sestavení kola spusťte izolovaný zabalený kouř životního cyklu s:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Instaluje se do dočasného virtuálního prostředí a dočasného domova, provádí celý místní životní cyklus bez povolení háčků a ověřuje, že projekt a konfigurace agenta neinterferují.

## Design produktu řízený experimenty

Chování produktu je omezeno [filozofie produktu řízená experimenty](docs/experiment-driven-product-philosophy.md): důkaz před závěry, první pozorovatelná hranice před závažností, typizované vztahy před plochými logy a deterministická rekonstrukce před pravděpodobnostní pomocí.

Současné reprodukovatelné místní důkazy zahrnují:

- 7/7 prošlo branami místního experimentu;
- 2 400/2 400 Kolektorové události přijaté bez vstupní/výstupní mutace;
- 14/14 deterministické diagnózy korpusu chyb bez nepodloženého kauzálního tvrzení;
- reprezentace relační diagnózy s přesností 13/14 a F1 0,963, zatímco ploché vyhledávání životního cyklu dosáhlo přesnosti 1/14 a F1 0,080;
- Případy studijního materiálu 11/11 umisťují nejdříve pozorovatelnou hranici jako první.

Tyto výsledky ověřují mechanismy a volby reprezentace, nikoli generalizaci nasazení nebo lidský prospěch. Skutečné studie druhého agenta, latence ocasu napříč platformami, kalibrace skutečné chyby a studie diagnózy účastníků zůstávají otevřené mezery v důkazech.

Směr výzkumu je také založen na sousední primární práci: [SkillsBench](https://arxiv.org/abs/2602.12670) a [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivují k diagnóze, protože efekty dovedností se liší a mohou ustoupit; [Harness-Bench](https://arxiv.org/abs/2605.27922) motivuje porovnávání mezi agenty na základě schopností; a [průzkum provenience provedení](https://arxiv.org/abs/2606.04990) motivuje typizované důkazní vztahy, původ původu a infrastrukturu auditu s ohledem na soukromí.

## Dokumentace

| Začněte zde | Účel |
|---|---|
| [Getting Started](docs/getting-started.md) | Nainstalujte, připojte Agenta, ověřte živé důkazy a odstraňte problémy |
| [Architektura](docs/architecture.md) | Sběrný kanál, hranice úložiště, motor evidence a model důvěry |
| [Matice schopností adaptéru](docs/adapter-capability-matrix.md) | Přesné signály a omezení podle agenta/verze |
| [Nastavení platformy pozorovatelnosti](docs/observability-platform-setup.md) | Připojte platformy kompatibilní s OTLP a importujte podporovaná trasování |
| [Model událostí za běhu](docs/runtime-event-model.md) | Stabilní slovník událostí, původ, vztahy a známky důkazů |
| [Informační architektura uživatelského rozhraní](docs/ui-information-architecture.md) | Přehled, první hranice, Panorama, Inspektor, Porovnat a Inferred Analysis |

Reference produktu a výzkumu: [definice produktu](docs/product-definition.md), [Specifikace MVP](docs/mvp-specification.md), [pozorovatelnost interoperabilita](docs/observability-interoperability.md), [filozofie produktu řízená experimenty](docs/experiment-driven-product-philosophy.md), [výsledky experimentu](docs/experiment-results-2026-07-29.md) a [výzkumná agenda](docs/research-paper-agenda.md).

## Cestovní mapa

1. **v0.2.0 — Nyní k dispozici:** živá kolekce otevřená při selhání, čtyři verzované adaptéry agentů, Runtime Overview, diagnostika první hranice, Panorama, Evidence Inspector, porovnání s funkcí, Inferred Analysis a interoperabilita OTLP.
2. **Další — Rozšíření adaptéru a diagnostiky:** širší pokrytí agentů/verzí, kalibrace skutečných chyb, ověření koncové latence mezi platformami a diagnostické studie účastníků.
3. **Později — Vyhodnocení efektu:** řízené s párovým hodnocením s dovedností/bez dovednosti, vedené explicitně odděleně od diagnostiky jednoho cyklu.

## Stav projektu

Verze `v0.2.0` je zveřejněna. Běhové prostředí zahrnuje inventář nainstalovaných definic, oficiální adaptéry Hook řízené souhlasem pro Codex, Claude Code a Qoder, plugin OpenCode pouze pro pozorování, označovaný záložní přepis, přiřazení aktivního rozsahu, přesný zdrojový soubor/rozdíl, cesta/cesta artefaktu SQLite ukládání, uchovávání, deterministická diagnostika, živé UI, a cross-run/cross-Agent srovnání. Exporty OTLP/Phoenix, Langfuse, LangSmith, W&B Weave a Datadog lze importovat; normalizované důkazy lze živě exportovat prostřednictvím přihlášení OTLP/HTTP.

Kandidátský objev uvnitř modelu, důvody interního výběru modelu, sémantická účinnost a tvrzení o kauzálních výsledcích zůstávají výslovně nepodporované, pokud zdroj nebo kontrolovaný experiment neposkytne takové důkazy.
