# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [Français](README.fr.md) ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · **Español** · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnosticar dónde divergió por primera vez una ejecución de habilidad del agente e inspeccionar la evidencia
> detrás de cada conclusión.

Agent Skill Runtime Intelligence es un sistema de diagnóstico y evidencia en tiempo de ejecución de solo lectura para Agent Skills. Combina definiciones de habilidades, eventos oficiales de tiempo de ejecución del agente, seguimientos importados, respaldo de sesión y resultados observables del espacio de trabajo en una Skill Run Panorama calificada por evidencia.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Inicio rápido

Instale e inicie la última versión en macOS o Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

No se requiere ningún clon, cuenta, `sudo` o GitHub CLI. El instalador verifica la suma de verificación de la versión, detecta agentes y habilidades admitidos, explica cada ruta que leerá, pregunta una vez antes de habilitar los enlaces de solo observación y abre la UI local en [http://127.0.0.1:4317](http://127.0.0.1:4317). Los datos de tiempo de ejecución permanecen en `~/.skill-runtime` a menos que configure explícitamente una exportación.

Puedes [inspeccionar el instalador](scripts/install.sh) antes de ejecutarlo.

### Mira tu primer directo SkillRun

1. Acepte la configuración opcional de apertura fallida Hook cuando el instalador lo solicite.
2. Reinicie el Agente y comience una nueva tarea. En Codex, revise primero los comandos administrados en `/hooks`; Las tareas existentes no cargan en caliente nuevas Hook.
3. Usa una Skill normalmente, luego confirma la integración y abre el UI:

```bash
skill-runtime doctor
skill-runtime status
```

Una integración está **activa** solo después de que el recopilador recibe un evento de ejecución real. Un Hook configurado pero no observado está **Pendiente** y nunca se presenta como evidencia real. Abra [http://127.0.0.1:4317](http://127.0.0.1:4317) o consulte [Guía de introducción](docs/getting-started.md) para obtener instrucciones específicas del agente y solución de problemas.

Para ejecutar directamente desde un pago de origen:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Superficie del producto | lo que responde |
|---|---|
| Runtime Overview | ¿Cuáles SkillRuns necesitan atención? |
| First Observable Boundary | ¿Dónde faltaron o fallaron las pruebas por primera vez? |
| Skill Run Panorama | ¿Cómo se conectaron la solicitud, la activación, los recursos, las herramientas, los artefactos y el resultado? |
| Evidence Inspector | ¿Qué fuente, grado, base y capacidad del adaptador respaldan esta afirmación? |
| Comparar | ¿Es una diferencia de comportamiento o sólo una diferencia de observabilidad? |
| Inferred Analysis | ¿Qué explicación basada en evidencia o qué próxima investigación es plausible? |
| Configuración / Médico | ¿Qué se lee, almacena, exporta, pendiente y verifica? |

## como funciona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observa el flujo de trabajo que ya utiliza. Los adaptadores versionados convierten los eventos nativos del agente en un ciclo de vida de habilidad estable, mientras que los sobres de origen sin procesar, los eventos normalizados, las relaciones y las inferencias permanecen separados. El motor de diagnóstico identifica primero el límite más temprano donde faltan o fallan pruebas; no inventa la intención del modelo ni la eficacia causal.

| fuente de datos | Role | Frescura | UI etiqueta |
|---|---|---|---|
| Ganchos/complementos oficiales del agente/eventos SDK | Ciclo de vida primario, herramienta, subagente y evidencia terminal | Vivir | `Official hook` / `Native telemetry` |
| Archivos de habilidades y resultados observables en el espacio de trabajo | Definición, recurso, archivo, artefacto y evidencia de prueba. | Instantánea en vivo / indexada | `Observed` |
| Transcripciones de sesiones | Respaldo de compatibilidad cuando el Agente no muestra suficiente tiempo de ejecución API | Casi vivo o histórico | `Transcript fallback` |
| OTLP y exportaciones de seguimiento admitidas | Interoperabilidad e importación histórica | Exportación en vivo/importación por lotes | Se muestra el perfil de origen |
| Correlación determinista | Conecta eventos a SkillRun sin cambiar los datos fuente | En caso de ingestión | `Derived` |
| asistencia semántica | Sólo explicaciones y sugerencias de investigación. | Bajo demanda | `Inferred` |

Los adaptadores propios admitidos tienen versiones independientes:

| Agente | Integración primaria | Retroceder | Visibilidad de activación |
|---|---|---|---|
| Codex | Comando oficial Hooks | Importación de sesión | Activación explícita cuando se expone por el evento Hook |
| Claude Code | Oficial Hooks | Importación de sesión | Herramienta de habilidad explícita y evidencia de comando de corte donde se expusieron |
| Qoder | Comando oficial Hooks | Registros locales | Activación explícita cuando se expone por su herramienta de habilidad. |
| OpenCode | Complemento global solo de observación | Registros locales | Devoluciones de llamadas de herramientas de habilidades donde quedaron expuestas |

Los límites de capacidad exactos están documentados en [matriz de capacidad del adaptador](docs/adapter-capability-matrix.md). Las etapas no soportadas y no observadas permanecen visibles en lugar de convertirse en fallas.

## el problema

Instalar una Skill no prueba que un agente la haya descubierto. El descubrimiento no prueba la activación. La activación no prueba que se hayan cargado todas las instrucciones y recursos. La ejecución no prueba que la Habilidad haya mejorado el resultado.

Hoy en día, estos fracasos suelen guardar silencio. Los desarrolladores se quedan preguntando:

- ¿Estaba la habilidad disponible para este agente?
- ¿Se activó para esta solicitud?
- ¿Qué instrucciones, referencias, guiones y recursos se cargaron?
- ¿Qué herramientas, llamadas MCP, subagentes, archivos y artefactos estuvieron involucrados?
- ¿Dónde falló la ejecución, se reintentó o se perdió contexto?
- ¿La habilidad ayudó o solo agregó costo y latencia?

## Diagnóstico específico de habilidades

El objeto de diagnóstico principal es un `SkillRun`, no una sesión completa del Agente:

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

El UI mantiene el ciclo de vida ordenado, escrito y calificado por evidencia. La telemetría de activación faltante significa "no observado" o "no admitido"; Esto no significa que el Agente definitivamente se haya saltado la Habilidad.

## Disciplina de evidencia

El UI nunca debe presentar una inferencia como un hecho en tiempo de ejecución:

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

## Alcance actual

El tiempo de ejecución admite Codex, Claude Code, Qoder y OpenCode a través de adaptadores versionados independientes y proporciona:

- instalado Descubrimiento y validación de habilidades;
- colección oficial Hook/plugin en tiempo real más reserva de sesión etiquetada;
- Activación de habilidades, carga de recursos y cronogramas de uso de herramientas;
- relaciones de subagente, MCP, archivo y artefacto;
- resúmenes de duración, token, error, reintento y estado cuando estén disponibles;
- Runtime Overview y diagnóstico de primer límite;
- un DAG panorámico, una cronología de eventos y un inspector de pruebas;
- comparación entre agentes y entre agentes con reconocimiento de capacidades;
- una superficie Inferred Analysis separada que no puede reescribir hechos en tiempo de ejecución;
- opt-in OTLP/HTTP exportación e importación de seguimiento de observabilidad admitida.

El MVP **no** incluye un mercado, tiempo de ejecución de agente universal, aplicación de seguridad, gobernanza empresarial ni afirmaciones de efectos causales.

## Instalación detallada

Para conocer la ruta más corta admitida, utilice el instalador de versión de una línea en [Inicio rápido](#quick-start). El flujo completo de primera ejecución, los pasos de confianza/reinicio específicos del agente, el comportamiento de privacidad y la solución de problemas se encuentran en la [Guía de introducción](docs/getting-started.md).

Para el desarrollo, la implementación básica no tiene dependencias de tiempo de ejecución más allá de Python 3.9+. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Luego abra [http://127.0.0.1:4317](http://127.0.0.1:4317).

El comando único `install`:

1. escanea ubicaciones de Skill de usuarios, proyectos y complementos almacenados en caché;
2. detecta Codex, Claude Code, Qoder y OpenCode sin cambiar su configuración;
3. muestra qué rutas de Agente y Habilidad se leerán;
4. descarga un remitente nativo de bajo inicio verificado con suma de verificación para la plataforma actual, recurriendo a una compilación C local y finalmente al remitente Python, y precalienta un binario nativo nuevo una vez durante la instalación;
5. crea `~/.skill-runtime/config.json` y el índice local SQLite.

Cuando se ejecuta de forma interactiva, pregunta una vez antes de agregar enlaces de agente de apertura fallida. `--no-hooks` mantiene la importación de transcripciones como respaldo etiquetado, mientras que `--enable-hooks` registra el consentimiento explícito e instala solo entradas administradas. Para Codex, abra `/hooks` después de la instalación, revise los comandos administrados exactos y confíe en ellos. Codex requiere intencionalmente esta revisión explícita de los enlaces agregados fuera de la configuración empresarial administrada. Inicie una nueva tarea/sesión Codex después de confiar en los Hook, luego ejecute:

```bash
.venv/bin/skill-runtime doctor
```

Qoder carga la configuración Hook al inicio, así que reinicie Qoder después de la primera instalación. OpenCode descubre el complemento administrado de solo observación desde su directorio global de complementos; reinicie OpenCode si el proceso actual es anterior a la instalación. Ninguna integración lee ni cambia las solicitudes de modelo.

La integración se vuelve **activa** solo después de que la base de datos reciba un evento `official_hook` real. Simplemente escribir `~/.codex/hooks.json` se muestra como **Pendiente**, nunca Conectado. `start` inicia el recopilador, el observador de respaldo de transcripciones, el trabajador de retención, el almacén SQLite y activa UI como un proceso en segundo plano administrado. No se representa ninguna solicitud de modelo.

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

`uninstall` elimina solo las entradas administradas de Hook y los archivos de propiedad de Skill Runtime. Sin `--keep-data`, requiere confirmación interactiva (o `--yes`) antes de eliminar `~/.skill-runtime`; Las sesiones de agentes y las fuentes de habilidades nunca se eliminan.

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

Los perfiles de importación versionados actualmente reconocen las formas OTLP/Phoenix, Langfuse, LangSmith, W&B Weave y Datadog JSON. Solo crean un SkillRun cuando la fuente contiene una semántica de Habilidad explícita; Los nombres de intervalo genéricos no se tratan como evidencia de activación.

Exporte evidencia de tiempo de ejecución normalizada y específica de la habilidad a cualquier punto final de seguimiento OTLP/HTTP:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

La exportación está deshabilitada a menos que se configure explícitamente un punto final. Los puntos de control, el estado de reintento y el estado del destino se muestran en Configuración. Las indicaciones sin procesar, las cargas útiles de las herramientas, las credenciales y el contenido de los recursos de habilidades no se exportan. Para exportación en segundo plano autenticada, proporcione el estándar `OTEL_EXPORTER_OTLP_HEADERS` en el entorno antes de `skill-runtime start`; los encabezados nunca se escriben en los argumentos de configuración o proceso de Skill Runtime.

## Enviar evidencia en tiempo de ejecución en vivo

`skill-runtime start` incluye un coleccionista local. Los adaptadores de telemetría nativos, los enlaces oficiales, los enlaces ligeros de apertura por error y las integraciones SDK pueden agregar un solo evento o un lote limitado a `POST /api/events`:

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

El punto final redacta las credenciales comunes antes de la persistencia, deduplica mediante `event_id`, conserva un sobre sin editar redactado por separado y devuelve el `skill_run_ids` resultante. `GET /api/collector/schema` expone el vocabulario de eventos admitidos y los modos de recopilación. El UI escucha a `/api/stream` usando SSE, con sondeo solo como alternativa de reconexión.

El indicador de origen distingue la evidencia de tiempo de ejecución primaria de `Transcript fallback` y los rastros importados. Un punto final de Collector por sí solo no reclama telemetría nativa: cada productor debe declarar si su evento provino de telemetría nativa, un gancho oficial, un gancho liviano o un SDK.

### Ganchos de agente opcionales

Inspeccione primero los caminos y eventos exactos. Este comando es de sólo lectura:

```bash
.venv/bin/skill-runtime setup
```

La instalación de Hook requiere una bandera explícita:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

El instalador realiza una copia de seguridad de la configuración del Agente, conserva los enlaces existentes y agrega solo entradas que llevan un marcador de administración Skill Runtime. El adaptador de gancho almacena campos mínimos del ciclo de vida en lugar de indicaciones completas o cargas útiles de herramientas. Para las llamadas a herramientas completas, extrae solo `SKILL.md` exacto, el recurso de habilidad estándar y las rutas de archivos modificados en la memoria; Los comandos sin formato, los cuerpos de los parches, los mensajes y las salidas de las herramientas se descartan antes de la persistencia. Mientras el tiempo de ejecución está activo, un socket Unix con permisos restringidos es la ruta rápida; un remitente nativo opcional evita el inicio de Python. Cuando el tiempo de ejecución no está activo, la ruta independiente de falla de apertura agrega evidencia redactada a `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` reproduce esa cola con deduplicación de ID de evento.

Los eventos Codex utilizan su Hook API oficial (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` y `Stop`). Codex actualmente ejecuta enlaces de comando de forma sincrónica, por lo que Skill Runtime usa un socket Unix local/remitente nativo con un tiempo de espera limitado. Cualquier error en la entrega se traga y se pone en cola; nunca cambia la decisión de un Agente. Vea el [documentación oficial del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Elimine solo las entradas administradas con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

El servidor se vincula a `127.0.0.1` de forma predeterminada. Los mensajes de transcripción completa y las cargas útiles de las herramientas no se copian en el índice. Los patrones secretos comunes se redactan antes de que persistan los resúmenes normalizados.

Ejecute el conjunto de pruebas sin dependencia con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingeniería de lanzamiento

GitHub Ejecuciones de acciones Python pruebas 3.9–3.13, validación de JavaScript, compilación del remitente nativo y una prueba de humo real de instalación/inicio/doctor/detención/desinstalación. Una etiqueta `v*` crea paquetes wheel/sdist más remitentes nativos Linux y macOS protegidos por suma de comprobación. El instalador de CLI descarga el activo de la versión correspondiente, por lo que los usuarios finales no necesitan un compilador.

Ejecute el primer experimento de diagnóstico vinculado al producto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inyecta fallas en la evidencia del ciclo de vida, fallas explícitas, ejecuciones incompletas y resultados no verificados, luego evalúa el mismo motor de diagnóstico determinista utilizado por API y UI. Consulte [Plan de experimento PAI-DSW](docs/pai-dsw-experiment-plan.md) para conocer la escala de experimentos, las pruebas de no interferencia y el contrato de reproducibilidad.

Después de construir la rueda, ejecute el humo del ciclo de vida empaquetado aislado con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Se instala en un entorno virtual temporal y en un hogar temporal, ejerce el ciclo de vida local completo sin habilitar enlaces y verifica que la configuración del agente y del proyecto no interfiera.

## Diseño de producto basado en experimentos

El comportamiento del producto está limitado por [Filosofía de producto basada en experimentos.](docs/experiment-driven-product-philosophy.md): evidencia antes que conclusiones, el primer límite observable antes que la severidad, relaciones tipificadas antes que los registros planos y reconstrucción determinista antes de la asistencia probabilística.

La evidencia local reproducible actual incluye:

- Pasaron 7/7 puertas de experimentos locales;
- 2400/2400 eventos de recopilador aceptados sin mutación de entrada/salida;
- 14/14 diagnósticos deterministas de corpus de fallas sin ninguna afirmación causal sin fundamento;
- la representación del diagnóstico relacional fue 13/14 exacta y F1 0,963, mientras que la recuperación plana del ciclo de vida alcanzó 1/14 exacta y F1 0,080;
- Los casos de material de estudio del 11/11 sitúan primero el límite observable más antiguo.

Estos resultados validan los mecanismos y las opciones de representación, no la generalización de la implementación o el beneficio humano. Los estudios reales de segundos agentes, la latencia de cola multiplataforma, la calibración de fallas reales y los estudios de diagnóstico de participantes siguen teniendo lagunas en la evidencia.

La dirección de la investigación también se basa en trabajos primarios adyacentes: [SkillsBench](https://arxiv.org/abs/2602.12670) y [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivan el diagnóstico porque los efectos de las habilidades varían y pueden retroceder; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva la comparación entre agentes consciente de la capacidad; y el [encuesta de procedencia de ejecución](https://arxiv.org/abs/2606.04990) motiva las relaciones de evidencia mecanografiada, el seguimiento de la procedencia y la infraestructura de auditoría consciente de la privacidad.

## Documentación

| Empieza aquí | Objetivo |
|---|---|
| [Getting Started](docs/getting-started.md) | Instalar, conectar un agente, verificar evidencia en vivo y solucionar problemas |
| [Arquitectura](docs/architecture.md) | Canal de recopilación, límites de almacenamiento, motor de evidencia y modelo de confianza |
| [Matriz de capacidades del adaptador](docs/adapter-capability-matrix.md) | Señales exactas y limitaciones por agente/versión |
| [Configuración de la plataforma de observabilidad.](docs/observability-platform-setup.md) | Conecte plataformas compatibles con OTLP e importe seguimientos compatibles |
| [Modelo de evento en tiempo de ejecución](docs/runtime-event-model.md) | Vocabulario estable de eventos, procedencia, relaciones y grados de evidencia. |
| [Arquitectura de información de la interfaz de usuario](docs/ui-information-architecture.md) | Descripción general, primer límite, Panorama, Inspector, Comparar y Inferred Analysis |

Referencias de productos e investigaciones: [definición de producto](docs/product-definition.md), [especificación MVP](docs/mvp-specification.md), [interoperabilidad de observabilidad](docs/observability-interoperability.md), [Filosofía de producto basada en experimentos.](docs/experiment-driven-product-philosophy.md), [resultados del experimento](docs/experiment-results-2026-07-29.md) y [agenda de investigación](docs/research-paper-agenda.md).

## Hoja de ruta

1. **v0.2.0: disponible ahora:** recopilación activa de fallos de apertura, cuatro adaptadores de agente versionados, Runtime Overview, diagnóstico de primer límite, panorama, Evidence Inspector, comparación con reconocimiento de capacidad, Inferred Analysis e interoperabilidad OTLP.
2. **Siguiente: Adaptador y refuerzo de diagnóstico:** cobertura más amplia de agente/versión, calibración de fallas reales, validación de latencia de cola multiplataforma y estudios de diagnóstico de participantes.
3. **Más tarde: evaluación del efecto:** evaluación emparejada controlada con habilidad/sin habilidad, mantenida explícitamente separada del diagnóstico de ejecución única.

## Estado del proyecto

Se publica la versión `v0.2.0`. El tiempo de ejecución incluye inventario de definiciones instaladas, adaptadores Hook oficiales basados en consentimiento para Codex, Claude Code y Qoder, un complemento OpenCode de solo observación, reserva de transcripción etiquetada, atribución de alcance activo, rutas exactas de archivos/artefactos, redacción, capas separadas de fuente/relación/inferencia, SQLite almacenamiento, retención, diagnóstico determinista, UI en vivo y comparación entre ejecuciones y agentes cruzados. Se pueden importar las exportaciones OTLP/Phoenix, Langfuse, LangSmith, W&B Weave y Datadog; La evidencia normalizada se puede exportar en vivo a través de la opción OTLP/HTTP.

El descubrimiento de candidatos dentro del modelo, las razones de selección internas del modelo, la efectividad semántica y las afirmaciones de resultados causales siguen sin estar explícitamente respaldadas a menos que una fuente o un experimento controlado proporcione esa evidencia.
