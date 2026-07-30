# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · **日本語** ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-インテリジェンス/アクション/ワークフロー/ci.yml)[！[リリース](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-インテリジェンス/リリース/最新)[！[ライセンス](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)]（ライセンス）[![パイソン](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> エージェント スキルの実行が最初に分岐した場所を診断し、証拠を検査します
> あらゆる結論の裏にあるもの。

Agent Skill Runtime Intelligenceは、エージェント スキルのための読み取り専用の実行時証拠および診断システムです。スキル定義、公式エージェント ランタイム イベント、インポートされたトレース、セッション フォールバック、観察可能なワークスペースの結果を組み合わせて、証拠に基づく等級付けを行います。Skill Run Panorama。

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## クイックスタート

最新のスタンドアロン リリースを macOS または Linux にインストールします。

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

クローンはありません。Gitハブアカウント、`sudo`、 またはGitハブ CLI が必要です。インストーラーは、一致する署名付きリリース ペイロードをダウンロードし、SHA-256 チェックサムを検証し、フェールオープン エージェント フックを有効にする前に 1 回確認し、すべてのランタイム データを次の場所に保存します。`~/.skill-runtime`。次に、ローカル ランタイムが起動して開きます。[http://127.0.0.1:4317](http://127.0.0.1:4317)。

あなたはできる[インストーラーを検査する](scripts/install.sh)実行する前に。

または、ソース チェックアウトから直接実行します。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

開ける[http://127.0.0.1:4317](http://127.0.0.1:4317)。のためにCodexで管理されているコマンドを確認して信頼します。`/hooks`、新しいエージェント ターンを 1 つ開始し、次のことを確認します。

```bash
skill-runtime doctor
```

統合は、実際の公式フック イベントを受信した後にのみ **検証済み** になります。設定されたフックは **保留中** として表示され、ライブ証拠として表示されることはありません。

| 製品表面 | 答えは何ですか |
|---|---|
| ランタイムの概要 | どれのSkillRuns注意が必要ですか？ |
| 最初の観測可能な境界 | 証拠が最初に紛失または失敗したのはどこですか? |
| Skill Run Panorama | リクエスト、アクティベーション、リソース、ツール、アーティファクト、結果はどのように結びついたのでしょうか? |
| 証拠調査官 | この主張を裏付けるソース、グレード、ベース、アダプター機能は何ですか? |
| 比較する | 違いは行動的なものですか、それとも可観測性の違いだけですか? |
| 設定 / ドクター | 読み取り、保存、エクスポート、保留、検証とは何ですか? |

## 問題

スキルをインストールしても、エージェントがスキルを発見したことは証明されません。発見は活性化を証明するものではありません。アクティベーションは、完全な命令とリソースがロードされたことを証明するものではありません。実行は、スキルが結果を改善したことを証明するものではありません。

今日、これらの失敗は沈黙していることがよくあります。開発者は次のような疑問を抱いています。

- このエージェントはスキルを利用できましたか?
- このリクエストに対してアクティブ化されましたか?
- どの命令、リファレンス、スクリプト、アセットがロードされましたか?
- どのツール、MCP通話、サブエージェント、ファイル、アーティファクトが関係していましたか?
- どこで実行が失敗、再試行、またはコンテキストが失われましたか?
- スキルは役に立ちましたか? それともコストと待ち時間が増えるだけでしたか?

## 製品の方向性

最初の製品は**ですSkill Run Panorama**:

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

パノラマは、モデルの自己報告ではなく、実際の信号から構築されます。

| ソース | 例 | 証拠 |
|---|---|---|
| スキルファイル | メタデータ、手順、スクリプト、リファレンス、アセット | 観察された |
| ランタイムイベント | スキル呼び出し、ツール呼び出し、サブエージェント、失敗、期間 | 観察された |
| セッションの記録 | プロンプト、メッセージ、ツールの入出力、順序付け | 観察された |
| ワークスペースの成果 | ファイルの変更、Git差分、レポート、生成されたアーティファクト | 観察された |
| 相関 | イベント、リソース、結果間の関係 | 派生または推測 |

## 証拠の規律

のUI実行時ファクトとして推論を決して提示してはなりません:

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

## 初期範囲

ランタイムがサポートするのは、Codex、Claude Code、Qoder、 そしてOpenCode独立したバージョン管理されたアダプターを通じて、以下を提供します。

- インストールされたスキルの検出と検証。
- セッションのインポートとライブローカル観察（サポートされている場合）。
- スキルのアクティブ化、リソースの読み込み、ツール呼び出しのタイムライン。
- 副代理人、MCP、ファイル、およびアーティファクトの関係。
- 期間、トークン、エラー、再試行、およびステータスの概要 (利用可能な場合)。
- 実行リスト、パノラマ DAG、イベント タイムライン、およびノー​​ド インスペクター。

MVP には、マーケットプレイス、ユニバーサル エージェント ランタイム、セキュリティ強制、エンタープライズ ガバナンス、または因果関係の主張は**含まれません**。

## 詳細なインストール

ベースライン実装には、それ以上のランタイム依存関係はありません。Python3.9+。リポジトリのルートから:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

次に開きます[http://127.0.0.1:4317](http://127.0.0.1:4317)。

ワンタイム`install`指示：

1. ユーザー、プロジェクト、およびキャッシュされたプラグインのスキルの場所をスキャンします。
2. 検出しますCodex、Claude Code、Qoder、 そしてOpenCode構成を変更することなく。
3. どのエージェントおよびスキルのパスが読み取られるかを示します。
4. 現在のプラットフォーム用のチェックサム検証済みの低起動ネイティブ センダーをダウンロードし、ローカル C ビルドにフォールバックし、最後にPython送信者は、インストール中に一度、新しいネイティブ バイナリをプリウォームします。
5. 作成します`~/.skill-runtime/config.json`そして地元のSQLite索引。

対話的に実行すると、フェールオープン エージェント フックを追加する前に 1 回尋ねられます。`--no-hooks`トランスクリプトのインポートをラベル付きフォールバックとして保持しますが、`--enable-hooks`明示的な同意を記録し、管理されたエントリのみをインストールします。のためにCodex、 開ける`/hooks`インストール後、管理されているコマンドを正確に確認し、信頼してください。Codex管理対象のエンタープライズ構成の外部に追加されたフックについては、この明示的なレビューが意図的に必要です。新しいエージェント ターンを開始して、次のコマンドを実行します。

```bash
.venv/bin/skill-runtime doctor
```

Qoder起動時にフック設定をロードするため、再起動しますQoder最初のインストール後。OpenCodeグローバル プラグイン ディレクトリからマネージド監視専用プラグインを検出します。再起動OpenCode現在のプロセスがインストール前のものである場合。どちらの統合でも、モデル リクエストの読み取りや変更は行われません。

統合は、データベースが実際のデータを受け取った後にのみ **ライブ** になります。`official_hook`イベント。ただ書くだけ`~/.codex/hooks.json`**保留中**として表示され、接続されていません。`start`コレクター、トランスクリプトフォールバックウォッチャー、保持ワーカーを起動します。SQLite蓄える、そして生きるUI管理されたバックグラウンドプロセスとして。モデルリクエストはプロキシされません。

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

`uninstall`管理対象のフック エントリのみを削除し、Skill Runtime-所有のファイル。それなし`--keep-data`、対話型の確認が必要です (または`--yes`) 削除する前に`~/.skill-runtime`;エージェント セッションとスキル ソースは削除されません。

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

現在、バージョン管理されたインポート プロファイルは OTLP/ を認識します。Phoenix、Langfuse、LangSmith、W&B Weave、 そしてDatadog JSON形。彼らはただ、SkillRunソースが明示的なスキル セマンティクスを保持している場合。一般的なスパン名はアクティベーションの証拠として扱われません。

正規化されたスキル固有のランタイム証拠を任意の場所にエクスポートしますOTLP/HTTPトレースエンドポイント:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

エンドポイントが明示的に構成されていない限り、エクスポートは無効になります。チェックポイント、再試行ステータス、宛先の健全性が [設定] に表示されます。未処理のプロンプト、ツール ペイロード、認証情報、およびスキル リソースのコンテンツはエクスポートされません。認証されたバックグラウンドエクスポートの場合は、標準を提供します`OTEL_EXPORTER_OTLP_HEADERS`以前の環境では`skill-runtime start`;ヘッダーは決して書き込まれませんSkill Runtime構成またはプロセスの引数。

## ライブ実行時の証拠を送信する

`skill-runtime start`ローカルコレクターが含まれます。ネイティブ テレメトリ アダプター、公式フック、軽量フェールオープン フック、およびSDK統合では、単一のイベントまたは制限されたバッチを追加できます。`POST /api/events`:

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

エンドポイントは、永続化の前に共通の認証情報を編集し、次の方法で重複を排除します。`event_id`、別の編集された生のエンベロープを保存し、結果として得られるエンベロープを返します。`skill_run_ids`。`GET /api/collector/schema`サポートされているイベントボキャブラリーと収集モードを公開します。のUI聞く`/api/stream`SSE を使用し、ポーリングは再接続フォールバックとしてのみ使用します。

ソースインジケーターは、主要な実行時の証拠を区別します。`Transcript fallback`そしてインポートされたトレース。コレクター エンドポイントだけではネイティブ テレメトリを要求しません。すべてのプロデューサーは、イベントがネイティブ テレメトリ、公式フック、軽量フック、またはSDK。

### オプションのエージェントフック

まず正確なパスとイベントを調べてください。このコマンドは読み取り専用です。

```bash
.venv/bin/skill-runtime setup
```

フックのインストールには明示的なフラグが必要です。

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

インストーラはエージェント設定をバックアップし、既存のフックを保存し、Skill Runtime管理マーカー。フック アダプターは、完全なプロンプトやツール ペイロードではなく、最小限のライフサイクル フィールドを保存します。ランタイムがアクティブである間は、アクセス許可が制限されます。Unixソケットは高速パスです。オプションのネイティブ送信者は回避しますPython起動する。ランタイムがアクティブでない場合、スタンドアロン フェールオープン パスは編集された証拠を`~/.skill-runtime/queue/events.jsonl`。`skill-runtime start`イベント ID の重複排除を使用してそのキューを再生します。

Codexイベントは公式フックを使用しますAPI(`SessionStart`、`SessionEnd`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`PreCompact`、`PostCompact`、`SubagentStart`、`SubagentStop`、 そして`Stop`）。Codex現在、コマンドフックは同期的に実行されるため、Skill Runtimeローカルを使用しますUnix制限されたタイムアウトを持つソケット/ネイティブ送信者。配信失敗はすべて飲み込まれてキューに入れられます。エージェントの決定が変更されることはありません。を参照してください。[Codex フックの公式ドキュメント](https://developers.openai.com/codex/config-advanced#hooks)。

次のコマンドを使用して、管理対象エントリのみを削除します。

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

サーバーがバインドするのは、`127.0.0.1`デフォルトでは。完全なトランスクリプト メッセージとツール ペイロードはインデックスにコピーされません。一般的な秘密のパターンは、正規化された概要が保存される前に編集されます。

以下を使用して、依存関係のないテスト スイートを実行します。

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## リリースエンジニアリング

Gitハブアクションの実行Python3.9 ～ 3.13 テスト、JavaScript 検証、ネイティブ センダー コンパイル、および実際のインストール/開始/ドクター/ストップ/アンインストール スモーク テスト。あ`v*`tag は、wheel/sdist パッケージに加えて、チェックサムで保護された Linux および macOS のネイティブ センダーを構築します。 CLI インストーラーは一致するリリース アセットをダウンロードするため、エンド ユーザーはコンパイラーを必要としません。

最初の製品にリンクされた診断実験を実行します。

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

ライフサイクル証拠のギャップ、明示的な障害、不完全な実行、および未検証の結果をフォールト挿入し、次に、APIそしてUI。を参照してください。[PAI-DSW実験計画](docs/pai-dsw-experiment-plan.md)実験ラダー、非干渉テスト、再現性契約など。

ホイールを構築した後、次のコマンドを使用して、分離されたパッケージ化されたライフサイクル スモークを実行します。

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

一時的な仮想環境と一時的なホームにインストールし、フックを有効にせずに完全なローカル ライフサイクルを実行し、プロジェクトとエージェント構成が干渉していないことを確認します。

## 実験主導の製品設計

製品の動作は以下によって制限されます。[実験主導の製品哲学](docs/experiment-driven-product-philosophy.md): 結論の前に証拠、重症度の前に最初に観察可能な境界、フラットログの前に型付けされた関係、確率論的な支援の前に決定論的な再構成。

現在再現可能な現地証拠には以下が含まれます。

- 7/7 ローカル実験ゲートを通過しました。
- 2,400/2,400 のコレクター イベントは入出力の変更なしで受け入れられます。
- 14/14 の決定論的な故障コーパス診断。裏付けのない因果関係の主張はありません。
- 関係診断表現は 13/14 正確、F1 0.963 でしたが、フラット ライフサイクル検索は 1/14 正確、F1 0.080 に達しました。
- 11/11 研究資料のケースでは、観察可能な最も古い境界が最初に配置されます。

これらの結果は、展開の一般化や人間の利益ではなく、メカニズムと表現の選択を検証します。実際のセカンドエージェント研究、クロスプラットフォームのテールレイテンシ、実際の障害キャリブレーション、および参加者診断研究には、依然として証拠のギャップが残っています。

研究の方向性は、隣接する主要な研究にも基づいています。[SkillsBench](https://arxiv.org/abs/2602.12670)そして[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)スキルの効果は変化し、後退する可能性があるため、診断を動機付けます。[Harness-Bench](https://arxiv.org/abs/2605.27922)機能を意識したエージェント間の比較を促進します。そして[執行来歴調査](https://arxiv.org/abs/2606.04990)型付けされた証拠関係、出所の追跡、およびプライバシーを意識した監査インフラストラクチャを動機付けます。

## ドキュメント

- [製品の定義](docs/product-definition.md)
- [MVPの仕様](docs/mvp-specification.md)
- [ランタイムイベントモデル](docs/runtime-event-model.md)
- [UI情報アーキテクチャ](docs/ui-information-architecture.md)
- [アダプター機能マトリックス](docs/adapter-capability-matrix.md)
- [可観測性の相互運用性](docs/observability-interoperability.md)
- [可観測性プラットフォームのセットアップ](docs/observability-platform-setup.md)
- [研究と競争環境](docs/research-and-competitive-landscape.md)
- [研究論文の議題](docs/research-paper-agenda.md)
- [実験主導の製品哲学](docs/experiment-driven-product-philosophy.md)
- [実験結果](docs/experiment-results-2026-07-29.md)
- [PAI-DSW実験計画](docs/pai-dsw-experiment-plan.md)

## ロードマップ

1. **v0.1 — 実行時の証拠と診断:** ライブ収集、Skill Run Panorama、第一境界診断、証拠検査、比較、OTLP 相互運用性。
2. **v0.2 — アダプターの強化と診断の研究:** 追加のエージェント バージョン、実際のエージェント間の実験、および参加者の評価。
3. **v0.3 — 効果評価:** スキルあり/スキルなしのペア評価を管理し、単一実行の診断とは別に管理します。

## プロジェクトのステータス

あSkillRun-最初のランタイムが実行可能です: インストールされた定義のインベントリ、Codexトランスクリプトフォールバック、同意主導型の公式フックアダプタCodex、Claude Code、 そしてQoder、観察のみOpenCodeプラグインアダプター、アクティブスコープの帰属、正確なファイル/アーティファクトパス、編集、個別のソース/関係/推論レイヤー、SQLiteストレージ、保持、クロスランおよびクロスエージェント比較、決定論的診断、およびライブパノラマUI。 OTLP/Phoenix、Langfuse、LangSmith、W&B Weave、 そしてDatadog輸出品は輸入可能です。正規化された証拠はオプトインを通じてライブでエクスポート可能OTLP/HTTP。候補の発見、モデル内部の選択理由、意味論的有効性、および因果関係の結果の主張は、明示的にサポートされていないままです。
