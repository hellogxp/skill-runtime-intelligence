# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · **Español** · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-inteligencia/acciones/flujos de trabajo/ci.yml)[![Liberar](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-inteligencia/lanzamientos/últimos)[![Licencia](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENCIA)[![Pitón](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnosticar dónde divergió por primera vez una ejecución de habilidad del agente e inspeccionar la evidencia
> detrás de cada conclusión.

Agent Skill Runtime Intelligencees un sistema de diagnóstico y evidencia en tiempo de ejecución de solo lectura para Agent Skills. Combina definiciones de habilidades, eventos oficiales de tiempo de ejecución del agente, seguimientos importados, respaldo de sesiones y resultados observables del espacio de trabajo en un sistema calificado por evidencia.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Inicio rápido

Instale la última versión independiente en macOS o Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Sin clon,Gitcuenta central,`sudo`, oGitSe requiere la CLI del concentrador. El instalador descarga la carga útil correspondiente de la versión firmada, verifica las sumas de verificación SHA-256, pregunta una vez antes de habilitar los enlaces del Agente de apertura fallida y almacena todos los datos del tiempo de ejecución en`~/.skill-runtime`. Luego inicia el tiempo de ejecución local y abre[http://127.0.0.1:4317](http://127.0.0.1:4317).

Puede[inspeccionar el instalador](scripts/install.sh)antes de ejecutarlo.

O ejecútelo directamente desde una fuente de pago:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Abierto[http://127.0.0.1:4317](http://127.0.0.1:4317). ParaCodex, revise y confíe en los comandos administrados en`/hooks`, comienza un nuevo turno de Agente, luego verifica:

```bash
skill-runtime doctor
```

La integración se vuelve **Verificada** solo después de recibir un evento oficial real. Un enlace configurado se muestra como **Pendiente**, nunca como evidencia real.

| Superficie del producto | lo que responde |
|---|---|
| Descripción general del tiempo de ejecución | CualSkillRuns¿Necesitas atención? |
| Primer límite observable | ¿Dónde faltaron o fallaron las pruebas por primera vez? |
| Skill Run Panorama | ¿Cómo se conectaron la solicitud, la activación, los recursos, las herramientas, los artefactos y el resultado? |
| inspector de pruebas | ¿Qué fuente, grado, base y capacidad del adaptador respaldan esta afirmación? |
| Comparar | ¿Es una diferencia de comportamiento o sólo una diferencia de observabilidad? |
| Configuración / Médico | ¿Qué se lee, almacena, exporta, pendiente y verifica? |

## el problema

Instalar una Skill no prueba que un agente la haya descubierto. El descubrimiento no prueba la activación. La activación no prueba que se hayan cargado todas las instrucciones y recursos. La ejecución no prueba que la Habilidad haya mejorado el resultado.

Hoy en día, estos fracasos suelen guardar silencio. Los desarrolladores se quedan preguntando:

- ¿Estaba la habilidad disponible para este agente?
- ¿Se activó para esta solicitud?
- ¿Qué instrucciones, referencias, guiones y recursos se cargaron?
- ¿Qué herramientas,MCP¿Estuvieron involucrados llamadas, subagentes, archivos y artefactos?
- ¿Dónde falló la ejecución, se reintentó o se perdió contexto?
- ¿La habilidad ayudó o solo agregó costo y latencia?

## Dirección del producto

El primer producto es un **Skill Run Panorama**:

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

El panorama se construye a partir de señales reales, no de modelos de autoinforme:

| Fuente | Ejemplos | Evidencia |
|---|---|---|
| Archivos de habilidades | metadatos, instrucciones, scripts, referencias, activos | Observado |
| Eventos de tiempo de ejecución | Llamadas de habilidades, llamadas de herramientas, subagentes, fallas, duración | Observado |
| Transcripciones de sesiones | indicaciones, mensajes, entradas y salidas de herramientas, pedidos | Observado |
| Resultados del espacio de trabajo | cambios de archivos,Gitdiff, informes, artefactos generados | Observado |
| Correlación | Relaciones entre eventos, recursos y resultados. | Derivado o Inferido |

## Disciplina de evidencia

ElUInunca debe presentar una inferencia como un hecho en tiempo de ejecución:

- **Observado**: presente explícitamente en un evento o archivo de origen.
- **Derivado**: conectado deterministamente a partir de evidencia observada.
- **Inferido**: una explicación plausible con incertidumbre.
- **Experimental**: un efecto medido mediante una evaluación pareada controlada.

Un único seguimiento puede respaldar la atribución de ejecución. No puede probar la eficacia causal. Afirmaciones como “esta habilidad mejoró la tasa de éxito” requieren evaluaciones repetidas con/sin habilidad.

## Principios del producto

- Privado de forma predeterminada, con implementación local, híbrida y conectada al equipo.
- Observación de sólo lectura; nunca se haga cargo del bucle del agente.
- Sin proxy modelo ni servicio en la nube obligatorio.
- Sin bloqueo, puerta de aprobación ni aplicación de políticas en el producto predeterminado.
- Procedencia explícita y clasificación de evidencia.
- Divulgación progresiva: narrativa simple primero, eventos crudos a pedido.
- Soporte basado en adaptador para cambiar los formatos de transcripción de agentes.

## Alcance inicial

El tiempo de ejecución admiteCodex,Claude Code,Qoder, yOpenCodea través de adaptadores versionados independientes y proporciona:

- instalado Descubrimiento y validación de habilidades;
- importación de sesiones y observación local en vivo cuando sea compatible;
- Activación de habilidades, carga de recursos y cronogramas de uso de herramientas;
- subagente,MCPrelaciones entre archivos, artefactos y archivos;
- resúmenes de duración, token, error, reintento y estado cuando estén disponibles;
- una lista de ejecuciones, DAG panorámico, línea de tiempo de eventos e inspector de nodos.

El MVP **no** incluye un mercado, tiempo de ejecución de agente universal, aplicación de seguridad, gobernanza empresarial ni afirmaciones de efectos causales.

## Instalación detallada

La implementación básica no tiene dependencias de tiempo de ejecución más alláPython3,9+. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Luego abre[http://127.0.0.1:4317](http://127.0.0.1:4317).

la única vez`install`dominio:

1. escanea ubicaciones de Skill de usuarios, proyectos y complementos almacenados en caché;
2. detectaCodex,Claude Code,Qoder, yOpenCodesin cambiar su configuración;
3. muestra qué rutas de Agente y Habilidad se leerán;
4. descarga un remitente nativo de bajo inicio verificado con suma de verificación para la plataforma actual, recurriendo a una compilación C local y finalmente elPythonremitente y precalienta un binario nativo nuevo una vez durante la instalación;
5. crea`~/.skill-runtime/config.json`y los localesSQLiteíndice.

Cuando se ejecuta de forma interactiva, pregunta una vez antes de agregar enlaces de agente de apertura fallida.`--no-hooks`mantiene la importación de transcripciones como reserva etiquetada, mientras`--enable-hooks`registra el consentimiento explícito e instala solo entradas administradas. ParaCodex, abierto`/hooks`Después de la instalación, revise los comandos administrados exactos y confíe en ellos.Codexrequiere intencionalmente esta revisión explícita de los enlaces agregados fuera de la configuración empresarial administrada. Inicie un nuevo turno de Agente, luego ejecute:

```bash
.venv/bin/skill-runtime doctor
```

Qodercarga la configuración de Hook al inicio, así que reinicieQoderdespués de la primera instalación.OpenCodedescubre el complemento administrado de solo observación desde su directorio global de complementos; ReanudarOpenCodesi el proceso actual es anterior a la instalación. Ninguna integración lee ni cambia las solicitudes de modelo.

La integración se vuelve **activa** solo después de que la base de datos reciba una notificación real.`official_hook`evento. Simplemente escribiendo`~/.codex/hooks.json`se muestra como **Pendiente**, nunca Conectado.`start`lanza el recopilador, el observador de reserva de transcripciones, el trabajador de retención,SQLitealmacenar y vivirUIcomo un proceso en segundo plano administrado. No se representa ninguna solicitud de modelo.

Comandos del ciclo de vida:

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

`uninstall`elimina solo las entradas de Hook administradas ySkill Runtime-archivos de propiedad. Sin`--keep-data`, requiere confirmación interactiva (o`--yes`) antes de retirar`~/.skill-runtime`; Las sesiones de agentes y las fuentes de habilidades nunca se eliminan.

Para indexar y publicar por separado:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importe una exportación de seguimiento existente desde un sistema de observabilidad convencional:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Los perfiles de importación versionados actualmente reconocen OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, yDatadog JSONformas. Sólo crean unSkillRuncuando la fuente contiene una semántica de Habilidad explícita; Los nombres de intervalo genéricos no se tratan como evidencia de activación.

Exporte evidencia de tiempo de ejecución normalizada y específica de habilidades a cualquierOTLP/HTTPpunto final de seguimiento:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

La exportación está deshabilitada a menos que se configure explícitamente un punto final. Los puntos de control, el estado de reintento y el estado del destino se muestran en Configuración. Las indicaciones sin procesar, las cargas útiles de las herramientas, las credenciales y el contenido de los recursos de habilidades no se exportan. Para exportación en segundo plano autenticada, proporcione estándar`OTEL_EXPORTER_OTLP_HEADERS`en el ambiente antes`skill-runtime start`; los encabezados nunca se escribenSkill Runtimeargumentos de configuración o proceso.

## Enviar evidencia en tiempo de ejecución en vivo

`skill-runtime start`Incluye un coleccionista local. Adaptadores de telemetría nativos, ganchos oficiales, ganchos livianos de apertura por falla ySDKLas integraciones pueden agregar un solo evento o un lote limitado a`POST /api/events`:

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

El punto final redacta las credenciales comunes antes de la persistencia, deduplica mediante`event_id`, conserva un sobre sin formato redactado por separado y devuelve el resultado`skill_run_ids`.`GET /api/collector/schema`expone el vocabulario de eventos admitidos y los modos de recopilación. ElUIescucha`/api/stream`usando SSE, con sondeo solo como alternativa de reconexión.

El indicador de origen distingue la evidencia de tiempo de ejecución primaria de`Transcript fallback`y rastros importados. Un punto final de Collector por sí solo no reclama telemetría nativa: cada productor debe declarar si su evento provino de telemetría nativa, un gancho oficial, un gancho liviano o unSDK.

### Ganchos de agente opcionales

Inspeccione primero los caminos y eventos exactos. Este comando es de sólo lectura:

```bash
.venv/bin/skill-runtime setup
```

La instalación del gancho requiere una bandera explícita:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

El instalador realiza una copia de seguridad de la configuración del Agente, conserva los enlaces existentes y agrega solo entradas que llevan unSkill Runtimemarcador de gestión. El adaptador de gancho almacena campos mínimos del ciclo de vida en lugar de indicaciones completas o cargas útiles de herramientas. Mientras el tiempo de ejecución está activo, un permiso restringidoUnixsocket es el camino rápido; un remitente nativo opcional evitaPythonpuesta en marcha. Cuando el tiempo de ejecución no está activo, la ruta independiente de apertura por error agrega evidencia redactada a`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`reproduce esa cola con deduplicación de ID de evento.

CodexLos eventos utilizan su gancho oficial.API(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, y`Stop`).Codexactualmente ejecuta enlaces de comando sincrónicamente, por lo queSkill Runtimeusa un localUnixsocket/remitente nativo con un tiempo de espera limitado. Cualquier error en la entrega se traga y se pone en cola; nunca cambia la decisión de un Agente. Ver el[documentación oficial del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Elimine solo las entradas administradas con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

El servidor se une a`127.0.0.1`por defecto. Los mensajes de transcripción completa y las cargas útiles de las herramientas no se copian en el índice. Los patrones secretos comunes se redactan antes de que persistan los resúmenes normalizados.

Ejecute el conjunto de pruebas sin dependencia con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingeniería de lanzamiento

GitSe ejecutan acciones del concentradorPython3.9–3.13 pruebas, validación de JavaScript, compilación del remitente nativo y una prueba de humo real de instalación/inicio/doctor/detener/desinstalar. A`v*`tag crea paquetes wheel/sdist además de remitentes nativos de Linux y macOS protegidos con suma de comprobación. El instalador de CLI descarga el activo de la versión correspondiente, por lo que los usuarios finales no necesitan un compilador.

Ejecute el primer experimento de diagnóstico vinculado al producto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inyecta fallas en la evidencia del ciclo de vida, fallas explícitas, ejecuciones incompletas y resultados no verificados, luego evalúa el mismo motor de diagnóstico determinista utilizado por elAPIyUI. Ver el[Plan de experimento PAI-DSW](docs/pai-dsw-experiment-plan.md)para la escalera experimental, pruebas de no interferencia y contrato de reproducibilidad.

Después de construir la rueda, ejecute el humo del ciclo de vida empaquetado aislado con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Se instala en un entorno virtual temporal y en un hogar temporal, ejerce el ciclo de vida local completo sin habilitar enlaces y verifica que la configuración del agente y del proyecto no interfiera.

## Diseño de producto basado en experimentos

El comportamiento del producto está limitado por la[Filosofía de producto basada en experimentos.](docs/experiment-driven-product-philosophy.md): evidencia antes que conclusiones, el primer límite observable antes que la severidad, relaciones tipificadas antes que los registros planos y reconstrucción determinista antes de la asistencia probabilística.

La evidencia local reproducible actual incluye:

- Pasaron 7/7 puertas de experimentos locales;
- 2400/2400 eventos de recopilador aceptados sin mutación de entrada/salida;
- 14/14 diagnósticos deterministas de corpus de fallas sin ninguna afirmación causal sin fundamento;
- la representación del diagnóstico relacional fue 13/14 exacta y F1 0,963, mientras que la recuperación plana del ciclo de vida alcanzó 1/14 exacta y F1 0,080;
- Los casos de material de estudio del 11/11 sitúan primero el límite observable más antiguo.

Estos resultados validan los mecanismos y las opciones de representación, no la generalización de la implementación o el beneficio humano. Los estudios reales de segundos agentes, la latencia de cola multiplataforma, la calibración de fallas reales y los estudios de diagnóstico de participantes siguen teniendo lagunas en la evidencia.

La dirección de la investigación también se basa en trabajos primarios adyacentes:[SkillsBench](https://arxiv.org/abs/2602.12670)y[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motivar el diagnóstico porque los efectos de las habilidades varían y pueden retroceder;[Harness-Bench](https://arxiv.org/abs/2605.27922)motiva la comparación entre agentes consciente de la capacidad; y el[encuesta de procedencia de ejecución](https://arxiv.org/abs/2606.04990)motiva las relaciones de evidencia mecanografiada, el seguimiento de la procedencia y la infraestructura de auditoría consciente de la privacidad.

## Documentación

- [Definición de producto](docs/product-definition.md)
- [especificación MVP](docs/mvp-specification.md)
- [Modelo de evento en tiempo de ejecución](docs/runtime-event-model.md)
- [Arquitectura de información de la interfaz de usuario](docs/ui-information-architecture.md)
- [Matriz de capacidades del adaptador](docs/adapter-capability-matrix.md)
- [Interoperabilidad de observabilidad](docs/observability-interoperability.md)
- [Configuración de la plataforma de observabilidad.](docs/observability-platform-setup.md)
- [Investigación y panorama competitivo](docs/research-and-competitive-landscape.md)
- [Agenda de trabajos de investigación](docs/research-paper-agenda.md)
- [Filosofía de producto basada en experimentos](docs/experiment-driven-product-philosophy.md)
- [Resultados del experimento](docs/experiment-results-2026-07-29.md)
- [Plan de experimento PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Hoja de ruta

1. **v0.1 — Diagnóstico y evidencia en tiempo de ejecución:** recopilación en vivo,Skill Run Panorama, diagnóstico de primer límite, inspección de evidencia, comparación e interoperabilidad OTLP.
2. **v0.2: estudios de diagnóstico y refuerzo de adaptadores:** versiones adicionales del agente, experimentos reales entre agentes y evaluación de participantes.
3. **v0.3 — Evaluación de efectos:** evaluación emparejada controlada con habilidad/sin habilidad, mantenida separada del diagnóstico de ejecución única.

## Estado del proyecto

ASkillRun-el primer tiempo de ejecución es ejecutable: inventario de definición instalada,Codexrespaldo de transcripción, adaptadores de gancho oficiales basados ​​en el consentimiento paraCodex,Claude Code, yQoder, una observación sóloOpenCodeadaptador de complemento, atribución de alcance activo, rutas exactas de archivos/artefactos, redacción, capas separadas de fuente/relación/inferencia,SQLitealmacenamiento, retención, comparación entre ejecuciones y agentes, diagnóstico determinista y panorama en vivoUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, yDatadoglas exportaciones pueden importarse; La evidencia normalizada se puede exportar en vivo mediante suscripción voluntaria.OTLP/HTTP. El descubrimiento de candidatos, las razones de selección interna del modelo, la efectividad semántica y las afirmaciones de resultados causales siguen sin estar explícitamente respaldadas.
