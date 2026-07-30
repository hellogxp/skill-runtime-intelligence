# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · **Magyar**
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligencia/kiadások/legújabb)[![Engedély](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](ENGEDÉLY)[![Piton](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnosztizálja, hol tért el először egy ügynöki készség – és nézze meg a bizonyítékokat
> minden következtetés mögött.

Agent Skill Runtime Intelligenceegy csak olvasható futásidejű bizonyíték- és diagnosztikai rendszer az Agent Skills számára. Egyesíti a készségdefiníciókat, a hivatalos ügynök futásidejű eseményeket, az importált nyomkövetéseket, a munkamenet-visszaállítást és a megfigyelhető munkaterület-eredményeket egy bizonyítékok szerinti osztályozásbanSkill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Gyors kezdés

Telepítse a legújabb önálló kiadást macOS vagy Linux rendszeren:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nincs klón,GitHub fiók,`sudo`, vagyGitHub CLI szükséges. A telepítő letölti a megfelelő aláírt kiadás hasznos adatot, ellenőrzi az SHA-256 ellenőrző összegeket, egyszer rákérdez, mielőtt engedélyezi a hibamentes ügynök hook-okat, és az összes futásidejű adatot a következő helyen tárolja.`~/.skill-runtime`. Ezután elindítja a helyi futási környezetet, és megnyílik[http://127.0.0.1:4317](http://127.0.0.1:4317).

Megteheti[ellenőrizze a telepítőt](scripts/install.sh)futtatása előtt.

Vagy futtassa közvetlenül a forráspénztárból:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Nyitott[http://127.0.0.1:4317](http://127.0.0.1:4317). MertCodex, tekintse át és bízza meg a kezelt parancsokat`/hooks`, kezdjen egy új ügynöki kört, majd ellenőrizze:

```bash
skill-runtime doctor
```

Az integráció csak akkor válik **ellenőrzötté**, ha valódi hivatalos horog esemény érkezik. A beállított horog **Függőben**ként jelenik meg, soha nem élő bizonyítékként.

| A termék felülete | Mit válaszol |
|---|---|
| Futásidejű áttekintés | MelyikSkillRunskell figyelni? |
| Első megfigyelhető határ | Hol tűntek el először a bizonyítékok vagy kudarcot vallottak? |
| Skill Run Panorama | Hogyan kapcsolódott össze a kérés, az aktiválás, az erőforrások, az eszközök, a műtermékek és az eredmény? |
| Bizonyítékfelügyelő | Milyen forrás, minőség, alap és adapter képesség támasztja alá ezt az állítást? |
| Hasonlítsa össze | A különbség viselkedésbeli, vagy csak megfigyelhetőségi különbség? |
| Beállítások / Orvos | Mi az olvasott, tárolt, exportált, függőben lévő és ellenőrzött? |

## A probléma

A Skill telepítése nem bizonyítja, hogy egy ügynök fedezte fel azt. A felfedezés nem bizonyítja az aktiválást. Az aktiválás nem bizonyítja, hogy a teljes utasítások és erőforrások betöltésre kerültek. A végrehajtás nem bizonyítja, hogy a Skill javította az eredményt.

Ma ezek a kudarcok gyakran hallgatnak. A fejlesztők kérdezik:

- Rendelkezésre állt a Skill ennek az ügynöknek?
- Aktiválódott erre a kérésre?
- Mely utasítások, hivatkozások, szkriptek és eszközök lettek betöltve?
- Milyen eszközök,MCPhívások, segédügynökök, fájlok és műtermékek érintettek?
- Hol nem sikerült a futtatás, hol próbálkozott újra vagy veszítette el a kontextust?
- A Skill segített, vagy csak növelte a költségeket és a késleltetést?

## A termék iránya

Az első termék egy **Skill Run Panorama**:

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

A panoráma valódi jelekből épül fel, nem modell önjelentésből:

| Forrás | Példák | Bizonyíték |
|---|---|---|
| Ügyességi fájlok | metaadatok, utasítások, szkriptek, hivatkozások, eszközök | Megfigyelt |
| Futásidejű események | Ügyességi hívások, szerszámhívások, segédanyagok, hibák, időtartam | Megfigyelt |
| A munkamenet átiratai | promptok, üzenetek, szerszám be- és kimenetek, rendelés | Megfigyelt |
| A munkaterület eredményei | fájl módosítások,Gitdiff, jelentések, generált műtermékek | Megfigyelt |
| Korreláció | események, erőforrások és eredmények közötti kapcsolatok | Származtatott vagy kikövetkeztetett |

## Bizonyítási fegyelem

AUIsoha nem szabad következtetést levonni futásidejű tényként:

- **Megfigyelt** – kifejezetten jelen van egy forráseseményben vagy fájlban.
- **Származtatott** – determinisztikusan kapcsolódik a megfigyelt bizonyítékokhoz.
- **Kikövetkeztetett** — elfogadható magyarázat, bizonytalansággal.
- **Kísérleti** – ellenőrzött páros értékeléssel mért hatás.

Egyetlen nyomkövetés támogathatja a végrehajtási hozzárendelést. Az ok-okozati hatást nem tudja bizonyítani. Az olyan állítások, mint például „ez a készség javította a sikerességi arányt”, ismételt készségértékelést igényelnek/készség nélkül.

## A termék alapelvei

- Alapértelmezés szerint privát, helyi, hibrid és csapatkapcsolatos telepítéssel.
- Csak olvasható megfigyelés; soha ne vegye át az ügynökhurkot.
- Nincs modellproxy és nincs kötelező felhőszolgáltatás.
- Az alapértelmezett termékben nincs blokkolás, jóváhagyási kapu vagy szabályzat érvényesítése.
- Explicit származás és bizonyítékok osztályozása.
- Progresszív közzététel: először egyszerű narratíva, igény szerint nyers események.
- Adapter alapú támogatás az ügynök átirat-formátumok megváltoztatásához.

## Kezdeti hatály

A futásidejű támogatjaCodex,Claude Code,Qoder, ésOpenCodefüggetlen, verziószámú adaptereken keresztül, és a következőket kínálja:

- telepített készségfelderítés és érvényesítés;
- munkamenet importálás és élő helyi megfigyelés, ahol támogatott;
- A készségek aktiválása, az erőforrások betöltése és az eszközhívások ütemezése;
- alárendelt,MCP, fájl és műtermék kapcsolatok;
- időtartam, token, hiba, újrapróbálkozás és állapot-összefoglalók, ha rendelkezésre állnak;
- egy futási lista, panoráma DAG, esemény idővonal és csomópont-ellenőr.

Az MVP **nem** tartalmazza a piacteret, az univerzális ügynök futtatókörnyezetét, a biztonsági végrehajtást, a vállalatirányítást vagy az ok-okozati összefüggéseket.

## Részletes telepítés

Az alapkivitelnek nincs futásidejű függősége azon túlPython3,9+. A tároló gyökérből:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Ezután nyissa meg[http://127.0.0.1:4317](http://127.0.0.1:4317).

Az egyszeri`install`parancs:

1. átvizsgálja a felhasználók, a projektek és a gyorsítótárazott beépülő modulok képzettségi helyeit;
2. észleliCodex,Claude Code,Qoder, ésOpenCodekonfigurációjuk megváltoztatása nélkül;
3. megmutatja, hogy mely ügynök és szakértelem útvonalak kerülnek beolvasásra;
4. letölt egy ellenőrzőösszeggel ellenőrzött alacsony indítású natív küldőt az aktuális platformhoz, visszatérve egy helyi C buildre, és végül aPythonküldőt, és a telepítés során egyszer előmelegít egy friss natív bináris fájlt;
5. létrehozza`~/.skill-runtime/config.json`és a helyiSQLiteindex.

Interaktív futtatáskor egyszer megkérdezi, mielőtt felveszi a feladatmegnyitó ügynök hook-okat.`--no-hooks`megőrzi a transzkriptum importálását címkézett tartalékként, míg`--enable-hooks`rögzíti a kifejezett hozzájárulást, és csak a kezelt bejegyzéseket telepíti. MertCodex, nyitott`/hooks`telepítés után tekintse át a pontosan kezelt parancsokat, és bízzon bennük.Codexszándékosan megköveteli ezt a kifejezett felülvizsgálatot a felügyelt vállalati konfiguráción kívül hozzáadott hookok esetében. Indítson el egy új ügynöki kört, majd futtassa:

```bash
.venv/bin/skill-runtime doctor
```

Qoderindításkor betölti a Hook konfigurációt, ezért indítsa újraQoderaz első telepítés után.OpenCodefelfedezi a felügyelt, csak megfigyelésre alkalmas beépülő modult a globális beépülő modulok könyvtárából; indítsa újraOpenCodeha az aktuális folyamat megelőzi a telepítést. Egyik integráció sem olvassa be vagy módosítja a modellkéréseket.

Az integráció csak akkor válik **Élő**-vé, ha az adatbázis valódi értéket kap`official_hook`esemény. Pusztán írás`~/.codex/hooks.json`**Függőben**ként jelenik meg, soha nincs csatlakoztatva.`start`elindítja a Collectort, az átiratok tartalékfigyelőjét, a megőrzési dolgozót,SQLitetárolni, és élniUImenedzselt háttérfolyamatként. Nincs modellkérelem proxy.

Életciklus parancsok:

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

`uninstall`csak kezelt Hook bejegyzéseket távolít el ésSkill Runtime-tulajdonú fájlok. Nélkül`--keep-data`, interaktív megerősítést igényel (vagy`--yes`) eltávolítása előtt`~/.skill-runtime`; Az ügynöki munkamenetek és a készségforrások soha nem kerülnek eltávolításra.

Indexelés és külön szolgáltatás:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Meglévő nyomkövetési export importálása egy általános megfigyelési rendszerből:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

A verziójú importprofilok jelenleg felismerik az OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, ésDatadog JSONformák. Csak létrehoznak aSkillRunamikor a forrás explicit Skill szemantikát hordoz; az általános tartományneveket nem kezelik aktiválási bizonyítékként.

Normalizált, készségspecifikus futásidejű bizonyítékok exportálása bármelyikreOTLP/HTTPnyomkövetési végpont:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Az exportálás le van tiltva, hacsak nincs kifejezetten konfigurálva egy végpont. Az ellenőrzőpontok, az újrapróbálkozás állapota és a cél állapota a Beállításokban jelennek meg. A nyers promptok, az eszköztárak, a hitelesítő adatok és a szakértelem-erőforrás tartalma nem exportálódik. A hitelesített háttérexportáláshoz adjon meg szabványt`OTEL_EXPORTER_OTLP_HEADERS`előtti környezetben`skill-runtime start`; fejlécek soha nem íródnakSkill Runtimekonfigurációs vagy folyamatargumentumok.

## Élő futásidejű bizonyítékok küldése

`skill-runtime start`tartalmaz egy helyi gyűjtőt. Natív telemetriai adapterek, hivatalos horgok, könnyű, hibamentes horgok ésSDKAz integrációk egyetlen eseményt vagy korlátos köteget fűzhetnek hozzá`POST /api/events`:

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

A végpont eltávolítja a gyakori hitelesítő adatokat a fennmaradás előtt, de duplikációt hajt végre`event_id`, megőrzi a külön szerkesztett nyers borítékot, és visszaküldi az eredményt`skill_run_ids`.`GET /api/collector/schema`megjeleníti a támogatott eseményszótárat és gyűjtési módokat. AUIhallgat`/api/stream`SSE használatával, a lekérdezéssel csak az újracsatlakozási tartalékként.

A forrásjelző megkülönbözteti az elsődleges futásidejű bizonyítékot a`Transcript fallback`és behozott nyomok. A Collector végpont önmagában nem igényel natív telemetriát: minden gyártónak nyilatkoznia kell, hogy eseménye natív telemetriából, hivatalos horogból, könnyűsúlyú horogból vagy egySDK.

### Opcionális Agent horgok

Először ellenőrizze a pontos útvonalakat és eseményeket. Ez a parancs csak olvasható:

```bash
.venv/bin/skill-runtime setup
```

A horog telepítése kifejezett jelzőt igényel:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

A telepítő biztonsági másolatot készít az ügynök konfigurációjáról, megőrzi a meglévő hookokat, és csak az a-t tartalmazó bejegyzéseket ad hozzáSkill Runtimemenedzsment jelző. A horogadapter minimális életciklus-mezőket tárol, nem pedig teljes promptokat vagy szerszámterhelést. Amíg a futtatókörnyezet aktív, egy engedély korlátozottUnixsocket a gyors út; az opcionális natív feladó elkerüliPythonindítás. Ha a futtatókörnyezet nem aktív, az önálló megszakítási útvonal hozzáfűzi a módosított bizonyítékot`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`újrajátssza a sort az eseményazonosító deduplikációjával.

Codexesemények a hivatalos Hook-ot használjákAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, és`Stop`).Codexjelenleg szinkronban hajtja végre a parancshorogokat, tehátSkill Runtimehelyit használUnixsocket/natív feladó korlátozott időkorláttal. Bármilyen kézbesítési hiba lenyelődik és sorba kerül; soha nem változtat az Ügynök döntésén. Lásd a[hivatalos Codex Hook dokumentáció](https://developers.openai.com/codex/config-advanced#hooks).

Csak a kezelt bejegyzéseket távolítsa el a következővel:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

A szerver kötődik`127.0.0.1`alapértelmezés szerint. A teljes átírási üzenetek és az eszköz hasznos terhei nem kerülnek az indexbe. A közös titkos mintákat a rendszer szerkeszti, mielőtt a normalizált összegzések megmaradnak.

Futtassa a függőségmentes tesztcsomagot a következővel:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Kiadási tervezés

GitA Hub Actions futPython3.9–3.13 tesztek, JavaScript-ellenőrzés, natív küldő-összeállítás és valódi telepítés/indítás/doctor/stop/uninstall füstteszt. A`v*`tag kerék/sdist csomagokat, valamint ellenőrzőösszeg-védett Linux és macOS natív küldőket épít fel. A CLI telepítője letölti a megfelelő kiadási eszközt, így a végfelhasználóknak nincs szükségük fordítóprogramra.

Futtassa az első termékhez kapcsolódó diagnosztikai kísérletet:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Hibákat szúr be az életciklusra vonatkozó bizonyítékok hiányosságaira, kifejezett hibákra, hiányos futtatásokra és ellenőrizetlen eredményekre, majd kiértékeli ugyanazt a determinisztikus diagnosztikai motort, amelyet aAPIésUI. Lásd a[PAI-DSW kísérleti terv](docs/pai-dsw-experiment-plan.md)a kísérleti létrához, az interferencia-tesztekhez és a reprodukálhatósági szerződéshez.

A kerék felépítése után futtassa az elkülönített csomagolt életciklus-füstöt a következővel:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Telepít egy ideiglenes virtuális környezetbe és ideiglenes otthonba, a teljes helyi életciklust a hoook engedélyezése nélkül gyakorolja, és ellenőrzi a projekt és az ügynök konfigurációjának zavartalanságát.

## Kísérletvezérelt terméktervezés

A termék viselkedését korlátozza a[kísérletvezérelt termékfilozófia](docs/experiment-driven-product-philosophy.md): bizonyíték a következtetések előtt, az első megfigyelhető határ a súlyosság előtt, a tipizált kapcsolatok a lapos rönkök előtt és a determinisztikus rekonstrukció a valószínűségi segítségnyújtás előtt.

A jelenlegi reprodukálható helyi bizonyítékok a következők:

- 7/7 helyi kísérleti kapu átment;
- 2 400/2 400 Gyűjtőesemények elfogadása bemeneti/kimeneti mutáció nélkül;
- 14/14 determinisztikus hibakorpusz diagnózis, alátámasztatlan ok-okozati összefüggés nélkül;
- a relációs diagnózis reprezentációja 13/14 pontos és F1 0,963, míg a lapos életciklus visszakeresés elérte az 1/14 pontos és F1 0,080;
- 11/11 tananyag esetek a legkorábbi megfigyelhető határt helyezik előtérbe.

Ezek az eredmények a mechanizmusokat és a reprezentációs választásokat igazolják, nem pedig a telepítés általánosítását vagy az emberi előnyöket. Valódi második ügynök tanulmányok, platformok közötti késleltetés, valós hibakalibrálás és résztvevő diagnosztikai vizsgálatok továbbra is nyitott bizonyítékok.

A kutatási irány a szomszédos elsődleges munkákra is épül:[SkillsBench](https://arxiv.org/abs/2602.12670)és[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motiválja a diagnózist, mert a készségek hatásai változóak és visszafejlődnek;[Harness-Bench](https://arxiv.org/abs/2605.27922)motiválja a képesség-tudatos cross-Agent összehasonlítást; és a[végrehajtás származási felmérés](https://arxiv.org/abs/2606.04990)motiválja a gépelt bizonyítékviszonyokat, a származási nyomkövetést és a magánélet-tudatos audit infrastruktúrát.

## Dokumentáció

- [A termék meghatározása](docs/product-definition.md)
- [MVP specifikáció](docs/mvp-specification.md)
- [Futásidejű eseménymodell](docs/runtime-event-model.md)
- [UI információs architektúra](docs/ui-information-architecture.md)
- [Adapter képesség mátrix](docs/adapter-capability-matrix.md)
- [Megfigyelhetőségi átjárhatóság](docs/observability-interoperability.md)
- [Megfigyelési platform beállítása](docs/observability-platform-setup.md)
- [Kutatás és versenyhelyzet](docs/research-and-competitive-landscape.md)
- [Kutatási napirend](docs/research-paper-agenda.md)
- [Kísérletvezérelt termékfilozófia](docs/experiment-driven-product-philosophy.md)
- [Kísérleti eredmények](docs/experiment-results-2026-07-29.md)
- [PAI-DSW kísérleti terv](docs/pai-dsw-experiment-plan.md)

## Útiterv

1. **v0.1 – Futásidejű bizonyítékok és diagnózis:** élő adatgyűjtés,Skill Run Panorama, első határdiagnózis, bizonyítékok vizsgálata, összehasonlítása és OTLP interoperabilitás.
2. **v0.2 – Adapter keményedési és diagnosztikai vizsgálatok:** további Agent verziók, valódi cross-Agent kísérletek és résztvevők értékelése.
3. **v0.3 – Hatásértékelés:** Ellenőrzött, készség/készség nélkül párosított értékeléssel, elkülönítve az egyszeri diagnosztikától.

## Projekt állapota

ASkillRun-az első futási környezet futtatható: telepített definíciós leltár,Codexátirat tartalék, beleegyezés-vezérelt hivatalos Hook adapterekCodex,Claude Code, ésQoder, csak megfigyelésOpenCodeplugin adapter, aktív hatókörű hozzárendelés, pontos fájl/műtermék elérési út, szerkesztés, külön forrás/kapcsolat/következtetési rétegek,SQLitetárolás, megőrzés, keresztfutás és ügynökök közötti összehasonlítás, determinisztikus diagnózis és az élő panorámaUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, ésDatadogaz export importálható; A normalizált bizonyítékok élőben exportálhatók a részvétellelOTLP/HTTP. A jelöltek felfedezése, a modell-belső kiválasztási okok, a szemantikai hatékonyság és az ok-okozati eredménnyel kapcsolatos állítások továbbra sem támogatottak.
