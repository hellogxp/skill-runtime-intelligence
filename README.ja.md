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


> 振り向く `SKILL.md` 実行時の期待値を確認可能にします。実際に何があるか見てみましょう
> 行動が最初に分岐した場所、そして判決の背後にある証拠。

Agent Skill Runtime Intelligence は、エージェント スキルのための読み取り専用の実行時証拠および診断システムです。現在のスキル定義から保守的で検査可能な制約を抽出し、それらを実行時のアクティビティと照合し、結果を証拠に基づいて評価したものとして再構築します。 Skill Run Panorama。これは、モデル リクエストをプロキシしたり、エージェント ループを引き継いだりすることなく、公式エージェント イベント、インポートされたトレース、ラベル付きセッション フォールバック、監視可能なワークスペースの結果を組み合わせます。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## クイックスタート

最新リリースをインストールして起動します macOS または Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

クローンもアカウントもありません `sudo`、 または GitHub CLI が必要です。インストーラーはリリース チェックサムを検証し、サポートされているエージェントとスキルを検出し、読み取られるすべてのパスを説明し、監視専用フックを有効にする前に一度質問し、ローカル ファイルを開きます。 UI で [http://127.0.0.1:4317](http://127.0.0.1:4317)。ランタイムデータは以下に留まります `~/.skill-runtime` 明示的にエクスポートを構成しない限り。

あなたはできる [インストーラーを検査する](scripts/install.sh) 実行する前に。

### 初めてのライブを見てみよう SkillRun

1. オプションのフェールオープンを受け入れます Hook インストーラーが尋ねたらセットアップします。
2. エージェントを再起動し、新しいタスクを開始します。で Codexで管理コマンドを確認してください。 `/hooks` 初め;既存のタスクは新しいタスクをホットロードしません Hooks.
3. 通常通りスキルを使用し、統合を確認して、 UI:

```bash
skill-runtime doctor
skill-runtime status
```

統合は、コレクターが実際のランタイム イベントを受信した後にのみ **ライブ** になります。設定されているが監視されていない Hook **保留中** - 生きた証拠として提示されていません。開ける [http://127.0.0.1:4317](http://127.0.0.1:4317)、または、を参照してください。 [入門ガイド](docs/getting-started.md) エージェント固有の手順とトラブルシューティングについては、こちらを参照してください。

ソース チェックアウトから直接実行するには:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 製品表面 | 答えは何ですか |
|---|---|
| Runtime Overview | どれの SkillRuns 注意が必要ですか？ |
| スキル動作チェック | どのチェック可能な指示が満たされたか、レビューが必要か、または評価できないものはどれですか? |
| 実際に何が起こったのか | どの指示、リソース、ツール、成果物、および結果が観察されましたか? |
| First Observable Boundary | 実行固有の証拠が最初に欠落または失敗したのはどこですか? |
| Skill Run Panorama | リクエスト、アクティベーション、リソース、ツール、アーティファクト、結果はどのように結びついたのでしょうか? |
| Evidence Inspector | この主張を裏付けるソース、グレード、ベース、アダプター機能は何ですか? |
| 比較する | 違いは行動的なものですか、それとも可観測性の違いだけですか? |
| Inferred Analysis | どのような証拠に基づいた説明や次の調査がもっともらしいでしょうか? |
| 設定 / ドクター | 読み取り、保存、エクスポート、保留、検証とは何ですか? |

## 仕組み

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime すでに使用しているワークフローを観察します。バージョン管理されたアダプターは、エージェントネイティブのイベントを安定したスキルのライフサイクルに変えますが、生のソースエンベロープ、正規化されたイベント、関係、および推論は分離されたままになります。診断エンジンは、その証拠に照らして明示的なスキル制約をチェックし、観察可能な最も早い逸脱を特定し、システム的なアダプターの盲点を実行固有の結果から切り離します。モデルの意図や因果関係の有効性を発明するものではありません。

| データソース | 役割 | 鮮度 | UI ラベル |
|---|---|---|---|
| 公式エージェントのフック / プラグイン / SDK イベント | 一次ライフサイクル、ツール、サブエージェント、および最終証拠 | ライブ | `Official hook` / `Native telemetry` |
| スキルファイルと観察可能なワークスペースの成果 | 定義、リソース、ファイル、アーティファクト、およびテストの証拠 | ライブスナップショット/インデックス付き | `Observed` |
| セッションの記録 | エージェントが十分なランタイムを公開しない場合の互換性フォールバック API | ほぼライブまたは過去のもの | `Transcript fallback` |
| OTLP とサポートされるトレース エクスポート | 相互運用性と履歴インポート | ライブエクスポート/バッチインポート | ソースプロファイルを表示 |
| 決定的な相関関係 | イベントを SkillRun ソース事実を変更せずに | 摂取時 | `Derived` |
| セマンティック支援 | 説明と調査提案のみ | オンデマンド | `Inferred` |

サポートされているファーストパーティ アダプタは、個別にバージョン管理されています。

| エージェント | 一次統合 | 後退する | アクティベーションの可視性 |
|---|---|---|---|
| Codex | 公式コマンド Hooks | セッションのインポート | によって公開された場合の明示的なアクティベーション Hook イベント |
| Claude Code | 正式 Hooks | セッションのインポート | 明示的スキルツールとスラッシュコマンドの証拠が公開された場合 |
| Qoder | 公式コマンド Hooks | 現地の記録 | スキルツールによって公開された場合の明示的なアクティベーション |
| OpenCode | 観測専用グローバルプラグイン | 現地の記録 | スキルツールのコールバックが公開されている場合 |

正確な機能制限については、次の文書に記載されています。 [アダプター機能マトリックス](docs/adapter-capability-matrix.md)。サポートされていないステージや監視されていないステージは、失敗に変換されずに表示されたままになります。

## 問題

スキルをインストールしても、エージェントがスキルを発見したことは証明されません。発見は活性化を証明するものではありません。アクティベーションは、完全な命令とリソースがロードされたことを証明するものではありません。指示をロードしても、エージェントがその指示に従ったかどうかは証明されません。実行は、スキルが結果を改善したことを証明するものではありません。

現在、こうした失敗は沈黙していることが多い。開発者は次のような疑問を抱いています。

- このエージェントはスキルを利用できましたか?
- このリクエストに対してアクティブ化されましたか?
- どの命令、リファレンス、スクリプト、アセットがロードされましたか?
- どの明示的なスキル要件が守られているか、守られていないか、または評価が不可能ですか?
- どのツール、 MCP 通話、サブエージェント、ファイル、アーティファクトが関係していましたか?
- どこで実行が失敗、再試行、またはコンテキストが失われましたか?
- スキルは役に立ちましたか? それともコストと待ち時間が増えるだけでしたか?

## スキル別診断

主な診断オブジェクトは、 `SkillRun`エージェント セッション全体ではありません。

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

の UI ライフサイクルを順序付け、型付けし、証拠を等級付けした状態に保ちます。アクティベーション テレメトリが見つからない場合は、「観察されない」または「サポートされていない」ことを意味します。エージェントが確実にスキルをスキップしたという意味ではありません。

## 証拠の規律

の UI 実行時ファクトとして推論を決して提示してはなりません:

- **観察** — ソース イベントまたはファイルに明示的に存在します。
- **派生** — 観察された証拠から決定論的に関連付けられています。
- **推測** — 不確実性はあるものの、もっともらしい説明。
- **実験** — 制御されたペア評価を通じて測定された効果。

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

ランタイムがサポートするのは、 Codex、 Claude Code、 Qoder、 そして OpenCode 独立したバージョン管理されたアダプターを通じて、以下を提供します。

- インストールされたスキルの検出と検証。
- リアルタイムオフィシャル Hook/plugin コレクションとラベル付きセッション フォールバック。
- スキルのアクティブ化、リソースの読み込み、ツール呼び出しのタイムライン。
- 副代理人、 MCP、ファイル、およびアーティファクトの関係。
- 期間、トークン、エラー、再試行、およびステータスの概要 (利用可能な場合)。
- 現在のデータから抽出された保守的な動作制約 `SKILL.md`;
- 証拠に基づく適合性、検証、および実行時障害チェック。
- 具体的な指示、リソース、ツール、成果物、および成果の目録。
- Runtime Overview 実行結果から分離された体系的なカバレッジ制限。
- 第一境界診断。
- パノラマ DAG、イベント タイムライン、証拠検査官。
- 機能を認識した同一エージェントとエージェント間の比較。
- 別の Inferred Analysis 実行時のファクトを書き換えることができない表面。
- オプトイン OTLP/HTTP エクスポートとサポートされている可観測性トレースのインポート。

MVP には、マーケットプレイス、ユニバーサル エージェント ランタイム、セキュリティ強制、エンタープライズ ガバナンス、または因果関係の主張は**含まれません**。

## 詳細なインストール

サポートされている最短のパスについては、次の 1 行のリリース インストーラーを使用してください。 [クイックスタート](#quick-start)。完全な初回実行フロー、エージェント固有の再起動/信頼手順、プライバシー動作、およびトラブルシューティングは、 [入門ガイド](docs/getting-started.md)。

開発の場合、ベースライン実装には実行時の依存関係がありません。 Python 3.9+。リポジトリのルートから:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

次に開きます [http://127.0.0.1:4317](http://127.0.0.1:4317)。

ワンタイム `install` 指示：

1. ユーザー、プロジェクト、およびキャッシュされたプラグインのスキルの場所をスキャンします。
2. 検出します Codex、 Claude Code、 Qoder、 そして OpenCode 構成を変更することなく。
3. どのエージェントおよびスキルのパスが読み取られるかを示します。
4. 現在のプラットフォーム用のチェックサム検証済みの低起動ネイティブ センダーをダウンロードし、ローカル C ビルドにフォールバックし、最後に Python 送信者は、インストール中に一度、新しいネイティブ バイナリをプリウォームします。
5. 作成します `~/.skill-runtime/config.json` そして地元の SQLite 索引。

最初のインデックスは、既存の互換性のあるエージェント セッションをインポートします。長期間使用されているワークステーションでは、新規インストールよりも時間がかかることがあります。後の開始は増分的であり、 UI バックグラウンド更新の実行中に利用可能になります。

対話的に実行すると、フェールオープン エージェント フックを追加する前に 1 回尋ねられます。 `--no-hooks` トランスクリプトのインポートをラベル付きフォールバックとして保持しますが、 `--enable-hooks` 明示的な同意を記録し、管理されたエントリのみをインストールします。のために Codex、 開ける `/hooks` インストール後、管理されているコマンドを正確に確認し、信頼してください。 Codex 管理対象のエンタープライズ構成の外部に追加されたフックについては、この明示的なレビューが意図的に必要です。新しいことを始める Codex を信頼した後のタスク/セッション Hook次に、次を実行します。

```bash
.venv/bin/skill-runtime doctor
```

Qoder 負荷 Hook 起動時の設定なので再起動してください Qoder 最初のインストール後。 OpenCode グローバル プラグイン ディレクトリからマネージド監視専用プラグインを検出します。再起動 OpenCode 現在のプロセスがインストール前のものである場合。どちらの統合でも、モデル リクエストの読み取りや変更は行われません。

統合は、データベースが実際のデータを受け取った後にのみ **ライブ** になります。 `official_hook` イベント。ただ書くだけ `~/.codex/hooks.json` **保留中**として表示され、接続されていません。 `start` コレクター、トランスクリプトフォールバックウォッチャー、保持ワーカーを起動します。 SQLite 蓄える、そして生きる UI 管理されたバックグラウンドプロセスとして。モデルリクエストはプロキシされません。

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

`uninstall` 管理対象のみを削除します Hook エントリーと Skill Runtime-所有のファイル。それなし `--keep-data`、対話型の確認が必要です (または `--yes`) 削除する前に `~/.skill-runtime`;エージェント セッションとスキル ソースは削除されません。

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

現在、バージョン管理されたインポート プロファイルは OTLP/ を認識します。Phoenix、 Langfuse、 LangSmith、 W&B Weave、 そして Datadog JSON 形。彼らはただ、 SkillRun ソースが明示的なスキル セマンティクスを保持している場合。一般的なスパン名はアクティベーションの証拠として扱われません。

正規化されたスキル固有のランタイム証拠を任意の場所にエクスポートします OTLP/HTTP トレースエンドポイント:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

エンドポイントが明示的に構成されていない限り、エクスポートは無効になります。チェックポイント、再試行ステータス、宛先の健全性が [設定] に表示されます。未処理のプロンプト、ツール ペイロード、認証情報、およびスキル リソースの内容はエクスポートされません。認証されたバックグラウンドエクスポートの場合は、標準を提供します `OTEL_EXPORTER_OTLP_HEADERS` 以前の環境では `skill-runtime start`;ヘッダーは決して書き込まれません Skill Runtime 構成またはプロセスの引数。

## ライブ実行時の証拠を送信する

`skill-runtime start` ローカルコレクターが含まれます。ネイティブ テレメトリ アダプター、公式フック、軽量フェールオープン フック、および SDK 統合では、単一のイベントまたは制限されたバッチを追加できます。 `POST /api/events`:

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

エンドポイントは、永続化の前に共通の認証情報を編集し、次の方法で重複を排除します。 `event_id`、別の編集された生のエンベロープを保存し、結果として得られるエンベロープを返します。 `skill_run_ids`。 `GET /api/collector/schema` サポートされているイベント語彙と収集モードを公開します。の UI 聞く `/api/stream` SSE を使用し、ポーリングは再接続フォールバックとしてのみ使用します。

ソースインジケーターは、主要な実行時の証拠を区別します。 `Transcript fallback` そしてインポートされたトレース。コレクター エンドポイントだけではネイティブ テレメトリを要求しません。すべてのプロデューサーは、イベントがネイティブ テレメトリ、公式フック、軽量フック、または SDK。

### オプションのエージェントフック

まず正確なパスとイベントを調べてください。このコマンドは読み取り専用です。

```bash
.venv/bin/skill-runtime setup
```

Hook インストールには明示的なフラグが必要です。

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

インストーラはエージェント設定をバックアップし、既存のフックを保存し、 Skill Runtime 管理マーカー。フック アダプターは、完全なプロンプトやツール ペイロードではなく、最小限のライフサイクル フィールドを保存します。完了したツール呼び出しについては、正確な内容のみが抽出されます `SKILL.md`、標準スキル リソース、およびメモリ内の変更されたファイル パス。 raw コマンド、パッチ本体、プロンプト、およびツール出力は、永続化の前に破棄されます。ランタイムがアクティブである間は、アクセス許可が制限されます。 Unix ソケットは高速パスです。オプションのネイティブ送信者は回避します Python 起動する。ランタイムがアクティブでない場合、スタンドアロン フェールオープン パスは編集された証拠を `~/.skill-runtime/queue/events.jsonl`。 `skill-runtime start` イベント ID の重複排除を使用してそのキューを再生します。

Codex イベントでは公式を使用します Hook API (`SessionStart`、 `SessionEnd`、 `UserPromptSubmit`、 `PreToolUse`、 `PostToolUse`、 `PreCompact`、 `PostCompact`、 `SubagentStart`、 `SubagentStop`、 そして `Stop`）。 Codex 現在、コマンドフックは同期的に実行されるため、 Skill Runtime ローカルを使用します Unix 制限されたタイムアウトを持つソケット/ネイティブ送信者。配信失敗はすべて飲み込まれてキューに入れられます。エージェントの決定が変更されることはありません。を参照してください。 [Codex フックの公式ドキュメント](https://developers.openai.com/codex/config-advanced#hooks)。

次のコマンドを使用して、管理対象エントリのみを削除します。

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

サーバーがバインドするのは、 `127.0.0.1` デフォルトでは。完全なトランスクリプト メッセージとツール ペイロードはインデックスにコピーされません。一般的な秘密のパターンは、正規化された概要が保存される前に編集されます。

以下を使用して、依存関係のないテスト スイートを実行します。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## リリースエンジニアリング

GitHub アクションの実行 Python 3.9 ～ 3.13 テスト、JavaScript 検証、ネイティブ センダー コンパイル、および実際のインストール/開始/ドクター/ストップ/アンインストール スモーク テスト。あ `v*` タグはホイール/SDIST パッケージとチェックサム保護をビルドします Linux そして macOS ネイティブの送信者。 CLI インストーラーは一致するリリース アセットをダウンロードするため、エンド ユーザーはコンパイラーを必要としません。

最初の製品にリンクされた診断実験を実行します。

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

ライフサイクル証拠のギャップ、明示的な障害、不完全な実行、および未検証の結果をフォールト挿入し、次に、 API そして UI。を参照してください。 [PAI-DSW実験計画](docs/pai-dsw-experiment-plan.md) 実験ラダー、非干渉テスト、再現性契約など。

ホイールを構築した後、次のコマンドを使用して、分離されたパッケージ化されたライフサイクル スモークを実行します。

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

一時的な仮想環境と一時的なホームにインストールし、フックを有効にせずに完全なローカル ライフサイクルを実行し、プロジェクトとエージェント構成が干渉していないことを確認します。

## 実験主導の製品設計

製品の動作は、実験主導の 4 つの制約に従います。結論の前に証拠、重大度の前に最初に観察可能な境界、フラット ログの前に型指定された関係、確率論的な支援の前に決定論的な再構築です。

再現可能な証拠とその制限は、 [実験レポート](docs/experiment-results-2026-07-29.md)。制限された結果には次のものが含まれます。

- 2,400/2,400 のコレクター イベントは入出力の変更なしで受け入れられます。
- 14/14 の決定論的な故障コーパス診断。裏付けのない因果関係の主張はありません。
- 関係診断表現は 13/14 正確、F1 0.963 でしたが、フラット ライフサイクル検索は 1/14 正確、F1 0.080 に達しました。
- プライバシーに配慮した実際の監査ですが、検証済みの結果、バランスの取れたエージェント間の対応範囲、および人間によるラベルが欠落しているため、製品効果の確認を目的とした主張には明らかに不適切です。

これらの結果は、展開の一般化や人間の利益ではなく、メカニズムと表現の選択を検証します。実際のセカンドエージェント研究、クロスプラットフォームのテールレイテンシー、実際の障害キャリブレーション、および参加者診断研究には、依然として証拠のギャップが残っています。

研究の方向性は、隣接する主要な研究にも基づいています。 [SkillsBench](https://arxiv.org/abs/2602.12670) そして [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) スキルの効果は変化し、後退する可能性があるため、診断の動機付け。 [Harness-Bench](https://arxiv.org/abs/2605.27922) 機能を意識したエージェント間の比較を促進します。そして [執行来歴調査](https://arxiv.org/abs/2606.04990) 型付けされた証拠関係、出所の追跡、およびプライバシーを意識した監査インフラストラクチャを動機付けます。

## ドキュメント

| ここから始めましょう | 目的 |
|---|---|
| [Getting Started](docs/getting-started.md) | エージェントのインストール、接続、ライブ証拠の検証、トラブルシューティング |
| [建築](docs/architecture.md) | 収集パイプライン、ストレージ境界、証拠エンジン、および信頼モデル |
| [アダプター機能マトリックス](docs/adapter-capability-matrix.md) | エージェント/バージョンごとの正確なシグナルと制限事項 |
| [可観測性プラットフォームのセットアップ](docs/observability-platform-setup.md) | OTLP 互換プラットフォームに接続し、サポートされているトレースをインポートします |
| [ランタイムイベントモデル](docs/runtime-event-model.md) | 安定したイベントの語彙、来歴、関係、および証拠のグレード |
| [UI情報アーキテクチャ](docs/ui-information-architecture.md) | 概要、最初の境界、パノラマ、インスペクター、比較、および Inferred Analysis |
| [変更履歴](CHANGELOG.md) | バージョン管理されたユーザーに表示される変更 |
| [v0.3.0 リリースノート](docs/releases/v0.3.0.md) | アップグレードのガイダンス、ハイライト、既知の制限事項 |

製品および研究の参考資料: [製品の定義](docs/product-definition.md)、 [MVPの仕様](docs/mvp-specification.md)、 [可観測性 相互運用性](docs/observability-interoperability.md)、 [実験結果](docs/experiment-results-2026-07-29.md)、そして [研究課題](docs/research-paper-agenda.md)。

## コミュニティとガバナンス

- 読む [貢献する](CONTRIBUTING.md) 証拠のセマンティクス、アダプター、または製品の動作を変更する前に。
- フォローしてください [行動規範](CODE_OF_CONDUCT.md) すべてのプロジェクトスペースで。
- 脆弱性を非公開で報告するには、 [セキュリティポリシー](SECURITY.md)、公的な問題ではありません。
- 構造化されたものを使用する [問題トラッカー](https://github.com/hellogxp/skill-runtime-intelligence/issues) 再現可能なバグや範囲を絞った機能の提案について。プライベート ランタイム データベースやセッション トランスクリプトを決して接続しないでください。

## ロードマップ

1. **v0.3.0 — 次のリリース:** チェック可能なスキル動作制約、具体的なランタイム アクティビティ、証拠に基づく評価、システム カバレッジ診断、および既存のライブ パノラマと比較のワークフロー。
2. **次 — アダプターと診断の強化:** より広範なエージェント/バージョンの適用範囲、実際の障害のキャリブレーション、クロスプラットフォームのテール レイテンシーの検証、および参加者の診断研究。
3. **後 — 効果評価:** スキルあり/スキルなしのペア評価を管理し、単一実行の診断とは明示的に分離します。

## プロジェクトのステータス

現在のソースツリーのターゲット `v0.3.0`;上のリリース バッジを使用して、最新の公開済みビルドを識別します。ランタイムには、チェック可能なスキルの動作制約、具体的なアクティビティの概要、インストールされた定義のインベントリ、同意に基づく公式が含まれます Hook のアダプター Codex、 Claude Code、 そして Qoder、観察のみ OpenCode プラグイン、ラベル付きトランスクリプトフォールバック、アクティブスコープの帰属、正確なファイル/アーティファクトパス、編集、個別のソース/関係/推論レイヤー、 SQLite ストレージ、保持、確定診断、ライブ UI、およびクロスラン/クロスエージェントの比較。 OTLP/Phoenix、 Langfuse、 LangSmith、 W&B Weave、 そして Datadog 輸出品は輸入可能です。正規化された証拠はオプトインを通じてライブでエクスポート可能 OTLP/HTTP。

モデル内の候補発見、モデル内部の選択理由、意味論的有効性、および因果関係の結果の主張は、ソースまたは対照実験がその証拠を提供しない限り、明示的にサポートされていないままです。
