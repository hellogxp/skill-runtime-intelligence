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


> Diagnosticar onde uma execução de habilidade do agente divergiu pela primeira vez e inspecionar as evidências
> por trás de cada conclusão.

Agent Skill Runtime Intelligence é um sistema de diagnóstico e evidência de tempo de execução somente leitura para habilidades de agente. Ele combina definições de habilidades, eventos oficiais de tempo de execução do agente, rastreamentos importados, fallback de sessão e resultados observáveis ​​do espaço de trabalho em um Skill Run Panorama com classificação de evidências.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Início rápido

Instale e inicie a versão mais recente em macOS ou Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nenhum clone, conta, `sudo` ou GitHub CLI é necessário. O instalador verifica a soma de verificação de lançamento, detecta Agentes e Habilidades suportadas, explica cada caminho que irá ler, pergunta uma vez antes de ativar ganchos somente de observação e abre o UI local em [http://127.0.0.1:4317](http://127.0.0.1:4317). Os dados de tempo de execução permanecem em `~/.skill-runtime`, a menos que você configure explicitamente uma exportação.

Você pode [inspecionar o instalador](scripts/install.sh) antes de executá-lo.

### Veja sua primeira live SkillRun

1. Aceite a configuração opcional de falha de abertura Hook quando o instalador solicitar.
2. Reinicie o Agente e inicie uma nova tarefa. Em Codex, revise primeiro os comandos gerenciados em `/hooks`; as tarefas existentes não carregam novos Hooks.
3. Use uma Skill normalmente, depois confirme a integração e abra o UI:

```bash
skill-runtime doctor
skill-runtime status
```

Uma integração estará **Live** somente depois que o Coletor receber um evento de tempo de execução real. Um Hook configurado, mas não observado, está **Pendente** – nunca apresentado como evidência real. Abra [http://127.0.0.1:4317](http://127.0.0.1:4317) ou consulte [Guia de primeiros passos](docs/getting-started.md) para obter instruções específicas do agente e solução de problemas.

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
| First Observable Boundary | Onde as evidências desapareceram ou falharam? |
| Skill Run Panorama | Como a solicitação, a ativação, os recursos, as ferramentas, os artefatos e o resultado se conectam? |
| Evidence Inspector | Que fonte, grau, base e capacidade do adaptador apoiam esta afirmação? |
| Comparar | A diferença é comportamental ou apenas uma diferença de observabilidade? |
| Inferred Analysis | Que explicação baseada em evidências ou próxima investigação é plausível? |
| Configurações / Médico | O que é lido, armazenado, exportado, pendente e verificado? |

## Como funciona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observa o fluxo de trabalho que você já usa. Os adaptadores versionados transformam os eventos nativos do agente em um ciclo de vida de habilidade estável, enquanto os envelopes de origem bruta, os eventos normalizados, os relacionamentos e as inferências permanecem separados. O mecanismo de diagnóstico identifica primeiro o limite mais antigo onde as evidências faltam ou falham; não inventa a intenção do modelo ou a eficácia causal.

| Fonte de dados | Papel | Frescura | UI rótulo |
|---|---|---|---|
| Ganchos/plugins/eventos SDK oficiais do agente | Ciclo de vida primário, ferramenta, subagente e evidência terminal | Ao vivo | `Official hook` / `Native telemetry` |
| Arquivos de habilidades e resultados observáveis ​​do espaço de trabalho | Definição, recurso, arquivo, artefato e evidência de teste | Instantâneo ao vivo/indexado | `Observed` |
| Transcrições da sessão | Fallback de compatibilidade quando o Agente não expõe tempo de execução suficiente API | Quase ao vivo ou histórico | `Transcript fallback` |
| OTLP e exportações de rastreamento compatíveis | Interoperabilidade e importação histórica | Exportação ao vivo/importação em lote | Perfil de origem mostrado |
| Correlação determinística | Conecta eventos a um SkillRun sem alterar os fatos de origem | Na ingestão | `Derived` |
| Assistência semântica | Apenas explicações e sugestões de investigação | Sob demanda | `Inferred` |

Os adaptadores originais suportados têm versões independentes:

| Agente | Integração primária | Cair pra trás | Visibilidade de ativação |
|---|---|---|---|
| Codex | Comando oficial Hooks | Importação de sessão | Ativação explícita quando exposta pelo evento Hook |
| Claude Code | Hooks oficiais | Importação de sessão | Ferramenta de habilidade explícita e evidências de comando de barra quando expostas |
| Qoder | Comando oficial Hooks | Registros locais | Ativação explícita quando exposta pela ferramenta Skill |
| OpenCode | Plug-in global somente de observação | Registros locais | Retornos de chamada da ferramenta de habilidade foram expostos |

Os limites exatos de capacidade estão documentados em [matriz de capacidade do adaptador](docs/adapter-capability-matrix.md). Os estágios não suportados e não observados permanecem visíveis em vez de serem convertidos em falhas.

## O problema

Instalar uma Skill não prova que um agente a descobriu. A descoberta não prova a ativação. A ativação não prova que todas as instruções e recursos foram carregados. A execução não prova que a Habilidade melhorou o resultado.

Hoje, estas falhas são muitas vezes silenciosas. Os desenvolvedores ficam perguntando:

- A habilidade estava disponível para este agente?
- Ele foi ativado para esta solicitação?
- Quais instruções, referências, scripts e ativos foram carregados?
- Quais ferramentas, chamadas MCP, subagentes, arquivos e artefatos estavam envolvidos?
- Onde a execução falhou, tentou novamente ou perdeu contexto?
- A habilidade ajudou ou apenas adicionou custo e latência?

## Diagnóstico específico de habilidade

O objeto de diagnóstico primário é um `SkillRun`, não uma sessão inteira do Agente:

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
- Suporte baseado em adaptador para alteração de formatos de transcrição de agentes.

## Escopo atual

O tempo de execução suporta Codex, Claude Code, Qoder e OpenCode por meio de adaptadores independentes com versão e fornece:

- descoberta e validação de habilidades instaladas;
- coleção Hook/plugin oficial em tempo real mais fallback de sessão rotulada;
- Ativação de habilidades, carregamento de recursos e cronogramas de chamada de ferramentas;
- relacionamentos de subagente, MCP, arquivo e artefato;
- resumos de duração, token, erro, nova tentativa e status, quando disponíveis;
- Runtime Overview e diagnóstico de primeiro limite;
- um DAG panorâmico, cronograma de eventos e inspetor de evidências;
- comparação entre agentes e entre agentes com reconhecimento de capacidade;
- uma superfície Inferred Analysis separada que não pode reescrever fatos de tempo de execução;
- exportação OTLP/HTTP opcional e importação de rastreamento de observabilidade suportada.

O MVP **não** inclui mercado, tempo de execução de agente universal, aplicação de segurança, governança corporativa ou declarações de efeito causal.

## Instalação detalhada

Para o caminho mais curto suportado, use o instalador de versão de uma linha em [Início rápido](#quick-start). O fluxo completo da primeira execução, as etapas de reinicialização/confiança específicas do agente, o comportamento de privacidade e a solução de problemas estão no [Guia de primeiros passos](docs/getting-started.md).

Para desenvolvimento, a implementação de linha de base não tem dependências de tempo de execução além de Python 3.9+. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Em seguida, abra [http://127.0.0.1:4317](http://127.0.0.1:4317).

O comando `install` único:

1. verifica locais de habilidades de usuários, projetos e plug-ins em cache;
2. detecta Codex, Claude Code, Qoder e OpenCode sem alterar sua configuração;
3. mostra quais caminhos de Agente e Habilidade serão lidos;
4. baixa um remetente nativo de baixa inicialização verificado por soma de verificação para a plataforma atual, recorrendo a uma compilação C local e, finalmente, ao remetente Python, e pré-aquece um novo binário nativo uma vez durante a instalação;
5. cria `~/.skill-runtime/config.json` e o índice SQLite local.

Quando executado de forma interativa, ele pergunta uma vez antes de adicionar ganchos de agente com falha aberta. `--no-hooks` mantém a importação de transcrição como substituto rotulado, enquanto `--enable-hooks` registra consentimento explícito e instala apenas entradas gerenciadas. Para Codex, abra `/hooks` após a instalação, revise os comandos gerenciados exatos e confie neles. Codex requer intencionalmente esta revisão explícita para ganchos adicionados fora da configuração corporativa gerenciada. Inicie uma nova tarefa/sessão Codex após confiar nos Hooks e execute:

```bash
.venv/bin/skill-runtime doctor
```

Qoder carrega a configuração Hook na inicialização, então reinicie Qoder após a primeira instalação. OpenCode descobre o plugin gerenciado somente para observação em seu diretório global de plugins; reinicie OpenCode se o processo atual for anterior à instalação. Nenhuma integração lê ou altera solicitações de modelo.

A integração se torna **Live** somente depois que o banco de dados recebe um evento `official_hook` real. Apenas escrever `~/.codex/hooks.json` é mostrado como **Pendente**, nunca Conectado. `start` lança o Coletor, o observador de transcrição de fallback, o trabalhador de retenção, o armazenamento SQLite e o UI ativo como um processo gerenciado em segundo plano. Nenhuma solicitação de modelo é proxy.

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

`uninstall` remove apenas entradas Hook gerenciadas e arquivos de propriedade de Skill Runtime. Sem `--keep-data`, requer confirmação interativa (ou `--yes`) antes de remover `~/.skill-runtime`; As sessões do agente e as fontes de habilidade nunca são removidas.

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

Os perfis de importação versionados atualmente reconhecem as formas OTLP/Phoenix, Langfuse, LangSmith, W&B Weave e Datadog JSON. Eles só criam um SkillRun quando a fonte carrega semântica explícita de Skill; nomes de span genéricos não são tratados como evidência de ativação.

Exporte evidências de tempo de execução normalizadas e específicas da habilidade para qualquer endpoint de rastreamento OTLP/HTTP:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

A exportação fica desabilitada, a menos que um endpoint seja configurado explicitamente. Pontos de verificação, status de nova tentativa e integridade do destino são mostrados em Configurações. Prompts brutos, cargas úteis de ferramentas, credenciais e conteúdos de recursos de habilidades não são exportados. Para exportação em segundo plano autenticada, forneça o padrão `OTEL_EXPORTER_OTLP_HEADERS` no ambiente antes de `skill-runtime start`; cabeçalhos nunca são gravados na configuração Skill Runtime ou nos argumentos do processo.

## Envie evidências de tempo de execução ao vivo

`skill-runtime start` inclui um coletor local. Adaptadores de telemetria nativos, ganchos oficiais, ganchos leves de falha aberta e integrações SDK podem anexar um único evento ou um lote limitado a `POST /api/events`:

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

O endpoint edita credenciais comuns antes da persistência, desduplica por `event_id`, preserva um envelope bruto redigido separado e retorna o `skill_run_ids` resultante. `GET /api/collector/schema` expõe o vocabulário de eventos suportado e os modos de coleta. O UI escuta `/api/stream` usando SSE, com polling apenas como um substituto para reconexão.

O indicador de origem distingue a evidência de tempo de execução primária de `Transcript fallback` e rastreamentos importados. Um endpoint de coletor por si só não reivindica telemetria nativa: todo produtor deve declarar se seu evento veio de telemetria nativa, de um gancho oficial, de um gancho leve ou de um SDK.

### Ganchos de agente opcionais

Inspecione primeiro os caminhos e eventos exatos. Este comando é somente leitura:

```bash
.venv/bin/skill-runtime setup
```

A instalação Hook requer um sinalizador explícito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

O instalador faz backup da configuração do Agente, preserva os ganchos existentes e adiciona apenas entradas que carregam um marcador de gerenciamento Skill Runtime. O adaptador de gancho armazena campos mínimos de ciclo de vida em vez de prompts completos ou cargas úteis de ferramentas. Para chamadas de ferramenta concluídas, ele extrai apenas `SKILL.md` exato, recurso de habilidade padrão e caminhos de arquivos alterados na memória; comandos brutos, corpos de patches, prompts e saídas de ferramentas são descartados antes da persistência. Enquanto o tempo de execução estiver ativo, um soquete Unix com permissão restrita é o caminho mais rápido; um remetente nativo opcional evita a inicialização do Python. Quando o tempo de execução não está ativo, o caminho de falha aberta independente anexa evidências editadas a `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` reproduz essa fila com desduplicação de ID de evento.

Os eventos Codex usam seu Hook API oficial (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` e `Stop`). Codex atualmente executa ganchos de comando de forma síncrona, então Skill Runtime usa um soquete Unix local/remetente nativo com um tempo limite limitado. Qualquer falha na entrega é engolida e colocada na fila; isso nunca altera uma decisão do Agente. Veja o [documentação oficial do Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

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

GitHub Actions executa testes Python 3.9–3.13, validação de JavaScript, compilação de remetente nativo e um teste real de instalação/iniciação/medicação/parada/desinstalação. Uma tag `v*` cria pacotes wheel/sdist mais remetentes nativos Linux e macOS protegidos por checksum. O instalador CLI faz download do ativo de lançamento correspondente, portanto, os usuários finais não precisam de um compilador.

Execute o primeiro experimento de diagnóstico vinculado ao produto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Ele injeta falhas nas evidências do ciclo de vida, falhas explícitas, execuções incompletas e resultados não verificados e, em seguida, avalia o mesmo mecanismo de diagnóstico determinístico usado pelo API e UI. Consulte o [Plano experimental PAI-DSW](docs/pai-dsw-experiment-plan.md) para a escala do experimento, testes de não interferência e contrato de reprodutibilidade.

Depois de construir a roda, execute a fumaça do ciclo de vida empacotada isolada com:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Ele é instalado em um ambiente virtual temporário e em uma residência temporária, exerce todo o ciclo de vida local sem habilitar ganchos e verifica a não interferência da configuração do projeto e do agente.

## Design de produto baseado em experimentos

O comportamento do produto é restringido pelo [filosofia de produto baseada em experimentos](docs/experiment-driven-product-philosophy.md): evidência antes das conclusões, o primeiro limite observável antes da gravidade, relacionamentos digitados antes dos registros planos e reconstrução determinística antes da assistência probabilística.

As evidências locais reproduzíveis atuais incluem:

- 7/7 portões de experimentos locais passaram;
- 2.400/2.400 eventos de coletor aceitos sem mutação de entrada/saída;
- 14/14 diagnósticos determinísticos de corpus de falhas sem nenhuma alegação causal sem suporte;
- representação de diagnóstico relacional em 13/14 exato e F1 0,963, enquanto a recuperação plana do ciclo de vida atingiu 1/14 exato e F1 0,080;
- Os casos de material de estudo do 11/11 colocam primeiro o limite observável mais antigo.

Estes resultados validam mecanismos e escolhas de representação, e não generalização de implantação ou benefício humano. Estudos reais de segundo agente, latência de cauda entre plataformas, calibração de falhas reais e estudos de diagnóstico de participantes permanecem lacunas de evidências abertas.

A direção da pesquisa também se baseia em trabalhos primários adjacentes: [SkillsBench](https://arxiv.org/abs/2602.12670) e [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivam o diagnóstico porque os efeitos das habilidades variam e podem regredir; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva comparação entre agentes com reconhecimento de capacidade; e o [levantamento de proveniência de execução](https://arxiv.org/abs/2606.04990) motiva relações de evidências digitadas, rastreamento de proveniência e infraestrutura de auditoria consciente da privacidade.

## Documentação

| Comece aqui | Propósito |
|---|---|
| [Getting Started](docs/getting-started.md) | Instale, conecte um agente, verifique evidências em tempo real e solucione problemas |
| [Arquitetura](docs/architecture.md) | Pipeline de coleta, limites de armazenamento, mecanismo de evidências e modelo de confiança |
| [Matriz de capacidade do adaptador](docs/adapter-capability-matrix.md) | Sinais e limitações exatos por agente/versão |
| [Configuração da plataforma de observabilidade](docs/observability-platform-setup.md) | Conecte plataformas compatíveis com OTLP e importe rastreamentos suportados |
| [Modelo de evento de tempo de execução](docs/runtime-event-model.md) | Vocabulário de eventos estável, procedência, relacionamentos e notas de evidências |
| [Arquitetura de informações da IU](docs/ui-information-architecture.md) | Visão geral, primeiro limite, Panorama, Inspetor, Comparar e Inferred Analysis |

Referências de produtos e pesquisas: [definição do produto](docs/product-definition.md), [Especificação MVP](docs/mvp-specification.md), [interoperabilidade de observabilidade](docs/observability-interoperability.md), [filosofia de produto baseada em experimentos](docs/experiment-driven-product-philosophy.md), [resultados do experimento](docs/experiment-results-2026-07-29.md) e [agenda de pesquisa](docs/research-paper-agenda.md).

## Roteiro

1. **v0.2.0 — Disponível agora:** coleta de falha aberta ao vivo, quatro adaptadores de agente versionados, Runtime Overview, diagnóstico de primeiro limite, Panorama, Evidence Inspector, comparação com reconhecimento de capacidade, Inferred Analysis e interoperabilidade OTLP.
2. **Próximo — Adaptador e fortalecimento de diagnóstico:** cobertura mais ampla de agente/versão, calibração de falhas reais, validação de latência final entre plataformas e estudos de diagnóstico de participantes.
3. **Mais tarde — Avaliação do efeito:** avaliação pareada controlada com habilidade/sem habilidade, mantida explicitamente separada do diagnóstico de execução única.

## Status do projeto

A versão `v0.2.0` foi publicada. O tempo de execução inclui inventário de definição instalada, adaptadores Hook oficiais orientados por consentimento para Codex, Claude Code e Qoder, um plug-in OpenCode somente de observação, fallback de transcrição rotulado, atribuição de escopo ativo, caminhos exatos de arquivo/artefato, redação, fontes separadas/relacionamento/camadas de inferência, armazenamento SQLite, retenção, diagnóstico determinístico, UI ao vivo e comparação entre execuções/entre agentes. As exportações OTLP/Phoenix, Langfuse, LangSmith, W&B Weave e Datadog podem ser importadas; evidências normalizadas podem ser exportadas ao vivo por meio do opt-in OTLP/HTTP.

A descoberta de candidatos dentro do modelo, as razões de seleção interna do modelo, a eficácia semântica e as alegações de resultados causais permanecem explicitamente sem suporte, a menos que uma fonte ou experimento controlado forneça essa evidência.
