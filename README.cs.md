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


> Otočte se `SKILL.md` do kontrolovatelných očekávání běhu. Podívejte se, co vlastně
> se stalo, kde se chování poprvé rozcházelo, a důkazy za rozsudkem.

Agent Skill Runtime Intelligence je runtime evidence a diagnostický systém pro dovednosti agentů pouze pro čtení. Extrahuje konzervativní, kontrolovatelná omezení ze současné definice dovedností, přiřazuje je k běhové aktivitě a rekonstruuje výsledek jako důkazy klasifikované Skill Run Panorama. Kombinuje oficiální události Agenta, importovaná trasování, označenou nouzovou relace a pozorovatelné výsledky pracovního prostoru bez proxy požadavků modelu nebo převzetí smyčky Agent.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Rychlý start

Nainstalujte a spusťte nejnovější verzi na macOS nebo Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Žádný klon, účet, `sudo`nebo GitHub CLI je vyžadováno. Instalační program ověří kontrolní součet vydání, zjistí podporované agenty a dovednosti, vysvětlí každou cestu, kterou přečte, jednou se zeptá, než povolí háky pouze pro pozorování, a otevře místní UI na [http://127.0.0.1:4317](http://127.0.0.1:4317). Data za běhu zůstávají pod `~/.skill-runtime` pokud explicitně nenakonfigurujete export.

Můžete [zkontrolovat instalačního technika](scripts/install.sh) než jej spustíte.

### Podívejte se na svůj první živý přenos SkillRun

1. Přijměte volitelné otevření při selhání Hook nastavení, když se instalační program zeptá.
2. Restartujte agenta a začněte s novou úlohou. V Codex, zkontrolujte spravované příkazy v `/hooks` první; existující úlohy se nenačítají nové Hooks.
3. Normálně použijte dovednost, poté potvrďte integraci a otevřete soubor UI:

```bash
skill-runtime doctor
skill-runtime status
```

Integrace je **Live** až poté, co Collector obdrží skutečnou událost za běhu. Nakonfigurovaný, ale nepozorovaný Hook je **Čeká** – nikdy není prezentováno jako živý důkaz. OTEVŘENO [http://127.0.0.1:4317](http://127.0.0.1:4317), nebo viz [Průvodce Začínáme](docs/getting-started.md) pro pokyny specifické pro agenty a řešení problémů.

Spuštění přímo ze zdroje:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Povrch produktu | Co to odpovídá |
|---|---|
| Runtime Overview | Který SkillRuns potřebují pozornost? |
| Kontrola dovednostního chování | Které ověřitelné pokyny byly splněny, je třeba je přezkoumat nebo je nelze vyhodnotit? |
| Co se vlastně stalo | Které pokyny, zdroje, nástroje, artefakty a výsledky byly pozorovány? |
| First Observable Boundary | Kde poprvé chybí nebo selhávají důkazy specifické pro běh? |
| Skill Run Panorama | Jak se propojila žádost, aktivace, zdroje, nástroje, artefakty a výsledek? |
| Evidence Inspector | Jaký zdroj, stupeň, základ a schopnost adaptéru toto tvrzení podporují? |
| Porovnejte | Je rozdíl v chování nebo pouze rozdíl ve pozorovatelnosti? |
| Inferred Analysis | Jaké důkazy ohraničené vysvětlení nebo další vyšetřování je přijatelné? |
| Nastavení / Doktor | Co se čte, ukládá, exportuje, čeká na vyřízení a ověřuje? |

## Jak to funguje

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime sleduje pracovní postup, který již používáte. Verzované adaptéry přeměňují události nativního agenta na stabilní životní cyklus dovedností, zatímco nezpracované zdrojové obálky, normalizované události, vztahy a odvození zůstávají odděleny. Diagnostický modul kontroluje explicitní omezení schopností proti těmto důkazům, identifikuje nejdříve pozorovatelnou odchylku a udržuje slepá místa systémových adaptérů oddělená od nálezů specifických pro běh. Nevymýšlí modelový záměr ani kauzální účinnost.

| Zdroj dat | Role | Svěžest | UI označení |
|---|---|---|---|
| Oficiální háky / pluginy / SDK události | Primární životní cyklus, nástroj, subagent a evidence terminálu | Žít | `Official hook` / `Native telemetry` |
| Soubory dovedností a pozorovatelné výsledky pracovního prostoru | Definice, zdroj, soubor, artefakt a důkazy testu | Živý snímek / indexovaný | `Observed` |
| Přepisy relace | Záchrana kompatibility, když Agent nevystaví dostatek runtime API | Téměř živé nebo historické | `Transcript fallback` |
| OTLP a podporované exporty trasování | Interoperabilita a historický import | Živý export / dávkový import | Zobrazen profil zdroje |
| Deterministická korelace | Připojuje události k a SkillRun aniž by se změnila zdrojová fakta | Při požití | `Derived` |
| Sémantická pomoc | Pouze vysvětlení a návrhy vyšetřování | Na požádání | `Inferred` |

Podporované adaptéry první strany jsou verzovány nezávisle:

| Činidlo | Primární integrace | Záložní | Viditelnost aktivace |
|---|---|---|---|
| Codex | Oficiální příkaz Hooks | Import relace | Explicitní aktivace, když je vystavena Hook událost |
| Claude Code | Oficiální Hooks | Import relace | Explicitní nástroj dovedností a důkazy příkazů lomítka, pokud jsou odhaleny |
| Qoder | Oficiální příkaz Hooks | Místní záznamy | Explicitní aktivace při odhalení nástrojem dovedností |
| OpenCode | Globální plugin pouze pro pozorování | Místní záznamy | Zpětná volání nástrojů dovedností byla odhalena |

Přesné limity schopností jsou zdokumentovány v [matice schopností adaptéru](docs/adapter-capability-matrix.md). Nepodporované a nepozorované fáze zůstávají viditelné místo toho, aby byly převedeny na selhání.

## Problém

Instalace dovednosti nedokazuje, že ji objevil agent. Discovery neprokazuje aktivaci. Aktivace neprokazuje, že byly načteny úplné pokyny a zdroje. Pokyny pro načítání nedokazují, že je agent dodržoval. Provedení nedokazuje, že dovednost zlepšila výsledek.

Dnes se o těchto selháních často mlčí. Vývojáři se ptají:

- Byla dovednost dostupná tomuto agentovi?
- Aktivoval se pro tento požadavek?
- Které pokyny, odkazy, skripty a prostředky byly načteny?
- Které explicitní požadavky na dovednosti byly dodrženy, vynechány nebo které nebylo možné vyhodnotit?
- Jaké nástroje, MCP byly zapojeny hovory, podagenti, soubory a artefakty?
- Kde se běh nezdařil, opakoval nebo ztratil kontext?
- Pomohla dovednost, nebo jen zvýšila náklady a latenci?

## Diagnostika specifická pro dovednosti

Primárním diagnostickým objektem je a `SkillRun`, nikoli celá relace agenta:

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

The UI udržuje životní cyklus uspořádaný, napsaný a klasifikovaný podle důkazů. Chybějící aktivační telemetrie znamená „nepozorováno“ nebo „nepodporováno“; neznamená to, že agent definitivně přeskočil dovednost.

## Důkazní disciplína

The UI nikdy nesmí představovat závěr jako běhový fakt:

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

Runtime podporuje Codex, Claude Code, Qodera OpenCode prostřednictvím nezávislých verzovaných adaptérů a poskytuje:

- nainstalované zjišťování a ověřování dovedností;
- úředník v reálném čase Hook/plugin collection plus označená relace záložní;
- Časové osy aktivace dovedností, načítání zdrojů a volání nástrojů;
- zástupce, MCPvztahy mezi soubory a artefakty;
- trvání, token, chyba, opakování a souhrny stavu, pokud jsou k dispozici;
- konzervativní omezení chování extrahovaná z proudu `SKILL.md`;
- kontroly shody na základě důkazů, ověřování a běhu;
- inventáře konkrétních instrukcí, zdrojů, nástrojů, artefaktů a výsledků;
- Runtime Overview s limity systémového pokrytí oddělenými od zjištění běhu;
- prvohraniční diagnóza;
- panoramatický DAG, časový plán události a inspektor důkazů;
- porovnání mezi stejnými agenty a mezi agenty;
- samostatný Inferred Analysis povrch, který nemůže přepsat běhová fakta;
- přihlásit se OTLP/HTTP export a podporovaný import sledovatelnosti.

MVP **nezahrnuje** tržiště, běhové prostředí univerzálního agenta, vynucování zabezpečení, podnikové řízení ani nároky s kauzálním účinkem.

## Detailní instalace

Pro nejkratší podporovanou cestu použijte jednořádkový instalační program v [Rychlý start](#quick-start). Kompletní postup prvního spuštění, kroky restartování/důvěry agenta, chování v oblasti ochrany osobních údajů a odstraňování problémů jsou k dispozici v [Průvodce Začínáme](docs/getting-started.md).

Pro vývoj nemá základní implementace žádné další runtime závislosti Python 3,9+. Z kořenového adresáře úložiště:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Poté otevřete [http://127.0.0.1:4317](http://127.0.0.1:4317).

Jednorázový `install` příkaz:

1. prohledá umístění dovedností uživatelů, projektů a pluginů v mezipaměti;
2. zjistí Codex, Claude Code, Qodera OpenCode beze změny jejich konfigurace;
3. ukazuje, které cesty agentů a dovedností budou načteny;
4. stáhne nativního odesílatele s nízkým spuštěním ověřeného kontrolním součtem pro aktuální platformu, vrátí se k místnímu sestavení C a nakonec Python odesílatel a během instalace jednou předehřeje čerstvý nativní binární soubor;
5. vytváří `~/.skill-runtime/config.json` a místní SQLite index.

První index importuje existující kompatibilní relace agenta. Na pracovní stanici s dlouhou životností to může trvat déle než nová instalace; pozdější starty jsou přírůstkové a UI bude k dispozici během aktualizace na pozadí.

Když je spuštěn interaktivně, zeptá se jednou před přidáním háčků agenta otevřeného při selhání. `--no-hooks` zachová import přepisu jako označenou záložní, zatímco `--enable-hooks` zaznamená výslovný souhlas a nainstaluje pouze spravované položky. Pro Codex, OTEVŘENO `/hooks` po instalaci si prohlédněte přesně spravované příkazy a důvěřujte jim. Codex záměrně vyžaduje tuto explicitní kontrolu pro háky přidané mimo konfiguraci spravovaného podniku. Začněte nový Codex úkol/relaci po důvěře Hooks, pak spusťte:

```bash
.venv/bin/skill-runtime doctor
```

Qoder zatížení Hook konfiguraci při startu, tak restart Qoder po první instalaci. OpenCode objeví spravovaný plugin pouze pro pozorování ze svého globálního adresáře pluginů; restartovat OpenCode pokud aktuální proces předchází instalaci. Integrace nečte ani nemění požadavky modelu.

Integrace se stane **Live** až poté, co databáze obdrží real `official_hook` událost. Pouze psaní `~/.codex/hooks.json` se zobrazí jako **Nevyřízeno**, nikdy nepřipojeno. `start` spouští Collector, záložního sledování přepisů, retenčního pracovníka, SQLite skladovat a žít UI jako řízený proces na pozadí. Žádný požadavek na model není zadán proxy.

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

`uninstall` odstraní pouze spravované Hook záznamy a Skill Runtime-vlastněné soubory. Bez `--keep-data`, vyžaduje interaktivní potvrzení (příp `--yes`) před odstraněním `~/.skill-runtime`; Relace agenta a zdroje dovedností nejsou nikdy odstraněny.

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

Verzované profily importu aktuálně rozpoznávají OTLP/Phoenix, Langfuse, LangSmith, W&B Weavea Datadog JSON tvary. Vytvářejí pouze a SkillRun když zdroj nese explicitní sémantiku dovedností; generické názvy span nejsou považovány za důkaz aktivace.

Exportujte normalizované, pro dovednosti specifické runtime důkazy do libovolného OTLP/HTTP trasování koncového bodu:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Export je zakázán, pokud není explicitně nakonfigurován koncový bod. Kontrolní body, stav opakování a stav cíle se zobrazují v Nastavení. Nezpracované výzvy, užitečné zatížení nástrojů, pověření a obsah zdrojů dovedností se neexportují. Pro ověřený export na pozadí poskytněte standard `OTEL_EXPORTER_OTLP_HEADERS` v prostředí předtím `skill-runtime start`; do hlaviček se nikdy nezapisuje Skill Runtime konfigurační nebo procesní argumenty.

## Odešlete živé běhové důkazy

`skill-runtime start` zahrnuje místní kolektor. Nativní telemetrické adaptéry, oficiální háky, lehké háky pro otevírání při selhání a SDK integrace mohou připojit jednu událost nebo ohraničenou dávku `POST /api/events`:

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

Koncový bod rediguje běžná pověření před persistencí, deduplikuje pomocí `event_id`, zachová samostatnou redigovanou nezpracovanou obálku a vrátí výsledek `skill_run_ids`. `GET /api/collector/schema` odhaluje podporovaný slovník událostí a režimy shromažďování. The UI poslouchá `/api/stream` pomocí SSE, s dotazováním pouze jako záložním řešením pro opětovné připojení.

Zdrojový indikátor odlišuje primární runtime evidence od `Transcript fallback` a importované stopy. Samotný koncový bod Collector si nenárokuje nativní telemetrii: každý výrobce musí deklarovat, zda jeho událost pochází z nativní telemetrie, oficiálního háčku, lehkého háčku nebo SDK.

### Volitelné háky agentů

Nejprve zkontrolujte přesné cesty a události. Tento příkaz je pouze pro čtení:

```bash
.venv/bin/skill-runtime setup
```

Hook instalace vyžaduje explicitní příznak:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Instalační program zazálohuje konfiguraci agenta, zachová existující háky a přidá pouze položky nesoucí a Skill Runtime manažerská značka. Adaptér háku ukládá pole minimálního životního cyklu spíše než úplné výzvy nebo užitečné zatížení nástrojů. U dokončených volání nástrojů extrahuje pouze přesné `SKILL.md`, standardní prostředek dovedností a změněné cesty k souborům v paměti; raw příkazy, těla záplat, výzvy a výstupy nástrojů jsou před persistencí zahozeny. Když je běhové prostředí aktivní, je omezeno oprávnění Unix zásuvka je rychlá cesta; nepovinný nativní odesílatel se vyhýbá Python spuštění. Když není běhové prostředí aktivní, samostatná cesta otevření při selhání připojí redigované důkazy `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` přehraje tuto frontu s deduplikací ID události.

Codex události používají své oficiální Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`a `Stop`). Codex aktuálně provádí zavěšení příkazů synchronně, takže Skill Runtime používá místní Unix socket/nativní odesílatel s omezeným časovým limitem. Jakékoli selhání doručení je spolknuto a zařazeno do fronty; nikdy to nezmění rozhodnutí agenta. Viz [oficiální dokumentace Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Odstraňte pouze spravované položky pomocí:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Server se váže na `127.0.0.1` standardně. Zprávy s úplným přepisem a užitečné zatížení nástrojů se do indexu nezkopírují. Běžné tajné vzory jsou redigovány předtím, než jsou uchovány normalizované souhrny.

Spusťte nezávislou testovací sadu pomocí:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Uvolňovací technika

GitHub Akce běží Python 3.9–3.13 testy, ověření JavaScriptu, kompilace nativního odesílatele a skutečný kouřový test instalace/spuštění/doktor/zastavení/odinstalace. A `v*` tag vytváří balíčky wheel/sdist plus chráněné kontrolním součtem Linux a macOS nativní odesílatelé. Instalační program CLI stáhne odpovídající aktivum vydání, takže koncoví uživatelé nepotřebují kompilátor.

Spusťte první diagnostický experiment spojený s produktem:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Vkládá chyby v důkazech o životním cyklu, explicitní selhání, nedokončené běhy a neověřené výsledky a poté vyhodnocuje stejný deterministický diagnostický engine, jaký používá API a UI. Viz [Plán experimentu PAI-DSW](docs/pai-dsw-experiment-plan.md) pro žebříček experimentů, testy nerušení a smlouvu reprodukovatelnosti.

Po sestavení kola spusťte izolovaný zabalený kouř životního cyklu s:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Instaluje se do dočasného virtuálního prostředí a dočasného domova, provádí celý místní životní cyklus bez povolení háčků a ověřuje, že projekt a konfigurace agenta neinterferují.

## Design produktu řízený experimenty

Chování produktu se řídí čtyřmi omezeními řízenými experimenty: důkazy před závěry, první pozorovatelná hranice před závažností, typizované vztahy před plochými logy a deterministická rekonstrukce před pravděpodobnostní pomocí.

Reprodukovatelné důkazy a jejich omezení jsou udržovány v [zpráva o experimentu](docs/experiment-results-2026-07-29.md). Omezené výsledky zahrnují:

- 2 400/2 400 Kolektorové události přijaté bez vstupní/výstupní mutace;
- 14/14 deterministické diagnózy korpusu chyb bez nepodloženého kauzálního tvrzení;
- reprezentace relační diagnózy s přesností 13/14 a F1 0,963, zatímco ploché vyhledávání životního cyklu dosáhlo přesnosti 1/14 a F1 0,080;
- audit v reálném provozu bezpečný pro ochranu soukromí, který je explicitně i nadále nevhodný pro potvrzující tvrzení o účinku produktu, protože chybí ověřené výsledky, vyvážené pokrytí mezi agenty a lidské označení.

Tyto výsledky ověřují mechanismy a volby reprezentace, nikoli zobecnění nasazení nebo lidský prospěch. Skutečné studie druhého agenta, latence ocasu napříč platformami, kalibrace skutečné chyby a studie diagnózy účastníků zůstávají otevřené mezery v důkazech.

Směr výzkumu je také založen na sousední primární práci: [SkillsBench](https://arxiv.org/abs/2602.12670) a [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivovat k diagnóze, protože účinky dovedností se liší a mohou ustoupit; [Harness-Bench](https://arxiv.org/abs/2605.27922) motivuje porovnávání mezi agenty na základě schopností; a [průzkum provenience provedení](https://arxiv.org/abs/2606.04990) motivuje vztahy s typizovanými důkazy, původ původu a infrastrukturu auditu s ohledem na soukromí.

## Dokumentace

| Začněte zde | Účel |
|---|---|
| [Getting Started](docs/getting-started.md) | Nainstalujte, připojte Agenta, ověřte živé důkazy a odstraňte problémy |
| [Architektura](docs/architecture.md) | Sběrný kanál, hranice úložiště, motor evidence a model důvěry |
| [Matice schopností adaptéru](docs/adapter-capability-matrix.md) | Přesné signály a omezení podle agenta/verze |
| [Nastavení platformy pozorovatelnosti](docs/observability-platform-setup.md) | Připojte platformy kompatibilní s OTLP a importujte podporovaná trasování |
| [Model událostí za běhu](docs/runtime-event-model.md) | Stabilní slovník událostí, původ, vztahy a známky důkazů |
| [Informační architektura uživatelského rozhraní](docs/ui-information-architecture.md) | Přehled, první hranice, Panorama, Inspektor, Porovnat a Inferred Analysis |
| [Seznam změn](CHANGELOG.md) | Verzované změny viditelné pro uživatele |
| [poznámky k vydání v0.3.0](docs/releases/v0.3.0.md) | Upgradujte navádění, zvýraznění a známé limity |

Reference produktu a výzkumu: [definice produktu](docs/product-definition.md), [Specifikace MVP](docs/mvp-specification.md), [pozorovatelnost interoperabilita](docs/observability-interoperability.md), [výsledky experimentu](docs/experiment-results-2026-07-29.md)a [výzkumná agenda](docs/research-paper-agenda.md).

## Společenství a správa věcí veřejných

- Číst [Přispívání](CONTRIBUTING.md) před změnou sémantiky důkazů, adaptérů nebo chování produktu.
- Postupujte podle [Kodex chování](CODE_OF_CONDUCT.md) ve všech projektových prostorách.
- Nahlaste zranitelnosti soukromě prostřednictvím [Bezpečnostní politika](SECURITY.md), není veřejný problém.
- Použijte strukturované [sledovač problémů](https://github.com/hellogxp/skill-runtime-intelligence/issues) pro reprodukovatelné chyby a návrhy funkcí v rozsahu. Nikdy nepřipojujte soukromé runtime databáze nebo přepisy relací.

## Cestovní mapa

1. **v0.3.0 — Příští vydání:** kontrolovatelná omezení chování dovedností, konkrétní běhová aktivita, hodnocení na základě důkazů, diagnostika systémového pokrytí a stávající pracovní postup Panorama a porovnání.
2. **Další — Rozšíření adaptéru a diagnostiky:** širší pokrytí agentů/verzí, kalibrace skutečných chyb, ověření koncové latence mezi platformami a diagnostické studie účastníků.
3. **Později — Vyhodnocení efektu:** řízené s párovým hodnocením s dovedností/bez dovednosti, vedené explicitně odděleně od diagnostiky jednoho cyklu.

## Stav projektu

Aktuální zdrojový strom cíle `v0.3.0`; pomocí odznaku vydání výše identifikujte nejnovější publikované sestavení. Runtime zahrnuje kontrolovatelná omezení chování dovedností, konkrétní souhrny aktivit, inventář nainstalovaných definic, úředníky řízené souhlasem Hook adaptéry pro Codex, Claude Codea Qoder, pouze pozorování OpenCode plugin, označený záložní přepis, přiřazení aktivního rozsahu, přesné cesty k souboru/artefaktu, redakce, samostatné vrstvy zdroje/vztahu/odvození, SQLite uložení, retence, deterministická diagnóza, živ UIa porovnání mezi běhy a agenty. OTLP/Phoenix, Langfuse, LangSmith, W&B Weavea Datadog export lze dovážet; normalizované důkazy lze živě exportovat prostřednictvím přihlášení OTLP/HTTP.

Kandidátský objev uvnitř modelu, důvody interního výběru modelu, sémantická účinnost a tvrzení o kauzálních výsledcích zůstávají výslovně nepodporované, pokud zdroj nebo kontrolovaný experiment neposkytne takové důkazy.
