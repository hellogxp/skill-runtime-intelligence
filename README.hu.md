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


> Fordulat `SKILL.md` ellenőrizhető futásidejű elvárásokba. Nézze meg, valójában mit
> megtörtént, ahol a viselkedés először eltért, és az ítélet mögött meghúzódó bizonyítékok.

Agent Skill Runtime Intelligence egy csak olvasható futásidejű bizonyíték- és diagnosztikai rendszer az Agent Skills számára. Kivonja a konzervatív, ellenőrizhető megszorításokat a jelenlegi Skill definícióból, hozzáigazítja azokat a futásidejű tevékenységhez, és az eredményt bizonyítékok szerinti osztályozásként rekonstruálja. Skill Run Panorama. Egyesíti a hivatalos ügynök-eseményeket, az importált nyomkövetéseket, a címkézett munkamenet-visszaesést és a megfigyelhető munkaterület-eredményeket anélkül, hogy proxy-modellkérelmeket venne át, vagy átvenné az ügynökhurkot.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Gyors kezdés

Telepítse és indítsa el a legújabb kiadást macOS vagy Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nincs klón, fiók, `sudo`, vagy GitHub CLI szükséges. A telepítő ellenőrzi a kiadás ellenőrző összegét, észleli a támogatott ügynököket és készségeket, elmagyaráz minden elérési utat, amelyet olvasni fog, egyszer megkérdezi a csak megfigyelési hook engedélyezése előtt, és megnyitja a helyi UI at [http://127.0.0.1:4317](http://127.0.0.1:4317). A futásidejű adatok alatt maradnak `~/.skill-runtime` kivéve, ha kifejezetten konfigurál egy exportálást.

Megteheti [ellenőrizze a telepítőt](scripts/install.sh) futtatása előtt.

### Nézze meg első élőben SkillRun

1. Fogadja el az opcionális hibamentességet Hook állítsa be, amikor a telepítő kéri.
2. Indítsa újra az ügynököt, és kezdjen el egy új feladatot. In Codex, tekintse át a kezelt parancsokat `/hooks` első; a meglévő feladatok nem töltenek be hot-load újat Hooks.
3. Használjon szokásosan egy Skill-t, majd erősítse meg az integrációt, és nyissa meg a UI:

```bash
skill-runtime doctor
skill-runtime status
```

Az integráció csak akkor **Élő**, ha a Collector valódi futásidejű eseményt kap. Egy beállított, de nem megfigyelt Hook **Függőben** – soha nem mutatták be élő bizonyítékként. Nyitott [http://127.0.0.1:4317](http://127.0.0.1:4317), vagy lásd a [Útmutató az első lépésekhez](docs/getting-started.md) ügynökspecifikus utasításokért és hibaelhárításért.

Közvetlenül a forráspénztárból történő futtatáshoz:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| A termék felülete | Mit válaszol |
|---|---|
| Runtime Overview | Melyik SkillRuns kell figyelni? |
| Képesség-viselkedés ellenőrzése | Mely ellenőrizhető utasítások teljesültek, felülvizsgálatra szorulnak, vagy nem értékelhetők? |
| Mi történt valójában | Milyen utasításokat, forrásokat, eszközöket, műtermékeket és eredményeket figyeltek meg? |
| First Observable Boundary | Hol hiányoznak vagy hibáznak először a futásspecifikus bizonyítékok? |
| Skill Run Panorama | Hogyan kapcsolódott össze a kérés, az aktiválás, az erőforrások, az eszközök, a műtermékek és az eredmény? |
| Evidence Inspector | Milyen forrás, minőség, alap és adapter képesség támasztja alá ezt az állítást? |
| Hasonlítsa össze | A különbség viselkedésbeli, vagy csak megfigyelhetőségi különbség? |
| Inferred Analysis | Milyen bizonyítékokhoz kötött magyarázat vagy következő vizsgálat hihető? |
| Beállítások / Orvos | Mi az olvasott, tárolt, exportált, függőben lévő és ellenőrzött? |

## Hogyan működik

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime megfigyeli a már használt munkafolyamatot. A változatos adapterek az ügynök-natív eseményeket stabil Skill életciklussá alakítják, míg a nyers forrású borítékok, a normalizált események, kapcsolatok és következtetések külön maradnak. A diagnosztikai motor ellenőrzi az explicit Skill-korlátokat a bizonyítékok alapján, azonosítja a legkorábbi megfigyelhető eltérést, és elkülöníti a szisztémás adapter holtfoltjait a futásspecifikus megállapításoktól. Nem találja ki a modell szándékát vagy az ok-okozati hatékonyságot.

| Adatforrás | Szerep | Frissesség | UI címke |
|---|---|---|---|
| Hivatalos ügynök hoook / bővítmények / SDK eseményeket | Elsődleges életciklus, szerszám, segédanyag és terminális bizonyíték | Élő | `Official hook` / `Native telemetry` |
| Ügyességi fájlok és megfigyelhető munkaterületi eredmények | Meghatározás, erőforrás, fájl, műtermék és teszt bizonyíték | Élő pillanatkép / indexelt | `Observed` |
| A munkamenet átiratai | Kompatibilitási tartalék, ha az ügynök nem tesz elegendő futási időt API | Élőközeli vagy történelmi | `Transcript fallback` |
| OTLP és támogatott nyomkövetési export | Interoperabilitás és történelmi import | Élő export / kötegelt import | Forrásprofil látható |
| Determinisztikus korreláció | Összekapcsolja az eseményeket a SkillRun a forrástények megváltoztatása nélkül | Lenyeléskor | `Derived` |
| Szemantikai segítségnyújtás | Csak magyarázatok és vizsgálati javaslatok | Igény szerint | `Inferred` |

A támogatott belső adapterek verziószáma egymástól függetlenül történik:

| Ügynök | Elsődleges integráció | Tartalék | Aktiválás láthatósága |
|---|---|---|---|
| Codex | Hivatalos parancs Hooks | Munkamenet importálása | Explicit aktiválás, amikor a Hook esemény |
| Claude Code | Hivatalos Hooks | Munkamenet importálása | Explicit Skill Tool és perjel-parancs bizonyítékok, ahol láthatók |
| Qoder | Hivatalos parancs Hooks | Helyi rekordok | Explicit aktiválás, amikor a Skill eszköz teszi közzé |
| OpenCode | Csak megfigyelésre használható globális bővítmény | Helyi rekordok | Ügyességi eszközök visszahívásai, ahol megjelennek |

A pontos képességhatárokat a [adapter képesség mátrix](docs/adapter-capability-matrix.md). A nem támogatott és nem megfigyelt szakaszok láthatóak maradnak, ahelyett, hogy meghibásodásokká alakulnának.

## A probléma

A Skill telepítése nem bizonyítja, hogy egy ügynök fedezte fel azt. A felfedezés nem bizonyítja az aktiválást. Az aktiválás nem bizonyítja, hogy a teljes utasítások és erőforrások betöltésre kerültek. Az utasítások betöltése nem bizonyítja, hogy az Ügynök követte azokat. A végrehajtás nem bizonyítja, hogy a Skill javította az eredményt.

Ma ezek a kudarcok gyakran hallgatnak. A fejlesztők kérdezik:

- Rendelkezésre állt a Skill ennek az ügynöknek?
- Aktiválódott erre a kérésre?
- Mely utasítások, hivatkozások, szkriptek és eszközök lettek betöltve?
- Mely kifejezett készségkövetelményeket követték, hiányoztak vagy lehetetlen értékelni?
- Milyen eszközök, MCP hívások, segédügynökök, fájlok és műtermékek érintettek?
- Hol nem sikerült a futtatás, hol próbálkozott újra vagy veszítette el a kontextust?
- A Skill segített, vagy csak növelte a költségeket és a késleltetést?

## Készségspecifikus diagnózis

Az elsődleges diagnosztikai objektum a `SkillRun`, nem egy teljes ügynöki munkamenet:

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

A UI az életciklust rendezetten, gépelve és bizonyítékok szerint osztályozva tartja. A hiányzó aktiválási telemetria azt jelenti, hogy „nem figyelték meg” vagy „nem támogatott”; ez nem jelenti azt, hogy az ügynök határozottan kihagyta a készséget.

## Bizonyítási fegyelem

A UI soha nem szabad következtetést futásidejű tényként bemutatni:

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

A futásidejű támogatja Codex, Claude Code, Qoder, és OpenCode független, verziószámú adaptereken keresztül, és a következőket kínálja:

- telepített készségfelderítés és érvényesítés;
- valós idejű hivatalos Hook/plugin gyűjtemény plusz címkézett munkamenet tartalék;
- A készségek aktiválása, az erőforrások betöltése és az eszközhívások ütemezése;
- alügynök, MCP, fájl és műtermék kapcsolatok;
- időtartam, token, hiba, újrapróbálkozás és állapot-összefoglalók, ha rendelkezésre állnak;
- az áramból kivont konzervatív viselkedési kényszerek `SKILL.md`;
- bizonyítékokhoz kötött megfelelőségi, ellenőrzési és futásidejű-hibaellenőrzések;
- konkrét utasítások, erőforrások, eszközök, műtermékek és eredmények leltárak;
- Runtime Overview a rendszerszintű lefedettségi korlátokkal elválasztva a futtatási eredményektől;
- első határdiagnózis;
- panoráma DAG, esemény idővonal és bizonyítékellenőr;
- képesség-tudatos azonos-ügynök és ügynökök közötti összehasonlítás;
- egy különálló Inferred Analysis felület, amely nem tudja átírni a futásidejű tényeket;
- feliratkozás OTLP/HTTP export és támogatott megfigyelhetőség-nyomkövetés import.

Az MVP **nem** tartalmazza a piacteret, az univerzális ügynök futtatókörnyezetét, a biztonsági végrehajtást, a vállalatirányítást vagy az ok-okozati összefüggéseket.

## Részletes telepítés

A legrövidebb támogatott útvonal eléréséhez használja az egysoros kiadás telepítőjét [Gyors kezdés](#quick-start). A teljes első futási folyamat, az ügynökspecifikus újraindítási/megbízhatósági lépések, az adatvédelmi viselkedés és a hibaelhárítás a [Útmutató az első lépésekhez](docs/getting-started.md).

A fejlesztéshez az alap megvalósításnak nincs futásidejű függősége azon túl Python 3,9+. A tároló gyökérből:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Ezután nyissa meg [http://127.0.0.1:4317](http://127.0.0.1:4317).

Az egyszeri `install` parancs:

1. átvizsgálja a felhasználók, a projektek és a gyorsítótárazott beépülő modulok képzettségi helyeit;
2. észleli Codex, Claude Code, Qoder, és OpenCode konfigurációjuk megváltoztatása nélkül;
3. megmutatja, hogy mely ügynök- és készségútvonalak kerülnek beolvasásra;
4. letölt egy ellenőrzőösszeggel ellenőrzött alacsony indítású natív küldőt az aktuális platformhoz, visszatérve egy helyi C buildre, és végül a Python küldőt, és a telepítés során egyszer előmelegít egy friss natív bináris fájlt;
5. létrehozza `~/.skill-runtime/config.json` és a helyi SQLite index.

Az első index a meglévő kompatibilis ügynöki munkameneteket importálja. Egy hosszú élettartamú munkaállomáson ez tovább tarthat, mint egy friss telepítés; a későbbi indítások növekményesek és a UI elérhetővé válik, miközben a háttérben történő frissítés fut.

Interaktív futtatáskor egyszer megkérdezi, mielőtt felveszi a feladatmegnyitó ügynök hook-okat. `--no-hooks` megőrzi a transzkriptum importálását címkézett tartalékként, míg `--enable-hooks` rögzíti a kifejezett hozzájárulást, és csak a kezelt bejegyzéseket telepíti. Mert Codex, nyitott `/hooks` telepítés után tekintse át a pontosan kezelt parancsokat, és bízzon bennük. Codex szándékosan megköveteli ezt a kifejezett felülvizsgálatot a felügyelt vállalati konfiguráción kívül hozzáadott hookok esetében. Kezdj egy újat Codex feladat/munkamenet után bízva a Hooks, majd futtassa:

```bash
.venv/bin/skill-runtime doctor
```

Qoder terhelések Hook konfigurálása indításkor, ezért indítsa újra Qoder az első telepítés után. OpenCode felfedezi a felügyelt, csak megfigyelésre alkalmas beépülő modult a globális beépülő modulok könyvtárából; indítsa újra OpenCode ha az aktuális folyamat megelőzi a telepítést. Egyik integráció sem olvassa be vagy módosítja a modellkéréseket.

Az integráció csak akkor válik **Élő**-vé, ha az adatbázis valódi értéket kap `official_hook` esemény. Pusztán írás `~/.codex/hooks.json` **Függőben**ként jelenik meg, soha nincs csatlakoztatva. `start` elindítja a Collectort, az átiratok tartalékfigyelőjét, a megőrzési dolgozót, SQLite tárolni, és élni UI menedzselt háttérfolyamatként. Nincs modellkérelem proxy.

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

`uninstall` csak kezelt eltávolítja Hook bejegyzések és Skill Runtime-tulajdonú fájlok. Nélkül `--keep-data`, interaktív megerősítést igényel (vagy `--yes`) eltávolítása előtt `~/.skill-runtime`; Az ügynöki munkamenetek és a készségforrások soha nem kerülnek eltávolításra.

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

A verziójú importprofilok jelenleg felismerik az OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, és Datadog JSON formák. Csak létrehoznak a SkillRun amikor a forrás explicit Skill szemantikát hordoz; az általános tartományneveket nem kezelik aktiválási bizonyítékként.

Normalizált, készségspecifikus futásidejű bizonyítékok exportálása bármelyikre OTLP/HTTP nyomkövetési végpont:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Az exportálás le van tiltva, hacsak nincs kifejezetten konfigurálva egy végpont. Az ellenőrzőpontok, az újrapróbálkozás állapota és a cél állapota a Beállításokban jelennek meg. A nyers promptok, az eszköztárak, a hitelesítő adatok és a szakértelem-erőforrás tartalma nem exportálódik. A hitelesített háttérexportáláshoz adjon meg szabványt `OTEL_EXPORTER_OTLP_HEADERS` előtti környezetben `skill-runtime start`; fejlécek soha nem íródnak Skill Runtime konfigurációs vagy folyamatargumentumok.

## Élő futásidejű bizonyítékok küldése

`skill-runtime start` tartalmaz egy helyi gyűjtőt. Natív telemetriai adapterek, hivatalos horgok, könnyű, hibamentes horgok és SDK Az integrációk egyetlen eseményt vagy korlátos köteget fűzhetnek hozzá `POST /api/events`:

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

A végpont eltávolítja a gyakori hitelesítő adatokat a fennmaradás előtt, de duplikációt hajt végre `event_id`, megőrzi a külön szerkesztett nyers borítékot, és visszaküldi az eredményt `skill_run_ids`. `GET /api/collector/schema` megjeleníti a támogatott eseményszótárat és gyűjtési módokat. A UI hallgat `/api/stream` SSE használatával, a lekérdezéssel csak az újracsatlakozási tartalékként.

A forrásjelző megkülönbözteti az elsődleges futásidejű bizonyítékot a `Transcript fallback` és behozott nyomok. A Collector végpont önmagában nem igényel natív telemetriát: minden gyártónak nyilatkoznia kell, hogy eseménye natív telemetriából, hivatalos horogból, könnyű horogból vagy egy SDK.

### Opcionális Agent horgok

Először ellenőrizze a pontos útvonalakat és eseményeket. Ez a parancs csak olvasható:

```bash
.venv/bin/skill-runtime setup
```

Hook a telepítéshez explicit jelző szükséges:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

A telepítő biztonsági másolatot készít az ügynök konfigurációjáról, megőrzi a meglévő horgokat, és csak az a-t tartalmazó bejegyzéseket ad hozzá Skill Runtime menedzsment jelző. A horogadapter minimális életciklus-mezőket tárol, nem pedig teljes promptokat vagy szerszámterhelést. A befejezett szerszámhívásoknál csak pontos kivonatokat készít `SKILL.md`, standard Skill erőforrás és megváltoztatott fájl elérési út a memóriában; A nyers parancsok, patch törzsek, promptok és eszközkimenetek a fennmaradás előtt el lesznek vetve. Amíg a futtatókörnyezet aktív, egy engedély korlátozott Unix socket a gyors út; az opcionális natív feladó elkerüli Python indítás. Ha a futtatókörnyezet nem aktív, az önálló megszakítási útvonal hozzáfűzi a szerkesztett bizonyítékot `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` újrajátssza azt a sort az eseményazonosító deduplikációjával.

Codex események a hivatalos Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, és `Stop`). Codex jelenleg szinkronban hajtja végre a parancshorogokat, tehát Skill Runtime helyit használ Unix socket/natív küldő korlátozott időkorláttal. Bármilyen kézbesítési hiba lenyelődik és sorba kerül; soha nem változtat az Ügynök döntésén. Lásd a [hivatalos Codex Hook dokumentáció](https://developers.openai.com/codex/config-advanced#hooks).

Csak a kezelt bejegyzéseket távolítsa el a következővel:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

A szerver kötődik `127.0.0.1` alapértelmezés szerint. A teljes átírási üzenetek és az eszköz hasznos terhei nem kerülnek az indexbe. A közös titkos mintákat a rendszer szerkeszti, mielőtt a normalizált összegzések megmaradnak.

Futtassa a függőségmentes tesztcsomagot a következővel:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Kiadási tervezés

GitHub Akciók futnak Python 3.9–3.13 tesztek, JavaScript-ellenőrzés, natív küldő-összeállítás és valódi telepítés/indítás/doctor/stop/uninstall füstteszt. A `v*` tag kerék/sdist csomagokat épít, plusz ellenőrzőösszeg-védett Linux és macOS natív feladók. A CLI telepítője letölti a megfelelő kiadási eszközt, így a végfelhasználóknak nincs szükségük fordítóprogramra.

Futtassa az első termékhez kapcsolódó diagnosztikai kísérletet:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Hibákat szúr be az életciklusra vonatkozó bizonyítékok hiányosságaira, kifejezett hibákra, hiányos futtatásokra és ellenőrizetlen eredményekre, majd kiértékeli ugyanazt a determinisztikus diagnosztikai motort, amelyet a API és UI. Lásd a [PAI-DSW kísérleti terv](docs/pai-dsw-experiment-plan.md) a kísérleti létrához, az interferencia-tesztekhez és a reprodukálhatósági szerződéshez.

A kerék felépítése után futtassa az elkülönített csomagolt életciklus-füstöt a következővel:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Telepít egy ideiglenes virtuális környezetbe és ideiglenes otthonba, a teljes helyi életciklust a hookok engedélyezése nélkül gyakorolja, és ellenőrzi a projekt és az ügynök konfigurációjának zavartalanságát.

## Kísérletvezérelt terméktervezés

A termék viselkedése négy kísérlet által vezérelt megszorítást követ: bizonyíték a következtetések előtt, az első megfigyelhető határ a súlyosság előtt, a típusos kapcsolatok a lapos rönkök előtt, és a determinisztikus rekonstrukció a valószínűségi segítségnyújtás előtt.

A reprodukálható bizonyítékokat és annak korlátait fenntartja a [kísérleti jelentés](docs/experiment-results-2026-07-29.md). A korlátozott eredmények a következők:

- 2 400/2 400 Gyűjtőesemények elfogadása bemeneti/kimeneti mutáció nélkül;
- 14/14 determinisztikus hibakorpusz diagnózis, alátámasztatlan okozati állítás nélkül;
- a relációs diagnózis reprezentációja 13/14 pontos és F1 0,963, míg a lapos életciklus visszakeresés elérte az 1/14 pontos és F1 0,080;
- adatvédelmi szempontból biztonságos, valós futású audit, amely kifejezetten alkalmatlan marad a megerősítő termékhatás-állításokra, mivel hiányoznak az ellenőrzött eredmények, a kiegyensúlyozott ügynökök közötti lefedettség és az emberi címkék.

Ezek az eredmények a mechanizmusokat és a reprezentációs választásokat igazolják, nem pedig a telepítés általánosítását vagy az emberi előnyöket. Valódi második ügynök tanulmányok, platformok közötti késleltetés, valós hibakalibrálás és résztvevő diagnosztikai vizsgálatok továbbra is nyitott bizonyítékok.

A kutatási irány a szomszédos elsődleges munkákra is épül: [SkillsBench](https://arxiv.org/abs/2602.12670) és [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motiválja a diagnózist, mert a készségek hatásai változóak és visszafejlődnek; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiválja a képesség-tudatos cross-Agent összehasonlítást; és a [végrehajtás származási felmérés](https://arxiv.org/abs/2606.04990) motiválja a gépelt bizonyítékviszonyokat, a származási nyomkövetést és a magánélet-tudatos audit infrastruktúrát.

## Dokumentáció

| Kezdje itt | Cél |
|---|---|
| [Getting Started](docs/getting-started.md) | Telepítsen, csatlakoztasson ügynököt, ellenőrizze az élő bizonyítékokat, és végezzen hibaelhárítást |
| [Építészet](docs/architecture.md) | Gyűjteményi folyamat, tárolási határok, bizonyítékmotor és megbízhatósági modell |
| [Adapter képesség mátrix](docs/adapter-capability-matrix.md) | Pontos jelek és korlátozások ügynök/verzió szerint |
| [Megfigyelési platform beállítása](docs/observability-platform-setup.md) | Csatlakoztasson OTLP-kompatibilis platformokat, és importáljon támogatott nyomkövetéseket |
| [Futásidejű eseménymodell](docs/runtime-event-model.md) | Stabil eseményszókincs, származás, kapcsolatok és bizonyítékok fokozatai |
| [UI információs architektúra](docs/ui-information-architecture.md) | Áttekintés, első határ, Panoráma, Ellenőrző, Összehasonlítás és Inferred Analysis |
| [Változásnapló](CHANGELOG.md) | Verziózott, felhasználó által látható változtatások |
| [v0.3.0 kiadási megjegyzések](docs/releases/v0.3.0.md) | Frissítési útmutató, kiemelések és ismert korlátok |

Termék- és kutatási referenciák: [termék meghatározása](docs/product-definition.md), [MVP specifikáció](docs/mvp-specification.md), [megfigyelhetőség interoperabilitás](docs/observability-interoperability.md), [kísérleti eredmények](docs/experiment-results-2026-07-29.md), és a [kutatási menetrend](docs/research-paper-agenda.md).

## közösség és kormányzás

- Olvas [Hozzájárulás](CONTRIBUTING.md) mielőtt megváltoztatná a bizonyíték szemantikáját, adaptereit vagy a termék viselkedését.
- Kövesse a [Magatartási kódex](CODE_OF_CONDUCT.md) minden projekttérben.
- A sebezhetőségeket privát módon jelentheti a következőn keresztül [Biztonsági politika](SECURITY.md), nem közügy.
- Használja a strukturált [problémakövető](https://github.com/hellogxp/skill-runtime-intelligence/issues) reprodukálható hibákhoz és hatókörű funkciójavaslatokhoz. Soha ne csatoljon privát futásidejű adatbázisokat vagy munkamenet-átiratokat.

## Útiterv

1. **v0.3.0 – Következő kiadás:** Ellenőrizhető készség-viselkedési korlátok, konkrét futásidejű tevékenységek, bizonyítékokhoz kötött értékelés, rendszerszintű lefedettség-diagnosztika és a meglévő élő Panorama és Compare munkafolyamat.
2. **Következő – Adapter és diagnózis megerősítése:** szélesebb ügynök-/verziólefedettség, valós hibakalibrálás, többplatformos faroklatencia-ellenőrzés és résztvevő diagnosztikai vizsgálatok.
3. **Később – Hatásértékelés:** Ellenőrzött – Képesség/készség nélkül – páros értékeléssel, kifejezetten elkülönítve az egyszeri diagnosztikától.

## Projekt állapota

Az aktuális forrásfa cél `v0.3.0`; használja a fenti kiadási jelvényt a legújabb közzétett build azonosításához. A futási idő ellenőrizhető készség-viselkedési korlátokat, konkrét tevékenység-összefoglalókat, telepített definíciós leltárt, beleegyezés-vezérelt tisztviselőt tartalmaz Hook adapterek Codex, Claude Code, és Qoder, csak megfigyelés OpenCode beépülő modul, címkézett átirat tartalék, aktív hatókörű hozzárendelés, pontos fájl/műtermék elérési út, szerkesztés, külön forrás/kapcsolat/következtetési rétegek, SQLite tárolás, megőrzés, determinisztikus diagnózis, élő UI, és cross-run/cross-Agent összehasonlítás. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, és Datadog az export importálható; A normalizált bizonyítékok élőben exportálhatók a részvétellel OTLP/HTTP.

A modellen belüli jelölt felfedezések, a modell belső szelekciós okai, a szemantikai hatékonyság és az ok-okozati eredménnyel kapcsolatos állítások továbbra sem támogatottak, kivéve, ha egy forrás vagy ellenőrzött kísérlet erre bizonyítékot szolgáltat.
