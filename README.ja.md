# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · **日本語** ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> エージェント スキルの実行が最初に分岐した場所を診断し、証拠を検査します
> あらゆる結論の裏にあるもの。

Agent Skill Runtime Intelligence は、エージェント スキルのための読み取り専用のランタイム証拠および診断システムです。スキル定義、公式エージェント ランタイム イベント、インポートされたトレース、セッション フォールバック、および観察可能なワークスペースの結果を組み合わせて、証拠グレードの Skill Run Panorama を作成します。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## クイックスタート

macOS または Linux に最新リリースをインストールして起動します。

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

クローン、アカウント、`sudo`、または GitHub CLI は必要ありません。インストーラーはリリース チェックサムを検証し、サポートされているエージェントとスキルを検出し、読み取られるすべてのパスを説明し、監視専用フックを有効にする前に 1 回問い合わせて、[http://127.0.0.1:4317](http://127.0.0.1:4317) でローカルの UI を開きます。エクスポートを明示的に構成しない限り、ランタイム データは `~/.skill-runtime` の下に残ります。

実行する前に [インストーラーを検査する](scripts/install.sh) を実行できます。

### 初めてのライブを見てください SkillRun

1. インストーラーの要求に応じて、オプションのフェールオープン Hook セットアップを受け入れます。
2. エージェントを再起動し、新しいタスクを開始します。 Codex では、まず `/hooks` の管理対象コマンドを確認します。既存のタスクは新しい Hook をホットロードしません。
3. 通常通りスキルを使用し、統合を確認して、UI を開きます。

```bash
skill-runtime doctor
skill-runtime status
```

統合は、コレクターが実際のランタイム イベントを受信した後にのみ **ライブ** になります。構成されているが観察されていない Hook は **保留中**であり、生きた証拠として提示されることはありません。エージェント固有の手順とトラブルシューティングについては、[http://127.0.0.1:4317](http://127.0.0.1:4317) を開くか、[入門ガイド](docs/getting-started.md) を参照してください。

ソース チェックアウトから直接実行するには:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 製品表面 | 答えは何ですか |
|---|---|
| Runtime Overview | どのSkillRunsに注意が必要ですか? |
| First Observable Boundary | 証拠が最初に紛失または失敗したのはどこですか? |
| Skill Run Panorama | リクエスト、アクティベーション、リソース、ツール、アーティファクト、結果はどのように結びついたのでしょうか? |
| Evidence Inspector | この主張を裏付けるソース、グレード、ベース、アダプター機能は何ですか? |
| 比較する | 違いは行動的なものですか、それとも可観測性の違いだけですか? |
| Inferred Analysis | どのような証拠に基づいた説明や次の調査がもっともらしいでしょうか? |
| 設定 / ドクター | 読み取り、保存、エクスポート、保留、検証とは何ですか? |

## 仕組み

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime は、すでに使用しているワークフローを監視します。バージョン管理されたアダプターは、エージェントネイティブのイベントを安定したスキルのライフサイクルに変えますが、生のソースエンベロープ、正規化されたイベント、関係、および推論は分離されたままになります。診断エンジンはまず、証拠が欠落または失敗する最も初期の境界を特定します。モデルの意図や因果関係の有効性を発明するものではありません。

| データソース | 役割 | 鮮度 | UI ラベル |
|---|---|---|---|
| 公式エージェントのフック / プラグイン / SDK イベント | 一次ライフサイクル、ツール、サブエージェント、および最終証拠 | ライブ | `Official hook` / `Native telemetry` |
| スキルファイルと観察可能なワークスペースの成果 | 定義、リソース、ファイル、アーティファクト、およびテストの証拠 | ライブスナップショット/インデックス付き | `Observed` |
| セッションの記録 | エージェントが十分なランタイムを公開しない場合の互換性フォールバック API | ほぼライブまたは過去のもの | `Transcript fallback` |
| OTLP とサポートされるトレース エクスポート | 相互運用性と履歴インポート | ライブエクスポート/バッチインポート | ソースプロファイルを表示 |
| 決定的な相関関係 | ソースファクトを変更せずにイベントを SkillRun に接続します | 摂取時 | `Derived` |
| セマンティック支援 | 説明と調査提案のみ | オンデマンド | `Inferred` |

サポートされているファーストパーティ アダプタは、個別にバージョン管理されています。

| エージェント | 一次統合 | 後退する | アクティベーションの可視性 |
|---|---|---|---|
| Codex | 公式コマンド Hooks | セッションのインポート | Hook イベントによって公開された場合の明示的なアクティブ化 |
| Claude Code | 公式Hook | セッションのインポート | 明示的スキルツールとスラッシュコマンドの証拠が公開された場合 |
| Qoder | 公式コマンド Hooks | 現地の記録 | スキルツールによって公開された場合の明示的なアクティベーション |
| OpenCode | 観測専用グローバルプラグイン | 現地の記録 | スキルツールのコールバックが公開されている場合 |

正確な機能制限は、[アダプター機能マトリックス](docs/adapter-capability-matrix.md) に文書化されています。サポートされていないステージや監視されていないステージは、失敗に変換されずに表示されたままになります。

## 問題

スキルをインストールしても、エージェントがスキルを発見したことは証明されません。発見は活性化を証明するものではありません。アクティベーションは、完全な命令とリソースがロードされたことを証明するものではありません。実行は、スキルが結果を改善したことを証明するものではありません。

今日、これらの失敗は沈黙していることがよくあります。開発者は次のような疑問を抱いています。

- このエージェントはスキルを利用できましたか?
- このリクエストに対してアクティブ化されましたか?
- どの命令、リファレンス、スクリプト、アセットがロードされましたか?
- どのツール、MCP 呼び出し、サブエージェント、ファイル、アーティファクトが関係していましたか?
- どこで実行が失敗、再試行、またはコンテキストが失われましたか?
- スキルは役に立ちましたか? それともコストと待ち時間が増えるだけでしたか?

## スキル別診断

主要な診断オブジェクトは `SkillRun` であり、エージェント セッション全体ではありません。

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

UI は、ライフサイクルを順序付け、型指定し、証拠を等級付けした状態に保ちます。アクティベーション テレメトリが見つからない場合は、「観察されない」または「サポートされていない」ことを意味します。エージェントが確実にスキルをスキップしたという意味ではありません。

## 証拠の規律

UI は、実行時のファクトとして推論を決して提示してはなりません。

- **観察** — ソース イベントまたはファイルに明示的に存在します。
- **派生** — 観察された証拠から決定論的に関連付けられています。
- **推測** — 不確実性はあるものの、もっともらしい説明。
- **実験** — 制御された一対の評価を通じて測定された効果。

単一のトレースで実行の属性をサポートできます。因果関係を証明することはできません。 「このスキルにより成功率が向上した」などの主張には、スキルあり/スキルなしの評価を繰り返す必要があります。

## 製品原理

- デフォルトではプライベートで、ローカル、ハイブリッド、チーム接続の展開が可能です。
- 読み取り専用の観察。決してエージェントループを引き継がないでください。
- モデル プロキシや必須のクラウド サービスはありません。
- デフォルトの製品には、ブロック、承認ゲート、ポリシーの強制はありません。
- 明示的な出所と証拠の格付け。
- 段階的な開示: 最初に単純な物語、オンデマンドで生の出来事。
- エージェントのトランスクリプト形式を変更するためのアダプターベースのサポート。

## 現在の範囲

ランタイムは、独立したバージョン管理されたアダプターを通じて Codex、Claude Code、Qoder、および OpenCode をサポートし、以下を提供します。

- インストールされたスキルの検出と検証。
- リアルタイムの公式 Hook/プラグイン コレクションとラベル付きセッション フォールバック。
- スキルのアクティブ化、リソースの読み込み、ツール呼び出しのタイムライン。
- サブエージェント、MCP、ファイル、およびアーティファクトの関係。
- 期間、トークン、エラー、再試行、およびステータスの概要 (利用可能な場合)。
- Runtime Overview および第一境界診断。
- パノラマ DAG、イベント タイムライン、証拠検査官。
- 機能を認識した同一エージェントとエージェント間の比較。
- 実行時ファクトを書き換えることができない別個の Inferred Analysis サーフェス。
- オプトイン OTLP/HTTP エクスポートとサポートされている可観測性トレースのインポート。

MVP には、マーケットプレイス、ユニバーサル エージェント ランタイム、セキュリティ強制、エンタープライズ ガバナンス、または因果関係の主張は**含まれません**。

## 詳細なインストール

サポートされている最短のパスについては、[クイックスタート](#quick-start) にある 1 行のリリース インストーラーを使用してください。完全な初回実行フロー、エージェント固有の再起動/信頼手順、プライバシー動作、およびトラブルシューティングは、[入門ガイド](docs/getting-started.md) にあります。

開発の場合、ベースライン実装には Python 3.9 以降のランタイム依存関係はありません。リポジトリのルートから:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

次に、[http://127.0.0.1:4317](http://127.0.0.1:4317) を開きます。

ワンタイム `install` コマンド:

1. ユーザー、プロジェクト、およびキャッシュされたプラグインのスキルの場所をスキャンします。
2. 構成を変更せずに Codex、Claude Code、Qoder、OpenCode を検出します。
3. どのエージェントおよびスキルのパスが読み取られるかを示します。
4. 現在のプラットフォーム用のチェックサム検証済みの低起動ネイティブ センダーをダウンロードし、ローカル C ビルド、最後に Python センダーにフォールバックし、インストール中に一度新しいネイティブ バイナリをプレウォームします。
5. `~/.skill-runtime/config.json` とローカル SQLite インデックスを作成します。

対話的に実行すると、フェールオープン エージェント フックを追加する前に 1 回尋ねられます。 `--no-hooks` はラベル付きフォールバックとしてトランスクリプトのインポートを保持しますが、`--enable-hooks` は明示的な同意を記録し、管理されたエントリのみをインストールします。 Codex の場合は、インストール後に `/hooks` を開き、管理されているコマンドを正確に確認して信頼します。 Codex では、管理対象のエンタープライズ構成の外部に追加されたフックについて、この明示的なレビューを意図的に要求しています。 Hook を信頼した後、新しい Codex タスク/セッションを開始し、次を実行します。

```bash
.venv/bin/skill-runtime doctor
```

Qoder は起動時に Hook 構成をロードするため、最初のインストール後に Qoder を再起動します。 OpenCode は、グローバル プラグイン ディレクトリから管理された監視専用プラグインを検出します。現在のプロセスがインストール前のものである場合は、OpenCode を再起動します。どちらの統合でも、モデル リクエストの読み取りや変更は行われません。

統合は、データベースが実際の `official_hook` イベントを受信した後にのみ **ライブ** になります。 `~/.codex/hooks.json` を書き込むだけでは **保留中** と表示され、接続されません。 `start` は、管理されたバックグラウンド プロセスとして、コレクター、トランスクリプト フォールバック ウォッチャー、保持ワーカー、SQLite ストア、およびライブ UI を起動します。モデルリクエストはプロキシされません。

ライフサイクルコマンド:

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

`uninstall` は、管理対象の Hook エントリと Skill Runtime が所有するファイルのみを削除します。 `--keep-data` がない場合、`~/.skill-runtime` を削除する前に対話型の確認 (または `--yes`) が必要です。エージェント セッションとスキル ソースは削除されません。

インデックスを付けて個別に提供するには:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

主流の可観測性システムから既存のトレース エクスポートをインポートします。

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

現在、バージョン管理されたインポート プロファイルは、OTLP/Phoenix、Langfuse、LangSmith、W&B Weave、および Datadog JSON の形状を認識します。ソースに明示的なスキル セマンティクスが含まれている場合にのみ、SkillRun が作成されます。一般的なスパン名はアクティベーションの証拠として扱われません。

正規化されたスキル固有のランタイム証拠を任意の OTLP/HTTP トレース エンドポイントにエクスポートします。

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

エンドポイントが明示的に構成されていない限り、エクスポートは無効になります。チェックポイント、再試行ステータス、宛先の健全性が [設定] に表示されます。未処理のプロンプト、ツール ペイロード、認証情報、およびスキル リソースのコンテンツはエクスポートされません。認証されたバックグラウンド エクスポートの場合、環境内で `skill-runtime start` の前に標準の `OTEL_EXPORTER_OTLP_HEADERS` を提供します。ヘッダーが Skill Runtime 設定またはプロセス引数に書き込まれることはありません。

## ライブ実行時の証拠を送信する

`skill-runtime start` にはローカル コレクターが含まれます。ネイティブ テレメトリ アダプター、公式フック、軽量フェールオープン フック、および SDK 統合は、単一のイベントまたは制限されたバッチを `POST /api/events` に追加できます。

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

エンドポイントは、永続化の前に共通の資格情報を編集し、`event_id` によって重複を排除し、別の編集された生のエンベロープを保存し、結果の `skill_run_ids` を返します。 `GET /api/collector/schema` は、サポートされているイベントボキャブラリーと収集モードを公開します。 UI は、SSE を使用して `/api/stream` をリッスンし、ポーリングは再接続フォールバックとしてのみ行われます。

ソース インジケーターは、`Transcript fallback` とインポートされたトレースからの主要な実行時の証拠を区別します。 Collector エンドポイントだけではネイティブ テレメトリを要求しません。すべてのプロデューサーは、イベントがネイティブ テレメトリ、公式フック、軽量フック、または SDK から来たのかを宣言する必要があります。

### オプションのエージェントフック

まず正確なパスとイベントを調べてください。このコマンドは読み取り専用です。

```bash
.venv/bin/skill-runtime setup
```

Hook のインストールには明示的なフラグが必要です。

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

インストーラはエージェント設定をバックアップし、既存のフックを保存し、Skill Runtime 管理マーカーを持つエントリのみを追加します。フック アダプターは、完全なプロンプトやツール ペイロードではなく、最小限のライフサイクル フィールドを保存します。完了したツール呼び出しでは、正確な `SKILL.md`、標準スキル リソース、およびメモリ内の変更されたファイル パスのみが抽出されます。 raw コマンド、パッチ本体、プロンプト、およびツール出力は、永続化の前に破棄されます。ランタイムがアクティブな間は、アクセス許可が制限された Unix ソケットが高速パスになります。オプションのネイティブ送信側は、Python の起動を回避します。ランタイムがアクティブでない場合、スタンドアロン フェールオープン パスは編集された証拠を `~/.skill-runtime/queue/events.jsonl` に追加します。 `skill-runtime start` は、イベント ID の重複排除を使用してそのキューを再生します。

Codex イベントでは、公式の Hook API (`SessionStart`、`SessionEnd`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PreCompact`、`PostCompact`、`SubagentStart`、 `SubagentStop`、および`Stop`）。現在、Codex はコマンド フックを同期的に実行するため、Skill Runtime は制限されたタイムアウトを持つローカルの Unix ソケット/ネイティブ送信側を使用します。配信失敗はすべて飲み込まれてキューに入れられます。エージェントの決定が変更されることはありません。 [Codex フックの公式ドキュメント](https://developers.openai.com/codex/config-advanced#hooks) を参照してください。

次のコマンドを使用して、管理対象エントリのみを削除します。

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

サーバーはデフォルトで `127.0.0.1` にバインドされます。完全なトランスクリプト メッセージとツール ペイロードはインデックスにコピーされません。一般的な秘密のパターンは、正規化された概要が保存される前に編集されます。

以下を使用して、依存関係のないテスト スイートを実行します。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## リリースエンジニアリング

GitHub アクションは、Python 3.9 ～ 3.13 テスト、JavaScript 検証、ネイティブ送信者のコンパイル、および実際のインストール/開始/ドクター/ストップ/アンインストール スモーク テストを実行します。 `v*` タグは、wheel/sdist パッケージに加えて、チェックサムで保護された Linux および macOS のネイティブ送信側を構築します。 CLI インストーラーは一致するリリース アセットをダウンロードするため、エンド ユーザーはコンパイラーを必要としません。

最初の製品にリンクされた診断実験を実行します。

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

ライフサイクル証拠のギャップ、明示的な障害、不完全な実行、未検証の結果をフォールト挿入し、API と UI で使用されるのと同じ決定論的診断エンジンを評価します。実験ラダー、非干渉テスト、再現性契約については、[PAI-DSW実験計画](docs/pai-dsw-experiment-plan.md) を参照してください。

ホイールを構築した後、次のコマンドを使用して、分離されたパッケージ化されたライフサイクル スモークを実行します。

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

一時的な仮想環境と一時的なホームにインストールし、フックを有効にせずに完全なローカル ライフサイクルを実行し、プロジェクトとエージェント構成が干渉していないことを確認します。

## 実験主導の製品設計

製品の動作は、[実験主導の製品哲学](docs/experiment-driven-product-philosophy.md): 結論の前の証拠、重大度の前の最初の観察可能な境界、フラット ログの前の型付き関係、および確率的支援の前の決定論的再構築によって制約されます。

現在再現可能な現地証拠には以下が含まれます。

- 7/7 ローカル実験ゲートを通過しました。
- 2,400/2,400 のコレクター イベントは入出力の変更なしで受け入れられます。
- 14/14 の決定論的な故障コーパス診断。裏付けのない因果関係の主張はありません。
- 関係診断表現は 13/14 正確、F1 0.963 でしたが、フラット ライフサイクル検索は 1/14 正確、F1 0.080 に達しました。
- 11/11 研究資料のケースでは、観察可能な最も古い境界が最初に配置されます。

これらの結果は、展開の一般化や人間の利益ではなく、メカニズムと表現の選択を検証します。実際のセカンドエージェント研究、クロスプラットフォームのテールレイテンシ、実際の障害キャリブレーション、および参加者診断研究には、依然として証拠のギャップが残っています。

研究の方向性は、隣接する主要な研究にも基づいています。スキルの効果は変動し、後退する可能性があるため、[SkillsBench](https://arxiv.org/abs/2602.12670) と [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) は診断の動機になります。 [Harness-Bench](https://arxiv.org/abs/2605.27922) は、機能を意識したエージェント間の比較を促進します。そして、[執行来歴調査](https://arxiv.org/abs/2606.04990) は、型付けされた証拠関係、出所の追跡、およびプライバシーを意識した監査インフラストラクチャを動機付けます。

## ドキュメント

| ここから始めましょう | 目的 |
|---|---|
| [Getting Started](docs/getting-started.md) | エージェントのインストール、接続、ライブ証拠の検証、トラブルシューティング |
| [建築](docs/architecture.md) | 収集パイプライン、ストレージ境界、証拠エンジン、および信頼モデル |
| [アダプター機能マトリックス](docs/adapter-capability-matrix.md) | エージェント/バージョンごとの正確なシグナルと制限事項 |
| [可観測性プラットフォームのセットアップ](docs/observability-platform-setup.md) | OTLP 互換プラットフォームに接続し、サポートされているトレースをインポートします |
| [ランタイムイベントモデル](docs/runtime-event-model.md) | 安定したイベントの語彙、来歴、関係、および証拠のグレード |
| [UI情報アーキテクチャ](docs/ui-information-architecture.md) | 概要、最初の境界、パノラマ、インスペクター、比較、および Inferred Analysis |

製品および研究の参照: [製品の定義](docs/product-definition.md)、[MVPの仕様](docs/mvp-specification.md)、[可観測性 相互運用性](docs/observability-interoperability.md)、[実験主導の製品哲学](docs/experiment-driven-product-philosophy.md)、[実験結果](docs/experiment-results-2026-07-29.md)、および [研究課題](docs/research-paper-agenda.md)。

## ロードマップ

1. **v0.2.0 — 現在利用可能:** ライブ フェールオープン コレクション、4 つのバージョン管理されたエージェント アダプター、Runtime Overview、第一境界診断、パノラマ、Evidence Inspector、機能認識比較、Inferred Analysis、および OTLP 相互運用性。
2. **次 — アダプターと診断の強化:** より広範なエージェント/バージョンの適用範囲、実際の障害のキャリブレーション、クロスプラットフォームのテール レイテンシーの検証、および参加者の診断研究。
3. **後 — 効果評価:** スキルあり/スキルなしのペア評価を管理し、単一実行の診断とは明示的に分離します。

## プロジェクトのステータス

バージョン`v0.2.0`が公開されました。ランタイムには、インストール定義インベントリ、Codex、Claude Code、Qoder 用の同意主導の公式Hook アダプター、観察専用のOpenCode プラグイン、ラベル付きトランスクリプトフォールバック、アクティブスコープの帰属、正確なファイル/アーティファクトパス、リダクション、個別のソース/関係/推論レイヤー、SQLite が含まれます。ストレージ、保持、確定的診断、ライブ UI、およびクロスラン/クロスエージェント比較。 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave、Datadog のエクスポートはインポートできます。正規化された証拠は、オプトイン OTLP/HTTP を通じてライブでエクスポートできます。

モデル内の候補発見、モデル内部の選択理由、意味論的有効性、および因果関係の結果の主張は、ソースまたは対照実験がその証拠を提供しない限り、明示的にサポートされていないままです。
