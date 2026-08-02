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


> Doblar `SKILL.md` en expectativas de tiempo de ejecución verificables. Mira lo que realmente
> sucedió, dónde el comportamiento divergió por primera vez y las pruebas detrás de la sentencia.

Agent Skill Runtime Intelligence es un sistema de diagnóstico y evidencia en tiempo de ejecución de solo lectura para Agent Skills. Extrae restricciones conservadoras e inspeccionables de la definición de Habilidad actual, las relaciona con la actividad en tiempo de ejecución y reconstruye el resultado como una clasificación calificada por evidencia. Skill Run Panorama. Combina eventos oficiales del Agente, seguimientos importados, respaldo de sesiones etiquetadas y resultados observables del espacio de trabajo sin enviar solicitudes de modelo ni hacerse cargo del bucle del Agente.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Inicio rápido

Instale e inicie la última versión en macOS o Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Sin clon, cuenta, `sudo`, o GitHub CLI se requiere. El instalador verifica la suma de verificación de la versión, detecta agentes y habilidades admitidos, explica cada ruta que leerá, pregunta una vez antes de habilitar los enlaces de solo observación y abre el archivo local. UI en [http://127.0.0.1:4317](http://127.0.0.1:4317). Los datos en tiempo de ejecución permanecen por debajo `~/.skill-runtime` a menos que configure explícitamente una exportación.

Puede [inspeccionar el instalador](scripts/install.sh) antes de ejecutarlo.

### Mira tu primer directo SkillRun

1. Acepte la opción de falla de apertura Hook configuración cuando el instalador lo solicite.
2. Reinicie el Agente y comience una nueva tarea. En Codex, revise los comandos administrados en `/hooks` primero; las tareas existentes no cargan nuevas en caliente Hooks.
3. Utilice una habilidad normalmente, luego confirme la integración y abra el UI:

```bash
skill-runtime doctor
skill-runtime status
```

Una integración está **activa** solo después de que el recopilador recibe un evento de ejecución real. Un configurado pero no observado. Hook está **Pendiente**: nunca se presenta como evidencia real. Abierto [http://127.0.0.1:4317](http://127.0.0.1:4317), o ver el [Guía de introducción](docs/getting-started.md) para obtener instrucciones específicas del agente y solución de problemas.

Para ejecutar directamente desde un pago de origen:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Superficie del producto | lo que responde |
|---|---|
| Runtime Overview | Cual SkillRuns ¿Necesitas atención? |
| Comprobación de comportamiento de habilidades | ¿Qué instrucciones verificables se cumplieron, necesitan revisión o no se pueden evaluar? |
| Lo que realmente pasó | ¿Qué instrucciones, recursos, herramientas, artefactos y resultados se observaron? |
| First Observable Boundary | ¿Dónde falta o falla por primera vez la evidencia específica de la ejecución? |
| Skill Run Panorama | ¿Cómo se conectaron la solicitud, la activación, los recursos, las herramientas, los artefactos y el resultado? |
| Evidence Inspector | ¿Qué fuente, grado, base y capacidad del adaptador respaldan esta afirmación? |
| Comparar | ¿Es una diferencia de comportamiento o sólo una diferencia de observabilidad? |
| Inferred Analysis | ¿Qué explicación basada en evidencia o qué próxima investigación es plausible? |
| Configuración / Médico | ¿Qué se lee, almacena, exporta, pendiente y verifica? |

## como funciona

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observa el flujo de trabajo que ya utiliza. Los adaptadores versionados convierten los eventos nativos del agente en un ciclo de vida de habilidad estable, mientras que los sobres de origen sin procesar, los eventos normalizados, las relaciones y las inferencias permanecen separados. El motor de diagnóstico compara las restricciones de habilidades explícitas con esa evidencia, identifica la desviación observable más temprana y mantiene los puntos ciegos del adaptador sistémico separados de los hallazgos específicos de la ejecución. No inventa la intención del modelo ni la eficacia causal.

| fuente de datos | Role | Frescura | UI etiqueta |
|---|---|---|---|
| Ganchos / complementos oficiales del agente / SDK eventos | Ciclo de vida primario, herramienta, subagente y evidencia terminal | Vivir | `Official hook` / `Native telemetry` |
| Archivos de habilidades y resultados observables en el espacio de trabajo | Definición, recurso, archivo, artefacto y evidencia de prueba. | Instantánea en vivo / indexada | `Observed` |
| Transcripciones de sesiones | Respaldo de compatibilidad cuando el Agente no expone suficiente tiempo de ejecución API | Casi vivo o histórico | `Transcript fallback` |
| OTLP y exportaciones de seguimiento admitidas | Interoperabilidad e importación histórica | Exportación en vivo/importación por lotes | Se muestra el perfil de origen |
| Correlación determinista | Conecta eventos a un SkillRun sin cambiar los hechos fuente | En caso de ingestión | `Derived` |
| asistencia semántica | Sólo explicaciones y sugerencias de investigación. | Bajo demanda | `Inferred` |

Los adaptadores propios admitidos tienen versiones independientes:

| Agente | Integración primaria | Retroceder | Visibilidad de activación |
|---|---|---|---|
| Codex | Comando oficial Hooks | Importación de sesión | Activación explícita cuando es expuesta por el Hook evento |
| Claude Code | Oficial Hooks | Importación de sesión | Herramienta de habilidad explícita y evidencia de comando de corte donde se expusieron |
| Qoder | Comando oficial Hooks | Registros locales | Activación explícita cuando se expone por su herramienta de habilidad. |
| OpenCode | Complemento global solo de observación | Registros locales | Devoluciones de llamadas de herramientas de habilidades donde quedaron expuestas |

Los límites de capacidad exactos están documentados en el [matriz de capacidad del adaptador](docs/adapter-capability-matrix.md). Las etapas no soportadas y no observadas permanecen visibles en lugar de convertirse en fallas.

## el problema

Instalar una Skill no prueba que un agente la haya descubierto. El descubrimiento no prueba la activación. La activación no prueba que se hayan cargado todas las instrucciones y recursos. Las instrucciones de carga no prueban que el Agente las haya seguido. La ejecución no prueba que la Habilidad haya mejorado el resultado.

Hoy en día, estos fracasos suelen guardar silencio. Los desarrolladores se quedan preguntando:

- ¿Estaba la habilidad disponible para este agente?
- ¿Se activó para esta solicitud?
- ¿Qué instrucciones, referencias, guiones y recursos se cargaron?
- ¿Qué requisitos explícitos de habilidades se siguieron, se omitieron o fueron imposibles de evaluar?
- ¿Qué herramientas, MCP ¿Estuvieron involucrados llamadas, subagentes, archivos y artefactos?
- ¿Dónde falló la ejecución, se reintentó o se perdió contexto?
- ¿La habilidad ayudó o solo agregó costo y latencia?

## Diagnóstico específico de habilidades

El objeto de diagnóstico primario es un `SkillRun`, no una sesión completa del Agente:

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

El tiempo de ejecución admite Codex, Claude Code, Qoder, y OpenCode a través de adaptadores versionados independientes y proporciona:

- instalado Descubrimiento y validación de habilidades;
- oficial en tiempo real Hook/colección de complementos más reserva de sesión etiquetada;
- Activación de habilidades, carga de recursos y cronogramas de uso de herramientas;
- subagente, MCPrelaciones entre archivos, artefactos y archivos;
- resúmenes de duración, token, error, reintento y estado cuando estén disponibles;
- restricciones de comportamiento conservador extraídas de la corriente `SKILL.md`;
- comprobaciones de conformidad, verificación y fallos en tiempo de ejecución basadas en evidencia;
- inventarios concretos de instrucción, recursos, herramientas, artefactos y resultados;
- Runtime Overview con límites de cobertura sistémica separados de los resultados de las corridas;
- diagnóstico de primer límite;
- un DAG panorámico, una cronología de eventos y un inspector de pruebas;
- comparación entre agentes y entre agentes con reconocimiento de capacidades;
- un separado Inferred Analysis superficie que no puede reescribir hechos en tiempo de ejecución;
- optar por OTLP/HTTP exportación e importación de seguimiento de observabilidad admitida.

El MVP **no** incluye un mercado, tiempo de ejecución de agente universal, aplicación de seguridad, gobernanza empresarial ni afirmaciones de efectos causales.

## Instalación detallada

Para obtener la ruta más corta admitida, utilice el instalador de versión de una línea en [Inicio rápido](#quick-start). El flujo completo de primera ejecución, los pasos de reinicio/confianza específicos del agente, el comportamiento de privacidad y la solución de problemas se encuentran en el [Guía de introducción](docs/getting-started.md).

Para el desarrollo, la implementación básica no tiene dependencias de tiempo de ejecución más allá Python 3,9+. Desde la raíz del repositorio:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Luego abre [http://127.0.0.1:4317](http://127.0.0.1:4317).

la única vez `install` dominio:

1. escanea ubicaciones de Skill de usuarios, proyectos y complementos almacenados en caché;
2. detecta Codex, Claude Code, Qoder, y OpenCode sin cambiar su configuración;
3. muestra qué rutas de Agente y Habilidad se leerán;
4. descarga un remitente nativo de bajo inicio verificado con suma de verificación para la plataforma actual, recurriendo a una compilación C local y finalmente el Python remitente y precalienta un binario nativo nuevo una vez durante la instalación;
5. crea `~/.skill-runtime/config.json` y los locales SQLite índice.

El primer índice importa sesiones de Agente compatibles existentes. En una estación de trabajo de larga duración, esto puede llevar más tiempo que una instalación nueva; los inicios posteriores son incrementales y el UI estará disponible mientras se ejecuta la actualización en segundo plano.

Cuando se ejecuta de forma interactiva, pregunta una vez antes de agregar enlaces de agente de apertura fallida. `--no-hooks` mantiene la importación de transcripciones como reserva etiquetada, mientras `--enable-hooks` registra el consentimiento explícito e instala solo entradas administradas. Para Codex, abierto `/hooks` Después de la instalación, revise los comandos administrados exactos y confíe en ellos. Codex requiere intencionalmente esta revisión explícita de los enlaces agregados fuera de la configuración empresarial administrada. empezar un nuevo Codex tarea/sesión después de confiar en el Hooks, luego ejecuta:

```bash
.venv/bin/skill-runtime doctor
```

Qoder cargas Hook configuración al inicio, así que reinicie Qoder después de la primera instalación. OpenCode descubre el complemento administrado de solo observación desde su directorio global de complementos; Reanudar OpenCode si el proceso actual es anterior a la instalación. Ninguna integración lee ni cambia las solicitudes de modelo.

La integración se vuelve **activa** solo después de que la base de datos reciba una notificación real. `official_hook` evento. Simplemente escribiendo `~/.codex/hooks.json` se muestra como **Pendiente**, nunca Conectado. `start` lanza el recopilador, el observador de reserva de transcripciones, el trabajador de retención, SQLite almacenar y vivir UI como un proceso en segundo plano administrado. No se representa ninguna solicitud de modelo.

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

`uninstall` elimina solo administrado Hook entradas y Skill Runtime-archivos de propiedad. Sin `--keep-data`, requiere confirmación interactiva (o `--yes`) antes de retirar `~/.skill-runtime`; Las sesiones de agentes y las fuentes de habilidades nunca se eliminan.

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

Los perfiles de importación versionados actualmente reconocen OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, y Datadog JSON formas. Sólo crean un SkillRun cuando la fuente contiene una semántica de Habilidad explícita; Los nombres de intervalo genéricos no se tratan como evidencia de activación.

Exporte evidencia de tiempo de ejecución normalizada y específica de habilidades a cualquier OTLP/HTTP punto final de seguimiento:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

La exportación está deshabilitada a menos que se configure explícitamente un punto final. Los puntos de control, el estado de reintento y el estado del destino se muestran en Configuración. Las indicaciones sin procesar, las cargas útiles de las herramientas, las credenciales y el contenido de los recursos de habilidades no se exportan. Para exportación en segundo plano autenticada, proporcione estándar `OTEL_EXPORTER_OTLP_HEADERS` en el ambiente antes `skill-runtime start`; los encabezados nunca se escriben Skill Runtime argumentos de configuración o proceso.

## Enviar evidencia en tiempo de ejecución en vivo

`skill-runtime start` Incluye un coleccionista local. Adaptadores de telemetría nativos, ganchos oficiales, ganchos livianos de apertura por falla y SDK Las integraciones pueden agregar un solo evento o un lote limitado a `POST /api/events`:

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

El punto final redacta las credenciales comunes antes de la persistencia, deduplica mediante `event_id`, conserva un sobre sin formato redactado por separado y devuelve el resultado `skill_run_ids`. `GET /api/collector/schema` expone el vocabulario de eventos admitidos y los modos de recopilación. El UI escucha `/api/stream` usando SSE, con sondeo solo como alternativa de reconexión.

El indicador de origen distingue la evidencia de tiempo de ejecución primaria de `Transcript fallback` y rastros importados. Un punto final de Collector por sí solo no reclama telemetría nativa: cada productor debe declarar si su evento provino de telemetría nativa, un gancho oficial, un gancho liviano o un SDK.

### Ganchos de agente opcionales

Inspeccione primero los caminos y eventos exactos. Este comando es de sólo lectura:

```bash
.venv/bin/skill-runtime setup
```

Hook la instalación requiere una bandera explícita:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

El instalador realiza una copia de seguridad de la configuración del Agente, conserva los enlaces existentes y agrega solo entradas que llevan un Skill Runtime marcador de gestión. El adaptador de gancho almacena campos mínimos del ciclo de vida en lugar de indicaciones completas o cargas útiles de herramientas. Para llamadas a herramientas completas, solo extrae datos exactos. `SKILL.md`, recurso de habilidad estándar y rutas de archivos modificados en la memoria; Los comandos sin formato, los cuerpos de los parches, los mensajes y las salidas de las herramientas se descartan antes de la persistencia. Mientras el tiempo de ejecución está activo, un permiso restringido Unix socket es el camino rápido; un remitente nativo opcional evita Python puesta en marcha. Cuando el tiempo de ejecución no está activo, la ruta independiente de apertura por error agrega evidencia redactada a `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` reproduce esa cola con deduplicación de ID de evento.

Codex eventos utilizan su oficial Hook API (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop`, y `Stop`). Codex actualmente ejecuta enlaces de comando sincrónicamente, por lo que Skill Runtime usa un local Unix socket/remitente nativo con un tiempo de espera limitado. Cualquier error en la entrega se traga y se pone en cola; nunca cambia la decisión de un Agente. Ver el [documentación oficial del Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Elimine solo las entradas administradas con:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

El servidor se une a `127.0.0.1` por defecto. Los mensajes de transcripción completa y las cargas útiles de las herramientas no se copian en el índice. Los patrones secretos comunes se redactan antes de que persistan los resúmenes normalizados.

Ejecute el conjunto de pruebas sin dependencia con:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingeniería de lanzamiento

GitHub Ejecuciones de acciones Python 3.9–3.13 pruebas, validación de JavaScript, compilación del remitente nativo y una prueba de humo real de instalación/inicio/doctor/detención/desinstalación. A `v*` la etiqueta construye paquetes wheel/sdist más protegidos por suma de comprobación Linux y macOS remitentes nativos. El instalador de CLI descarga el activo de la versión correspondiente, por lo que los usuarios finales no necesitan un compilador.

Ejecute el primer experimento de diagnóstico vinculado al producto:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Inyecta fallas en la evidencia del ciclo de vida, fallas explícitas, ejecuciones incompletas y resultados no verificados, luego evalúa el mismo motor de diagnóstico determinista utilizado por el API y UI. Ver el [Plan de experimento PAI-DSW](docs/pai-dsw-experiment-plan.md) para la escalera experimental, pruebas de no interferencia y contrato de reproducibilidad.

Después de construir la rueda, ejecute el humo del ciclo de vida empaquetado aislado con:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Se instala en un entorno virtual temporal y en un hogar temporal, ejerce el ciclo de vida local completo sin habilitar enlaces y verifica que la configuración del agente y del proyecto no interfiera.

## Diseño de producto basado en experimentos

El comportamiento del producto sigue cuatro restricciones impulsadas por experimentos: evidencia antes que conclusiones, el primer límite observable antes que la gravedad, relaciones tipificadas antes que registros planos y reconstrucción determinista antes de la asistencia probabilística.

La evidencia reproducible y sus limitaciones se mantienen en el [informe del experimento](docs/experiment-results-2026-07-29.md). Los resultados acotados incluyen:

- 2400/2400 eventos de recopilador aceptados sin mutación de entrada/salida;
- 14/14 diagnósticos deterministas de corpus de fallas sin afirmación causal sin fundamento;
- la representación del diagnóstico relacional fue 13/14 exacta y F1 0,963, mientras que la recuperación plana del ciclo de vida alcanzó 1/14 exacta y F1 0,080;
- una auditoría real segura para la privacidad que explícitamente sigue siendo inadecuada para afirmaciones confirmatorias sobre los efectos del producto porque faltan resultados verificados, una cobertura equilibrada entre agentes y etiquetas humanas.

Estos resultados validan los mecanismos y las opciones de representación, no la generalización de la implementación o el beneficio humano. Los estudios reales de segundos agentes, la latencia de cola multiplataforma, la calibración de fallas reales y los estudios de diagnóstico de participantes siguen teniendo lagunas de evidencia abiertas.

La dirección de la investigación también se basa en trabajos primarios adyacentes: [SkillsBench](https://arxiv.org/abs/2602.12670) y [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivar el diagnóstico porque los efectos de las habilidades varían y pueden retroceder; [Harness-Bench](https://arxiv.org/abs/2605.27922) motiva la comparación entre agentes consciente de la capacidad; y el [encuesta de procedencia de ejecución](https://arxiv.org/abs/2606.04990) motiva las relaciones de evidencia mecanografiada, el seguimiento de la procedencia y la infraestructura de auditoría consciente de la privacidad.

## Documentación

| Empieza aquí | Objetivo |
|---|---|
| [Getting Started](docs/getting-started.md) | Instalar, conectar un agente, verificar evidencia en vivo y solucionar problemas |
| [Arquitectura](docs/architecture.md) | Canal de recopilación, límites de almacenamiento, motor de evidencia y modelo de confianza |
| [Matriz de capacidades del adaptador](docs/adapter-capability-matrix.md) | Señales exactas y limitaciones por agente/versión |
| [Configuración de la plataforma de observabilidad.](docs/observability-platform-setup.md) | Conecte plataformas compatibles con OTLP e importe seguimientos compatibles |
| [Modelo de evento en tiempo de ejecución](docs/runtime-event-model.md) | Vocabulario estable de eventos, procedencia, relaciones y grados de evidencia. |
| [Arquitectura de información de la interfaz de usuario](docs/ui-information-architecture.md) | Descripción general, primer límite, Panorama, Inspector, Comparar y Inferred Analysis |
| [Registro de cambios](CHANGELOG.md) | Cambios versionados visibles para el usuario |
| [notas de la versión v0.3.0](docs/releases/v0.3.0.md) | Guía de actualización, aspectos destacados y límites conocidos |

Referencias de productos e investigaciones: [definición de producto](docs/product-definition.md), [especificación MVP](docs/mvp-specification.md), [interoperabilidad de observabilidad](docs/observability-interoperability.md), [resultados del experimento](docs/experiment-results-2026-07-29.md), y el [agenda de investigación](docs/research-paper-agenda.md).

## Comunidad y gobernanza

- Leer [Contribuyendo](CONTRIBUTING.md) antes de cambiar la semántica de la evidencia, los adaptadores o el comportamiento del producto.
- Sigue el [Código de conducta](CODE_OF_CONDUCT.md) en todos los espacios del proyecto.
- Informar vulnerabilidades de forma privada a través del [Política de seguridad](SECURITY.md), no es un asunto público.
- Utilice el estructurado [rastreador de problemas](https://github.com/hellogxp/skill-runtime-intelligence/issues) para errores reproducibles y propuestas de funciones específicas. Nunca adjunte bases de datos privadas en tiempo de ejecución o transcripciones de sesiones.

## Hoja de ruta

1. **v0.3.0 — Próxima versión:** restricciones de comportamiento de habilidades verificables, actividad de tiempo de ejecución concreta, evaluación basada en evidencia, diagnóstico de cobertura sistémica y el flujo de trabajo Panorama y Comparación en vivo existente.
2. **Siguiente: Adaptador y refuerzo de diagnóstico:** cobertura más amplia de agente/versión, calibración de fallas reales, validación de latencia de cola multiplataforma y estudios de diagnóstico de participantes.
3. **Más tarde: evaluación del efecto:** evaluación emparejada controlada con habilidad/sin habilidad, mantenida explícitamente separada del diagnóstico de ejecución única.

## Estado del proyecto

El árbol de origen actual apunta `v0.3.0`; utilice la insignia de versión anterior para identificar la última versión publicada. El tiempo de ejecución incluye restricciones de comportamiento de habilidades verificables, resúmenes de actividades concretas, inventario de definiciones instaladas, información oficial basada en el consentimiento. Hook adaptadores para Codex, Claude Code, y Qoder, una observación sólo OpenCode complemento, reserva de transcripción etiquetada, atribución de alcance activo, rutas exactas de archivos/artefactos, redacción, capas separadas de fuente/relación/inferencia, SQLite almacenamiento, retención, diagnóstico determinista, vivo UIy comparación entre ejecuciones y agentes. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, y Datadog las exportaciones pueden importarse; La evidencia normalizada se puede exportar en vivo mediante suscripción voluntaria. OTLP/HTTP.

El descubrimiento de candidatos dentro del modelo, las razones de selección internas del modelo, la efectividad semántica y las afirmaciones de resultados causales siguen sin estar explícitamente respaldadas a menos que una fuente o un experimento controlado proporcione esa evidencia.
