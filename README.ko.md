# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
**한국어** · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)[![풀어 주다](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-지능/릴리스/최신)[![특허](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](특허)[![파이썬](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> 에이전트 스킬 실행이 처음으로 분기된 위치를 진단하고 증거를 조사합니다.
> 모든 결론 뒤에.

Agent Skill Runtime Intelligence에이전트 스킬에 대한 읽기 전용 런타임 증거 및 진단 시스템입니다. 스킬 정의, 공식 에이전트 런타임 이벤트, 가져온 추적, 세션 대체 및 관찰 가능한 작업 공간 결과를 증거 등급으로 결합합니다.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## 빠른 시작

macOS 또는 Linux에 최신 독립 실행형 릴리스를 설치합니다.

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

클론 없음,Git허브 계정,`sudo`, 또는Git허브 CLI가 필요합니다. 설치 프로그램은 일치하는 서명된 릴리스 페이로드를 다운로드하고, SHA-256 체크섬을 확인하고, 페일오픈 에이전트 후크를 활성화하기 전에 한 번 묻고, 모든 런타임 데이터를`~/.skill-runtime`. 그런 다음 로컬 런타임을 시작하고 열립니다.[http://127.0.0.1:4317](http://127.0.0.1:4317).

당신은 할 수 있습니다[설치 프로그램을 검사하다](scripts/install.sh)실행하기 전에.

또는 소스 체크아웃에서 직접 실행하십시오.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

열려 있는[http://127.0.0.1:4317](http://127.0.0.1:4317). 을 위한Codex, 관리되는 명령을 검토하고 신뢰합니다.`/hooks`, 새로운 에이전트 턴을 한 번 시작한 후 다음을 확인하세요.

```bash
skill-runtime doctor
```

실제 공식 후크 이벤트가 수신된 후에만 통합이 **검증**됩니다. 구성된 후크는 **보류 중**으로 표시되며 실시간 증거로 표시되지 않습니다.

| 제품 표면 | 답변 내용 |
|---|---|
| 런타임 개요 | 어느SkillRuns관심이 필요해? |
| 첫 번째 관찰 가능한 경계 | 증거가 처음으로 누락되거나 실패한 곳은 어디입니까? |
| Skill Run Panorama | 요청, 활성화, 리소스, 도구, 아티팩트 및 결과가 어떻게 연결되었나요? |
| 증거 조사관 | 이 주장을 뒷받침하는 소스, 등급, 기준 및 어댑터 기능은 무엇입니까? |
| 비교하다 | 차이점은 행동상의 차이인가요, 아니면 관찰 가능성의 차이인가요? |
| 설정 / 의사 | 읽고, 저장하고, 내보내고, 보류하고, 확인하는 작업은 무엇입니까? |

## 문제

스킬을 설치한다고 해서 에이전트가 스킬을 발견했다는 사실이 입증되는 것은 아닙니다. 검색은 활성화를 증명하지 않습니다. 활성화는 전체 지침과 리소스가 로드되었음을 증명하지 않습니다. 실행은 스킬이 결과를 향상시켰다는 것을 증명하지 않습니다.

오늘날 이러한 실패는 종종 조용합니다. 개발자는 다음과 같은 질문을 남깁니다.

- 이 상담원이 스킬을 사용할 수 있었나요?
- 이 요청에 대해 활성화되었습니까?
- 어떤 지침, 참조, 스크립트 및 자산이 로드되었습니까?
- 어떤 도구,MCP호출, 하위 에이전트, 파일 및 아티팩트가 관련되었습니까?
- 실행이 실패하거나 재시도되거나 컨텍스트가 손실된 위치는 어디입니까?
- 기술이 도움이 되었나요? 아니면 비용과 대기 시간만 추가되었나요?

## 제품 방향

첫 번째 제품은 **입니다.Skill Run Panorama**:

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

파노라마는 모델 자체 보고가 아닌 실제 신호로 구성됩니다.

| 원천 | 예 | 증거 |
|---|---|---|
| 스킬 파일 | 메타데이터, 지침, 스크립트, 참조, 자산 | 관찰됨 |
| 런타임 이벤트 | 스킬 호출, 도구 호출, 하위 에이전트, 실패, 기간 | 관찰됨 |
| 세션 기록 | 프롬프트, 메시지, 도구 입력 및 출력, 주문 | 관찰됨 |
| 작업 공간 결과 | 파일 변경,Git차이점, 보고서, 생성된 아티팩트 | 관찰됨 |
| 상관관계 | 사건, 자원, 결과 사이의 관계 | 파생 또는 추론 |

## 증거 규율

그만큼UI추론을 런타임 사실로 제시해서는 안 됩니다.

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

## 초기 범위

런타임은 다음을 지원합니다.Codex,Claude Code,Qoder, 그리고OpenCode버전이 지정된 독립적인 어댑터를 통해 다음을 제공합니다.

- 설치된 스킬 발견 및 검증;
- 지원되는 경우 세션 가져오기 및 실시간 로컬 관찰;
- 기술 활성화, 리소스 로딩 및 도구 호출 타임라인
- 하위 에이전트,MCP, 파일 및 아티팩트 관계;
- 기간, 토큰, 오류, 재시도 및 상태 요약(사용 가능한 경우)
- 실행 목록, 파노라마 DAG, 이벤트 타임라인 및 노드 검사기.

MVP에는 마켓플레이스, 범용 에이전트 런타임, 보안 시행, 기업 거버넌스 또는 인과관계 주장이 포함되지 **않습니다**.

## 상세한 설치

기본 구현에는 런타임 종속성이 없습니다.Python3.9+. 저장소 루트에서:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

그런 다음 열어[http://127.0.0.1:4317](http://127.0.0.1:4317).

일회성`install`명령:

1. 사용자, 프로젝트 및 캐시된 플러그인 스킬 위치를 스캔합니다.
2. 감지하다Codex,Claude Code,Qoder, 그리고OpenCode구성을 변경하지 않고;
3. 읽을 에이전트 및 스킬 경로를 표시합니다.
4. 현재 플랫폼에 대해 체크섬 확인된 낮은 시작 네이티브 발신자를 다운로드하고 로컬 C 빌드로 대체한 다음 마지막으로Python발신자이며 설치 중에 새로운 기본 바이너리를 한 번 미리 준비합니다.
5. 창조하다`~/.skill-runtime/config.json`그리고 지역SQLite색인.

대화형으로 실행할 경우 페일오픈 에이전트 후크를 추가하기 전에 한 번 묻습니다.`--no-hooks`성적표 가져오기를 레이블이 지정된 대체 항목으로 유지하는 반면`--enable-hooks`명시적인 동의를 기록하고 관리되는 항목만 설치합니다. 을 위한Codex, 열려 있는`/hooks`설치 후 정확한 관리 명령을 검토하고 신뢰하십시오.Codex관리되는 엔터프라이즈 구성 외부에 추가된 후크에 대해 의도적으로 이러한 명시적인 검토가 필요합니다. 새 에이전트 차례를 시작한 후 다음을 실행합니다.

```bash
.venv/bin/skill-runtime doctor
```

Qoder시작 시 Hook 구성을 로드하므로 다시 시작하세요.Qoder첫 설치 후.OpenCode전역 플러그인 디렉터리에서 관리형 관찰 전용 플러그인을 검색합니다. 다시 시작하다OpenCode현재 프로세스가 설치보다 이전인 경우. 통합은 모델 요청을 읽거나 변경하지 않습니다.

데이터베이스가 실제 데이터를 수신한 후에만 통합이 **라이브** 상태가 됩니다.`official_hook`이벤트. 그냥 쓰는 것`~/.codex/hooks.json`**보류 중**으로 표시되며 연결되지 않습니다.`start`수집기, 기록 대체 감시자, 보존 작업자를 시작합니다.SQLite저장하고 살아요UI관리되는 백그라운드 프로세스로. 모델 요청이 프록시되지 않습니다.

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

`uninstall`관리되는 Hook 항목만 제거하고Skill Runtime-소유 파일. 없이`--keep-data`, 대화형 확인이 필요합니다(또는`--yes`) 제거하기 전에`~/.skill-runtime`; 상담원 세션과 스킬 소스는 제거되지 않습니다.

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

버전이 지정된 가져오기 프로필은 현재 OTLP/를 인식합니다.Phoenix,Langfuse,LangSmith,W&B Weave, 그리고Datadog JSON모양. 그들은 단지SkillRun소스가 명시적인 스킬 의미를 전달하는 경우; 일반 스팬 이름은 활성화 증거로 처리되지 않습니다.

정규화된 스킬별 런타임 증거를 다음으로 내보냅니다.OTLP/HTTP추적 끝점:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

엔드포인트가 명시적으로 구성되지 않으면 내보내기가 비활성화됩니다. 체크포인트, 재시도 상태, 대상 상태는 설정에 표시됩니다. 원시 프롬프트, 도구 페이로드, 자격 증명 및 스킬 리소스 콘텐츠는 내보내지지 않습니다. 인증된 백그라운드 내보내기를 위해 표준 제공`OTEL_EXPORTER_OTLP_HEADERS`전에 환경에서`skill-runtime start`; 헤더는 절대 작성되지 않습니다.Skill Runtime구성 또는 프로세스 인수.

## 실시간 런타임 증거 보내기

`skill-runtime start`로컬 수집기가 포함됩니다. 기본 원격 측정 어댑터, 공식 후크, 경량 페일오픈 후크 및SDK통합은 단일 이벤트 또는 제한된 배치를 추가할 수 있습니다.`POST /api/events`:

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

엔드포인트는 지속성 전에 일반 자격 증명을 수정하고 다음을 통해 중복을 제거합니다.`event_id`, 별도의 수정된 원시 봉투를 유지하고 결과를 반환합니다.`skill_run_ids`.`GET /api/collector/schema`지원되는 이벤트 어휘 및 수집 모드를 노출합니다. 그만큼UI듣는다`/api/stream`재연결 폴백으로만 폴링을 사용하여 SSE를 사용합니다.

소스 표시기는 주요 런타임 증거를 다음과 구별합니다.`Transcript fallback`그리고 가져온 흔적. Collector 엔드포인트만으로는 기본 원격 측정을 주장하지 않습니다. 모든 생산자는 해당 이벤트가 기본 원격 측정, 공식 후크, 경량 후크 또는SDK.

### 선택적 에이전트 후크

먼저 정확한 경로와 이벤트를 검사하세요. 이 명령은 읽기 전용입니다.

```bash
.venv/bin/skill-runtime setup
```

후크 설치에는 명시적인 플래그가 필요합니다.

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

설치 프로그램은 에이전트 구성을 백업하고 기존 후크를 유지하며 다음을 전달하는 항목만 추가합니다.Skill Runtime관리 마커. 후크 어댑터는 전체 프롬프트나 도구 페이로드가 아닌 최소한의 수명 주기 필드를 저장합니다. 런타임이 활성화된 동안 권한이 제한됩니다.Unix소켓은 빠른 경로입니다. 선택적인 기본 발신자는 회피합니다Python시작. 런타임이 활성화되지 않은 경우 독립 실행형 페일오픈 경로는 수정된 증거를 다음에 추가합니다.`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`이벤트 ID 중복 제거를 통해 해당 대기열을 재생합니다.

Codex이벤트는 공식 Hook을 사용합니다.API(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, 그리고`Stop`).Codex현재 명령 후크를 동기식으로 실행하므로Skill Runtime로컬을 사용한다Unix제한된 시간 초과가 있는 소켓/네이티브 발신자. 모든 배달 실패는 삼켜지고 대기열에 추가됩니다. 상담원의 결정은 결코 변경되지 않습니다. 참조[공식 Codex Hook 문서](https://developers.openai.com/codex/config-advanced#hooks).

다음을 사용하여 관리되는 항목만 제거하십시오.

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

서버는 다음에 바인딩됩니다.`127.0.0.1`기본적으로. 전체 기록 메시지와 도구 페이로드는 색인에 복사되지 않습니다. 정규화된 요약이 유지되기 전에 일반적인 비밀 패턴이 수정됩니다.

다음을 사용하여 종속성 없는 테스트 도구 모음을 실행하세요.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## 릴리스 엔지니어링

Git허브 작업 실행Python3.9–3.13 테스트, JavaScript 검증, 기본 발신자 컴파일 및 실제 설치/시작/의사/중지/제거 스모크 테스트. 에이`v*`태그는 휠/sdist 패키지와 체크섬으로 보호되는 Linux 및 macOS 기본 발신자를 빌드합니다. CLI 설치 프로그램은 일치하는 릴리스 자산을 다운로드하므로 최종 사용자에게는 컴파일러가 필요하지 않습니다.

첫 번째 제품 연결 진단 실험을 ​​실행합니다.

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

수명주기 증거 격차, 명시적인 오류, 불완전한 실행 및 확인되지 않은 결과를 오류로 주입한 다음,API그리고UI. 참조[PAI-DSW 실험 계획](docs/pai-dsw-experiment-plan.md)실험 사다리, 비간섭 테스트 및 재현성 계약을 위해.

휠을 구축한 후 다음을 사용하여 격리된 패키지 수명 주기 연기를 실행합니다.

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

임시 가상 환경과 임시 홈에 설치하고 후크를 활성화하지 않고 전체 로컬 수명주기를 실행하며 프로젝트 및 에이전트 구성이 간섭하지 않는지 확인합니다.

## 실험 중심의 제품 디자인

제품 동작은 다음에 의해 제한됩니다.[실험 중심의 제품 철학](docs/experiment-driven-product-philosophy.md): 결론 이전의 증거, 심각도 이전의 첫 번째 관찰 가능한 경계, 평탄한 로그 이전의 유형화된 관계, 확률적 지원 이전의 결정론적 재구성.

현재 재현 가능한 현지 증거에는 다음이 포함됩니다.

- 7/7 지역 실험 게이트 통과;
- 2,400/2,400개의 수집기 이벤트가 입력/출력 변형 없이 허용됩니다.
- 뒷받침되지 않는 인과관계 주장이 없는 14/14 결정론적 결함 코퍼스 진단;
- 관계형 진단 표현은 13/14 정확 및 F1 0.963인 반면, 플랫 수명주기 검색은 1/14 정확 및 F1 0.080에 도달했습니다.
- 11/11 연구 자료 사례에서는 가장 먼저 관찰 가능한 경계를 먼저 배치합니다.

이러한 결과는 배포 일반화나 인간의 이익이 아닌 메커니즘과 표현 선택을 검증합니다. 실제 2차 에이전트 연구, 플랫폼 간 테일 대기 시간, 실제 결함 보정 및 참가자 진단 연구는 여전히 공개 증거 격차로 남아 있습니다.

연구 방향은 인접한 주요 연구에도 기반을 두고 있습니다.[SkillsBench](https://arxiv.org/abs/2602.12670)그리고[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)스킬 효과는 다양하고 퇴보할 수 있으므로 진단에 동기를 부여합니다.[Harness-Bench](https://arxiv.org/abs/2605.27922)기능 인식 교차 에이전트 비교에 동기를 부여합니다. 그리고[실행 출처 조사](https://arxiv.org/abs/2606.04990)유형화된 증거 관계, 출처 추적 및 개인정보 보호 감사 인프라를 활성화합니다.

## 선적 서류 비치

- [제품 정의](docs/product-definition.md)
- [MVP 사양](docs/mvp-specification.md)
- [런타임 이벤트 모델](docs/runtime-event-model.md)
- [UI 정보 아키텍처](docs/ui-information-architecture.md)
- [어댑터 기능 매트릭스](docs/adapter-capability-matrix.md)
- [관찰 가능성 상호 운용성](docs/observability-interoperability.md)
- [관찰 가능성 플랫폼 설정](docs/observability-platform-setup.md)
- [연구 및 경쟁 환경](docs/research-and-competitive-landscape.md)
- [연구논문 안건](docs/research-paper-agenda.md)
- [실험 중심의 제품 철학](docs/experiment-driven-product-philosophy.md)
- [실험 결과](docs/experiment-results-2026-07-29.md)
- [PAI-DSW 실험 계획](docs/pai-dsw-experiment-plan.md)

## 로드맵

1. **v0.1 — 런타임 증거 및 진단:** 실시간 수집,Skill Run Panorama, 1차 경계 진단, 증거 조사, 비교 및 ​​OTLP 상호 운용성.
2. **v0.2 — 어댑터 강화 및 진단 연구:** 추가 에이전트 버전, 실제 교차 에이전트 실험 및 참가자 평가.
3. **v0.3 — 효과 평가:** 기술 유무에 따른 쌍 평가가 제어되며 단일 실행 진단과 별도로 유지됩니다.

## 프로젝트 현황

에이SkillRun-첫 번째 런타임이 실행 가능합니다: 설치된 정의 인벤토리,Codex성적표 폴백, 동의 기반 공식 후크 어댑터Codex,Claude Code, 그리고Qoder, 관찰 전용OpenCode플러그인 어댑터, 활성 범위 속성, 정확한 파일/아티팩트 경로, 수정, 별도의 소스/관계/추론 레이어,SQLite저장, 보존, 교차 실행 및 에이전트 간 비교, 결정론적 진단 및 라이브 파노라마UI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, 그리고Datadog수출품을 수입할 수 있습니다. 정규화된 증거는 옵트인을 통해 실시간으로 내보낼 수 있습니다.OTLP/HTTP. 후보 발견, 모델 내부 선택 이유, 의미론적 효율성 및 인과적 결과 주장은 명시적으로 지원되지 않습니다.
