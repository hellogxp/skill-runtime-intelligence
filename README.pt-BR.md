# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · **Português (Brasil)** · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Vez `SKILL.md` em expectativas de tempo de execução verificáveis. Veja o que realmente
> aconteceu, onde o comportamento divergiu pela primeira vez, e as evidências por trás do julgamento.

Agent Skill Runtime Intelligence é um sistema de diagnóstico e evidência de tempo de execução somente leitura para habilidades de agente. Ele extrai restrições conservadoras e inspecionáveis ​​da definição de habilidade atual, combina-as com a atividade de tempo de execução e reconstrói o resultado como um resultado classificado por evidências. Skill Run Panorama. Ele combina eventos oficiais do agente, rastreamentos importados, fallback de sessão rotulada e resultados observáveis ​​do espaço de trabalho sem fazer proxy de solicitações de modelo ou assumir o controle do loop do agente.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Início rápido

Instale e inicie a versão mais recente em macOS ou Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Sem clone, conta, `sudo`, ou GitHub CLI é necessário. O instalador verifica a soma de verificação da versão, detecta Agentes e Habilidades suportadas, explica cada caminho que irá ler, pergunta uma vez antes de ativar ganchos somente de observação e abre o local UI no [http://127.0.0.1:4317](http://127.0.0.1:4317). Os dados de tempo de execução permanecem em `~/.skill-runtime` a menos que você configure explicitamente uma exportação.

Você pode [inspecionar o instalador](scripts/install.sh) antes de executá-lo.

### Veja sua primeira live SkillRun

1. Aceite o fail-open opcional Hook configure quando o instalador perguntar.
2. Reinicie o Agente e inicie uma nova tarefa. Em Codex, revise os comandos gerenciados em `/hooks` primeiro; tarefas existentes não carregam novas HookS.
3. Use uma Skill normalmente, depois confirme a integração e abra o UI:

```bash
skill-runtime doctor
skill-runtime status
```

Uma integração estará **Live** somente depois que o Coletor receber um evento de tempo de execução real. Um configurado, mas não observado Hook está **Pendente** – nunca apresentado como evidência real. Abrir [http://127.0.0.1:4317](http://127.0.0.1:4317), ou veja o [Guia de primeiros passos](docs/getting-started.md) para obter instruções e solução de problemas específicas do agente.

Para executar diretamente de uma verificação de origem:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Superfície do produto | O que isso responde |
|---|---|
| Runtime Overview | Qual SkillRuns precisa de atenção? |
| Verificação de comportamento de habilidade | Quais instruções verificáveis ​​foram atendidas, precisam de revisão ou não podem ser avaliadas? |
| O que realmente aconteceu | Quais instruções, recursos, ferramentas, artefatos e resultados foram observados? |
| First Observable Boundary | Onde as evidências específicas da execução primeiro desaparecem ou falham? |
| Skill Run Panorama | Como a solicitação, a ativação, os recursos, as ferramentas, os artefatos e o resultado se conectam? |
| Evidence Inspector | Que fonte, grau, base e capacidade do adaptador apoiam esta afirmação? |
| Comparar | A diferença é comportamental ou apenas uma diferença de observabilidade? |
| Inferred Analysis | Que explicação baseada em evidências ou próxima investigação é plausível? |
| Configurações / Médico | O que é lido, armazenado, exportado, pendente e verificado? |

## Como funciona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observa o fluxo de trabalho que você já usa. Os adaptadores versionados transformam os eventos nativos do agente em um ciclo de vida de habilidade estável, enquanto os envelopes de origem bruta, os eventos normalizados, os relacionamentos e as inferências permanecem separados. O mecanismo de diagnóstico verifica as restrições explícitas do Skill em relação a essas evidências, identifica o primeiro desvio observável e mantém os pontos cegos do adaptador sistêmico separados das descobertas específicas da execução. Não inventa a intenção do modelo ou a eficácia causal.

| Fonte de dados | Papel | Frescura | UI rótulo |
|---|---|---|---|
| Ganchos/plugins/plugins oficiais do agente SDK eventos | Ciclo de vida primário, ferramenta, subagente e evidência terminal | Ao vivo | `Official hook` / `Native telemetry` |
| Arquivos de habilidades e resultados observáveis ​​do espaço de trabalho | Definição, recurso, arquivo, artefato e evidência de teste | Instantâneo ao vivo/indexado | `Observed` |
| Transcrições da sessão | Fallback de compatibilidade quando o Agente não expõe tempo de execução suficiente API | Quase ao vivo ou histórico | `Transcript fallback` |
| OTLP e exportações de rastreamento compatíveis | Interoperabilidade e importação histórica | Exportação ao vivo/importação em lote | Perfil de origem mostrado |
| Correlação determinística | Conecta eventos a um SkillRun sem alterar os fatos originais | Na ingestão | `Derived` |
| Assistência semântica | Apenas explicações e sugestões de investigação | Sob demanda | `Inferred` |

Os adaptadores originais suportados têm versões independentes:

| Agente | Integração primária | Cair pra trás | Visibilidade de ativação |
|---|---|---|---|
| Codex | Comando oficial Hooké | Importação de sessão | Ativação explícita quando exposta pelo Hook evento |
| Claude Code | Oficial Hooké | Importação de sessão | Ferramenta de habilidade explícita e evidências de comando de barra quando expostas |
| Qoder | Comando oficial Hooké | Registros locais | Ativação explícita quando exposta pela ferramenta Skill |
| OpenCode | Plug-in global somente de observação | Registros locais | Retornos de chamada da ferramenta de habilidade foram expostos |

Os limites exatos de capacidade estão documentados no [matriz de capacidade do adaptador](docs/adapter-capability-matrix.md). Os estágios não suportados e não observados permanecem visíveis em vez de serem convertidos em falhas.

## O problema

Instalar uma Skill não prova que um agente a descobriu. A descoberta não prova a ativação. A ativação não prova que todas as instruções e recursos foram carregados. As instruções de carregamento não provam que o Agente as seguiu. A execução não prova que a habilidade melhorou o resultado.

Hoje, estas falhas são muitas vezes silenciosas. Os desenvolvedores ficam perguntando:

- A habilidade estava disponível para este agente?
- Ele foi ativado para esta solicitação?
- Quais instruções, referências, scripts e ativos foram carregados?
- Quais requisitos explícitos de habilidades foram seguidos, ignorados ou impossíveis de avaliar?
- Quais ferramentas, MCP chamadas, subagentes, arquivos e artefatos estavam envolvidos?
- Onde a execução falhou, tentou novamente ou perdeu contexto?
- A habilidade ajudou ou apenas adicionou custo e latência?

## Diagnóstico específico de habilidade

O principal objeto de diagnóstico é um `SkillRun`, não uma sessão inteira do agente:

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

O UI mantém o ciclo de vida ordenado, digitado e classificado por evidências. Telemetria de ativação ausente significa “não observado” ou “não suportado”; isso não significa que o Agente definitivamente ignorou a Habilidade.

## Disciplina de evidências

O UI nunca deve apresentar uma inferência como um fato de tempo de execução:

- **Observado** — explicitamente presente em um evento ou arquivo de origem.
- **Derivado** — conectado deterministicamente a partir de evidências observadas.
- **Inferido** — uma explicação plausível com incerteza.
- **Experimental** — um efeito medido através de avaliação pareada controlada.

Um único rastreamento pode oferecer suporte à atribuição de execução. Não pode provar eficácia causal. Afirmações como “esta habilidade melhorou a taxa de sucesso” exigem avaliações repetidas com/sem habilidade.

## Princípios do produto

- Privado por padrão, com implantação local, híbrida e conectada em equipe.
- Observação somente leitura; nunca assuma o controle do loop do agente.
- Nenhum proxy modelo e nenhum serviço de nuvem obrigatório.
- Sem bloqueio, aprovação ou aplicação de políticas no produto padrão.
- Proveniência explícita e classificação de evidências.
- Divulgação progressiva: narrativa simples primeiro, eventos brutos sob demanda.
- Suporte baseado em adaptador para alteração de formatos de transcrição de agente.

## Escopo atual

O tempo de execução suporta Codex, Claude Code, Qoder, e OpenCode por meio de adaptadores independentes e versionados e fornece:

- descoberta e validação de habilidades instaladas;
- oficial em tempo real HookColeção /plugin mais fallback de sessão rotulado;
- Ativação de habilidades, carregamento de recursos e cronogramas de chamada de ferramentas;
- subagente, MCPrelacionamentos entre arquivos, arquivos e artefatos;
- resumos de duração, token, erro, nova tentativa e status, quando disponíveis;
- restrições de comportamento conservador extraídas do atual `SKILL.md`;
- conformidade limitada por evidências, verificação e verificações de falhas em tempo de execução;
- inventários concretos de instruções, recursos, ferramentas, artefatos e resultados;
- Runtime Overview com limites de cobertura sistémicos separados dos resultados da execução;
- diagnóstico de primeiro limite;
- um DAG panorâmico, cronograma de eventos e inspetor de evidências;
- comparação entre agentes e entre agentes com reconhecimento de capacidade;
- um separado Inferred Analysis superfície que não pode reescrever fatos de tempo de execução;
- aceitar OTLP/HTTP exportação e importação de rastreamento de observabilidade suportada.

O MVP **não** inclui mercado, tempo de execução de agente universal, aplicação de segurança, governança corporativa ou declarações de efeito causal.

## Instalação detalhada

Para obter o caminho mais curto suportado, use o instalador de versão de uma linha em [Início rápido](#quick-start). O fluxo completo de primeira execução, as etapas de reinicialização/confiança específicas do agente, o comportamento de privacidade e a solução de problemas estão disponíveis no [Guia de primeiros passos](docs/getting-started.md).

Para desenvolvimento, a implementação da linha de base não tem dependências de tempo de execução além Python 3,9+. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Então abra [http://127.0.0.1:4317](http://127.0.0.1:4317).

O único `install` comando:

1. verifica locais de habilidades de usuários, projetos e plug-ins em cache;
2. detecta Codex, Claude Code, Qoder, e OpenCode sem alterar sua configuração;
3. mostra quais caminhos de Agente e Habilidade serão lidos;
4. baixa um remetente nativo de baixa inicialização verificado por soma de verificação para a plataforma atual, voltando para uma compilação C local e, finalmente, o Python remetente e pré-aquece um novo binário nativo uma vez durante a instalação;
5. cria `~/.skill-runtime/config.json` e o local SQLite índice.

O primeiro índice importa sessões de agente compatíveis existentes. Em uma estação de trabalho de longa duração, isso pode levar mais tempo do que uma nova instalação; partidas posteriores são incrementais e o UI fica disponível enquanto a atualização em segundo plano é executada.

Quando executado de forma interativa, ele pergunta uma vez antes de adicionar ganchos de agente com falha aberta. `--no-hooks` mantém a importação da transcrição como substituto rotulado, enquanto `--enable-hooks` registra consentimento explícito e instala apenas entradas gerenciadas. Para Codex, abrir `/hooks` após a instalação, revise os comandos gerenciados exatos e confie neles. Codex requer intencionalmente esta revisão explícita para ganchos adicionados fora da configuração empresarial gerenciada. Comece um novo Codex tarefa/sessão depois de confiar no Hooks e execute:

```bash
.venv/bin/skill-runtime doctor
```

Qoder cargas Hook configuração na inicialização, então reinicie Qoder após a primeira instalação. OpenCode descobre o plug-in gerenciado somente para observação em seu diretório global de plug-ins; reiniciar OpenCode se o processo atual for anterior à instalação. Nenhuma integração lê ou altera solicitações de modelo.

A integração se torna **Live** somente depois que o banco de dados recebe uma resposta real `official_hook` evento. Apenas escrevendo `~/.codex/hooks.json` é mostrado como **Pendente**, nunca conectado. `start` lança o Coletor, o observador de fallback de transcrição, o trabalhador de retenção, SQLite armazenar e viver UI como um processo gerenciado em segundo plano. Nenhuma solicitação de modelo é proxy.

Comandos do ciclo de vida:

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

`uninstall` remove apenas gerenciado Hook entradas e Skill Runtimearquivos de propriedade. Sem `--keep-data`, requer confirmação interativa (ou `--yes`) antes de remover `~/.skill-runtime`; As sessões do agente e as fontes de habilidade nunca são removidas.

Para indexar e veicular separadamente:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importe uma exportação de rastreamento existente de um sistema de observabilidade convencional:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Os perfis de importação versionados atualmente reconhecem OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, e Datadog JSON formas. Eles apenas criam um SkillRun quando a fonte carrega semântica explícita de Skill; nomes de span genéricos não são tratados como evidência de ativação.

Exporte evidências de tempo de execução normalizadas e específicas de habilidades para qualquer OTLP/HTTP ponto de extremidade de rastreamento:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

A exportação fica desabilitada, a menos que um endpoint seja configurado explicitamente. Pontos de verificação, status de nova tentativa e integridade do destino são mostrados em Configurações. Prompts brutos, cargas úteis de ferramentas, credenciais e conteúdos de recursos de habilidades não são exportados. Para exportação autenticada em segundo plano, forneça padrão `OTEL_EXPORTER_OTLP_HEADERS` no ambiente antes `skill-runtime start`; cabeçalhos nunca são gravados Skill Runtime argumentos de configuração ou processo.

## Envie evidências de tempo de execução ao vivo

`skill-runtime start` inclui um coletor local. Adaptadores de telemetria nativos, ganchos oficiais, ganchos leves de falha aberta e SDK integrações podem anexar um único evento ou um lote limitado a `POST /api/events`:

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

O endpoint edita credenciais comuns antes da persistência, desduplica por `event_id`, preserva um envelope bruto redigido separado e retorna o resultado `skill_run_ids`. `GET /api/collector/schema` expõe o vocabulário de eventos suportado e os modos de coleta. O UI ouve `/api/stream` usando SSE, com polling apenas como alternativa de reconexão.

O indicador de origem distingue as evidências primárias de tempo de execução das `Transcript fallback` e vestígios importados. Um endpoint de coletor por si só não reivindica telemetria nativa: todo produtor deve declarar se seu evento veio de telemetria nativa, de um gancho oficial, de um gancho leve ou de um gancho. SDK.

### Ganchos de agente opcionais

Inspecione primeiro os caminhos e eventos exatos. Este comando é somente leitura:

```bash
.venv/bin/skill-runtime setup
```

Hook a instalação requer um sinalizador explícito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

O instalador faz backup da configuração do Agente, preserva os ganchos existentes e adiciona apenas entradas que carregam um Skill Runtime marcador de gestão. O adaptador de gancho armazena campos mínimos de ciclo de vida em vez de prompts completos ou cargas úteis de ferramentas. Para chamadas de ferramenta concluídas, ele extrai apenas dados exatos `SKILL.md`, recurso de habilidade padrão e caminhos de arquivos alterados na memória; comandos brutos, corpos de patches, prompts e saídas de ferramentas são descartados antes da persistência. Enquanto o tempo de execução estiver ativo, um arquivo com permissão restrita Unix soquete é o caminho mais rápido; um remetente nativo opcional evita Python comece. Quando o tempo de execução não está ativo, o caminho de falha aberta independente anexa evidências editadas ao `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` reproduz essa fila com desduplicação de ID de evento.

Codex eventos usam seu oficial Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, e `Stop`). Codex atualmente executa ganchos de comando de forma síncrona, então Skill Runtime usa um local Unix remetente soquete/nativo com um tempo limite limitado. Qualquer falha na entrega é engolida e colocada na fila; isso nunca altera uma decisão do Agente. Veja o [documentação oficial do Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Remova apenas as entradas gerenciadas com:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

O servidor se liga a `127.0.0.1` por padrão. Mensagens de transcrição completa e cargas de ferramentas não são copiadas no índice. Padrões secretos comuns são redigidos antes que os resumos normalizados sejam persistidos.

Execute o conjunto de testes sem dependência com:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Engenharia de liberação

GitHub Ações são executadas Python Testes 3.9–3.13, validação de JavaScript, compilação de remetente nativo e um teste real de instalação/iniciação/medicação/parada/desinstalação. UM `v*` tag cria pacotes wheel/sdist mais protegidos por checksum Linux e macOS remetentes nativos. O instalador CLI faz download do ativo de lançamento correspondente, portanto, os usuários finais não precisam de um compilador.

Execute o primeiro experimento de diagnóstico vinculado ao produto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Ele injeta falhas nas evidências do ciclo de vida, falhas explícitas, execuções incompletas e resultados não verificados e, em seguida, avalia o mesmo mecanismo de diagnóstico determinístico usado pelo API e UI. Veja o [Plano experimental PAI-DSW](docs/pai-dsw-experiment-plan.md) para a escada do experimento, testes de não interferência e contrato de reprodutibilidade.

Depois de construir a roda, execute a fumaça do ciclo de vida empacotada isolada com:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Ele é instalado em um ambiente virtual temporário e em uma residência temporária, exerce todo o ciclo de vida local sem habilitar ganchos e verifica a não interferência da configuração do projeto e do agente.

## Design de produto baseado em experimentos

O comportamento do produto segue quatro restrições baseadas em experimentos: evidência antes das conclusões, o primeiro limite observável antes da gravidade, relacionamentos digitados antes dos registros planos e reconstrução determinística antes da assistência probabilística.

Evidências reproduzíveis e suas limitações são mantidas no [relatório de experiência](docs/experiment-results-2026-07-29.md). Os resultados limitados incluem:

- 2.400/2.400 eventos de coletor aceitos sem mutação de entrada/saída;
- 14/14 diagnósticos determinísticos de corpus de falhas sem nenhuma alegação causal sem suporte;
- representação de diagnóstico relacional em 13/14 exato e F1 0,963, enquanto a recuperação plana do ciclo de vida atingiu 1/14 exato e F1 0,080;
- uma auditoria real, segura para a privacidade, que permanece explicitamente inadequada para declarações confirmatórias de efeito do produto porque faltam resultados verificados, cobertura equilibrada entre agentes e rótulos humanos.

Estes resultados validam mecanismos e escolhas de representação, e não generalização de implantação ou benefício humano. Estudos reais de segundo agente, latência de cauda entre plataformas, calibração de falhas reais e estudos de diagnóstico de participantes permanecem lacunas de evidências abertas.

A direção da pesquisa também se baseia em trabalhos primários adjacentes: [SkillsBench](https://arxiv.org/abs/2602.12670) e [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivar o diagnóstico porque os efeitos das habilidades variam e podem regredir; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva a comparação entre agentes com reconhecimento de capacidade; e o [levantamento de proveniência de execução](https://arxiv.org/abs/2606.04990) motiva relações de evidências digitadas, rastreamento de origem e infraestrutura de auditoria com reconhecimento de privacidade.

## Documentação

| Comece aqui | Propósito |
|---|---|
| [Getting Started](docs/getting-started.md) | Instale, conecte um agente, verifique evidências em tempo real e solucione problemas |
| [Arquitetura](docs/architecture.md) | Pipeline de coleta, limites de armazenamento, mecanismo de evidências e modelo de confiança |
| [Matriz de capacidade do adaptador](docs/adapter-capability-matrix.md) | Sinais e limitações exatos por agente/versão |
| [Configuração da plataforma de observabilidade](docs/observability-platform-setup.md) | Conecte plataformas compatíveis com OTLP e importe rastreamentos suportados |
| [Modelo de evento de tempo de execução](docs/runtime-event-model.md) | Vocabulário de eventos estável, procedência, relacionamentos e notas de evidências |
| [Arquitetura de informações da IU](docs/ui-information-architecture.md) | Visão geral, primeiro limite, Panorama, Inspetor, Comparar e Inferred Analysis |
| [Registro de alterações](CHANGELOG.md) | Alterações versionadas visíveis ao usuário |
| [notas de versão v0.3.0](docs/releases/v0.3.0.md) | Orientações de atualização, destaques e limites conhecidos |

Referências de produtos e pesquisas: [definição do produto](docs/product-definition.md), [Especificação MVP](docs/mvp-specification.md), [interoperabilidade de observabilidade](docs/observability-interoperability.md), [resultados do experimento](docs/experiment-results-2026-07-29.md), e o [agenda de pesquisa](docs/research-paper-agenda.md).

## Comunidade e governança

- Ler [Contribuindo](CONTRIBUTING.md) antes de alterar a semântica das evidências, os adaptadores ou o comportamento do produto.
- Siga o [Código de Conduta](CODE_OF_CONDUCT.md) em todos os espaços do projeto.
- Relate vulnerabilidades de forma privada por meio do [Política de segurança](SECURITY.md), não é uma questão pública.
- Utilize o estruturado [rastreador de problemas](https://github.com/hellogxp/skill-runtime-intelligence/issues) para bugs reproduzíveis e propostas de recursos com escopo definido. Nunca anexe bancos de dados de tempo de execução privados ou transcrições de sessões.

## Roteiro

1. **v0.3.0 — Próxima versão:** restrições verificáveis ​​de comportamento de habilidade, atividade concreta de tempo de execução, avaliação limitada por evidências, diagnóstico de cobertura sistêmica e o fluxo de trabalho existente de Panorama e Comparação ao vivo.
2. **Próximo — Adaptador e fortalecimento de diagnóstico:** cobertura mais ampla de agente/versão, calibração de falhas reais, validação de latência final entre plataformas e estudos de diagnóstico de participantes.
3. **Mais tarde — Avaliação do efeito:** avaliação pareada controlada com habilidade/sem habilidade, mantida explicitamente separada do diagnóstico de execução única.

## Status do projeto

Os alvos atuais da árvore de origem `v0.3.0`; use o selo de lançamento acima para identificar a versão publicada mais recente. O tempo de execução inclui restrições de comportamento de habilidades verificáveis, resumos de atividades concretas, inventário de definição instalada, informações oficiais orientadas por consentimento Hook adaptadores para Codex, Claude Code, e Qoder, uma observação apenas OpenCode plug-in, substituto de transcrição rotulado, atribuição de escopo ativo, caminhos exatos de arquivo/artefato, redação, camadas separadas de origem/relacionamento/inferência, SQLite armazenamento, retenção, diagnóstico determinístico, UIe comparação entre execuções/entre agentes. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, e Datadog as exportações podem ser importadas; evidências normalizadas podem ser exportadas ao vivo por meio de opt-in OTLP/HTTP.

A descoberta de candidatos dentro do modelo, as razões de seleção interna do modelo, a eficácia semântica e as alegações de resultados causais permanecem explicitamente sem suporte, a menos que uma fonte ou experimento controlado forneça essa evidência.
