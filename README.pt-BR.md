# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · **Português (Brasil)** · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-inteligência/ações/fluxos de trabalho/ci.yml)[![Liberar](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-inteligência/lançamentos/mais recentes)[![Licença](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENÇA)[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnosticar onde uma execução de habilidade do agente divergiu pela primeira vez e inspecionar as evidências
> por trás de cada conclusão.

Agent Skill Runtime Intelligenceé um sistema de diagnóstico e evidência de tempo de execução somente leitura para habilidades de agente. Ele combina definições de habilidades, eventos oficiais de tempo de execução do agente, rastreamentos importados, fallback de sessão e resultados observáveis ​​do espaço de trabalho em um relatório classificado por evidências.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Início rápido

Instale a versão autônoma mais recente no macOS ou Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Nenhum clone,GitConta central,`sudo`, ouGitA CLI do hub é necessária. O instalador baixa a carga útil de liberação assinada correspondente, verifica as somas de verificação SHA-256, pergunta uma vez antes de ativar ganchos de agente com falha aberta e armazena todos os dados de tempo de execução em`~/.skill-runtime`. Em seguida, ele inicia o tempo de execução local e abre[http://127.0.0.1:4317](http://127.0.0.1:4317).

Você pode[inspecionar o instalador](scripts/install.sh)antes de executá-lo.

Ou execute diretamente de uma verificação de origem:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Abrir[http://127.0.0.1:4317](http://127.0.0.1:4317). ParaCodex, revise e confie nos comandos gerenciados em`/hooks`, inicie um novo turno do Agente e verifique:

```bash
skill-runtime doctor
```

A integração se torna **Verificada** somente após um evento oficial real ser recebido. Um gancho configurado é mostrado como **Pendente**, nunca como evidência ativa.

| Superfície do produto | O que isso responde |
|---|---|
| Visão geral do tempo de execução | QualSkillRunsprecisa de atenção? |
| Primeiro limite observável | Onde as evidências desapareceram ou falharam? |
| Skill Run Panorama | Como a solicitação, a ativação, os recursos, as ferramentas, os artefatos e o resultado se conectam? |
| Inspetor de Evidências | Que fonte, grau, base e capacidade do adaptador apoiam esta afirmação? |
| Comparar | A diferença é comportamental ou apenas uma diferença de observabilidade? |
| Configurações / Médico | O que é lido, armazenado, exportado, pendente e verificado? |

## O problema

Instalar uma Skill não prova que um agente a descobriu. A descoberta não prova a ativação. A ativação não prova que todas as instruções e recursos foram carregados. A execução não prova que a Habilidade melhorou o resultado.

Hoje, estas falhas são muitas vezes silenciosas. Os desenvolvedores ficam perguntando:

- A habilidade estava disponível para este agente?
- Ele foi ativado para esta solicitação?
- Quais instruções, referências, scripts e ativos foram carregados?
- Quais ferramentas,MCPchamadas, subagentes, arquivos e artefatos estavam envolvidos?
- Onde a execução falhou, tentou novamente ou perdeu contexto?
- A habilidade ajudou ou apenas adicionou custo e latência?

## Direção do produto

O primeiro produto é um **Skill Run Panorama**:

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

O panorama é construído a partir de sinais reais, não de modelos de auto-relato:

| Fonte | Exemplos | Evidência |
|---|---|---|
| Arquivos de habilidade | metadados, instruções, scripts, referências, ativos | Observado |
| Eventos de tempo de execução | Chamadas de habilidades, chamadas de ferramentas, subagentes, falhas, duração | Observado |
| Transcrições da sessão | prompts, mensagens, entradas e saídas de ferramentas, pedidos | Observado |
| Resultados do espaço de trabalho | alterações de arquivo,Gitdiff, relatórios, artefatos gerados | Observado |
| Correlação | relações entre eventos, recursos e resultados | Derivado ou Inferido |

## Disciplina de evidências

OUInunca deve apresentar uma inferência como um fato de tempo de execução:

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

## Escopo inicial

O tempo de execução suportaCodex,Claude Code,Qoder, eOpenCodepor meio de adaptadores independentes e versionados e fornece:

- descoberta e validação de habilidades instaladas;
- importação de sessão e observação local ao vivo quando houver suporte;
- Ativação de habilidades, carregamento de recursos e cronogramas de chamada de ferramentas;
- subagente,MCPrelacionamentos entre arquivos, arquivos e artefatos;
- resumos de duração, token, erro, nova tentativa e status, quando disponíveis;
- uma lista de execuções, panorama DAG, linha do tempo de eventos e inspetor de nós.

O MVP **não** inclui mercado, tempo de execução de agente universal, aplicação de segurança, governança corporativa ou declarações de efeito causal.

## Instalação detalhada

A implementação da linha de base não tem dependências de tempo de execução alémPython3,9+. Na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Então abra[http://127.0.0.1:4317](http://127.0.0.1:4317).

O único`install`comando:

1. verifica locais de habilidades de usuários, projetos e plug-ins em cache;
2. detectaCodex,Claude Code,Qoder, eOpenCodesem alterar sua configuração;
3. mostra quais caminhos de Agente e Habilidade serão lidos;
4. baixa um remetente nativo de baixa inicialização verificado por soma de verificação para a plataforma atual, voltando para uma compilação C local e, finalmente, oPythonremetente e pré-aquece um novo binário nativo uma vez durante a instalação;
5. cria`~/.skill-runtime/config.json`e o localSQLiteíndice.

Quando executado de forma interativa, ele pergunta uma vez antes de adicionar ganchos de agente com falha aberta.`--no-hooks`mantém a importação da transcrição como substituto rotulado, enquanto`--enable-hooks`registra consentimento explícito e instala apenas entradas gerenciadas. ParaCodex, abrir`/hooks`após a instalação, revise os comandos gerenciados exatos e confie neles.Codexrequer intencionalmente esta revisão explícita para ganchos adicionados fora da configuração empresarial gerenciada. Inicie um novo turno do Agente e execute:

```bash
.venv/bin/skill-runtime doctor
```

Qodercarrega a configuração do Hook na inicialização, então reinicieQoderapós a primeira instalação.OpenCodedescobre o plug-in gerenciado somente para observação em seu diretório global de plug-ins; reiniciarOpenCodese o processo atual for anterior à instalação. Nenhuma integração lê ou altera solicitações de modelo.

A integração se torna **Live** somente depois que o banco de dados recebe uma resposta real`official_hook`evento. Apenas escrevendo`~/.codex/hooks.json`é mostrado como **Pendente**, nunca conectado.`start`lança o Coletor, o observador de fallback de transcrição, o trabalhador de retenção,SQLitearmazenar e viverUIcomo um processo gerenciado em segundo plano. Nenhuma solicitação de modelo é proxy.

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

`uninstall`remove apenas entradas gerenciadas do Hook eSkill Runtimearquivos de propriedade. Sem`--keep-data`, requer confirmação interativa (ou`--yes`) antes de remover`~/.skill-runtime`; As sessões do agente e as fontes de habilidade nunca são removidas.

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

Os perfis de importação versionados atualmente reconhecem OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, eDatadog JSONformas. Eles apenas criam umSkillRunquando a fonte carrega semântica explícita de Skill; nomes de span genéricos não são tratados como evidência de ativação.

Exporte evidências de tempo de execução normalizadas e específicas de habilidade para qualquerOTLP/HTTPponto de extremidade de rastreamento:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

A exportação fica desabilitada, a menos que um endpoint seja configurado explicitamente. Pontos de verificação, status de nova tentativa e integridade do destino são mostrados em Configurações. Prompts brutos, cargas úteis de ferramentas, credenciais e conteúdos de recursos de habilidades não são exportados. Para exportação autenticada em segundo plano, forneça padrão`OTEL_EXPORTER_OTLP_HEADERS`no ambiente antes`skill-runtime start`; cabeçalhos nunca são gravadosSkill Runtimeargumentos de configuração ou processo.

## Envie evidências de tempo de execução ao vivo

`skill-runtime start`inclui um coletor local. Adaptadores de telemetria nativos, ganchos oficiais, ganchos leves de falha aberta eSDKintegrações podem anexar um único evento ou um lote limitado a`POST /api/events`:

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

O endpoint edita credenciais comuns antes da persistência, desduplica por`event_id`, preserva um envelope bruto redigido separado e retorna o resultado`skill_run_ids`.`GET /api/collector/schema`expõe o vocabulário de eventos suportado e os modos de coleta. OUIouve`/api/stream`usando SSE, com polling apenas como alternativa de reconexão.

O indicador de origem distingue as evidências primárias de tempo de execução das`Transcript fallback`e vestígios importados. Um endpoint de coletor por si só não reivindica telemetria nativa: todo produtor deve declarar se seu evento veio de telemetria nativa, de um gancho oficial, de um gancho leve ou de um gancho.SDK.

### Ganchos de agente opcionais

Inspecione primeiro os caminhos e eventos exatos. Este comando é somente leitura:

```bash
.venv/bin/skill-runtime setup
```

A instalação do gancho requer um sinalizador explícito:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

O instalador faz backup da configuração do Agente, preserva os ganchos existentes e adiciona apenas entradas que carregam umSkill Runtimemarcador de gestão. O adaptador de gancho armazena campos mínimos de ciclo de vida em vez de prompts completos ou cargas úteis de ferramentas. Enquanto o tempo de execução estiver ativo, um arquivo com permissão restritaUnixsoquete é o caminho mais rápido; um remetente nativo opcional evitaPythoncomece. Quando o tempo de execução não está ativo, o caminho de falha aberta independente anexa evidências editadas ao`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`reproduz essa fila com desduplicação de ID de evento.

Codexeventos usam seu Hook oficialAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, e`Stop`).Codexatualmente executa ganchos de comando de forma síncrona, entãoSkill Runtimeusa um localUnixremetente soquete/nativo com um tempo limite limitado. Qualquer falha na entrega é engolida e colocada na fila; isso nunca altera uma decisão do Agente. Veja o[documentação oficial do Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Remova apenas as entradas gerenciadas com:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

O servidor se liga a`127.0.0.1`por padrão. Mensagens de transcrição completa e cargas de ferramentas não são copiadas no índice. Padrões secretos comuns são redigidos antes que os resumos normalizados sejam persistidos.

Execute o conjunto de testes sem dependência com:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Engenharia de liberação

GitExecuções de ações do HubPythonTestes 3.9–3.13, validação de JavaScript, compilação de remetente nativo e um teste real de instalação/iniciação/medicação/parada/desinstalação. UM`v*`tag cria pacotes wheel/sdist, além de remetentes nativos Linux e macOS protegidos por soma de verificação. O instalador CLI faz download do ativo de lançamento correspondente, portanto, os usuários finais não precisam de um compilador.

Execute o primeiro experimento de diagnóstico vinculado ao produto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Ele injeta falhas nas evidências do ciclo de vida, falhas explícitas, execuções incompletas e resultados não verificados e, em seguida, avalia o mesmo mecanismo de diagnóstico determinístico usado peloAPIeUI. Veja o[Plano experimental PAI-DSW](docs/pai-dsw-experiment-plan.md)para a escada do experimento, testes de não interferência e contrato de reprodutibilidade.

Depois de construir a roda, execute a fumaça do ciclo de vida empacotada isolada com:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Ele é instalado em um ambiente virtual temporário e em uma residência temporária, exerce todo o ciclo de vida local sem habilitar ganchos e verifica a não interferência da configuração do projeto e do agente.

## Design de produto baseado em experimentos

O comportamento do produto é limitado pelo[filosofia de produto baseada em experimentos](docs/experiment-driven-product-philosophy.md): evidência antes das conclusões, o primeiro limite observável antes da gravidade, relacionamentos digitados antes dos registros planos e reconstrução determinística antes da assistência probabilística.

As evidências locais reproduzíveis atuais incluem:

- 7/7 portões de experimentos locais passaram;
- 2.400/2.400 eventos de coletor aceitos sem mutação de entrada/saída;
- 14/14 diagnósticos determinísticos de corpus de falhas sem nenhuma alegação causal sem suporte;
- representação de diagnóstico relacional em 13/14 exato e F1 0,963, enquanto a recuperação plana do ciclo de vida atingiu 1/14 exato e F1 0,080;
- Os casos de material de estudo do 11/11 colocam primeiro o limite observável mais antigo.

Estes resultados validam mecanismos e escolhas de representação, e não generalização de implantação ou benefício humano. Estudos reais de segundo agente, latência de cauda entre plataformas, calibração de falhas reais e estudos de diagnóstico de participantes permanecem lacunas de evidências abertas.

A direção da pesquisa também se baseia em trabalhos primários adjacentes:[SkillsBench](https://arxiv.org/abs/2602.12670)e[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motivar o diagnóstico porque os efeitos das habilidades variam e podem regredir;[Harness-Bench](https://arxiv.org/abs/2605.27922)motiva a comparação entre agentes com reconhecimento de capacidade; e o[levantamento de proveniência de execução](https://arxiv.org/abs/2606.04990)motiva relações de evidências digitadas, rastreamento de origem e infraestrutura de auditoria com reconhecimento de privacidade.

## Documentação

- [Definição do produto](docs/product-definition.md)
- [Especificação MVP](docs/mvp-specification.md)
- [Modelo de evento de tempo de execução](docs/runtime-event-model.md)
- [Arquitetura de informações da IU](docs/ui-information-architecture.md)
- [Matriz de capacidade do adaptador](docs/adapter-capability-matrix.md)
- [Interoperabilidade de observabilidade](docs/observability-interoperability.md)
- [Configuração da plataforma de observabilidade](docs/observability-platform-setup.md)
- [Pesquisa e cenário competitivo](docs/research-and-competitive-landscape.md)
- [Agenda de artigos de pesquisa](docs/research-paper-agenda.md)
- [Filosofia de produto baseada em experimentos](docs/experiment-driven-product-philosophy.md)
- [Resultados da experiência](docs/experiment-results-2026-07-29.md)
- [Plano experimental PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Roteiro

1. **v0.1 — Evidência e diagnóstico em tempo de execução:** coleta ao vivo,Skill Run Panorama, diagnóstico de primeiro limite, inspeção de evidências, comparação e interoperabilidade OTLP.
2. **v0.2 — Estudos de diagnóstico e proteção do adaptador:** versões adicionais do agente, experimentos reais entre agentes e avaliação dos participantes.
3. **v0.3 — Avaliação do efeito:** avaliação pareada controlada com habilidade/sem habilidade, mantida separada do diagnóstico de execução única.

## Status do projeto

UMSkillRun-o primeiro tempo de execução é executável: inventário de definição instalada,Codexsubstituto de transcrição, adaptadores Hook oficiais orientados por consentimento paraCodex,Claude Code, eQoder, uma observação apenasOpenCodeadaptador de plug-in, atribuição de escopo ativo, caminhos exatos de arquivo/artefato, redação, camadas separadas de origem/relacionamento/inferência,SQLitearmazenamento, retenção, comparação entre execuções e entre agentes, diagnóstico determinístico e panorama ao vivoUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, eDatadogas exportações podem ser importadas; evidências normalizadas podem ser exportadas ao vivo por meio de opt-inOTLP/HTTP. A descoberta de candidatos, as razões de seleção interna do modelo, a eficácia semântica e as alegações de resultados causais permanecem explicitamente sem suporte.
