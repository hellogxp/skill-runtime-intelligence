# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
**한국어** · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> 에이전트 스킬 실행이 처음으로 분기된 위치를 진단하고 증거를 조사합니다.
> 모든 결론 뒤에.

Agent Skill Runtime Intelligence는 에이전트 스킬에 대한 읽기 전용 런타임 증거 및 진단 시스템입니다. 스킬 정의, 공식 에이전트 런타임 이벤트, 가져온 추적, 세션 대체 및 관찰 가능한 작업 공간 결과를 증거 등급 Skill Run Panorama로 결합합니다.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 빠른 시작

macOS 또는 Linux에 최신 릴리스를 설치하고 시작합니다.

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

복제, 계정, `sudo` 또는 GitHub CLI이 필요하지 않습니다. 설치 프로그램은 릴리스 체크섬을 확인하고, 지원되는 에이전트 및 스킬을 감지하고, 읽을 모든 경로를 설명하고, 관찰 전용 후크를 활성화하기 전에 한 번 묻고, [http://127.0.0.1:4317](http://127.0.0.1:4317)에서 로컬 UI를 엽니다. 내보내기를 명시적으로 구성하지 않는 한 런타임 데이터는 `~/.skill-runtime` 아래에 유지됩니다.

실행하기 전에 [설치 프로그램을 검사하다](scripts/install.sh)할 수 있습니다.

### 첫 번째 라이브를 시청하세요 SkillRun

1. 설치 프로그램이 요청할 때 선택적인 오류 개방 Hook 설정을 수락합니다.
2. 에이전트를 다시 시작하고 새 작업을 시작합니다. Codex에서는 먼저 `/hooks`의 관리 명령을 검토하세요. 기존 작업은 새로운 Hook를 핫로드하지 않습니다.
3. 스킬을 정상적으로 사용한 다음 통합을 확인하고 UI를 엽니다.

```bash
skill-runtime doctor
skill-runtime status
```

Collector가 실제 런타임 이벤트를 수신한 후에만 통합이 **라이브**됩니다. 구성되었지만 관찰되지 않은 Hook는 **보류 중**이며 실제 증거로 제시되지 않습니다. 에이전트별 지침 및 문제 해결을 보려면 [http://127.0.0.1:4317](http://127.0.0.1:4317)을 열거나 [시작하기 가이드](docs/getting-started.md)를 참조하세요.

소스 체크아웃에서 직접 실행하려면:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| 제품 표면 | 답변 내용 |
|---|---|
| Runtime Overview | 어떤 SkillRuns에 주의가 필요합니까? |
| First Observable Boundary | 증거가 처음으로 누락되거나 실패한 곳은 어디입니까? |
| Skill Run Panorama | 요청, 활성화, 리소스, 도구, 아티팩트 및 결과가 어떻게 연결되었나요? |
| Evidence Inspector | 이 주장을 뒷받침하는 소스, 등급, 기준 및 어댑터 기능은 무엇입니까? |
| 비교하다 | 차이점은 행동상의 차이인가요, 아니면 관찰 가능성의 차이인가요? |
| Inferred Analysis | 어떤 증거에 근거한 설명이나 다음 조사가 타당합니까? |
| 설정 / 의사 | 읽고, 저장하고, 내보내고, 보류하고, 확인하는 작업은 무엇입니까? |

## 작동 원리

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime는 이미 사용하고 있는 작업 흐름을 관찰합니다. 버전이 지정된 어댑터는 에이전트 기본 이벤트를 안정적인 스킬 수명 주기로 전환하는 동시에 원시 소스 엔벨로프, 정규화된 이벤트, 관계 및 추론은 별도로 유지됩니다. 진단 엔진은 먼저 증거가 누락되거나 실패하는 가장 빠른 경계를 식별합니다. 모델 의도나 인과적 효율성을 만들어내지는 않습니다.

| 데이터 소스 | 역할 | 선도 | UI 라벨 |
|---|---|---|---|
| 공식 에이전트 후크 / 플러그인 / SDK 이벤트 | 기본 수명주기, 도구, 하위 에이전트 및 최종 증거 | 살다 | `Official hook` / `Native telemetry` |
| 기술 파일 및 관찰 가능한 작업 공간 결과 | 정의, 리소스, 파일, 아티팩트 및 테스트 증거 | 라이브 스냅샷/인덱싱됨 | `Observed` |
| 세션 기록 | 에이전트가 충분한 런타임을 노출하지 않는 경우 호환성 대체 API | 실시간 또는 과거 | `Transcript fallback` |
| OTLP 및 지원되는 추적 내보내기 | 상호 운용성 및 역사적 가져오기 | 실시간 내보내기/일괄 가져오기 | 표시된 소스 프로필 |
| 결정론적 상관관계 | 소스 사실을 변경하지 않고 이벤트를 SkillRun에 연결합니다. | 섭취시 | `Derived` |
| 의미론적 지원 | 설명 및 조사 제안만 | 주문형 | `Inferred` |

지원되는 자사 어댑터는 독립적으로 버전이 지정됩니다.

| 대리인 | 기본 통합 | 대체 | 활성화 가시성 |
|---|---|---|---|
| Codex | 공식 명령 Hooks | 세션 가져오기 | Hook 이벤트에 의해 노출된 경우 명시적 활성화 |
| Claude Code | 공식 Hook | 세션 가져오기 | 노출된 경우 명시적 스킬 도구 및 슬래시 명령 증거 |
| Qoder | 공식 명령 Hooks | 지역 기록 | 스킬 도구에 노출되면 명시적으로 활성화됩니다. |
| OpenCode | 관찰 전용 전역 플러그인 | 지역 기록 | 노출된 스킬 도구 콜백 |

정확한 기능 제한은 [어댑터 기능 매트릭스](docs/adapter-capability-matrix.md)에 문서화되어 있습니다. 지원되지 않고 관찰되지 않는 단계는 실패로 변환되는 대신 계속 표시됩니다.

## 문제

스킬을 설치한다고 해서 에이전트가 스킬을 발견했다는 사실이 입증되는 것은 아닙니다. 검색은 활성화를 증명하지 않습니다. 활성화는 전체 지침과 리소스가 로드되었음을 증명하지 않습니다. 실행은 스킬이 결과를 향상시켰다는 것을 증명하지 않습니다.

오늘날 이러한 실패는 종종 조용합니다. 개발자는 다음과 같은 질문을 남깁니다.

- 이 상담원이 스킬을 사용할 수 있었나요?
- 이 요청에 대해 활성화되었습니까?
- 어떤 지침, 참조, 스크립트 및 자산이 로드되었습니까?
- 어떤 도구, MCP 호출, 하위 에이전트, 파일 및 아티팩트가 관련되어 있습니까?
- 실행이 실패하거나 재시도되거나 컨텍스트가 손실된 위치는 어디입니까?
- 기술이 도움이 되었나요? 아니면 비용과 대기 시간만 추가되었나요?

## 스킬별 진단

기본 진단 개체는 전체 에이전트 세션이 아닌 `SkillRun`입니다.

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

UI는 수명주기를 정렬하고, 입력하고, 증거 등급을 유지합니다. 누락된 활성화 원격 측정은 "관찰되지 않음" 또는 "지원되지 않음"을 의미합니다. 이는 에이전트가 확실히 스킬을 건너뛰었다는 의미는 아닙니다.

## 증거 규율

UI는 추론을 런타임 사실로 제시해서는 안 됩니다.

- **관찰됨** — 소스 이벤트 또는 파일에 명시적으로 존재합니다.
- **파생** — 관찰된 증거로부터 결정론적으로 연결됩니다.
- **추론** — 불확실성이 있지만 그럴듯한 설명입니다.
- **실험** — 통제된 쌍별 평가를 통해 측정된 효과입니다.

단일 추적은 실행 속성을 지원할 수 있습니다. 인과적 유효성을 증명할 수는 없습니다. "이 기술로 성공률이 향상되었습니다"와 같은 주장에는 기술 유무에 대한 반복적인 평가가 필요합니다.

## 제품 원리

- 로컬, 하이브리드 및 팀 연결 배포를 통해 기본적으로 비공개입니다.
- 읽기 전용 관찰; 에이전트 루프를 인계받지 마십시오.
- 모델 프록시도 없고 필수 클라우드 서비스도 없습니다.
- 기본 제품에는 차단, 승인 게이트 또는 정책 시행이 없습니다.
- 명시적인 출처 및 증거 등급.
- 점진적 공개: 간단한 설명이 우선이고 요청 시 원시 이벤트가 제공됩니다.
- 상담원 성적표 형식 변경을 위한 어댑터 기반 지원.

## 현재 범위

런타임은 버전이 지정된 독립적인 어댑터를 통해 Codex, Claude Code, Qoder 및 OpenCode를 지원하며 다음을 제공합니다.

- 설치된 스킬 발견 및 검증;
- 실시간 공식 Hook/플러그인 컬렉션 및 레이블이 지정된 세션 대체;
- 기술 활성화, 리소스 로딩 및 도구 호출 타임라인
- 하위 에이전트, MCP, 파일 및 아티팩트 관계;
- 기간, 토큰, 오류, 재시도 및 상태 요약(사용 가능한 경우)
- Runtime Overview 및 1차 경계 진단;
- 파노라마 DAG, 이벤트 타임라인 및 증거 조사관
- 기능 인식 동일 에이전트 및 교차 에이전트 비교
- 런타임 팩트를 다시 쓸 수 없는 별도의 Inferred Analysis 표면;
- 옵트인 OTLP/HTTP 내보내기 및 관찰 가능성 추적 가져오기 지원.

MVP에는 마켓플레이스, 범용 에이전트 런타임, 보안 시행, 기업 거버넌스 또는 인과관계 주장이 포함되지 **않습니다**.

## 상세한 설치

지원되는 최단 경로의 경우 [빠른 시작](#quick-start)의 한 줄 릴리스 설치 프로그램을 사용하세요. 전체 첫 실행 흐름, 에이전트별 다시 시작/신뢰 단계, 개인 정보 보호 동작 및 문제 해결이 [시작하기 가이드](docs/getting-started.md)에 실시간으로 제공됩니다.

개발을 위해 기본 구현에는 Python 3.9+ 이상의 런타임 종속성이 없습니다. 저장소 루트에서:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

그런 다음 [http://127.0.0.1:4317](http://127.0.0.1:4317)를 엽니다.

일회성 `install` 명령:

1. 사용자, 프로젝트 및 캐시된 플러그인 스킬 위치를 스캔합니다.
2. 구성을 변경하지 않고 Codex, Claude Code, Qoder 및 OpenCode를 감지합니다.
3. 읽을 에이전트 및 스킬 경로를 표시합니다.
4. 현재 플랫폼에 대해 체크섬 확인된 낮은 시작 네이티브 발신자를 다운로드하고 로컬 C 빌드로 대체한 다음 마지막으로 Python 발신자를 다운로드하고 설치 중에 한 번 새로운 네이티브 바이너리를 미리 준비합니다.
5. `~/.skill-runtime/config.json` 및 로컬 SQLite 색인을 생성합니다.

대화형으로 실행할 경우 페일오픈 에이전트 후크를 추가하기 전에 한 번 묻습니다. `--no-hooks`는 레이블이 지정된 대체 항목으로 성적표 가져오기를 유지하는 반면, `--enable-hooks`은 명시적인 동의를 기록하고 관리되는 항목만 설치합니다. Codex의 경우 설치 후 `/hooks`를 열고 정확한 관리 명령을 검토한 후 신뢰하세요. Codex는 관리되는 엔터프라이즈 구성 외부에 추가된 후크에 대해 의도적으로 이러한 명시적인 검토를 요구합니다. Hook를 신뢰한 후 새 Codex 작업/세션을 시작한 후 다음을 실행하세요.

```bash
.venv/bin/skill-runtime doctor
```

Qoder는 시작 시 Hook 구성을 로드하므로 처음 설치한 후 Qoder를 다시 시작하세요. OpenCode는 전역 플러그인 디렉터리에서 관리형 관찰 전용 플러그인을 검색합니다. 현재 프로세스가 설치보다 이전인 경우 OpenCode를 다시 시작하세요. 통합은 모델 요청을 읽거나 변경하지 않습니다.

데이터베이스가 실제 `official_hook` 이벤트를 수신한 후에만 통합이 **라이브** 상태가 됩니다. `~/.codex/hooks.json`만 쓰면 **보류 중**으로 표시되고 연결되지 않습니다. `start` 수집기, 기록 대체 감시자, 보존 작업자, SQLite 저장소 및 라이브 UI를 관리형 백그라운드 프로세스로 실행합니다. 모델 요청이 프록시되지 않습니다.

수명주기 명령:

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

`uninstall`는 관리되는 Hook 항목과 Skill Runtime 소유 파일만 제거합니다. `--keep-data`가 없으면 `~/.skill-runtime`를 제거하기 전에 대화형 확인(또는 `--yes`)이 필요합니다. 상담원 세션과 스킬 소스는 제거되지 않습니다.

별도로 색인을 생성하고 검색하려면 다음 안내를 따르세요.

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

주류 관찰 시스템에서 기존 추적 내보내기를 가져옵니다.

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

버전이 지정된 가져오기 프로필은 현재 OTLP/Phoenix, Langfuse, LangSmith, W&B Weave 및 Datadog JSON 모양을 인식합니다. 소스가 명시적인 스킬 의미를 전달하는 경우에만 SkillRun를 생성합니다. 일반 스팬 이름은 활성화 증거로 처리되지 않습니다.

정규화된 스킬별 런타임 증거를 OTLP/HTTP 추적 엔드포인트로 내보냅니다.

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

엔드포인트가 명시적으로 구성되지 않으면 내보내기가 비활성화됩니다. 체크포인트, 재시도 상태, 대상 상태는 설정에 표시됩니다. 원시 프롬프트, 도구 페이로드, 자격 증명 및 스킬 리소스 콘텐츠는 내보내지지 않습니다. 인증된 백그라운드 내보내기를 위해서는 `skill-runtime start` 이전 환경에 표준 `OTEL_EXPORTER_OTLP_HEADERS`을 제공하세요. 헤더는 Skill Runtime 구성 또는 프로세스 인수에 기록되지 않습니다.

## 실시간 런타임 증거 보내기

`skill-runtime start`에는 로컬 수집기가 포함됩니다. 기본 원격 측정 어댑터, 공식 후크, 경량 페일오픈 후크 및 SDK 통합은 단일 이벤트 또는 제한된 배치를 `POST /api/events`에 추가할 수 있습니다.

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

엔드포인트는 지속성 전에 일반 자격 증명을 수정하고, `event_id`로 중복을 제거하고, 수정된 별도의 원시 봉투를 보존하고, 결과 `skill_run_ids`를 반환합니다. `GET /api/collector/schema`는 지원되는 이벤트 어휘 및 수집 모드를 노출합니다. UI는 SSE를 사용하여 `/api/stream`를 수신하며 폴링은 재연결 폴백으로만 사용됩니다.

소스 표시기는 기본 런타임 증거를 `Transcript fallback` 및 가져온 추적과 구별합니다. Collector 엔드포인트만으로는 기본 원격 측정을 주장하지 않습니다. 모든 생산자는 해당 이벤트가 기본 원격 측정, 공식 후크, 경량 후크 또는 SDK에서 나온 것인지 선언해야 합니다.

### 선택적 에이전트 후크

먼저 정확한 경로와 이벤트를 검사하세요. 이 명령은 읽기 전용입니다.

```bash
.venv/bin/skill-runtime setup
```

Hook 설치에는 명시적인 플래그가 필요합니다.

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

설치 프로그램은 에이전트 구성을 백업하고 기존 후크를 유지하며 Skill Runtime 관리 표시가 있는 항목만 추가합니다. 후크 어댑터는 전체 프롬프트나 도구 페이로드가 아닌 최소한의 수명 주기 필드를 저장합니다. 완료된 도구 호출의 경우 정확한 `SKILL.md`, 표준 스킬 리소스 및 메모리의 변경된 파일 경로만 추출합니다. 원시 명령, 패치 본문, 프롬프트 및 도구 출력은 지속되기 전에 삭제됩니다. 런타임이 활성화되어 있는 동안에는 권한이 제한된 Unix 소켓이 빠른 경로입니다. 선택적 기본 발신자는 Python 시작을 방지합니다. 런타임이 활성화되지 않은 경우 독립 실행형 페일오픈 경로는 수정된 증거를 `~/.skill-runtime/queue/events.jsonl`에 추가합니다. `skill-runtime start`는 이벤트 ID 중복 제거를 통해 해당 대기열을 재생합니다.

Codex 이벤트는 공식 Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` 및 `Stop`). Codex는 현재 명령 후크를 동기식으로 실행하므로 Skill Runtime는 제한 시간이 있는 로컬 Unix 소켓/네이티브 발신자를 사용합니다. 모든 배달 실패는 삼켜지고 대기열에 추가됩니다. 상담원의 결정은 결코 변경되지 않습니다. [공식 Codex Hook 문서](https://developers.openai.com/codex/config-advanced#hooks)를 참조하세요.

다음을 사용하여 관리되는 항목만 제거하십시오.

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

서버는 기본적으로 `127.0.0.1`에 바인딩됩니다. 전체 기록 메시지와 도구 페이로드는 색인에 복사되지 않습니다. 정규화된 요약이 유지되기 전에 일반적인 비밀 패턴이 수정됩니다.

다음을 사용하여 종속성 없는 테스트 도구 모음을 실행하세요.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 릴리스 엔지니어링

GitHub Actions는 Python 3.9–3.13 테스트, JavaScript 검증, 기본 발신자 컴파일 및 실제 설치/시작/의사/중지/제거 스모크 테스트를 실행합니다. `v*` 태그는 휠/sdist 패키지와 체크섬으로 보호된 Linux 및 macOS 기본 발신자를 구축합니다. CLI 설치 프로그램은 일치하는 릴리스 자산을 다운로드하므로 최종 사용자에게는 컴파일러가 필요하지 않습니다.

첫 번째 제품 연결 진단 실험을 ​​실행합니다.

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

수명 주기 증거 격차, 명시적인 오류, 불완전한 실행, 확인되지 않은 결과를 오류로 주입한 다음 API 및 UI에서 사용하는 것과 동일한 결정적 진단 엔진을 평가합니다. 실험 사다리, 비간섭 테스트, 재현성 계약에 대해서는 [PAI-DSW 실험 계획](docs/pai-dsw-experiment-plan.md)를 참조하세요.

휠을 구축한 후 다음을 사용하여 격리된 패키지 수명 주기 연기를 실행합니다.

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

임시 가상 환경과 임시 홈에 설치하고 후크를 활성화하지 않고 전체 로컬 수명주기를 실행하며 프로젝트 및 에이전트 구성이 간섭하지 않는지 확인합니다.

## 실험 중심의 제품 디자인

제품 동작은 [실험 중심의 제품 철학](docs/experiment-driven-product-philosophy.md)(결론 전 증거, 심각도 전 첫 번째 관찰 가능한 경계, 단순 로그 전 유형화된 관계, 확률적 지원 전 결정론적 재구성)에 의해 제한됩니다.

현재 재현 가능한 현지 증거에는 다음이 포함됩니다.

- 7/7 지역 실험 게이트 통과;
- 2,400/2,400개의 수집기 이벤트가 입력/출력 변형 없이 허용됩니다.
- 뒷받침되지 않는 인과관계 주장이 없는 14/14 결정론적 결함 코퍼스 진단;
- 관계형 진단 표현은 13/14 정확 및 F1 0.963인 반면, 플랫 수명주기 검색은 1/14 정확 및 F1 0.080에 도달했습니다.
- 11/11 연구 자료 사례에서는 가장 먼저 관찰 가능한 경계를 먼저 배치합니다.

이러한 결과는 배포 일반화나 인간의 이익이 아닌 메커니즘과 표현 선택을 검증합니다. 실제 2차 에이전트 연구, 플랫폼 간 테일 대기 시간, 실제 결함 보정 및 참가자 진단 연구는 여전히 공개 증거 격차로 남아 있습니다.

연구 방향은 인접한 기본 작업에도 기반을 두고 있습니다. [SkillsBench](https://arxiv.org/abs/2602.12670) 및 [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)는 스킬 효과가 다양하고 회귀할 수 있으므로 진단에 동기를 부여합니다. [Harness-Bench](https://arxiv.org/abs/2605.27922)는 기능 인식 에이전트 간 비교에 동기를 부여합니다. [실행 출처 조사](https://arxiv.org/abs/2606.04990)는 유형화된 증거 관계, 출처 추적 및 개인정보 보호 감사 인프라를 활성화합니다.

## 선적 서류 비치

| 여기서 시작하세요 | 목적 |
|---|---|
| [Getting Started](docs/getting-started.md) | 에이전트 설치, 연결, 실시간 증거 확인 및 문제 해결 |
| [건축학](docs/architecture.md) | 수집 파이프라인, 저장 경계, 증거 엔진 및 신뢰 모델 |
| [어댑터 기능 매트릭스](docs/adapter-capability-matrix.md) | 에이전트/버전별 정확한 신호 및 제한사항 |
| [관찰 가능성 플랫폼 설정](docs/observability-platform-setup.md) | OTLP 호환 플랫폼을 연결하고 지원되는 추적 가져오기 |
| [런타임 이벤트 모델](docs/runtime-event-model.md) | 안정적인 사건 어휘, 출처, 관계, 증거 등급 |
| [UI 정보 아키텍처](docs/ui-information-architecture.md) | 개요, 첫 번째 경계, 파노라마, 검사기, 비교 및 ​​Inferred Analysis |

제품 및 연구 참고 자료: [제품 정의](docs/product-definition.md), [MVP 사양](docs/mvp-specification.md), [관찰성 상호 운용성](docs/observability-interoperability.md), [실험 중심의 제품 철학](docs/experiment-driven-product-philosophy.md), [실험 결과](docs/experiment-results-2026-07-29.md) 및 [연구 의제](docs/research-paper-agenda.md).

## 로드맵

1. **v0.2.0 — 현재 사용 가능:** 라이브 페일오픈 컬렉션, 버전이 지정된 4개의 에이전트 어댑터, Runtime Overview, 첫 번째 경계 진단, 파노라마, Evidence Inspector, 기능 인식 비교, Inferred Analysis 및 OTLP 상호 운용성.
2. **다음 — 어댑터 및 진단 강화:** 광범위한 에이전트/버전 적용 범위, 실제 오류 교정, 플랫폼 간 테일 지연 시간 검증 및 참가자 진단 연구.
3. **나중에 — 효과 평가:** 기술 유무/기술 없이 쌍을 이루는 평가가 제어되며 단일 실행 진단과 명시적으로 분리되어 유지됩니다.

## 프로젝트 현황

버전 `v0.2.0`이 게시되었습니다. 런타임에는 설치된 정의 인벤토리, Codex, Claude Code 및 Qoder용 동의 기반 공식 Hook 어댑터, 관찰 전용 OpenCode 플러그인, 레이블이 지정된 기록 폴백, 활성 범위 속성, 정확한 파일/아티팩트 경로, 수정, 별도의 소스/관계/추론 레이어, SQLite 저장소, 보존, 결정론적 진단, 실시간 UI 및 교차 실행/에이전트 간 비교. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave 및 Datadog 내보내기를 가져올 수 있습니다. 정규화된 증거는 옵트인 OTLP/HTTP을 통해 실시간으로 내보낼 수 있습니다.

모델 내부의 후보 발견, 모델 내부 선택 이유, 의미론적 효율성 및 인과적 결과 주장은 소스 또는 통제된 실험이 해당 증거를 제공하지 않는 한 명시적으로 지원되지 않습니다.
