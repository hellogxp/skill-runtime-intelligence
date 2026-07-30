# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · **Magyar**
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnosztizálja, hol tért el először egy ügynöki készség – és nézze meg a bizonyítékokat
> minden következtetés mögött.

Az Agent Skill Runtime Intelligence egy csak olvasható futásidejű bizonyíték- és diagnosztikai rendszer az ügynöki készségekhez. Egyesíti a készségdefiníciókat, a hivatalos ügynök futásidejű eseményeit, az importált nyomkövetéseket, a munkamenet-visszaesést és a megfigyelhető munkaterület-eredményeket egy bizonyítékok szerinti Skill Run Panorama-ben.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Gyors kezdés

Telepítse és indítsa el a legújabb kiadást az macOS vagy Linux oldalon:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nem szükséges klón, fiók, `sudo` vagy GitHub CLI. A telepítő ellenőrzi a kiadás ellenőrző összegét, felismeri a támogatott ügynököket és készségeket, elmagyaráz minden elérési utat, amit olvasni fog, egyszer megkérdezi, mielőtt engedélyezi a csak megfigyelési hook-ot, és megnyitja a helyi UI-t az [http://127.0.0.1:4317](http://127.0.0.1:4317) címen. A futásidejű adatok `~/.skill-runtime` alatt maradnak, hacsak nem konfigurálja kifejezetten az exportálást.

A futtatás előtt beírhatja az [ellenőrizze a telepítőt](scripts/install.sh) parancsot.

### Nézd meg az első élő adásodat SkillRun

1. Ha a telepítő kéri, fogadja el az opcionális feladatmegnyitási Hook beállítást.
2. Indítsa újra az ügynököt, és kezdjen el egy új feladatot. Az Codex-ben először tekintse át az `/hooks` kezelt parancsait; A meglévő feladatok nem töltik be forrón az új Hook-eket.
3. Használjon egy készséget a szokásos módon, majd erősítse meg az integrációt, és nyissa meg az UI-t:

```bash
skill-runtime doctor
skill-runtime status
```

Az integráció csak akkor **Élő**, ha a Collector valódi futásidejű eseményt kap. Egy konfigurált, de nem megfigyelt Hook **Függőben** – soha nem kerül bemutatásra élő bizonyítékként. Nyissa meg az [http://127.0.0.1:4317](http://127.0.0.1:4317)-t, vagy tekintse meg az [Útmutató az első lépésekhez](docs/getting-started.md) részt az ügynökspecifikus utasításokért és a hibaelhárításért.

Közvetlenül a forráspénztárból történő futtatáshoz:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| A termék felülete | Mit válaszol |
|---|---|
| Runtime Overview | Melyik SkillRuns igényel figyelmet? |
| First Observable Boundary | Hol tűntek el először a bizonyítékok vagy kudarcot vallottak? |
| Skill Run Panorama | Hogyan kapcsolódott össze a kérés, az aktiválás, az erőforrások, az eszközök, a műtermékek és az eredmény? |
| Evidence Inspector | Milyen forrás, minőség, alap és adapter képesség támasztja alá ezt az állítást? |
| Hasonlítsa össze | A különbség viselkedésbeli, vagy csak megfigyelhetőségi különbség? |
| Inferred Analysis | Milyen bizonyítékokhoz kötött magyarázat vagy következő vizsgálat hihető? |
| Beállítások / Orvos | Mi az olvasott, tárolt, exportált, függőben lévő és ellenőrzött? |

## Hogyan működik

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime figyeli a már használt munkafolyamatot. A változatos adapterek az ügynök-natív eseményeket stabil Skill életciklussá alakítják, míg a nyers forrású borítékok, a normalizált események, kapcsolatok és következtetések külön maradnak. A diagnosztikai motor először azonosítja azt a legkorábbi határt, ahol a bizonyítékok hiányoznak vagy meghiúsulnak; nem modellszándékot vagy ok-okozati hatást talál ki.

| Adatforrás | Szerep | Frissesség | UI címke |
|---|---|---|---|
| Hivatalos ügynök hookok / beépülő modulok / SDK események | Elsődleges életciklus, szerszám, segédanyag és terminális bizonyíték | Élő | `Official hook` / `Native telemetry` |
| Ügyességi fájlok és megfigyelhető munkaterületi eredmények | Meghatározás, erőforrás, fájl, műtermék és teszt bizonyíték | Élő pillanatkép / indexelt | `Observed` |
| A munkamenet átiratai | Kompatibilitási tartalék, ha az ügynök nem tesz elegendő futási időt API | Élőközeli vagy történelmi | `Transcript fallback` |
| OTLP és támogatott nyomkövetési export | Interoperabilitás és történelmi import | Élő export / kötegelt import | Forrásprofil látható |
| Determinisztikus korreláció | Az eseményeket az SkillRun-hez kapcsolja anélkül, hogy megváltoztatná a forrás tényeit | Lenyeléskor | `Derived` |
| Szemantikai segítségnyújtás | Csak magyarázatok és vizsgálati javaslatok | Igény szerint | `Inferred` |

A támogatott belső adapterek verziószáma egymástól függetlenül történik:

| Ügynök | Elsődleges integráció | Tartalék | Aktiválás láthatósága |
|---|---|---|---|
| Codex | Hivatalos parancs Hooks | Munkamenet importálása | Explicit aktiválás, amikor az Hook esemény ki van téve |
| Claude Code | Hivatalos Hooks | Munkamenet importálása | Explicit Skill Tool és perjel-parancs bizonyítékok, ahol láthatók |
| Qoder | Hivatalos parancs Hooks | Helyi rekordok | Explicit aktiválás, amikor a Skill eszköz teszi közzé |
| OpenCode | Csak megfigyelésre használható globális bővítmény | Helyi rekordok | Ügyességi eszközök visszahívásai, ahol megjelennek |

A pontos képességkorlátokat az [adapter képesség mátrix](docs/adapter-capability-matrix.md) dokumentálja. A nem támogatott és nem megfigyelt szakaszok láthatóak maradnak, ahelyett, hogy meghibásodásokká alakulnának.

## A probléma

A Skill telepítése nem bizonyítja, hogy egy ügynök fedezte fel azt. A felfedezés nem bizonyítja az aktiválást. Az aktiválás nem bizonyítja, hogy a teljes utasítások és erőforrások betöltésre kerültek. A végrehajtás nem bizonyítja, hogy a Skill javította az eredményt.

Ma ezek a kudarcok gyakran hallgatnak. A fejlesztők kérdezik:

- Rendelkezésre állt a Skill ennek az ügynöknek?
- Aktiválódott erre a kérésre?
- Mely utasítások, hivatkozások, szkriptek és eszközök lettek betöltve?
- Mely eszközök, MCP hívások, alügynökök, fájlok és műtermékek voltak érintettek?
- Hol nem sikerült a futtatás, hol próbálkozott újra vagy veszítette el a kontextust?
- A Skill segített, vagy csak növelte a költségeket és a késleltetést?

## Készségspecifikus diagnózis

Az elsődleges diagnosztikai objektum egy `SkillRun`, nem pedig egy teljes ügynök-munkamenet:

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

Az UI az életciklust rendezetten, gépelve és bizonyítékok szerint osztályozva tartja. A hiányzó aktiválási telemetria azt jelenti, hogy „nem figyelték meg” vagy „nem támogatott”; ez nem jelenti azt, hogy az ügynök határozottan kihagyta a készséget.

## Bizonyítási fegyelem

Az UI soha nem mutathat be következtetést futásidejű tényként:

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

## Jelenlegi hatókör

A futtatókörnyezet támogatja az Codex, Claude Code, Qoder és OpenCode fájlokat független, verziózott adaptereken keresztül, és a következőket biztosítja:

- telepített készségfelderítés és érvényesítés;
- valós idejű hivatalos Hook/bővítménygyűjtemény plusz címkézett munkamenet-visszaállítás;
- A készségek aktiválása, az erőforrások betöltése és az eszközhívások ütemezése;
- alágens, MCP, fájl és műtermék kapcsolatok;
- időtartam, token, hiba, újrapróbálkozás és állapot-összefoglalók, ha rendelkezésre állnak;
- Runtime Overview és első határdiagnózis;
- panoráma DAG, esemény idővonal és bizonyítékellenőr;
- képesség-tudatos azonos-ügynök és ügynökök közötti összehasonlítás;
- egy külön Inferred Analysis felület, amely nem tudja átírni a futásidejű tényeket;
- opt-in OTLP/HTTP export és támogatott megfigyelhetőségi nyomkövetési import.

Az MVP **nem** tartalmazza a piacteret, az univerzális ügynök futtatókörnyezetét, a biztonsági végrehajtást, a vállalatirányítást vagy az ok-okozati összefüggéseket.

## Részletes telepítés

A legrövidebb támogatott elérési úthoz használja az [Gyors kezdés](#quick-start) egysoros kiadás telepítőjét. A teljes első futási folyamat, az ügynökspecifikus újraindítási/megbízhatósági lépések, az adatvédelmi viselkedés és a hibaelhárítás az [Útmutató az első lépésekhez](docs/getting-started.md)-ben elérhető.

Fejlesztéshez az alap megvalósításnak nincs futásidejű függősége az Python 3.9+ verzión túl. A tároló gyökérből:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Ezután nyissa meg az [http://127.0.0.1:4317](http://127.0.0.1:4317)-t.

Az egyszeri `install` parancs:

1. átvizsgálja a felhasználók, a projektek és a gyorsítótárazott beépülő modulok képzettségi helyeit;
2. észleli az Codex, Claude Code, Qoder és OpenCode jeleket anélkül, hogy megváltoztatná a konfigurációjukat;
3. megmutatja, hogy mely ügynök és szakértelem útvonalak kerülnek beolvasásra;
4. letölt egy ellenőrzőösszeggel ellenőrzött, alacsony indítású natív feladót az aktuális platformhoz, amely visszamegy egy helyi C buildre és végül az Python feladóra, és egyszer a telepítés során előmelegít egy friss natív binárist;
5. létrehozza az `~/.skill-runtime/config.json`-t és a helyi SQLite indexet.

Interaktív futtatáskor egyszer megkérdezi, mielőtt felveszi a feladatmegnyitó ügynök hook-okat. Az `--no-hooks` az átirat-importálást tartja meg címkézett tartalékként, míg az `--enable-hooks` a kifejezett hozzájárulást rögzíti, és csak a kezelt bejegyzéseket telepíti. Codex esetén nyissa meg az `/hooks`-t a telepítés után, tekintse át a pontosan felügyelt parancsokat, és bízzon bennük. Az Codex szándékosan megköveteli ezt a kifejezett felülvizsgálatot a felügyelt vállalati konfiguráción kívül hozzáadott hookok esetében. Indítson el egy új Codex feladatot/munkamenetet, miután megbízott az Hook-ekben, majd futtassa:

```bash
.venv/bin/skill-runtime doctor
```

Az Qoder betölti az Hook konfigurációt indításkor, ezért az első telepítés után indítsa újra az Qoder fájlt. OpenCode felfedezi a felügyelt, csak megfigyelésre alkalmas beépülő modult a globális bővítménykönyvtárából; indítsa újra az OpenCode-t, ha az aktuális folyamat a telepítés előtt történt. Egyik integráció sem olvassa be vagy módosítja a modellkéréseket.

Az integráció csak akkor válik **Élő**-vé, ha az adatbázis valódi `official_hook` eseményt kap. Pusztán az `~/.codex/hooks.json` beírása **Függőben**ként jelenik meg, soha nem kapcsolódik. Az `start` felügyelt háttérfolyamatként elindítja a Collectort, az átiratok tartalékfigyelőjét, az adatmegőrzési dolgozót, az SQLite áruházat és az élő UI-t. Nincs modellkérelem proxy.

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

Az `uninstall` csak a kezelt Hook bejegyzéseket és az Skill Runtime tulajdonú fájlokat távolítja el. `--keep-data` nélkül az `~/.skill-runtime` eltávolítása előtt interaktív megerősítésre van szükség (vagy `--yes`); Az ügynöki munkamenetek és a készségforrások soha nem kerülnek eltávolításra.

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

A verziójú importprofilok jelenleg felismerik az OTLP/Phoenix, Langfuse, LangSmith, W&B Weave és Datadog JSON alakzatokat. Csak akkor hoznak létre SkillRun-t, ha a forrás explicit Skill szemantikát hordoz; az általános tartományneveket nem kezelik aktiválási bizonyítékként.

Normalizált, készségspecifikus futásidejű bizonyíték exportálása bármely OTLP/HTTP nyomkövetési végpontra:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Az exportálás le van tiltva, hacsak nincs kifejezetten konfigurálva egy végpont. Az ellenőrzőpontok, az újrapróbálkozás állapota és a cél állapota a Beállításokban jelennek meg. A nyers promptok, az eszköztárak, a hitelesítő adatok és a szakértelem-erőforrás tartalma nem exportálódik. A hitelesített háttérexportáláshoz adja meg a szabványos `OTEL_EXPORTER_OTLP_HEADERS` értéket a környezetben az `skill-runtime start` előtt; a fejlécek soha nem íródnak az Skill Runtime konfigurációs vagy feldolgozási argumentumokhoz.

## Élő futásidejű bizonyítékok küldése

Az `skill-runtime start` tartalmaz egy helyi gyűjtőt. A natív telemetria-adapterek, a hivatalos hook-ok, a könnyű, hibamentes hook-ok és az SDK integrációk egyetlen eseményt vagy egy korlátozott köteget hozzáfűzhetnek az `POST /api/events`-hez:

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

A végpont a megmaradás előtt redukálja a közös hitelesítési adatokat, deduplikációkat hajt végre az `event_id` értékkel, megőrzi egy külön szerkesztett nyers borítékot, és visszaadja a kapott `skill_run_ids` értéket. Az `GET /api/collector/schema` megjeleníti a támogatott eseményszókincset és gyűjtési módokat. Az UI az `/api/stream`-t SSE használatával hallgatja, a lekérdezéssel csak az újracsatlakozási tartalékként.

A forrásjelző megkülönbözteti az elsődleges futásidejű bizonyítékokat az `Transcript fallback`-től és az importált nyomkövetésektől. A Collector végpont önmagában nem igényel natív telemetriát: minden gyártónak nyilatkoznia kell, hogy eseménye natív telemetriáról, hivatalos horogról, könnyű horogról vagy SDK-ről származott.

### Opcionális Agent horgok

Először ellenőrizze a pontos útvonalakat és eseményeket. Ez a parancs csak olvasható:

```bash
.venv/bin/skill-runtime setup
```

Hook telepítéshez explicit jelző szükséges:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

A telepítő biztonsági másolatot készít az ügynök konfigurációjáról, megőrzi a meglévő hookokat, és csak az Skill Runtime felügyeleti jelzőt hordozó bejegyzéseket ad hozzá. A horogadapter minimális életciklus-mezőket tárol, nem pedig teljes promptokat vagy szerszámterhelést. A befejezett eszközhívásokhoz csak a pontos `SKILL.md`-t, a standard Skill erőforrást és a megváltozott fájl elérési útjait vonja ki a memóriából; A nyers parancsok, patch törzsek, promptok és eszközkimenetek a fennmaradás előtt el lesznek vetve. Amíg a futtatókörnyezet aktív, az engedélyekkel korlátozott Unix socket a gyors elérési út; az opcionális natív feladó elkerüli az Python indítását. Ha a futtatókörnyezet nem aktív, az önálló megszakítási útvonal hozzáfűzi a redukált bizonyítékot az `~/.skill-runtime/queue/events.jsonl`-hez. Az `skill-runtime start` újrajátssza a sort az eseményazonosító deduplikációjával.

Az Codex események a hivatalos Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, ⟦1⟦⟧, ⟦0L9 `SubagentStop` és `Stop`). Az Codex jelenleg szinkronban hajtja végre a parancshorgokat, így az Skill Runtime helyi Unix socketet/natív feladót használ korlátozott időkorláttal. Bármilyen kézbesítési hiba lenyelődik és sorba kerül; soha nem változtat az Ügynök döntésén. Lásd: [hivatalos Codex Hook dokumentáció](https://developers.openai.com/codex/config-advanced#hooks).

Csak a kezelt bejegyzéseket távolítsa el a következővel:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

A szerver alapértelmezés szerint az `127.0.0.1`-hez kötődik. A teljes átírási üzenetek és az eszköz hasznos terhei nem kerülnek az indexbe. A közös titkos mintákat a rendszer szerkeszti, mielőtt a normalizált összegzések megmaradnak.

Futtassa a függőségmentes tesztcsomagot a következővel:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Kiadási tervezés

GitHub Az Actions Python 3.9–3.13 teszteket, JavaScript-ellenőrzést, natív küldő fordítást és valódi telepítés/indítás/doctor/stop/uninstall füsttesztet futtat. Az `v*` címke kerek/sdist csomagokat, valamint ellenőrzőösszeg-védett Linux és macOS natív feladókat épít fel. A CLI telepítője letölti a megfelelő kiadási eszközt, így a végfelhasználóknak nincs szükségük fordítóprogramra.

Futtassa az első termékhez kapcsolódó diagnosztikai kísérletet:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Hibabefecskendezi az életciklusra vonatkozó bizonyítékok hiányosságait, kifejezett hibákat, hiányos futtatásokat és ellenőrizetlen eredményeket, majd kiértékeli ugyanazt a determinisztikus diagnosztikai motort, amelyet az API és UI használ. Lásd az [PAI-DSW kísérleti terv](docs/pai-dsw-experiment-plan.md)-t a kísérleti létráról, az interferencia-tesztekről és a reprodukálhatósági szerződésről.

A kerék felépítése után futtassa az elkülönített csomagolt életciklus-füstöt a következővel:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Telepít egy ideiglenes virtuális környezetbe és ideiglenes otthonba, a teljes helyi életciklust a hoook engedélyezése nélkül gyakorolja, és ellenőrzi a projekt és az ügynök konfigurációjának zavartalanságát.

## Kísérletvezérelt terméktervezés

A termék viselkedését korlátozza az [kísérletvezérelt termékfilozófia](docs/experiment-driven-product-philosophy.md): bizonyíték a következtetések előtt, az első megfigyelhető határ a súlyosság előtt, a típusos kapcsolatok a lapos rönkök előtt és a determinisztikus rekonstrukció a valószínűségi segítségnyújtás előtt.

A jelenlegi reprodukálható helyi bizonyítékok a következők:

- 7/7 helyi kísérleti kapu átment;
- 2 400/2 400 Gyűjtőesemények elfogadása bemeneti/kimeneti mutáció nélkül;
- 14/14 determinisztikus hibakorpusz diagnózis, alátámasztatlan ok-okozati összefüggés nélkül;
- a relációs diagnózis reprezentációja 13/14 pontos és F1 0,963, míg a lapos életciklus visszakeresés elérte az 1/14 pontos és F1 0,080;
- 11/11 tananyag esetek a legkorábbi megfigyelhető határt helyezik előtérbe.

Ezek az eredmények a mechanizmusokat és a reprezentációs választásokat igazolják, nem pedig a telepítés általánosítását vagy az emberi előnyöket. Valódi második ügynök tanulmányok, platformok közötti késleltetés, valós hibakalibrálás és résztvevő diagnosztikai vizsgálatok továbbra is nyitott bizonyítékok.

A kutatási irány a szomszédos elsődleges munkákon is alapul: [SkillsBench](https://arxiv.org/abs/2602.12670) és [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motiválják a diagnózist, mert a készséghatások változóak és visszafejlődnek; [Harness-Bench](https://arxiv.org/abs/2605.27922) képesség-tudatos cross-Agent összehasonlítást motivál; és az [végrehajtás származási felmérés](https://arxiv.org/abs/2606.04990) motiválja a típusos bizonyítékviszonyokat, a nyomkövetési eredetet és a magánélet-tudatos audit infrastruktúrát.

## Dokumentáció

| Kezdje itt | Cél |
|---|---|
| [Getting Started](docs/getting-started.md) | Telepítsen, csatlakoztasson ügynököt, ellenőrizze az élő bizonyítékokat, és végezzen hibaelhárítást |
| [Építészet](docs/architecture.md) | Gyűjteményi folyamat, tárolási határok, bizonyítékmotor és megbízhatósági modell |
| [Adapter képesség mátrix](docs/adapter-capability-matrix.md) | Pontos jelek és korlátozások ügynök/verzió szerint |
| [Megfigyelési platform beállítása](docs/observability-platform-setup.md) | Csatlakoztasson OTLP-kompatibilis platformokat, és importáljon támogatott nyomkövetéseket |
| [Futásidejű eseménymodell](docs/runtime-event-model.md) | Stabil eseményszókincs, származás, kapcsolatok és bizonyítékok fokozatai |
| [UI információs architektúra](docs/ui-information-architecture.md) | Áttekintés, első határ, Panoráma, Ellenőrző, Összehasonlítás és Inferred Analysis |

Termék- és kutatási hivatkozások: [termék meghatározása](docs/product-definition.md), [MVP specifikáció](docs/mvp-specification.md), [megfigyelhetőség interoperabilitás](docs/observability-interoperability.md), [kísérletvezérelt termékfilozófia](docs/experiment-driven-product-philosophy.md), [kísérleti eredmények](docs/experiment-results-2026-07-29.md) és [kutatási menetrend](docs/research-paper-agenda.md).

## Útiterv

1. **v0.2.0 – Most elérhető:** élő hibamentes gyűjtemény, négy verziójú ügynökadapter, Runtime Overview, első határdiagnózis, Panorama, Evidence Inspector, képesség-tudatos Compare, Inferred Analysis és OTLP együttműködés.
2. **Következő – Adapter és diagnózis megerősítése:** szélesebb ügynök-/verziólefedettség, valós hibakalibrálás, többplatformos faroklatencia-ellenőrzés és résztvevő diagnosztikai vizsgálatok.
3. **Később – Hatásértékelés:** Ellenőrzött – Képesség/készség nélkül – páros értékeléssel, kifejezetten elkülönítve az egyszeri diagnosztikától.

## Projekt állapota

Az `v0.2.0` verzió megjelent. A futtatókörnyezet telepített definíciós leltárt, beleegyezés-vezérelt hivatalos Hook adaptereket tartalmaz az Codex, Claude Code és Qoder, csak megfigyelésre alkalmas OpenCode beépülő modul, címkézett átirat tartalék, aktív hatókörű visszajelölés, különálló forrásmeghatározás, pontos forráshivatkozás/tartozás. rétegek, SQLite tárolás, megőrzés, determinisztikus diagnosztika, élő UI és cross-run/cross-Agent összehasonlítás. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave és Datadog exportok importálhatók; A normalizált bizonyítékok élőben exportálhatók az OTLP/HTTP opcióval.

A modellen belüli jelölt felfedezések, a modell belső szelekciós okai, a szemantikai hatékonyság és az ok-okozati eredménnyel kapcsolatos állítások továbbra sem támogatottak, kivéve, ha egy forrás vagy ellenőrzött kísérlet erre bizonyítékot szolgáltat.
