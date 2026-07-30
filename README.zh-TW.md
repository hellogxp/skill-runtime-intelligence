# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · **繁體中文** · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-情報/行動/工作流程/ci.yml）[！ [發布](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-情報/發布/最新）[！ [執照](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)]（執照）[！ [Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> 診斷特工技能運作首先出現分歧的位置並檢查證據
> 每一個結論的背後。

Agent Skill Runtime Intelligence是一個針對代理技能的唯讀運行時證據和診斷系統。它將技能定義、官方代理程式運行時事件、導入的追蹤、會話回退和可觀察的工作區結果組合成證據分級的Skill Run Panorama。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 快速啟動

在 macOS 或 Linux 上安裝最新的獨立版本：

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

沒有克隆，Git中心帳戶，`sudo`， 或者Git需要集線器 CLI。安裝程式下載匹配的簽章發佈有效負載，驗證 SHA-256 校驗和，在啟用故障開放代理掛鉤之前詢問一次，並將所有運行時資料儲存在`~/.skill-runtime`。然後它啟動本地運行時並打開[http://127.0.0.1:4317](http://127.0.0.1:4317)。

你可以[檢查安裝程式](scripts/install.sh)在運行之前。

或直接從源結帳運行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

打開[http://127.0.0.1:4317](http://127.0.0.1:4317)。使用 Codex 時，請在
`/hooks` 查看並信任託管命令，然後建立新的 Codex 任務/工作階段（已開啟的舊任務
不會熱載入新安裝的 Hook），再進行驗證：

```bash
skill-runtime doctor
```

僅在收到真正的官方掛鉤事件後，整合才會變為**已驗證**。配置的鉤子顯示為 **Pending**，永遠不會作為即時證據。

| 產品表面 | 它回答什麼 |
|---|---|
| 運行時概述 | 哪個SkillRuns需要注意嗎？ |
| 第一個可觀察邊界 | 證據首先在哪裡遺失或失效？ |
| Skill Run Panorama | 請求、啟動、資源、工具、工件和結果如何連結？ |
| 證據檢查員 | 什麼來源、等級、基礎和適配器能力支持這一說法？ |
| 比較 | 差異是行為差異，還是只是可觀察差異？ |
| 設定/醫生 | 讀取、儲存、匯出、待處理和驗證什麼？ |

## 問題

安裝技能並不能證明代理商發現了它。發現並不證明激活。激活並不證明已載入完整的指令和資源。執行並不能證明該技能改善了結果。

如今，這些失敗往往是悄無聲息的。開發人員會問：

- 該特工可以使用該技能嗎？
- 它是否針對此請求啟動了？
- 載入了哪些指令、參考、腳本和資源？
- 哪些工具，MCP涉及調用、子代理、文件和工件嗎？
- 運行在哪裡失敗、重試或遺失上下文？
- 該技能有幫助嗎，還是只會增加成本和延遲？

## 產品方向

第一個產品是**Skill Run Panorama**：

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

全景圖是根據真實訊號建構的，而不是模型自我報告：

| 來源 | 範例 | 證據 |
|---|---|---|
| 技能檔案 | 元資料、說明、腳本、參考文獻、資產 | 觀察到 |
| 運行時事件 | 技能呼叫、工具呼叫、子代理、失敗、持續時間 | 觀察到 |
| 會議記錄 | 提示、訊息、工具輸入與輸出、排序 | 觀察到 |
| 工作空間成果 | 文件更改，Gitdiff、報表、產生的工件 | 觀察到 |
| 相關性 | 事件、資源與結果之間的關係 | 推導或推斷 |

## 證據紀律

這UI絕不能將推論呈現為運行時事實：

- **觀察到** — 明確存在於來源事件或文件中。
- **派生** — 與觀察到的證據確定性相關。
- **推論**——一個看似合理但不確定的解釋。
- **實驗性** — 以受控配對評估測量的效果。

單一追蹤可以支援執行歸因。它不能證明因果有效性。諸如「此技能提高了成功率」之類的主張需要重複進行有技能/無技能評估。

## 產品原理

- 預設是私有的，具有本地、混合和團隊連接的部署。
- 只讀觀察；永遠不要接管代理循環。
- 沒有模型代理，也沒有強制的雲端服務。
- 預設產品中沒有阻止、批准門或策略執行。
- 明確的出處和證據分級。
- 漸進式揭露：簡單敘述優先，按需提供原始事件。
- 基於適配器的支援更改代理轉錄格式。

## 初始範圍

運行時支援Codex,Claude Code,Qoder， 和OpenCode透過獨立的版本化適配器並提供：

- 安裝技能發現和驗證；
- 支援會話導入和即時本地觀察；
- 技能啟動、資源載入和工具調用時間表；
- 分代理,MCP、文件和工件關係；
- 持續時間、令牌、錯誤、重試和狀態摘要（如果可用）；
- 運行清單、全景 DAG、事件時間軸和節點檢查器。

MVP **不**包括市場、通用代理運行時、安全實施、企業治理或因果關係聲明。

## 安裝詳細

基線實作沒有運行時依賴性Python3.9+。從儲存庫根目錄：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

然後打開[http://127.0.0.1:4317](http://127.0.0.1:4317)。

一次性的`install`命令：

1. 掃描用戶、項目和快取插件技能位置；
2. 檢測到Codex,Claude Code,Qoder， 和OpenCode無需更改其配置；
3. 顯示將讀取哪些代理程式和技能路徑；
4. 下載目前平台的校驗和驗證的低啟動本機發送器，回退到本地 C 構建，最後Python發送器，並在安裝過程中預熱一次新的本機二進位；
5. 創造`~/.skill-runtime/config.json`和當地的SQLite指數。

當以互動方式運行時，它會在添加故障開放代理掛鉤之前詢問一次。`--no-hooks`將轉錄本導入保留為標記後備，同時`--enable-hooks`記錄明確同意並僅安裝託管條目。為了Codex， 打開`/hooks`安裝後，請查看確切的託管命令並信任它們。Codex有意要求對在託管企業配置之外添加的掛鉤進行明確的審查。啟動新的代理回合，然後運行：

```bash
.venv/bin/skill-runtime doctor
```

Qoder啟動時載入Hook配置，所以重新啟動Qoder第一次安裝後。OpenCode從其全域插件目錄中發現託管的僅觀察插件；重新啟動OpenCode如果目前進程早於安裝。整合都不會讀取或更改模型請求。

只有當資料庫收到真實的資料後，整合才會變成**Live**`official_hook`事件。只是寫`~/.codex/hooks.json`顯示為**待處理**，從未連線。`start`啟動收集器、成績單後備觀察者、保留工作人員，SQLite儲存和生活UI作為託管後台進程。沒有代理模型請求。

生命週期命令：

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

`uninstall`僅刪除託管 Hook 條目，且Skill Runtime- 擁有的文件。沒有`--keep-data`，它需要互動式確認（或`--yes`) 刪除前`~/.skill-runtime`;代理會話和技能來源永遠不會被刪除。

單獨索引和服務：

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

從主流可觀測系統匯入現有的追蹤導出：

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

版本化導入設定檔目前可識別 OTLP/Phoenix,Langfuse,LangSmith,W&B Weave， 和Datadog JSON形狀。他們只創造一個SkillRun當源攜帶明確的技能語意時；通用跨度名稱不被視為激活證據。

將標準化的、特定於技能的運行時證據匯出到任何OTLP/HTTP追蹤端點：

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

除非明確配置端點，否則匯出將被停用。檢查點、重試狀態和目標運作狀況顯示在「設定」中。不會匯出原始提示、工具負載、憑證和技能資源內容。對於經過身份驗證的後台導出，請提供標準`OTEL_EXPORTER_OTLP_HEADERS`在之前的環境中`skill-runtime start`;標頭永遠不會被寫入Skill Runtime配置或進程參數。

## 發送即時運行時證據

`skill-runtime start`包括當地的收藏家。本機遙測轉接器、官方掛鉤、輕量級故障開放掛鉤，以及SDK整合可以將單一事件或有界批次附加到`POST /api/events`:

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

端點在持久化之前編輯通用憑證，並透過以下方式進行重複資料刪除`event_id`，保留一個單獨的經過編輯的原始信封，並返回結果`skill_run_ids`。`GET /api/collector/schema`公開支持的事件詞彙和收集模式。這UI聽`/api/stream`使用 SSE，輪詢僅作為重新連接後備。

源指示器將主要運行時證據與`Transcript fallback`和進口痕跡。僅收集器端點不會聲明本機遙測：每個生產者都必須聲明其事件是否來自本機遙測、官方掛鉤、輕量級掛鉤或SDK。

### 可選代理掛鉤

首先檢查確切的路徑和事件。該指令是唯讀的：

```bash
.venv/bin/skill-runtime setup
```

掛鉤安裝需要明確標誌：

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

安裝程式備份代理配置，保留現有掛鉤，並僅添加帶有Skill Runtime管理標記。鉤子適配器儲存最小的生命週期字段，而不是完整的提示或工具負載。當運行時處於活動狀態時，權限受限Unixsocket是快速路徑；可選的本機寄件者避免Python啟動。當運行時不活動時，獨立的故障開放路徑會將經過編輯的證據附加到`~/.skill-runtime/queue/events.jsonl`。`skill-runtime start`使用事件 ID 重複資料刪除重播該佇列。

Codex事件使用其官方 HookAPI（`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`， 和`Stop`）。Codex目前同步執行命令掛鉤，因此Skill Runtime使用本地Unix具有有限超時的套接字/本機發送方。任何投遞失敗都會被吞掉並排隊；它永遠不會改變代理的決定。請參閱[Codex Hook 官方文檔](https://developers.openai.com/codex/config-advanced#hooks)。

僅刪除託管項目：

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

伺服器綁定到`127.0.0.1`預設情況下。完整的轉錄訊息和工具負載不會複製到索引中。在保留標準化摘要之前，會對常見的秘密模式進行編輯。

使用以下命令執行無依賴測試套件：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 發布工程

Git中心操作運行Python3.9–3.13 測試、JavaScript 驗證、本機發送器編譯以及真實的安裝/啟動/醫生/停止/卸載冒煙測試。一個`v*`標籤建構wheel/sdist套件以及受校驗和保護的Linux和macOS本機發送器。 CLI 安裝程式會下載相符的版本資產，因此最終使用者不需要編譯器。

執行第一個產品相關診斷實驗：

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

它錯誤地註入生命週期證據差距、明確故障、不完整的運作和未經驗證的結果，然後評估系統使用的相同確定性診斷引擎。API和UI。請參閱[PAI-DSW實驗計劃](docs/pai-dsw-experiment-plan.md)用於實驗階梯、無幹擾測試和再現性合約。

建置輪子後，使用以下命令運行隔離的打包生命週期煙霧：

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

它安裝到臨時虛擬環境和臨時家庭中，在不啟用鉤子的情況下執行完整的本地生命週期，並驗證專案和代理配置不干擾。

## 實驗驅動的產品設計

產品行為受到以下因素的限制[實驗驅動的產品理念](docs/experiment-driven-product-philosophy.md)：證據先於結論，第一個可觀察邊界先於嚴重性，類型化關係先於平面日誌，確定性重建先於機率輔助。

目前可複製的當地證據包括：

- 7/7局部實驗門通過；
- 接受 2,400/2,400 個收集器事件，無需輸入/輸出突變；
- 14/14 確定性故障語料庫診斷，沒有不支持的因果關係；
- 關係診斷表示達到 13/14 準確率和 F1 0.963，而平面生命週期檢索達到 1/14 準確率和 F1 0.080；
- 11/11 學習材料案例將最早可觀察的邊界放在第一位。

這些結果驗證了機制和表示選擇，而不是部署泛化或人類利益。真實的第二個智能體研究、跨平台尾部延遲、真實故障校準和參與者診斷研究仍然存在證據差距。

此研究方向也基於相鄰的主要工作：[SkillsBench](https://arxiv.org/abs/2602.12670)和[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)促進診斷，因為技能效果各不相同並且可能倒退；[Harness-Bench](https://arxiv.org/abs/2605.27922)激發能力感知的跨代理比較；和[執行來源調查](https://arxiv.org/abs/2606.04990)激發類型化證據關係、追蹤來源和隱私意識審計基礎設施。

## 文件

- [產品定義](docs/product-definition.md)
- [MVP規範](docs/mvp-specification.md)
- [運行時事件模型](docs/runtime-event-model.md)
- [UI資訊架構](docs/ui-information-architecture.md)
- [適配器能力矩陣](docs/adapter-capability-matrix.md)
- [可觀測性互通性](docs/observability-interoperability.md)
- [可觀測性平台設置](docs/observability-platform-setup.md)
- [研究和競爭格局](docs/research-and-competitive-landscape.md)
- [研究論文議程](docs/research-paper-agenda.md)
- [實驗驅動的產品理念](docs/experiment-driven-product-philosophy.md)
- [實驗結果](docs/experiment-results-2026-07-29.md)
- [PAI-DSW實驗計劃](docs/pai-dsw-experiment-plan.md)

## 路線圖

1. **v0.1 — 運行時證據和診斷：** 即時採集，Skill Run Panorama、第一邊界診斷、證據檢查、比較和 OTLP 互通性。
2. **v0.2 — 適配器強化和診斷研究：** 額外的 Agent 版本、真實的跨 Agent 實驗和參與者評估。
3. **v0.3 — 效果評估：** 控制有技能/無技能配對評估，與單次運行診斷分開。

## 項目狀況

一個SkillRun-第一個運行時可運行：已安裝的定義清單，Codex轉錄後備，同意驅動的官方 Hook 適配器Codex,Claude Code， 和Qoder，僅觀察OpenCode插件適配器、活動範圍歸因、精確文件/工件路徑、編輯、單獨的來源/關係/推理層、SQLite儲存、保留、交叉運行和跨代理比較、確定性診斷和即時全景UI。 OTLP/Phoenix,Langfuse,LangSmith,W&B Weave， 和Datadog出口可以進口；標準化證據可以透過選擇即時導出OTLP/HTTP。候選發現、模型內部選擇原因、語意有效性和因果結果主張仍明確不受支持。
