# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
**Polski** · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Zakręt `SKILL.md` w sprawdzalne oczekiwania dotyczące czasu wykonania. Zobacz co właściwie
> doszło do pierwszego rozbieżności w zachowaniu oraz dowody leżące u podstaw wyroku.

Agent Skill Runtime Intelligence to system dowodowy i diagnostyczny w trybie tylko do odczytu dla Agent Skills. Wyodrębnia konserwatywne, możliwe do sprawdzenia ograniczenia z bieżącej definicji Umiejętności, dopasowuje je do aktywności w czasie wykonywania i rekonstruuje wynik w postaci oceny opartej na dowodach Skill Run Panorama. Łączy w sobie oficjalne zdarzenia Agenta, zaimportowane ślady, oznaczony powrót do sesji i obserwowalne wyniki obszaru roboczego bez pośrednictwa żądań modelu lub przejmowania pętli Agenta.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Szybki start

Zainstaluj i uruchom najnowszą wersję macOS Lub Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Brak klonu, konta, `sudo`, Lub GitHub CLI jest wymagane. Instalator weryfikuje sumę kontrolną wersji, wykrywa obsługiwanych agentów i umiejętności, wyjaśnia każdą ścieżkę, którą odczyta, pyta raz przed włączeniem haków przeznaczonych tylko do obserwacji i otwiera lokalny UI Na [http://127.0.0.1:4317](http://127.0.0.1:4317). Dane wykonawcze pozostają poniżej `~/.skill-runtime` chyba że wyraźnie skonfigurujesz eksport.

Możesz [sprawdź instalatora](scripts/install.sh) przed uruchomieniem.

### Zobacz swój pierwszy występ na żywo SkillRun

1. Zaakceptuj opcjonalne otwarcie awaryjne Hook skonfigurować, gdy instalator o to poprosi.
2. Uruchom ponownie Agenta i rozpocznij nowe zadanie. W Codex, przejrzyj zarządzane polecenia w `/hooks` Pierwszy; istniejące zadania nie są ładowane na gorąco HookS.
3. Użyj umiejętności normalnie, a następnie potwierdź integrację i otwórz plik UI:

```bash
skill-runtime doctor
skill-runtime status
```

Integracja jest **na żywo** dopiero po odebraniu przez moduł zbierający prawdziwego zdarzenia wykonawczego. Skonfigurowany, ale niezaobserwowany Hook jest **Oczekuje** — nigdy nie jest przedstawiany jako żywy dowód. Otwarte [http://127.0.0.1:4317](http://127.0.0.1:4317)lub zobacz [Przewodnik dla początkujących](docs/getting-started.md) aby uzyskać instrukcje dotyczące konkretnego agenta i rozwiązywać problemy.

Aby uruchomić bezpośrednio ze źródła realizacji transakcji:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Powierzchnia produktu | Co odpowiada |
|---|---|
| Runtime Overview | Który SkillRuns potrzebujesz uwagi? |
| Kontrola zachowania umiejętności | Które instrukcje możliwe do sprawdzenia zostały spełnione, wymagają przeglądu lub nie mogą zostać ocenione? |
| Co się właściwie wydarzyło | Jakie instrukcje, zasoby, narzędzia, artefakty i wyniki zaobserwowano? |
| First Observable Boundary | W którym miejscu po raz pierwszy brakuje dowodów specyficznych dla danej serii lub zawodzą one? |
| Skill Run Panorama | W jaki sposób prośba, aktywacja, zasoby, narzędzia, artefakty i wynik połączyły się? |
| Evidence Inspector | Jakie źródło, klasa, podstawa i możliwości adaptera potwierdzają to twierdzenie? |
| Porównywać | Czy różnica ma charakter behawioralny, czy tylko różnica w obserwowalności? |
| Inferred Analysis | Jakie wyjaśnienie oparte na dowodach lub jakie następne badanie jest wiarygodne? |
| Ustawienia / Lekarz | Co jest odczytywane, przechowywane, eksportowane, oczekujące i weryfikowane? |

## Jak to działa

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime obserwuje przepływ pracy, z którego już korzystasz. Wersjonowane adaptery przekształcają zdarzenia natywne dla agentów w stabilny cykl życia umiejętności, podczas gdy surowe koperty źródłowe, znormalizowane zdarzenia, relacje i wnioski pozostają oddzielne. Silnik diagnostyczny sprawdza wyraźne ograniczenia Umiejętności w oparciu o te dowody, identyfikuje najwcześniejsze zauważalne odchylenie i oddziela systemowe martwe punkty adaptera od wyników specyficznych dla przebiegu. Nie wymyśla intencji modelowej ani skuteczności przyczynowej.

| Źródło danych | Rola | Świeżość | UI etykieta |
|---|---|---|---|
| Oficjalne haki agenta / wtyczki / SDK wydarzenia | Podstawowy cykl życia, narzędzie, podagent i dowód końcowy | Na żywo | `Official hook` / `Native telemetry` |
| Pliki umiejętności i obserwowalne wyniki w obszarze roboczym | Definicja, zasób, plik, artefakt i dowód testowy | Migawka na żywo / indeksowana | `Observed` |
| Transkrypcje sesji | Awaryjna kompatybilność, gdy Agent nie udostępnia wystarczającego czasu działania API | Prawie żywe lub historyczne | `Transcript fallback` |
| OTLP i obsługiwane eksporty śledzenia | Interoperacyjność i znaczenie historyczne | Eksport na żywo / import wsadowy | Pokazano profil źródłowy |
| Korelacja deterministyczna | Łączy zdarzenia z a SkillRun bez zmiany faktów źródłowych | Przy spożyciu | `Derived` |
| Pomoc semantyczna | Tylko wyjaśnienia i sugestie dotyczące dochodzenia | Na żądanie | `Inferred` |

Obsługiwane adaptery innych firm są wersjonowane niezależnie:

| Agent | Integracja pierwotna | Powrót | Widoczność aktywacji |
|---|---|---|---|
| Codex | Oficjalne polecenie HookS | Import sesji | Wyraźna aktywacja po ujawnieniu przez Hook wydarzenie |
| Claude Code | Urzędnik HookS | Import sesji | Wyraźne narzędzie umiejętności i dowód polecenia ukośnika, jeśli są ujawnione |
| Qoder | Oficjalne polecenie HookS | Lokalne rekordy | Wyraźna aktywacja po ujawnieniu przez narzędzie Umiejętności |
| OpenCode | Globalna wtyczka przeznaczona wyłącznie do obserwacji | Lokalne rekordy | Wywołania zwrotne narzędzi umiejętności, jeśli są ujawnione |

Dokładne limity możliwości są udokumentowane w pliku [macierz możliwości adaptera](docs/adapter-capability-matrix.md). Nieobsługiwane i niezaobserwowane etapy pozostają widoczne, zamiast zamieniać się w awarie.

## Problem

Zainstalowanie umiejętności nie oznacza, że ​​agent ją odkrył. Odkrycie nie dowodzi aktywacji. Aktywacja nie oznacza, że ​​załadowano pełne instrukcje i zasoby. Załadowanie instrukcji nie stanowi dowodu, że Agent ich przestrzegał. Wykonanie nie dowodzi, że Umiejętność poprawiła wynik.

Dziś te niepowodzenia często milczą. Deweloperzy pozostają z pytaniem:

- Czy Umiejętność była dostępna dla tego agenta?
- Czy zostało aktywowane dla tego żądania?
- Jakie instrukcje, odniesienia, skrypty i zasoby zostały załadowane?
- Które wyraźne wymagania dotyczące umiejętności zostały spełnione, pominięte lub niemożliwe do oceny?
- Które narzędzia, MCP w grę wchodziły połączenia telefoniczne, podagenci, pliki i artefakty?
- W którym miejscu uruchomienie zakończyło się niepowodzeniem, ponowieniem próby lub utratą kontekstu?
- Czy umiejętność pomogła, czy tylko zwiększyła koszty i opóźnienia?

## Diagnoza specyficzna dla umiejętności

Podstawowym obiektem diagnostycznym jest a `SkillRun`, a nie całą sesję Agenta:

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

The UI utrzymuje porządek cyklu życia, typowanie i ocenę dowodów. Brak danych telemetrycznych aktywacji oznacza „nie zaobserwowano” lub „nieobsługiwany”; nie oznacza to jednak, że Agent zdecydowanie pominął Umiejętność.

## Dyscyplina dowodowa

The UI nigdy nie wolno przedstawiać wnioskowania jako faktu w czasie wykonywania:

- **Zaobserwowane** — wyraźnie obecne w zdarzeniu źródłowym lub pliku.
- **Pochodne** – deterministycznie powiązane z zaobserwowanymi dowodami.
- **Wywnioskowanie** — wiarygodne wyjaśnienie z niepewnością.
- **Eksperymentalny** – efekt mierzony poprzez kontrolowaną ocenę w parach.

Pojedynczy ślad może obsługiwać przypisanie wykonania. Nie może wykazać skuteczności przyczynowej. Twierdzenia takie jak „zwiększenie wskaźnika sukcesu dzięki tej umiejętności” wymagają ponownej oceny z umiejętnością/bez umiejętności.

## Zasady produktu

- Domyślnie prywatny, z wdrożeniem lokalnym, hybrydowym i połączonym z zespołem.
- Obserwacja tylko do odczytu; nigdy nie przejmuj pętli agenta.
- Brak modelowego serwera proxy i obowiązkowej usługi w chmurze.
- W produkcie domyślnym nie ma blokowania, bramki zatwierdzającej ani egzekwowania zasad.
- Wyraźne pochodzenie i klasyfikacja dowodów.
- Stopniowe ujawnianie informacji: najpierw prosta narracja, surowe wydarzenia na żądanie.
- Oparta na adapterach obsługa zmiany formatów transkrypcji agentów.

## Aktualny zakres

Środowisko wykonawcze obsługuje Codex, Claude Code, Qoder, I OpenCode poprzez niezależne, wersjonowane adaptery i zapewnia:

- zainstalowany Odkrywanie i weryfikacja umiejętności;
- urzędnik czasu rzeczywistego Hook/kolekcja wtyczek plus oznaczona sesja rezerwowa;
- Aktywacja umiejętności, ładowanie zasobów i harmonogramy wywoływania narzędzi;
- subagent, MCPrelacje między plikami i artefaktami;
- czas trwania, token, błąd, ponowna próba i podsumowania stanu, jeśli są dostępne;
- konserwatywne ograniczenia zachowań wydobyte z prądu `SKILL.md`;
- oparte na dowodach kontrole zgodności, weryfikacja i kontrole pod kątem błędów w czasie wykonywania;
- konkretne instrukcje, zasoby, narzędzia, artefakty i inwentarze wyników;
- Runtime Overview z limitami zasięgu systemowego oddzielonymi od ustaleń z przebiegu;
- diagnoza pierwszej granicy;
- panoramiczny DAG, harmonogram wydarzeń i inspektor dowodów;
- porównanie tego samego agenta i wielu agentów uwzględniające możliwości;
- oddzielny Inferred Analysis powierzchnia, która nie może przepisać faktów wykonawczych;
- wyrazić zgodę OTLP/HTTP eksport i obsługiwany import śledzenia obserwacji.

MVP **nie** obejmuje rynku, środowiska wykonawczego agenta uniwersalnego, egzekwowania zabezpieczeń, ładu korporacyjnego ani roszczeń o skutku przyczynowym.

## Szczegółowa instalacja

Aby uzyskać najkrótszą obsługiwaną ścieżkę, użyj jednowierszowego instalatora wersji [Szybki start](#quick-start). Pełny przebieg pierwszego uruchomienia, kroki ponownego uruchomienia/zaufania specyficzne dla agenta, zachowanie prywatności i rozwiązywanie problemów są dostępne w pliku [Przewodnik dla początkujących](docs/getting-started.md).

W przypadku programowania podstawowa implementacja nie ma innych zależności w czasie wykonywania Python 3,9+. Z katalogu głównego repozytorium:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Następnie otwórz [http://127.0.0.1:4317](http://127.0.0.1:4317).

Jednorazowy `install` rozkaz:

1. skanuje lokalizacje umiejętności użytkownika, projektu i wtyczki buforowanej;
2. wykrywa Codex, Claude Code, Qoder, I OpenCode bez zmiany ich konfiguracji;
3. pokazuje, które ścieżki Agenta i Umiejętności zostaną odczytane;
4. pobiera zweryfikowanego przez sumę kontrolną natywnego nadawcę o niskim uruchomieniu dla bieżącej platformy, powracając do lokalnej kompilacji C i na koniec Python nadawcy i podczas instalacji wstępnie podgrzewa świeży natywny plik binarny;
5. tworzy `~/.skill-runtime/config.json` i lokalny SQLite indeks.

Pierwszy indeks importuje istniejące kompatybilne sesje agentów. Na stacji roboczej o długiej żywotności może to potrwać dłużej niż nowa instalacja; późniejsze starty są przyrostowe i UI staje się dostępny po uruchomieniu odświeżania w tle.

Kiedy jest uruchamiany interaktywnie, pyta raz przed dodaniem haków agenta typu Fail-Open. `--no-hooks` utrzymuje import transkrypcji jako etykietę zastępczą, podczas gdy `--enable-hooks` rejestruje wyraźną zgodę i instaluje tylko wpisy zarządzane. Dla Codex, otwarty `/hooks` po instalacji przejrzyj dokładnie zarządzane polecenia i zaufaj im. Codex celowo wymaga tego wyraźnego przeglądu pod kątem haków dodanych poza konfiguracją zarządzanego przedsiębiorstwa. Rozpocznij nowe Codex zadanie/sesja po zaufaniu Hooks, a następnie uruchom:

```bash
.venv/bin/skill-runtime doctor
```

Qoder masa Hook konfigurację przy uruchomieniu, więc uruchom ponownie Qoder po pierwszej instalacji. OpenCode odkrywa zarządzaną wtyczkę służącą tylko do obserwacji w swoim globalnym katalogu wtyczek; uruchom ponownie OpenCode jeśli bieżący proces poprzedza instalację. Żadna integracja nie odczytuje ani nie zmienia żądań modelu.

Integracja staje się **Live** dopiero po otrzymaniu przez bazę danych rzeczywistego `official_hook` wydarzenie. Jedynie pisanie `~/.codex/hooks.json` jest wyświetlany jako **Oczekujący**, nigdy nie połączony. `start` uruchamia Kolektora, obserwatora rezerwowego transkrypcji, pracownika retencji, SQLite przechowuj i żyj UI jako zarządzany proces w tle. Żadne żądanie modelu nie jest przesyłane przez serwer proxy.

Polecenia cyklu życia:

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

`uninstall` usuwa tylko zarządzane Hook wpisy i Skill Runtime-własne pliki. Bez `--keep-data`, wymaga interaktywnego potwierdzenia (lub `--yes`) przed usunięciem `~/.skill-runtime`; Sesje agentów i źródła umiejętności nigdy nie są usuwane.

Aby indeksować i wyświetlać osobno:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Zaimportuj istniejący eksport śledzenia z głównego systemu obserwowalności:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Wersjonowane profile importu obecnie rozpoznają OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, I Datadog JSON kształty. Tworzą tylko tzw SkillRun gdy źródło zawiera wyraźną semantykę Umiejętności; Ogólne nazwy zakresów nie są traktowane jako dowód aktywacji.

Eksportuj znormalizowane dowody środowiska wykonawczego specyficzne dla umiejętności do dowolnego OTLP/HTTP punkt końcowy śledzenia:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Eksport jest wyłączony, chyba że punkt końcowy jest jawnie skonfigurowany. Punkty kontrolne, stan ponownych prób i stan miejsca docelowego są wyświetlane w Ustawieniach. Surowe podpowiedzi, ładunki narzędzi, dane uwierzytelniające i zawartość zasobów umiejętności nie są eksportowane. W przypadku uwierzytelnionego eksportu w tle podaj standard `OTEL_EXPORTER_OTLP_HEADERS` wcześniej w środowisku `skill-runtime start`; nagłówki nigdy nie są zapisywane Skill Runtime argumenty konfiguracyjne lub procesowe.

## Wysyłaj dowody działania na żywo

`skill-runtime start` obejmuje lokalnego kolekcjonera. Natywne adaptery telemetryczne, oficjalne haki, lekkie haki typu Fail-Open i SDK integracje mogą dołączać pojedyncze zdarzenie lub ograniczoną partię `POST /api/events`:

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

Punkt końcowy redaguje typowe poświadczenia przed utrwaleniem, deduplikuje według `event_id`, zachowuje oddzielną, zredagowaną, surową kopertę i zwraca wynik `skill_run_ids`. `GET /api/collector/schema` udostępnia obsługiwane słownictwo i tryby gromadzenia zdarzeń. The UI słucha `/api/stream` przy użyciu SSE, z odpytywaniem tylko jako rezerwowym ponownym połączeniem.

Wskaźnik źródła odróżnia podstawowe dowody środowiska wykonawczego od `Transcript fallback` i importowane ślady. Sam punkt końcowy modułu Collector nie żąda natywnej telemetrii: każdy producent musi zadeklarować, czy jego zdarzenie pochodzi z natywnej telemetrii, oficjalnego haka, lekkiego haka czy SDK.

### Opcjonalne haki agenta

Najpierw sprawdź dokładne ścieżki i zdarzenia. To polecenie jest tylko do odczytu:

```bash
.venv/bin/skill-runtime setup
```

Hook instalacja wymaga wyraźnej flagi:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Instalator tworzy kopię zapasową konfiguracji Agenta, zachowuje istniejące zaczepy i dodaje tylko wpisy zawierające plik Skill Runtime znacznik zarządzania. Adapter haka przechowuje minimalne pola cyklu życia zamiast pełnych podpowiedzi lub ładunków narzędzi. W przypadku ukończonych wywołań narzędzi wyodrębnia tylko dokładne `SKILL.md`, standardowy zasób umiejętności i zmienione ścieżki plików w pamięci; surowe polecenia, treści poprawek, podpowiedzi i dane wyjściowe narzędzi są odrzucane przed utrwaleniem. Gdy środowisko wykonawcze jest aktywne, uprawnienia są ograniczone Unix gniazdo to szybka ścieżka; opcjonalny natywny nadawca unika Python uruchomienie. Gdy środowisko wykonawcze nie jest aktywne, samodzielna ścieżka otwierania awaryjnego dołącza zredagowane dowody `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` odtwarza tę kolejkę z deduplikacją identyfikatora zdarzenia.

Codex wydarzenia wykorzystują swojego urzędnika Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, I `Stop`). Codex obecnie wykonuje zaczepy poleceń synchronicznie, więc Skill Runtime używa lokalnego Unix gniazdo/natywny nadawca z ograniczonym limitem czasu. Wszelkie niepowodzenia w dostawie są przełykane i umieszczane w kolejce; nigdy nie zmienia decyzji Agenta. Zobacz [oficjalna dokumentacja Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Usuń tylko zarządzane wpisy za pomocą:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Serwer łączy się z `127.0.0.1` domyślnie. Komunikaty z pełną transkrypcją i ładunki narzędzi nie są kopiowane do indeksu. Wspólne tajne wzorce są redagowane przed utrwaleniem znormalizowanych podsumowań.

Uruchom wolny od zależności zestaw testów za pomocą:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Inżynieria wydania

GitHub Działania biegną Python Testy 3.9–3.13, walidacja JavaScript, kompilacja natywnych nadawców i prawdziwy test dymu instalacji/startu/doktora/zatrzymania/odinstalowania. A `v*` tag tworzy pakiety koła/sdist plus chronione sumą kontrolną Linux I macOS rodzimych nadawców. Instalator CLI pobiera pasujący zasób wersji, więc użytkownicy końcowi nie potrzebują kompilatora.

Uruchom pierwszy eksperyment diagnostyczny powiązany z produktem:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Wprowadza błędy w dowodach dotyczących cyklu życia, wyraźne awarie, niekompletne przebiegi i niezweryfikowane wyniki, a następnie ocenia ten sam deterministyczny silnik diagnostyczny, którego używa API I UI. Zobacz [Plan eksperymentu PAI-DSW](docs/pai-dsw-experiment-plan.md) dla drabinki eksperymentu, testów braku zakłóceń i umowy odtwarzalności.

Po zbudowaniu koła uruchom izolowany pakiet dymu cyklu życia za pomocą:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Instaluje się w tymczasowym środowisku wirtualnym i tymczasowym domu, wykonuje pełny lokalny cykl życia bez włączania przechwytów i weryfikuje brak zakłóceń w konfiguracji projektu i Agenta.

## Projektowanie produktu oparte na eksperymentach

Zachowanie produktu podlega czterem ograniczeniom wynikającym z eksperymentów: dowody przed wnioskami, pierwsza obserwowalna granica przed dotkliwością, relacje typowane przed płaskimi logami i rekonstrukcja deterministyczna przed pomocą probabilistyczną.

Powtarzalne dowody i ich ograniczenia są utrzymane w [raport z eksperymentu](docs/experiment-results-2026-07-29.md). Wyniki ograniczone obejmują:

- 2400/2400 zdarzeń modułu zbierającego zaakceptowanych bez mutacji wejścia/wyjścia;
- 14/14 deterministyczne diagnozy korpusu usterek bez nieuzasadnionych twierdzeń przyczynowych;
- reprezentacja diagnozy relacyjnej z dokładnością 13/14 i F1 0,963, podczas gdy pobieranie płaskiego cyklu życia osiągnęło dokładność 1/14 i F1 0,080;
- bezpieczny dla prywatności, prowadzony w czasie rzeczywistym audyt, który wyraźnie nie nadaje się do potwierdzania oświadczeń dotyczących wpływu produktu, ponieważ brakuje zweryfikowanych wyników, zrównoważonego zasięgu między agentami i ludzkich etykiet.

Wyniki te potwierdzają mechanizmy i wybory dotyczące reprezentacji, a nie uogólnienie wdrożenia czy korzyści dla ludzi. Badania prawdziwego drugiego agenta, międzyplatformowe opóźnienia ogona, kalibracja rzeczywistych błędów i badania diagnozy uczestników pozostają otwartymi lukami w dowodach.

Kierunek badań jest również osadzony w sąsiednich pracach podstawowych: [SkillsBench](https://arxiv.org/abs/2602.12670) I [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motywować do diagnozy, ponieważ efekty Umiejętności są różne i mogą ulec regresowi; [Harness-Bench](https://arxiv.org/abs/2605.27922) motywuje do porównań między agentami uwzględniających możliwości; i [badanie pochodzenia wykonania](https://arxiv.org/abs/2606.04990) motywuje wpisane relacje dowodowe, śledzenie pochodzenia i infrastrukturę audytu uwzględniającą prywatność.

## Dokumentacja

| Zacznij tutaj | Zamiar |
|---|---|
| [Getting Started](docs/getting-started.md) | Zainstaluj, podłącz agenta, zweryfikuj dowody na żywo i rozwiąż problemy |
| [Architektura](docs/architecture.md) | Potok gromadzenia, granice przechowywania, silnik dowodów i model zaufania |
| [Macierz możliwości adaptera](docs/adapter-capability-matrix.md) | Dokładne sygnały i ograniczenia według agenta/wersji |
| [Konfiguracja platformy obserwowalności](docs/observability-platform-setup.md) | Połącz platformy kompatybilne z OTLP i importuj obsługiwane ślady |
| [Model zdarzeń środowiska wykonawczego](docs/runtime-event-model.md) | Stabilne słownictwo dotyczące zdarzeń, pochodzenie, relacje i oceny dowodów |
| [Architektura informacji interfejsu użytkownika](docs/ui-information-architecture.md) | Przegląd, pierwsza granica, Panorama, Inspektor, Porównaj i Inferred Analysis |
| [Dziennik zmian](CHANGELOG.md) | Wersjonowane zmiany widoczne dla użytkownika |
| [Informacje o wydaniu wersji 0.3.0](docs/releases/v0.3.0.md) | Wskazówki dotyczące aktualizacji, najważniejsze informacje i znane limity |

Referencje dotyczące produktów i badań: [definicja produktu](docs/product-definition.md), [Specyfikacja MVP](docs/mvp-specification.md), [obserwowalność interoperacyjność](docs/observability-interoperability.md), [wyniki eksperymentu](docs/experiment-results-2026-07-29.md), oraz [program badawczy](docs/research-paper-agenda.md).

## Społeczność i zarządzanie

- Czytać [Wkład](CONTRIBUTING.md) przed zmianą semantyki dowodów, adapterów lub zachowania produktu.
- Postępuj zgodnie z [Kodeks postępowania](CODE_OF_CONDUCT.md) we wszystkich przestrzeniach projektowych.
- Zgłaszaj luki w zabezpieczeniach prywatnie za pośrednictwem [Polityka bezpieczeństwa](SECURITY.md), a nie kwestia publiczna.
- Użyj strukturalnego [narzędzie do śledzenia problemów](https://github.com/hellogxp/skill-runtime-intelligence/issues) dla powtarzalnych błędów i propozycji funkcji o określonym zakresie. Nigdy nie dołączaj prywatnych baz danych środowiska wykonawczego ani transkrypcji sesji.

## Plan działania

1. **wersja 0.3.0 — Następna wersja:** sprawdzalne ograniczenia zachowania umiejętności, konkretna aktywność w czasie wykonywania, ocena oparta na dowodach, diagnoza zasięgu systemowego oraz istniejący przepływ pracy Panorama i porównanie na żywo.
2. **Następnie — Wzmocnienie adapterów i diagnostyki:** szersze pokrycie agentów/wersji, kalibracja rzeczywistych błędów, weryfikacja opóźnień między platformami i badania diagnostyczne uczestników.
3. **Później — Ocena efektu:** kontrolowana ocena parowana z umiejętnością/bez umiejętności, wyraźnie oddzielona od diagnozy jednorazowej.

## Stan projektu

Bieżące cele drzewa źródłowego `v0.3.0`; użyj powyższej plakietki wydania, aby zidentyfikować najnowszą opublikowaną wersję. Środowisko wykonawcze obejmuje sprawdzalne ograniczenia zachowania umiejętności, konkretne podsumowania działań, inwentaryzację zainstalowanej definicji, oficjalne informacje oparte na zgodzie Hook adaptery do Codex, Claude Code, I Qoder, tylko obserwacja OpenCode wtyczka, oznaczona transkrypcja zastępcza, atrybucja w zakresie aktywnym, dokładne ścieżki plików/artefaktów, redakcja, oddzielne warstwy źródła/relacji/wnioskowania, SQLite przechowywanie, przechowywanie, diagnoza deterministyczna, na żywo UIoraz porównanie między różnymi agentami. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, I Datadog eksport może być importowany; znormalizowane dowody można eksportować na żywo po wyrażeniu zgody OTLP/HTTP.

Odkrycie kandydata w modelu, powody selekcji wewnętrznej modelu, skuteczność semantyczna i twierdzenia o wyniku przyczynowym pozostają wyraźnie nie poparte, chyba że źródło lub kontrolowany eksperyment dostarczy takich dowodów.
