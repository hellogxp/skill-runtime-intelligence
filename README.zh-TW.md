# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · **繁體中文** · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> 診斷特工技能運作首先出現分歧的位置並檢查證據
> 每一個結論的背後。

Agent Skill Runtime Intelligence是一個唯讀的運行時代理技能證據和診斷系統。它將技能定義、官方代理運行時事件、導入的追蹤、會話回退和可觀察的工作區結果組合到證據分級的Skill Run Panorama中。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 快速啟動

在macOS或Linux上安裝並啟動最新版本：

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

不需要複製、帳戶、`sudo`或GitHub CLI。安裝程式會驗證版本校驗和，檢測支援的代理和技能，解釋它將讀取的每個路徑，在啟用僅觀察掛鉤之前詢問一次，並在 [http://127.0.0.1:4317](http://127.0.0.1:4317) 打開本地 UI。除非您明確配置匯出，否則運行時資料將保留在 `~/.skill-runtime` 下。

您可以在運行之前[檢查安裝程式](scripts/install.sh)。

### 看你的第一次現場直播SkillRun

1. 當安裝程式詢問時，接受可選的故障開啟 Hook 設定。
2. 重新啟動代理程式並開始新任務。在Codex中，先查看`/hooks`中的託管指令；現有任務不會熱載入新的Hook。
3. 正常使用技能，然後確認融合並開啟UI：

```bash
skill-runtime doctor
skill-runtime status
```

只有當收集器收到真實的運行時事件後，整合才處於「即時」狀態。已配置但未觀察到的Hook **待定** - 從未作為即時證據呈現。開啟 [http://127.0.0.1:4317](http://127.0.0.1:4317)，或參閱 [入門指南](docs/getting-started.md) 以了解特定於代理的說明和故障排除。

要直接從來源簽出運行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 產品表面 | 它回答什麼 |
|---|---|
| Runtime Overview | 哪些SkillRuns需要注意？ |
| First Observable Boundary | 證據首先在哪裡遺失或失效？ |
| Skill Run Panorama | 請求、啟動、資源、工具、工件和結果如何連結？ |
| Evidence Inspector | 什麼來源、等級、基礎和適配器能力支持這一說法？ |
| 比較 | 差異是行為差異，還是只是可觀察差異？ |
| Inferred Analysis | 哪些有證據支持的解釋或下一步調查是可信的？ |
| 設定/醫生 | 讀取、儲存、匯出、待處理和驗證什麼？ |

## 它是如何運作的

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime 觀察您已經使用的工作流程。版本化適配器將代理本機事件轉變為穩定的技能生命週期，而原始來源信封、規範化事件、關係和推理保持獨立。診斷引擎首先識別證據遺失或失敗的最早邊界；它不會發明模型意圖或因果有效性。

| 數據來源 | 角色 | 新鮮 | UI標籤 |
|---|---|---|---|
| 官方代理掛鉤/插件/SDK事件 | 主要生命週期、工具、子代理程式和終端證據 | 居住 | `Official hook` / `Native telemetry` |
| 技能文件和可觀察的工作空間結果 | 定義、資源、文件、工件和測試證據 | 即時快照/索引 | `Observed` |
| 會議記錄 | 當代理暴露沒有足夠的運行時時的兼容性回退API | 近實時或歷史的 | `Transcript fallback` |
| OTLP 和支援的追蹤導出 | 互通性和歷史導入 | 即時導出/批次匯入 | 顯示來源設定檔 |
| 確定性相關性 | 將事件連接到SkillRun而不更改來源事實 | 攝入時 | `Derived` |
| 語意輔助 | 僅提供解釋和調查建議 | 一經請求 | `Inferred` |

支援的第一方適配器的版本是獨立的：

| 代理人 | 初級整合 | 倒退 | 啟動可見性 |
|---|---|---|---|
| Codex | 官方命令Hooks | 會話導入 | Hook 事件暴露時明確激活 |
| Claude Code | 官方Hooks | 會話導入 | 暴露的顯式技能工具和斜線命令證據 |
| Qoder | 官方命令Hooks | 本地記錄 | 當其技能工具暴露時明確激活 |
| OpenCode | 僅觀察全域插件 | 本地記錄 | 暴露的技能工具回調 |

確切的能力限制記錄在[適配器能力矩陣](docs/adapter-capability-matrix.md)中。不受支援和未觀察到的階段保持可見，而不是轉化為失敗。

## 問題

安裝技能並不能證明代理商發現了它。發現並不證明激活。激活並不證明已載入完整的指令和資源。執行並不能證明該技能改善了結果。

如今，這些失敗往往是悄無聲息的。開發人員會問：

- 該特工可以使用該技能嗎？
- 它是否針對此請求啟動了？
- 載入了哪些指令、參考、腳本和資源？
- 涉及哪些工具、MCP 呼叫、子代理、檔案和工件？
- 運行在哪裡失敗、重試或遺失上下文？
- 該技能有幫助嗎，還是只會增加成本和延遲？

## 技能特異性診斷

主要診斷對像是`SkillRun`，而不是整個代理會話：

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

UI 保持生命週期有序、類型化和證據分級。缺少啟動遙測意味著「未觀察到」或「不受支援」；這並不意味著特工肯定跳過了該技能。

## 證據紀律

UI 絕對不能將推論呈現為運行時事實：

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

## 目前範圍

運行時透過獨立的版本化適配器支援Codex、Claude Code、Qoder和OpenCode，並提供：

- 安裝技能發現和驗證；
- 即時官方Hook/外掛集加上標記的會話回退；
- 技能啟動、資源載入和工具調用時間表；
- 子代理、MCP、文件和工件關係；
- 持續時間、令牌、錯誤、重試和狀態摘要（如果可用）；
- Runtime Overview及第一邊界診斷；
- 全景 DAG、事件時間軸和證據檢查器；
- 能力感知的同Agent和跨Agent比較；
- 一個單獨的Inferred Analysis表面，不能重寫運行時事實；
- 選擇加入OTLP/HTTP導出並支援可觀察性追蹤導入。

MVP **不**包括市場、通用代理運行時、安全實施、企業治理或因果關係聲明。

## 安裝詳細

對於支援的最短路徑，請使用 [快速啟動](#quick-start) 中的單行版本安裝程式。完整的首次運行流程、特定於代理的重新啟動/信任步驟、隱私行為和故障排除位於 [入門指南](docs/getting-started.md) 中。

對於開發來說，基線實作沒有超過 Python 3.9+ 的運行時依賴性。從儲存庫根目錄：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

然後打開[http://127.0.0.1:4317](http://127.0.0.1:4317)。

一次性`install`命令：

1. 掃描用戶、項目和快取插件技能位置；
2. 檢測Codex、Claude Code、Qoder和OpenCode而不更改其配置；
3. 顯示將讀取哪些代理程式和技能路徑；
4. 為目前平台下載一個經過校驗和驗證的低啟動本機發送器，回退到本地 C 版本，最後是 Python 發送器，並在安裝過程中預熱一次新的本機二進位；
5. 建立 `~/.skill-runtime/config.json` 和本地 SQLite 索引。

當以互動方式運行時，它會在添加故障開放代理掛鉤之前詢問一次。 `--no-hooks` 將轉錄本匯入保留為標記後備，而 `--enable-hooks` 記錄明確同意並僅安裝託管條目。對於Codex，安裝後打開`/hooks`，查看確切的託管命令並信任它們。 Codex 有意要求對在託管企業配置之外添加的掛鉤進行明確的審查。信任 Hook 後啟動新的 Codex 任務/會話，然後執行：

```bash
.venv/bin/skill-runtime doctor
```

Qoder在啟動時載入Hook配置，因此首次安裝後重新啟動Qoder。 OpenCode 從其全域插件目錄中發現託管的僅觀察插件；如果當前進程早於安裝，請重新啟動OpenCode。整合都不會讀取或更改模型請求。

僅在資料庫收到真實的 `official_hook` 事件後，整合才會變為 **Live**。僅寫入 `~/.codex/hooks.json` 顯示為 **Pending**，從未連接。 `start` 啟動收集器、成績單回退觀察程序、保留工作人員、SQLite 儲存和即時 UI 作為託管後台進程。沒有代理模型請求。

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

`uninstall` 僅刪除託管的 Hook 條目和 Skill Runtime 擁有的檔案。沒有`--keep-data`，需要交互確認（或⟦L​​4⟧）才能移除`~/.skill-runtime`；代理會話和技能源永遠不會被刪除。

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

版本化導入設定檔目前可辨識 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave 和 Datadog JSON 形狀。只有當來源攜帶明確的 Skill 語義時，它們才會創建 SkillRun；通用跨度名稱不被視為激活證據。

將標準化的、特定於技能的運行時證據導出到任何 OTLP/HTTP 追蹤端點：

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

除非明確配置端點，否則匯出將被停用。檢查點、重試狀態和目標運作狀況顯示在「設定」中。不會匯出原始提示、工具負載、憑證和技能資源內容。對於認證後台導出，在`skill-runtime start`之前的環境中提供標準`OTEL_EXPORTER_OTLP_HEADERS`；標頭永遠不會寫入Skill Runtime配置或進程參數。

## 發送即時運行時證據

`skill-runtime start` 包括本地收集器。本機遙測適配器、官方掛鉤、輕量級故障開放掛鉤和SDK整合可以將單一事件或有界批次附加到`POST /api/events`：

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

端點在持久化之前編輯通用憑證，並按`event_id`進行重複資料刪除，保留單獨的編輯後的原始信封，並返回結果`skill_run_ids`。 `GET /api/collector/schema`公開了支持的事件詞彙和收集模式。 UI 使用 SSE 監聽 `/api/stream`，輪詢僅作為重新連接後備。

源指示器將主要運行時證據與 `Transcript fallback` 和導入的追蹤區分開來。單獨的收集器端點不會聲明本機遙測：每個生產者都必須聲明其事件是否來自本機遙測、官方掛鉤、輕量級掛鉤還是SDK。

### 可選代理掛鉤

首先檢查確切的路徑和事件。該指令是唯讀的：

```bash
.venv/bin/skill-runtime setup
```

Hook 安裝需要明確標誌：

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

安裝程式會備份代理配置，保留現有掛鉤，並僅新增帶有 Skill Runtime 管理標記的條目。鉤子適配器儲存最小的生命週期字段，而不是完整的提示或工具負載。對於已完成的工具調用，它僅提取精確的`SKILL.md`、標準技能資源和內存中更改的文件路徑；原始命令、補丁主體、提示和工具輸出在持久化之前被丟棄。當運作時處於活動狀態時，權限受限的Unix套接字是快速路徑；可選的本機發送器可避免 Python 啟動。當運行時不活動時，獨立的故障開放路徑會將經過編輯的證據附加到`~/.skill-runtime/queue/events.jsonl`。 `skill-runtime start` 透過事件 ID 重複資料刪除來重播該佇列。

Codex活動使用其官方HookAPI（`SessionStart`，`SessionEnd`，`UserPromptSubmit`，`PreToolUse`，`PostToolUse`，`PreCompact`，`PostCompact` `SubagentStop`、`Stop`）。 Codex 目前同步執行指令掛鉤，因此 Skill Runtime 使用具有有限逾時的本地 Unix 套接字/本機發送方。任何投遞失敗都會被吞掉並排隊；它永遠不會改變代理的決定。請參閱[Codex Hook 官方文檔](https://developers.openai.com/codex/config-advanced#hooks)。

僅刪除託管項目：

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

伺服器預設綁定到`127.0.0.1`。完整的轉錄訊息和工具負載不會複製到索引中。在保留標準化摘要之前，會對常見的秘密模式進行編輯。

使用以下命令執行無依賴測試套件：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 發布工程

GitHub Actions 運行 Python 3.9–3.13 測試、JavaScript 驗證、本機發送器編譯以及真正的安裝/啟動/醫生/停止/卸載冒煙測試。 `v*`標籤建構wheel/sdist包以及受校驗和保護的Linux和macOS本機發送器。 CLI 安裝程式會下載相符的版本資產，因此最終使用者不需要編譯器。

執行第一個產品相關診斷實驗：

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

它錯誤注入生命週期證據差距、顯式故障、不完整的運行和未經驗證的結果，然後評估 API 和 UI 使用的相同確定性診斷引擎。有關實驗階梯、無幹擾測試和再現性合同，請參閱[PAI-DSW實驗計劃](docs/pai-dsw-experiment-plan.md)。

建置輪子後，使用以下命令運行隔離的打包生命週期煙霧：

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

它安裝到臨時虛擬環境和臨時家庭中，在不啟用鉤子的情況下執行完整的本地生命週期，並驗證專案和代理配置不干擾。

## 實驗驅動的產品設計

產品行為受到[實驗驅動的產品理念](docs/experiment-driven-product-philosophy.md)的約束：證據先於結論，第一個可觀察邊界先於嚴重性，類型化關係先於平面日誌，確定性重建先於機率輔助。

目前可複製的當地證據包括：

- 7/7局部實驗門通過；
- 接受 2,400/2,400 個收集器事件，無需輸入/輸出突變；
- 14/14 確定性故障語料庫診斷，沒有不支持的因果關係；
- 關係診斷表示達到 13/14 準確率和 F1 0.963，而平面生命週期檢索達到 1/14 準確率和 F1 0.080；
- 11/11 學習材料案例將最早可觀察的邊界放在第一位。

這些結果驗證了機制和表示選擇，而不是部署泛化或人類利益。真實的第二個智能體研究、跨平台尾部延遲、真實故障校準和參與者診斷研究仍然存在證據差距。

研究方向也基於相鄰的主要工作：[SkillsBench](https://arxiv.org/abs/2602.12670)和[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)激發診斷，因為技能效果各不相同並且可能會回歸； [Harness-Bench](https://arxiv.org/abs/2605.27922) 激發能力感知的跨 Agent 比較； [執行來源調查](https://arxiv.org/abs/2606.04990) 促進類型化證據關係、追踪來源和隱私意識審計基礎設施。

## 文件

| 從這裡開始 | 目的 |
|---|---|
| [Getting Started](docs/getting-started.md) | 安裝、連接代理、驗證即時證據並排除故障 |
| [建築學](docs/architecture.md) | 採集管道、儲存邊界、證據引擎和信任模型 |
| [適配器能力矩陣](docs/adapter-capability-matrix.md) | 代理/版本的確切訊號和限制 |
| [可觀測性平台設置](docs/observability-platform-setup.md) | 連接 OTLP 相容平台並導入支援的追蹤 |
| [運行時事件模型](docs/runtime-event-model.md) | 穩定的事件詞彙、出處、關係和證據等級 |
| [UI資訊架構](docs/ui-information-architecture.md) | 概覽、第一邊界、全景、檢查器、比較和 Inferred Analysis |

產品與研究參考：[產品定義](docs/product-definition.md)、[MVP規範](docs/mvp-specification.md)、[可觀測性 互通性](docs/observability-interoperability.md)、[實驗驅動的產品理念](docs/experiment-driven-product-philosophy.md)、[實驗結果](docs/experiment-results-2026-07-29.md) 和 [研究議程](docs/research-paper-agenda.md)。

## 路線圖

1. **v0.2.0 — 現已推出：** 即時故障開放集合、四個版本代理適配器、Runtime Overview、第一邊界診斷、Panorama、Evidence Inspector、功能感知比較、Inferred Analysis 和 OTLP 互通性。
2. **下一步 - 適配器和診斷強化：**更廣泛的代理/版本覆蓋範圍、真實故障校準、跨平台尾部延遲驗證和參與者診斷研究。
3. **後來－效果評估：**控制有技能/無技能配對評估，與單一運行診斷明確分開。

## 項目狀況

版本`v0.2.0`發布。運行時包括已安裝的定義清單、用於Codex、Claude Code和Qoder的同意驅動的官方Hook適配器、僅觀察的OpenCode插件、標記的轉錄後備、活動範圍歸因、精確文件/工件路徑、修訂、單獨的來源/關係/推理層、SQLite儲存、保留、確定性診斷、即時UI以及跨運行/跨代理比較。 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave、Datadog出口可匯入；標準化證據可透過選擇加入OTLP/HTTP即時匯出。

模型內部的候選發現、模型內部選擇原因、語意效度和因果結果主張仍然明確不受支持，除非來源或對照實驗提供了證據。
