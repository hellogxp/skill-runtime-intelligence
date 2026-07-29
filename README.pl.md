# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
**Polski** · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->


> Zdiagnozuj, gdzie po raz pierwszy przebiegała umiejętność agenta, i sprawdź dowody
> za każdym wnioskiem.

Agent Skill Runtime Intelligenceto system dowodowy i diagnostyczny w trybie tylko do odczytu dla Agent Skills. Łączy definicje umiejętności, oficjalne zdarzenia wykonawcze agenta, zaimportowane ślady, powrót do sesji i obserwowalne wyniki obszaru roboczego w oparty na dowodachSkill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Szybki start

Zainstaluj wersję autonomiczną z prywatnego repozytorium z uwierzytelnionym plikiemGitInterfejs wiersza polecenia koncentratora:

```bash
install_tmp="$(mktemp -d)"
gh release download --repo hellogxp/skill-runtime-intelligence \
  --pattern install.sh --dir "$install_tmp"
sh "$install_tmp/install.sh"
skill-runtime start
```

Lub uruchom bezpośrednio z kasy źródłowej:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Otwarte[http://127.0.0.1:4317](http://127.0.0.1:4317). DlaCodex, przejrzyj i zaufaj zarządzanym poleceniom w`/hooks`, rozpocznij jedną nową turę Agenta, a następnie sprawdź:

```bash
.venv/bin/skill-runtime doctor
```

Integracja zostaje **zweryfikowana** dopiero po odebraniu prawdziwego oficjalnego zdarzenia haka. Skonfigurowany hak jest pokazywany jako **Oczekujący**, nigdy jako żywy dowód.

| Powierzchnia produktu | Co odpowiada |
|---|---|
| Przegląd środowiska wykonawczego | KtórySkillRunspotrzebujesz uwagi? |
| Pierwsza obserwowalna granica | Gdzie po raz pierwszy zaginęły dowody lub zostały one zawiedzione? |
| Skill Run Panorama | W jaki sposób prośba, aktywacja, zasoby, narzędzia, artefakty i wynik połączyły się? |
| Inspektor ds. dowodów | Jakie źródło, klasa, podstawa i możliwości adaptera potwierdzają to twierdzenie? |
| Porównywać | Czy różnica ma charakter behawioralny, czy tylko różnica w obserwowalności? |
| Ustawienia / Lekarz | Co jest odczytywane, przechowywane, eksportowane, oczekujące i weryfikowane? |

## Problem

Zainstalowanie umiejętności nie oznacza, że ​​agent ją odkrył. Odkrycie nie dowodzi aktywacji. Aktywacja nie oznacza, że ​​załadowano pełne instrukcje i zasoby. Wykonanie nie dowodzi, że Umiejętność poprawiła wynik.

Dziś te niepowodzenia często milczą. Deweloperzy pozostają z pytaniem:

- Czy Umiejętność była dostępna dla tego agenta?
- Czy zostało aktywowane dla tego żądania?
- Jakie instrukcje, odniesienia, skrypty i zasoby zostały załadowane?
- Które narzędzia,MCPw grę wchodziły połączenia telefoniczne, podagenci, pliki i artefakty?
- W którym miejscu uruchomienie zakończyło się niepowodzeniem, ponowieniem próby lub utratą kontekstu?
- Czy umiejętność pomogła, czy tylko zwiększyła koszty i opóźnienia?

## Kierunek produktu

Pierwszy produkt to **Skill Run Panorama**:

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

Panorama budowana jest na podstawie rzeczywistych sygnałów, a nie samoopisu modelu:

| Źródło | Przykłady | Dowód |
|---|---|---|
| Pliki umiejętności | metadane, instrukcje, skrypty, referencje, zasoby | Zauważony |
| Wydarzenia w czasie wykonywania | Wezwania umiejętności, wywołania narzędzi, podagenci, awarie, czas trwania | Zauważony |
| Transkrypcje sesji | podpowiedzi, komunikaty, wejścia i wyjścia narzędzi, zamawianie | Zauważony |
| Wyniki obszaru roboczego | zmiany plików,Gitdiff, raporty, wygenerowane artefakty | Zauważony |
| Korelacja | relacje między zdarzeniami, zasobami i wynikami | Pochodne lub wywnioskowane |

## Dyscyplina dowodowa

TheUInigdy nie wolno przedstawiać wnioskowania jako faktu w czasie wykonywania:

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

## Zakres początkowy

MVP wspieraClaude CodeICodexi zapewnia:

- zainstalowany Odkrywanie i weryfikacja umiejętności;
- import sesji i lokalna obserwacja na żywo, jeśli jest obsługiwana;
- Aktywacja umiejętności, ładowanie zasobów i harmonogramy wywoływania narzędzi;
- subagent,MCPrelacje między plikami i artefaktami;
- czas trwania, token, błąd, ponowna próba i podsumowania stanu, jeśli są dostępne;
- lista uruchomień, panoramiczny DAG, oś czasu wydarzenia i inspektor węzłów.

MVP **nie** obejmuje rynku, środowiska wykonawczego agenta uniwersalnego, egzekwowania zabezpieczeń, ładu korporacyjnego ani roszczeń o skutku przyczynowym.

## Szczegółowa instalacja

Implementacja podstawowa nie ma poza nią żadnych zależności w czasie wykonywaniaPython3,9+. Z katalogu głównego repozytorium:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Następnie otwórz[http://127.0.0.1:4317](http://127.0.0.1:4317).

Jednorazowy`install`rozkaz:

1. skanuje lokalizacje umiejętności użytkownika, projektu i wtyczki buforowanej;
2. wykrywaCodexIClaude Codebez zmiany ich konfiguracji;
3. pokazuje, które ścieżki Agenta i Umiejętności zostaną odczytane;
4. pobiera zweryfikowanego przez sumę kontrolną natywnego nadawcę o niskim uruchomieniu dla bieżącej platformy, powracając do lokalnej kompilacji C i na koniecPythonnadawcy i podczas instalacji wstępnie podgrzewa świeży natywny plik binarny;
5. tworzy`~/.skill-runtime/config.json`i lokalnySQLiteindeks.

Kiedy jest uruchamiany interaktywnie, pyta raz przed dodaniem haków agenta typu Fail-Open.`--no-hooks`utrzymuje import transkrypcji jako oznaczony jako rezerwowy, podczas gdy`--enable-hooks`rejestruje wyraźną zgodę i instaluje tylko wpisy zarządzane. DlaCodex, otwarty`/hooks`po instalacji przejrzyj dokładnie zarządzane polecenia i zaufaj im.Codexcelowo wymaga tego wyraźnego przeglądu pod kątem haków dodanych poza konfiguracją zarządzanego przedsiębiorstwa. Rozpocznij nową turę Agenta, a następnie wykonaj:

```bash
.venv/bin/skill-runtime doctor
```

Integracja staje się **Live** dopiero po otrzymaniu przez bazę danych rzeczywistego`official_hook`wydarzenie. Jedynie pisanie`~/.codex/hooks.json`jest wyświetlany jako **Oczekujący**, nigdy nie połączony.`start`uruchamia Kolektora, obserwatora rezerwowego transkrypcji, pracownika retencji,SQLiteprzechowuj i żyjUIjako zarządzany proces w tle. Żadne żądanie modelu nie jest przesyłane przez serwer proxy.

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

`uninstall`usuwa tylko zarządzane wpisy Hook iSkill Runtime-własne pliki. Bez`--keep-data`, wymaga interaktywnego potwierdzenia (lub`--yes`) przed usunięciem`~/.skill-runtime`; Sesje agentów i źródła umiejętności nigdy nie są usuwane.

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

Wersjonowane profile importu obecnie rozpoznają OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, IDatadog JSONkształty. Tworzą tylko tzwSkillRungdy źródło zawiera wyraźną semantykę Umiejętności; Ogólne nazwy zakresów nie są traktowane jako dowód aktywacji.

Eksportuj znormalizowane dowody środowiska wykonawczego specyficzne dla umiejętności do dowolnegoOTLP/HTTPpunkt końcowy śledzenia:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Eksport jest wyłączony, chyba że punkt końcowy jest jawnie skonfigurowany. Punkty kontrolne, stan ponownych prób i stan miejsca docelowego są wyświetlane w Ustawieniach. Surowe podpowiedzi, ładunki narzędzi, dane uwierzytelniające i zawartość zasobów umiejętności nie są eksportowane. W przypadku uwierzytelnionego eksportu w tle podaj standard`OTEL_EXPORTER_OTLP_HEADERS`wcześniej w środowisku`skill-runtime start`; nagłówki nigdy nie są zapisywaneSkill Runtimeargumenty konfiguracyjne lub procesowe.

## Wysyłaj dowody działania na żywo

`skill-runtime start`obejmuje lokalnego kolekcjonera. Natywne adaptery telemetryczne, oficjalne haki, lekkie haki typu Fail-Open iSDKintegracje mogą dołączać pojedyncze zdarzenie lub ograniczoną partię`POST /api/events`:

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

Punkt końcowy redaguje typowe poświadczenia przed utrwaleniem, deduplikuje według`event_id`, zachowuje oddzielną, zredagowaną, surową kopertę i zwraca wynik`skill_run_ids`.`GET /api/collector/schema`udostępnia obsługiwane słownictwo i tryby gromadzenia zdarzeń. TheUIsłucha`/api/stream`przy użyciu SSE, z odpytywaniem tylko jako rezerwowym ponownym połączeniem.

Wskaźnik źródła odróżnia podstawowe dowody środowiska wykonawczego od`Transcript fallback`i importowane ślady. Sam punkt końcowy modułu Collector nie żąda natywnej telemetrii: każdy producent musi zadeklarować, czy jego zdarzenie pochodzi z natywnej telemetrii, oficjalnego haka, lekkiego haka czySDK.

### Opcjonalne haki agenta

Najpierw sprawdź dokładne ścieżki i zdarzenia. To polecenie jest tylko do odczytu:

```bash
.venv/bin/skill-runtime setup
```

Instalacja haka wymaga wyraźnej flagi:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Instalator tworzy kopię zapasową konfiguracji Agenta, zachowuje istniejące zaczepy i dodaje tylko wpisy zawierające plikSkill Runtimeznacznik zarządzania. Adapter haka przechowuje minimalne pola cyklu życia zamiast pełnych podpowiedzi lub ładunków narzędzi. Gdy środowisko wykonawcze jest aktywne, uprawnienia są ograniczoneUnixgniazdo to szybka ścieżka; opcjonalny natywny nadawca unikaPythonuruchomienie. Gdy środowisko wykonawcze nie jest aktywne, samodzielna ścieżka otwierania awaryjnego dołącza zredagowane dowody`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`odtwarza tę kolejkę z deduplikacją identyfikatora zdarzenia.

Codexwydarzenia korzystają z oficjalnego hakaAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, I`Stop`).Codexobecnie wykonuje zaczepy poleceń synchronicznie, więcSkill Runtimeużywa lokalnegoUnixgniazdo/natywny nadawca z ograniczonym limitem czasu. Wszelkie niepowodzenia w dostawie są przełykane i umieszczane w kolejce; nigdy nie zmienia decyzji Agenta. Zobacz[oficjalna dokumentacja Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Usuń tylko zarządzane wpisy za pomocą:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Serwer łączy się z`127.0.0.1`domyślnie. Komunikaty z pełną transkrypcją i ładunki narzędzi nie są kopiowane do indeksu. Wspólne tajne wzorce są redagowane przed utrwaleniem znormalizowanych podsumowań.

Uruchom wolny od zależności zestaw testów za pomocą:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Inżynieria wydania

GitDziała Centrum AkcjePythonTesty 3.9–3.13, walidacja JavaScript, kompilacja natywnych nadawców i prawdziwy test dymu instalacji/startu/doktora/zatrzymania/odinstalowania. A`v*`tag tworzy pakiety Wheel/sdist oraz natywnych nadawców chronionych sumą kontrolną dla systemów Linux i macOS. Instalator CLI pobiera pasujący zasób wersji, więc użytkownicy końcowi nie potrzebują kompilatora.

Uruchom pierwszy eksperyment diagnostyczny powiązany z produktem:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Wprowadza błędy w dowodach dotyczących cyklu życia, wyraźne awarie, niekompletne przebiegi i niezweryfikowane wyniki, a następnie ocenia ten sam deterministyczny silnik diagnostyczny, którego używaAPIIUI. Zobacz[Plan eksperymentu PAI-DSW](docs/pai-dsw-experiment-plan.md)dla drabinki eksperymentu, testów braku zakłóceń i umowy odtwarzalności.

Po zbudowaniu koła uruchom izolowany pakiet dymu cyklu życia za pomocą:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Instaluje się w tymczasowym środowisku wirtualnym i tymczasowym domu, wykonuje pełny lokalny cykl życia bez włączania przechwytów i weryfikuje brak zakłóceń w konfiguracji projektu i Agenta.

## Projektowanie produktu oparte na eksperymentach

Zachowanie produktu jest ograniczone przez[filozofia produktu oparta na eksperymentach](docs/experiment-driven-product-philosophy.md): dowody przed wnioskami, pierwsza obserwowalna granica przed dotkliwością, relacje typowane przed logami płaskimi i rekonstrukcja deterministyczna przed pomocą probabilistyczną.

Aktualne, powtarzalne dowody lokalne obejmują:

- Minęło 7/7 lokalnych bram eksperymentalnych;
- 2400/2400 zdarzeń modułu zbierającego zaakceptowanych bez mutacji wejścia/wyjścia;
- 14/14 deterministyczne diagnozy korpusu usterek bez nieuzasadnionych twierdzeń przyczynowych;
- reprezentacja diagnozy relacyjnej z dokładnością 13/14 i F1 0,963, podczas gdy pobieranie płaskiego cyklu życia osiągnęło dokładność 1/14 i F1 0,080;
- W przypadku materiałów badawczych z 11/11 na pierwszym miejscu znajduje się najwcześniejsza obserwowalna granica.

Wyniki te potwierdzają mechanizmy i wybory dotyczące reprezentacji, a nie uogólnienie wdrożenia czy korzyści dla ludzi. Badania prawdziwego drugiego agenta, międzyplatformowe opóźnienia ogona, kalibracja rzeczywistych błędów i badania diagnozy uczestników pozostają otwartymi lukami w dowodach.

Kierunek badań jest również osadzony w sąsiednich pracach podstawowych:[SkillsBench](https://arxiv.org/abs/2602.12670)I[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motywować do diagnozy, ponieważ efekty Umiejętności są różne i mogą ulec regresowi;[Harness-Bench](https://arxiv.org/abs/2605.27922)motywuje do porównań między agentami uwzględniających możliwości; i[badanie pochodzenia wykonania](https://arxiv.org/abs/2606.04990)motywuje wpisane relacje dowodowe, śledzenie pochodzenia i infrastrukturę audytu uwzględniającą prywatność.

## Dokumentacja

- [Definicja produktu](docs/product-definition.md)
- [Specyfikacja MVP](docs/mvp-specification.md)
- [Model zdarzeń środowiska wykonawczego](docs/runtime-event-model.md)
- [Architektura informacji interfejsu użytkownika](docs/ui-information-architecture.md)
- [Macierz możliwości adaptera](docs/adapter-capability-matrix.md)
- [Interoperacyjność obserwowalności](docs/observability-interoperability.md)
- [Konfiguracja platformy obserwowalności](docs/observability-platform-setup.md)
- [Krajobraz badawczy i konkurencyjny](docs/research-and-competitive-landscape.md)
- [Agenda publikacji naukowych](docs/research-paper-agenda.md)
- [Filozofia produktu oparta na eksperymentach](docs/experiment-driven-product-philosophy.md)
- [Wyniki eksperymentu](docs/experiment-results-2026-07-29.md)
- [Plan eksperymentu PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Plan działania

1. **v0.1 — Dowody i diagnoza w czasie wykonywania:** kolekcja na żywo,Skill Run Panorama, diagnoza pierwszej granicy, kontrola dowodów, porównanie i interoperacyjność OTLP.
2. **v0.2 — Badania dotyczące szerokości adaptera i diagnozy:** dodatkowi agenci, rzeczywiste eksperymenty między agentami i ocena uczestników.
3. **v0.3 — Ocena efektu:** kontrolowana ocena sparowana z umiejętnością/bez umiejętności, oddzielona od diagnostyki pojedynczej.

## Stan projektu

ASkillRun- możliwe jest uruchomienie pierwszego środowiska wykonawczego: inwentarz w zainstalowanej rozdzielczości,Codextranskrypcja zastępcza, oparta na zgodzieCodexIClaude Codeoficjalne adaptery hooków, przypisywanie zakresu aktywnego, dokładne ścieżki plików/artefaktów, redakcja, oddzielne warstwy źródeł/relacji/wnioskowania,SQLiteprzechowywanie, przechowywanie, porównywanie między różnymi agentami, diagnostyka deterministyczna i panorama na żywoUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, IDatadogeksport może być importowany; znormalizowane dowody można eksportować na żywo po wyrażeniu zgodyOTLP/HTTP. Obecny powtarzalny zestaw ma siedem przechodzących bramek eksperymentalnych. Odkrycie kandydata, powody selekcji wewnętrznej w modelu, skuteczność semantyczna i twierdzenia o wynikach przyczynowych pozostają wyraźnie nie poparte.
