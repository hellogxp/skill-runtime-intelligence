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


> 轉動 `SKILL.md` 進入可檢查的運行時期望。看看實際上是什麼
> 發生的情況、行為首次出現分歧的地方以及判決背後的證據。

Agent Skill Runtime Intelligence 是一個針對代理技能的唯讀運行時證據和診斷系統。它從當前技能定義中提取保守的、可檢查的約束，將它們與運行時活動相匹配，並將結果重建為證據分級的結果 Skill Run Panorama。它結合了官方代理事件、導入的追蹤、標記的會話回退和可觀察的工作區結果，無需代理模型請求或接管代理循環。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 快速啟動

安裝並啟動最新版本 macOS 或者 Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

沒有克隆、帳戶、 `sudo`， 或者 GitHub CLI 是必須的。安裝程式驗證版本校驗和，檢測支援的代理和技能，解釋它將讀取的每個路徑，在啟用僅觀察掛鉤之前詢問一次，並打開本地 UI 在 [http://127.0.0.1:4317](http://127.0.0.1:4317)。運行時資料保持在 `~/.skill-runtime` 除非您明確配置匯出。

你可以 [檢查安裝程式](scripts/install.sh) 在運行之前。

### 觀看您的第一次直播 SkillRun

1. 接受可選的故障開放 Hook 當安裝程式詢問時進行設定。
2. 重新啟動代理程式並開始新任務。在 Codex，查看中的託管命令 `/hooks` 第一的;現有任務不會熱載入新任務 Hooks。
3. 正常使用技能，然後確認融合併打開 UI:

```bash
skill-runtime doctor
skill-runtime status
```

只有當收集器收到真實的運行時事件後，整合才處於「即時」狀態。已配置但未觀察到的 Hook **待決**——從未作為活生生的證據呈現。打開 [http://127.0.0.1:4317](http://127.0.0.1:4317)，或查看 [入門指南](docs/getting-started.md) 有關代理特定的說明和故障排除。

要直接從來源簽出運行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 產品表面 | 它回答什麼 |
|---|---|
| Runtime Overview | 哪個 SkillRuns 需要注意嗎？ |
| 技能行為檢定 | 哪些可檢查的指令被滿足、需要審查或無法評估？ |
| 到底發生了什麼事 | 觀察到了哪些指令、資源、工具、工件和結果？ |
| First Observable Boundary | 運行特定的證據首先在哪裡丟失或失敗？ |
| Skill Run Panorama | 請求、啟動、資源、工具、工件和結果如何連結？ |
| Evidence Inspector | 什麼來源、等級、基礎和適配器能力支持這一說法？ |
| 比較 | 差異是行為差異，還是只是可觀察差異？ |
| Inferred Analysis | 哪些有證據支持的解釋或下一步調查是可信的？ |
| 設定/醫生 | 讀取、儲存、匯出、待處理和驗證什麼？ |

## 它是如何運作的

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime 觀察您已經使用的工作流程。版本化適配器將代理本機事件轉變為穩定的技能生命週期，而原始來源信封、規範化事件、關係和推理保持獨立。診斷引擎根據該證據檢查明確的技能約束，識別最早可觀察到的偏差，並將系統適配器盲點與特定於運行的發現分開。它不會發明模型意圖或因果有效性。

| 數據來源 | 角色 | 新鮮 | UI 標籤 |
|---|---|---|---|
| 官方代理掛鉤/插件/ SDK 事件 | 主要生命週期、工具、子代理程式和終端證據 | 居住 | `Official hook` / `Native telemetry` |
| 技能文件和可觀察的工作空間結果 | 定義、資源、文件、工件和測試證據 | 即時快照/索引 | `Observed` |
| 會議記錄 | 當代理暴露沒有足夠的運行時時的兼容性回退 API | 近實時或歷史的 | `Transcript fallback` |
| OTLP 和支援的追蹤導出 | 互通性和歷史導入 | 即時導出/批次匯入 | 顯示來源設定檔 |
| 確定性相關性 | 將事件連接到 SkillRun 不改變源事實 | 攝入時 | `Derived` |
| 語意輔助 | 僅提供解釋和調查建議 | 一經請求 | `Inferred` |

支援的第一方適配器的版本是獨立的：

| 代理人 | 初級整合 | 倒退 | 啟動可見性 |
|---|---|---|---|
| Codex | 官方命令 Hooks | 會話導入 | 暴露時顯式激活 Hook 事件 |
| Claude Code | 官方的 Hooks | 會話導入 | 暴露的顯式技能工具和斜線命令證據 |
| Qoder | 官方命令 Hooks | 本地記錄 | 當其技能工具暴露時明確激活 |
| OpenCode | 僅觀察全域插件 | 本地記錄 | 暴露的技能工具回調 |

確切的能力限制記錄在 [適配器能力矩陣](docs/adapter-capability-matrix.md)。不受支援和未觀察到的階段保持可見，而不是轉化為失敗。

## 問題

安裝技能並不能證明代理商發現了它。發現並不證明激活。激活並不證明已載入完整的指令和資源。加載說明並不能證明特工遵循了這些說明。執行並不能證明該技能改善了結果。

如今，這些失敗往往是悄無聲息的。開發人員會問：

- 該特工可以使用該技能嗎？
- 它是否針對此請求啟動了？
- 載入了哪些指令、參考、腳本和資源？
- 遵循、錯過或無法評估哪些明確的技能要求？
- 哪些工具， MCP 涉及調用、子代理、文件和工件嗎？
- 運行在哪裡失敗、重試或遺失上下文？
- 該技能有幫助嗎，還是只會增加成本和延遲？

## 技能特異性診斷

主要診斷對像是 `SkillRun`，而不是整個代理會話：

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

這 UI 保持生命週期有序、類型化和證據分級。缺少啟動遙測意味著「未觀察到」或「不受支援」；這並不意味著特工肯定跳過了該技能。

## 證據紀律

這 UI 絕不能將推論呈現為運行時事實：

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

運行時支援 Codex, Claude Code, Qoder， 和 OpenCode 透過獨立的版本化適配器並提供：

- 安裝技能發現和驗證；
- 即時官方 Hook/插件集合加上標記的會話後備；
- 技能啟動、資源載入和工具調用時間表；
- 分代理, MCP、文件和工件關係；
- 持續時間、令牌、錯誤、重試和狀態摘要（如果可用）；
- 從目前的行為中提取保守的行為約束 `SKILL.md`;
- 有證據限制的一致性、驗證和運行時故障檢查；
- 具體指導、資源、工具、工件和成果清單；
- Runtime Overview 系統覆蓋範圍與運作結果分開；
- 第一邊界診斷；
- 全景 DAG、事件時間軸和證據檢查器；
- 能力感知的同Agent和跨Agent比較；
- 一個單獨的 Inferred Analysis 無法重寫運行時事實的表面；
- 選擇加入 OTLP/HTTP 匯出並支援可觀察性追蹤導入。

MVP **不**包括市場、通用代理運行時、安全實施、企業治理或因果關係聲明。

## 安裝詳細

對於最短的支援路徑，請使用單行版本安裝程式 [快速啟動](#quick-start)。完整的首次運行流程、特定於代理的重新啟動/信任步驟、隱私行為和故障排除位於 [入門指南](docs/getting-started.md)。

對於開發來說，基線實作沒有運行時依賴性 Python 3.9+。從儲存庫根目錄：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

然後打開 [http://127.0.0.1:4317](http://127.0.0.1:4317)。

一次性的 `install` 命令：

1. 掃描用戶、項目和快取插件技能位置；
2. 檢測到 Codex, Claude Code, Qoder， 和 OpenCode 無需更改其配置；
3. 顯示將讀取哪些代理程式和技能路徑；
4. 下載目前平台的校驗和驗證的低啟動本機發送器，回退到本地 C 構建，最後 Python 發送器，並在安裝過程中預熱一次新的本機二進位；
5. 創造 `~/.skill-runtime/config.json` 和當地的 SQLite 指數。

第一個索引匯入現有的相容代理會話。在壽命較長的工作站上，這可能比全新安裝需要更長的時間；以後的啟動是增量的，並且 UI 當後台刷新運行時變得可用。

當以互動方式運行時，它會在添加故障開放代理掛鉤之前詢問一次。 `--no-hooks` 將轉錄本導入保留為標記後備，同時 `--enable-hooks` 記錄明確同意並僅安裝託管條目。為了 Codex， 打開 `/hooks` 安裝後，請查看確切的託管命令並信任它們。 Codex 有意要求對在託管企業配置之外添加的掛鉤進行明確的審查。開始新的 Codex 信任後的任務/會話 Hooks，然後運行：

```bash
.venv/bin/skill-runtime doctor
```

Qoder 負載 Hook 啟動時配置，所以重新啟動 Qoder 第一次安裝後。 OpenCode 從其全域插件目錄中發現託管的僅觀察插件；重新啟動 OpenCode 如果目前進程早於安裝。整合都不會讀取或更改模型請求。

只有當資料庫收到真實的資料後，整合才會變成**Live** `official_hook` 事件。只是寫 `~/.codex/hooks.json` 顯示為**待處理**，從未連線。 `start` 啟動收集器、成績單後備觀察者、保留工作人員， SQLite 儲存和生活 UI 作為託管後台進程。沒有代理模型請求。

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

`uninstall` 僅刪除託管的 Hook 條目和 Skill Runtime- 擁有的文件。沒有 `--keep-data`，它需要互動式確認（或 `--yes`) 刪除前 `~/.skill-runtime`;代理會話和技能來源永遠不會被刪除。

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

版本化導入設定檔目前可識別 OTLP/Phoenix, Langfuse, LangSmith, W&B Weave， 和 Datadog JSON 形狀。他們只創造一個 SkillRun 當源攜帶明確的技能語意時；通用跨度名稱不被視為激活證據。

將標準化的、特定於技能的運行時證據匯出到任何 OTLP/HTTP 追蹤端點：

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

除非明確配置端點，否則匯出將被停用。檢查點、重試狀態和目標運作狀況顯示在「設定」中。不會匯出原始提示、工具負載、憑證和技能資源內容。對於經過身份驗證的後台導出，請提供標準 `OTEL_EXPORTER_OTLP_HEADERS` 在之前的環境中 `skill-runtime start`;標頭永遠不會被寫入 Skill Runtime 配置或進程參數。

## 發送即時運行時證據

`skill-runtime start` 包括當地的收藏家。本機遙測適配器、官方掛鉤、輕量級故障開放掛鉤以及 SDK 整合可以將單一事件或有界批次附加到 `POST /api/events`:

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

端點在持久化之前編輯通用憑證，並透過以下方式進行重複資料刪除 `event_id`，保留一個單獨的經過編輯的原始信封，並返回結果 `skill_run_ids`。 `GET /api/collector/schema` 公開支持的事件詞彙和收集模式。這 UI 聽 `/api/stream` 使用 SSE，輪詢僅作為重新連接後備。

源指示器將主要運行時證據與 `Transcript fallback` 和進口痕跡。僅收集器端點不會聲明本機遙測：每個生產者都必須聲明其事件是否來自本機遙測、官方掛鉤、輕量級掛鉤或 SDK。

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

安裝程式備份代理配置，保留現有掛鉤，並僅添加帶有 Skill Runtime 管理標記。鉤子適配器儲存最小的生命週期字段，而不是完整的提示或工具負載。對於已完成的工具調用，它僅提取精確的 `SKILL.md`、標準技能資源以及記憶體中的更改檔案路徑；原始命令、補丁主體、提示和工具輸出在持久化之前被丟棄。當運行時處於活動狀態時，權限受限 Unix socket是快速路徑；可選的本機寄件者避免 Python 啟動。當運行時不活動時，獨立的故障開放路徑會將經過編輯的證據附加到 `~/.skill-runtime/queue/events.jsonl`。 `skill-runtime start` 使用事件 ID 重複資料刪除重播該佇列。

Codex 活動使用其官方 Hook API （`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`， 和 `Stop`）。 Codex 目前同步執行命令掛鉤，所以 Skill Runtime 使用本地 Unix 具有有限超時的套接字/本機發送方。任何投遞失敗都會被吞掉並排隊；它永遠不會改變代理的決定。請參閱 [Codex Hook 官方文檔](https://developers.openai.com/codex/config-advanced#hooks)。

僅刪除託管項目：

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

伺服器綁定到 `127.0.0.1` 預設情況下。完整的轉錄訊息和工具負載不會複製到索引中。在保留標準化摘要之前，會對常見的秘密模式進行編輯。

使用以下命令執行無依賴測試套件：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 發布工程

GitHub 行動運行 Python 3.9–3.13 測試、JavaScript 驗證、本機發送器編譯以及真實的安裝/啟動/醫生/停止/卸載煙霧測試。一個 `v*` 標籤建構wheel/sdist包以及受校驗和保護的包 Linux 和 macOS 本地寄件者。 CLI 安裝程式會下載相符的版本資產，因此最終使用者不需要編譯器。

執行第一個產品相關診斷實驗：

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

它錯誤地註入生命週期證據差距、明確故障、不完整的運作和未經驗證的結果，然後評估系統使用的相同確定性診斷引擎。 API 和 UI。請參閱 [PAI-DSW實驗計劃](docs/pai-dsw-experiment-plan.md) 用於實驗階梯、無幹擾測試和再現性合約。

建置輪子後，使用以下命令運行隔離的打包生命週期煙霧：

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

它安裝到臨時虛擬環境和臨時家庭中，在不啟用鉤子的情況下執行完整的本地生命週期，並驗證專案和代理配置不干擾。

## 實驗驅動的產品設計

產品行為遵循四個實驗驅動的限制：結論之前的證據、嚴重性之前的第一個可觀察邊界、平面日誌之前的類型化關係、機率輔助之前的確定性重建。

可重複的證據及其局限性保留在 [實驗報告](docs/experiment-results-2026-07-29.md)。有界結果包括：

- 接受 2,400/2,400 個收集器事件，無需輸入/輸出突變；
- 14/14 確定性故障語料庫診斷，沒有不支持的因果關係；
- 關係診斷表示達到 13/14 準確率和 F1 0.963，而平面生命週期檢索達到 1/14 準確率和 F1 0.080；
- 隱私安全的實際運作審核顯然仍然不適合確認性產品效果聲明，因為缺少經過驗證的結果、平衡的跨代理覆蓋和人工標籤。

這些結果驗證了機制和表示選擇，而不是部署泛化或人類利益。真實的第二個智能體研究、跨平台尾部延遲、真實故障校準和參與者診斷研究仍然存在證據差距。

此研究方向也基於相鄰的主要工作： [SkillsBench](https://arxiv.org/abs/2602.12670) 和 [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) 激發診斷，因為技能效果各不相同並且可能會倒退； [Harness-Bench](https://arxiv.org/abs/2605.27922) 激發能力感知的跨代理比較；和 [執行來源調查](https://arxiv.org/abs/2606.04990) 激發類型化證據關係、追蹤來源和隱私意識審計基礎設施。

## 文件

| 從這裡開始 | 目的 |
|---|---|
| [Getting Started](docs/getting-started.md) | 安裝、連接代理、驗證即時證據並排除故障 |
| [建築學](docs/architecture.md) | 採集管道、儲存邊界、證據引擎和信任模型 |
| [適配器能力矩陣](docs/adapter-capability-matrix.md) | 代理/版本的確切訊號和限制 |
| [可觀測性平台設置](docs/observability-platform-setup.md) | 連接 OTLP 相容平台並導入支援的追蹤 |
| [運行時事件模型](docs/runtime-event-model.md) | 穩定的事件詞彙、出處、關係和證據等級 |
| [UI資訊架構](docs/ui-information-architecture.md) | 概覽、第一邊界、全景、檢查器、比較和 Inferred Analysis |
| [變更日誌](CHANGELOG.md) | 版本化的使用者可見的更改 |
| [v0.3.0 發行說明](docs/releases/v0.3.0.md) | 升級指南、亮點和已知限制 |

產品與研究參考： [產品定義](docs/product-definition.md), [MVP規範](docs/mvp-specification.md), [可觀測性 互通性](docs/observability-interoperability.md), [實驗結果](docs/experiment-results-2026-07-29.md)，以及 [研究議程](docs/research-paper-agenda.md)。

## 社區與治理

- 讀 [貢獻](CONTRIBUTING.md) 在更改證據語義、適配器或產品行為之前。
- 遵循 [行為守則](CODE_OF_CONDUCT.md) 在所有項目空間中。
- 透過私下報告漏洞 [安全政策](SECURITY.md)，不是公共問題。
- 使用結構化的 [問題追蹤器](https://github.com/hellogxp/skill-runtime-intelligence/issues) 用於可重現的錯誤和範圍內的功能提案。切勿附加私有執行時間資料庫或會話記錄。

## 路線圖

1. **v0.3.0 — 下一個版本：** 可檢查的技能行為限制、具體的運行時活動、有證據的評估、系統覆蓋診斷以及現有的即時全景和比較工作流程。
2. **下一步 - 適配器和診斷強化：**更廣泛的代理/版本覆蓋範圍、真實故障校準、跨平台尾部延遲驗證和參與者診斷研究。
3. **後來－效果評估：**控制有技能/無技能配對評估，與單一運行診斷明確分開。

## 項目狀況

目前原始碼樹目標 `v0.3.0`;使用上面的發布徽章來識別最新發布的版本。運行時包括可檢查的技能行為約束、具體活動摘要、安裝定義清單、同意驅動的官方 Hook 適配器用於 Codex, Claude Code， 和 Qoder，僅觀察 OpenCode 外掛程式、標記的轉錄後備、活動範圍歸因、確切的文件/工件路徑、編輯、單獨的來源/關係/推理層、 SQLite 儲存、保留、確定性診斷、即時 UI，以及跨運行/跨代理比較。 OTLP/Phoenix, Langfuse, LangSmith, W&B Weave， 和 Datadog 出口可以進口；標準化證據可以透過選擇即時導出 OTLP/HTTP。

模型內部的候選發現、模型內部選擇原因、語意效度和因果結果主張仍然明確不受支持，除非來源或對照實驗提供了證據。
