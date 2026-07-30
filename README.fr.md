# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · **Français** ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)


> Diagnostiquez où une compétence d'agent a divergé pour la première fois et inspectez les preuves
> derrière chaque conclusion.

Agent Skill Runtime Intelligence est un système de preuve et de diagnostic d'exécution en lecture seule pour les compétences d'agent. Il combine les définitions de compétences, les événements d'exécution officiels de l'agent, les traces importées, le repli de session et les résultats observables de l'espace de travail dans un Skill Run Panorama classé par preuves.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Démarrage rapide

Installez et démarrez la dernière version sur macOS ou Linux :

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Aucun clone, compte, `sudo` ou GitHub CLI n'est requis. Le programme d'installation vérifie la somme de contrôle de la version, détecte les agents et les compétences pris en charge, explique chaque chemin qu'il lira, demande une fois avant d'activer les hooks d'observation uniquement et ouvre le UI local à [http://127.0.0.1:4317](http://127.0.0.1:4317). Les données d'exécution restent sous `~/.skill-runtime` sauf si vous configurez explicitement une exportation.

Vous pouvez [inspecter l'installateur](scripts/install.sh) avant de l'exécuter.

### Voyez votre premier live SkillRun

1. Acceptez la configuration facultative d'ouverture en cas d'échec Hook lorsque le programme d'installation le demande.
2. Redémarrez l'agent et commencez une nouvelle tâche. Dans Codex, examinez d'abord les commandes gérées dans `/hooks` ; les tâches existantes ne chargent pas à chaud de nouveaux Hook.
3. Utilisez une Skill normalement, puis confirmez l'intégration et ouvrez le UI :

```bash
skill-runtime doctor
skill-runtime status
```

Une intégration n'est **Live** qu'une fois que le collecteur a reçu un événement d'exécution réel. Un Hook configuré mais non observé est **En attente** — jamais présenté comme preuve réelle. Ouvrez [http://127.0.0.1:4317](http://127.0.0.1:4317) ou consultez [Guide de démarrage](docs/getting-started.md) pour obtenir des instructions et un dépannage spécifiques à l'agent.

Pour exécuter directement à partir d’une extraction source :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Surface du produit | Ce à quoi il répond |
|---|---|
| Runtime Overview | Quels SkillRuns nécessitent une attention particulière ? |
| First Observable Boundary | Où les preuves ont-elles pour la première fois disparu ou échoué ? |
| Skill Run Panorama | Comment la demande, l’activation, les ressources, les outils, les artefacts et le résultat se sont-ils connectés ? |
| Evidence Inspector | Quelles capacités de source, de qualité, de base et d'adaptateur soutiennent cette affirmation ? |
| Comparer | Une différence est-elle comportementale, ou seulement une différence d’observabilité ? |
| Inferred Analysis | Quelle explication fondée sur des preuves ou quelle prochaine enquête est plausible ? |
| Paramètres / Médecin | Qu'est-ce qui est lu, stocké, exporté, en attente et vérifié ? |

## Comment ça marche

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observe le flux de travail que vous utilisez déjà. Les adaptateurs versionnés transforment les événements natifs de l'agent en un cycle de vie de compétence stable, tandis que les enveloppes sources brutes, les événements normalisés, les relations et les inférences restent séparés. Le moteur de diagnostic identifie d'abord la première limite où les preuves deviennent manquantes ou échouent ; il n’invente pas l’intention du modèle ni l’efficacité causale.

| Source de données | Rôle | Fraîcheur | Étiquette UI |
|---|---|---|---|
| Hooks / plugins officiels de l'agent / événements SDK | Cycle de vie primaire, outil, sous-agent et preuve terminale | En direct | `Official hook` / `Native telemetry` |
| Fichiers de compétences et résultats observables de l'espace de travail | Définition, ressource, fichier, artefact et preuve de test | Instantané en direct / indexé | `Observed` |
| Transcriptions des séances | Repli de compatibilité lorsque l'agent n'expose pas de temps d'exécution suffisant API | Quasi-vivant ou historique | `Transcript fallback` |
| OTLP et exportations de traces prises en charge | Interopérabilité et importation historique | Exportation en direct / importation par lots | Profil source affiché |
| Corrélation déterministe | Connecte les événements à un SkillRun sans modifier les faits sources | À l'ingestion | `Derived` |
| Assistance sémantique | Explications et suggestions d'enquête uniquement | Sur demande | `Inferred` |

Les adaptateurs propriétaires pris en charge sont versionnés indépendamment :

| Agent | Intégration primaire | Retomber | Visibilité des activations |
|---|---|---|---|
| Codex | Commande officielle Hooks | Importation de sessions | Activation explicite lorsqu'elle est exposée par l'événement Hook |
| Claude Code | Hook officiels | Importation de sessions | Outil de compétence explicite et preuves de commande slash lorsqu'elles sont exposées |
| Qoder | Commande officielle Hooks | Registres locaux | Activation explicite lorsqu'il est exposé par son outil de compétence |
| OpenCode | Plugin global d'observation uniquement | Registres locaux | Rappels d’outils de compétences lorsqu’ils sont exposés |

Les limites exactes des capacités sont documentées dans le [matrice de capacité de l'adaptateur](docs/adapter-capability-matrix.md). Les étapes non prises en charge et non observées restent visibles au lieu d'être converties en échecs.

## Le problème

Installer une Skill ne prouve pas qu'un agent l'a découverte. La découverte ne prouve pas l'activation. L'activation ne prouve pas que les instructions et ressources complètes ont été chargées. L'exécution ne prouve pas que la compétence a amélioré le résultat.

Aujourd’hui, ces échecs sont souvent silencieux. Les développeurs se demandent :

- La compétence était-elle disponible pour cet agent ?
- A-t-il été activé pour cette demande ?
- Quelles instructions, références, scripts et ressources ont été chargés ?
- Quels outils, appels MCP, sous-agents, fichiers et artefacts étaient impliqués ?
- Où l'exécution a-t-elle échoué, réessayée ou perdu le contexte ?
- La compétence a-t-elle aidé, ou n'a-t-elle fait qu'ajouter du coût et de la latence ?

## Diagnostic spécifique à la compétence

L'objet de diagnostic principal est un `SkillRun`, et non une session d'agent entière :

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

Le UI maintient le cycle de vie ordonné, tapé et classé par preuves. La télémétrie d'activation manquante signifie « non observée » ou « non prise en charge » ; cela ne signifie pas que l'agent a définitivement ignoré la compétence.

## Discipline de la preuve

Le UI ne doit jamais présenter une inférence comme un fait d'exécution :

- **Observé** — explicitement présent dans un événement ou un fichier source.
- **Dérivé** — connecté de manière déterministe à partir de preuves observées.
- **Déduit** — une explication plausible avec incertitude.
- **Expérimental** — un effet mesuré par une évaluation par paires contrôlée.

Une seule trace peut prendre en charge l’attribution de l’exécution. Cela ne peut pas prouver l’efficacité causale. Des affirmations telles que « ce taux de réussite amélioré par cette compétence » nécessitent une évaluation répétée avec/sans compétence.

## Principes du produit

- Privé par défaut, avec déploiement local, hybride et connecté à l'équipe.
- Observation en lecture seule ; ne prenez jamais en charge la boucle des agents.
- Pas de proxy modèle et pas de service cloud obligatoire.
- Aucun blocage, aucune porte d'approbation ou application de politique dans le produit par défaut.
- Provenance explicite et classement des preuves.
- Divulgation progressive : récit simple d’abord, événements bruts à la demande.
- Prise en charge basée sur un adaptateur pour modifier les formats de transcription des agents.

## Portée actuelle

Le runtime prend en charge Codex, Claude Code, Qoder et OpenCode via des adaptateurs indépendants et versionnés et fournit :

- découverte et validation des compétences installées ;
- Collection officielle Hook/plugin en temps réel plus sauvegarde de session étiquetée ;
- Activation des compétences, chargement des ressources et calendriers d'appel d'outils ;
- relations entre les sous-agents, MCP, les fichiers et les artefacts ;
- résumés de durée, de jeton, d'erreur, de nouvelle tentative et d'état lorsqu'ils sont disponibles ;
- Runtime Overview et diagnostic de première limite ;
- un DAG panoramique, une chronologie des événements et un inspecteur de preuves ;
- comparaison entre agents et agents prenant en compte les capacités ;
- une surface Inferred Analysis distincte qui ne peut pas réécrire les faits d'exécution ;
- opt-in pour l'exportation OTLP/HTTP et prise en charge de l'importation de trace d'observabilité.

Le MVP n'inclut **pas** de marché, d'exécution d'agent universel, d'application de la sécurité, de gouvernance d'entreprise ou de réclamations à effet causal.

## Installation détaillée

Pour le chemin le plus court pris en charge, utilisez le programme d'installation de la version sur une ligne dans [Démarrage rapide](#quick-start). Le flux complet de première exécution, les étapes de redémarrage/de confiance spécifiques à l'agent, le comportement en matière de confidentialité et le dépannage sont disponibles dans le [Guide de démarrage](docs/getting-started.md).

Pour le développement, l'implémentation de base n'a aucune dépendance d'exécution au-delà de Python 3.9+. Depuis la racine du référentiel :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Ensuite, ouvrez [http://127.0.0.1:4317](http://127.0.0.1:4317).

La commande unique `install` :

1. analyse les emplacements de compétences des utilisateurs, des projets et des plugins mis en cache ;
2. détecte Codex, Claude Code, Qoder et OpenCode sans modifier leur configuration ;
3. indique quels chemins d'agent et de compétences seront lus ;
4. télécharge un expéditeur natif à faible démarrage vérifié par somme de contrôle pour la plate-forme actuelle, retombe sur une version C locale et enfin sur l'expéditeur Python, et préchauffe un nouveau binaire natif une fois pendant l'installation ;
5. crée `~/.skill-runtime/config.json` et l'index local SQLite.

Lorsqu'il est exécuté de manière interactive, il demande une fois avant d'ajouter des hooks d'agent d'ouverture en cas d'échec. `--no-hooks` conserve l'importation de transcription comme solution de secours étiquetée, tandis que `--enable-hooks` enregistre le consentement explicite et installe uniquement les entrées gérées. Pour Codex, ouvrez `/hooks` après l'installation, examinez les commandes gérées exactes et faites-leur confiance. Codex nécessite intentionnellement cette révision explicite pour les hooks ajoutés en dehors de la configuration d'entreprise gérée. Démarrez une nouvelle tâche/session Codex après avoir fait confiance aux Hook, puis exécutez :

```bash
.venv/bin/skill-runtime doctor
```

Qoder charge la configuration Hook au démarrage, alors redémarrez Qoder après la première installation. OpenCode découvre le plugin géré d'observation uniquement à partir de son répertoire global de plugins ; redémarrez OpenCode si le processus en cours est antérieur à l'installation. Aucune des deux intégrations ne lit ou ne modifie les demandes de modèle.

L'intégration ne devient **Live** qu'après que la base de données reçoit un véritable événement `official_hook`. Le simple fait d'écrire `~/.codex/hooks.json` est affiché comme **En attente**, jamais connecté. `start` lance le collecteur, l'observateur de repli de transcription, le travailleur de rétention, le magasin SQLite et met en ligne UI en tant que processus en arrière-plan géré. Aucune demande de modèle n'est proxy.

Commandes de cycle de vie :

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

`uninstall` supprime uniquement les entrées Hook gérées et les fichiers appartenant à Skill Runtime. Sans `--keep-data`, il nécessite une confirmation interactive (ou `--yes`) avant de supprimer `~/.skill-runtime` ; Les sessions d'agent et les sources de compétences ne sont jamais supprimées.

Pour indexer et servir séparément :

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Importez une exportation de trace existante à partir d'un système d'observabilité grand public :

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Les profils d'importation versionnés reconnaissent actuellement les formes OTLP/Phoenix, Langfuse, LangSmith, W&B Weave et Datadog JSON. Ils ne créent un SkillRun que lorsque la source porte une sémantique de compétence explicite ; les noms de span génériques ne sont pas traités comme une preuve d'activation.

Exportez les preuves d'exécution normalisées et spécifiques aux compétences vers n'importe quel point de terminaison de traces OTLP/HTTP :

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

L'exportation est désactivée sauf si un point de terminaison est explicitement configuré. Les points de contrôle, l’état des nouvelles tentatives et l’état de la destination sont affichés dans Paramètres. Les invites brutes, les charges utiles des outils, les informations d'identification et le contenu des ressources de compétences ne sont pas exportés. Pour une exportation en arrière-plan authentifiée, fournissez la norme `OTEL_EXPORTER_OTLP_HEADERS` dans l'environnement avant `skill-runtime start` ; les en-têtes ne sont jamais écrits dans les arguments de configuration ou de processus Skill Runtime.

## Envoyer des preuves d'exécution en direct

`skill-runtime start` inclut un collecteur local. Les adaptateurs de télémétrie natifs, les hooks officiels, les hooks légers à ouverture par échec et les intégrations SDK peuvent ajouter un seul événement ou un lot limité à `POST /api/events` :

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

Le point de terminaison rédige les informations d'identification communes avant la persistance, les duplique par `event_id`, conserve une enveloppe brute rédigée distincte et renvoie le `skill_run_ids` résultant. `GET /api/collector/schema` expose le vocabulaire d'événements et les modes de collecte pris en charge. Le UI écoute le `/api/stream` en utilisant SSE, avec une interrogation uniquement comme solution de secours de reconnexion.

L'indicateur source distingue les preuves d'exécution principales de `Transcript fallback` et les traces importées. Un point de terminaison Collector à lui seul ne revendique pas la télémétrie native : chaque producteur doit déclarer si son événement provient de la télémétrie native, d'un hook officiel, d'un hook léger ou d'un SDK.

### Hooks d’agent facultatifs

Inspectez d’abord les chemins et les événements exacts. Cette commande est en lecture seule :

```bash
.venv/bin/skill-runtime setup
```

L'installation Hook nécessite un indicateur explicite :

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Le programme d'installation sauvegarde la configuration de l'agent, préserve les hooks existants et ajoute uniquement les entrées portant un marqueur de gestion Skill Runtime. L'adaptateur de hook stocke un minimum de champs de cycle de vie plutôt que des invites complètes ou des charges utiles d'outils. Pour les appels d'outils terminés, il extrait uniquement le `SKILL.md` exact, la ressource de compétence standard et les chemins de fichiers modifiés en mémoire ; Les commandes brutes, les corps de correctifs, les invites et les sorties d'outils sont supprimés avant la persistance. Lorsque le runtime est actif, un socket Unix restreint aux autorisations constitue le chemin rapide ; un expéditeur natif facultatif évite le démarrage de Python. Lorsque le moteur d'exécution n'est pas actif, le chemin d'ouverture en cas d'échec autonome ajoute des preuves expurgées à `~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` relit cette file d'attente avec la déduplication de l'ID d'événement.

Les événements Codex utilisent ses Hook API officiels (`SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SubagentStart`, `SubagentStop` et `Stop`). Codex exécute actuellement les hooks de commande de manière synchrone, donc Skill Runtime utilise un socket/expéditeur natif Unix local avec un délai d'attente limité. Tout échec de livraison est avalé et mis en file d'attente ; cela ne change jamais la décision d'un agent. Voir le [documentation officielle du Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Supprimez uniquement les entrées gérées avec :

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Le serveur se lie à `127.0.0.1` par défaut. Les messages de transcription complète et les charges utiles des outils ne sont pas copiés dans l’index. Les modèles secrets courants sont rédigés avant que les résumés normalisés ne soient conservés.

Exécutez la suite de tests sans dépendance avec :

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingénierie des versions

GitHub Actions exécute les tests Python 3.9 à 3.13, la validation JavaScript, la compilation de l'expéditeur natif et un véritable test de fumée d'installation/démarrage/médecin/arrêt/désinstallation. Une balise `v*` crée des packages wheel/sdist ainsi que des expéditeurs natifs Linux et macOS protégés par une somme de contrôle. Le programme d'installation CLI télécharge l'actif de version correspondant, les utilisateurs finaux n'ont donc pas besoin d'un compilateur.

Exécutez la première expérience de diagnostics liés au produit :

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Il injecte des erreurs dans les preuves du cycle de vie, des échecs explicites, des exécutions incomplètes et des résultats non vérifiés, puis évalue le même moteur de diagnostic déterministe utilisé par les API et UI. Voir le [Plan d'expérimentation PAI-DSW](docs/pai-dsw-experiment-plan.md) pour l'échelle d'expérimentation, les tests de non-interférence et le contrat de reproductibilité.

Après avoir construit la roue, exécutez la fumée de cycle de vie emballée isolée avec :

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Il s'installe dans un environnement virtuel temporaire et un domicile temporaire, exerce le cycle de vie local complet sans activer les hooks et vérifie la non-interférence de la configuration du projet et de l'agent.

## Conception de produits basée sur l'expérimentation

Le comportement du produit est contraint par le [philosophie de produit basée sur l'expérimentation](docs/experiment-driven-product-philosophy.md) : la preuve avant les conclusions, la première limite observable avant la gravité, les relations typées avant les logs plats et la reconstruction déterministe avant l'assistance probabiliste.

Les preuves locales reproductibles actuelles comprennent :

- 7/7 portes d'expérimentation locales franchies ;
- 2 400/2 400 événements collecteur acceptés sans mutation entrée/sortie ;
- 14/14 diagnostics déterministes de corpus de fautes sans affirmation causale non étayée ;
- représentation du diagnostic relationnel à 13/14 exact et F1 0,963, tandis que la récupération plate du cycle de vie a atteint 1/14 exact et F1 0,080 ;
- Les cas matériels d’étude du 11/11 placent la première limite observable en premier.

Ces résultats valident les mécanismes et les choix de représentation, et non la généralisation du déploiement ou le bénéfice humain. Les études sur les véritables seconds agents, la latence de queue multiplateforme, l'étalonnage des défauts réels et les études de diagnostic des participants restent des lacunes en matière de preuves.

L'orientation de la recherche s'appuie également sur des travaux primaires adjacents : [SkillsBench](https://arxiv.org/abs/2602.12670) et [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivent le diagnostic car les effets des compétences varient et peuvent régresser ; [Harness-Bench](https://arxiv.org/abs/2605.27922) motive la comparaison entre agents tenant compte des capacités ; et le [enquête de provenance d'exécution](https://arxiv.org/abs/2606.04990) motive les relations avec les preuves dactylographiées, la provenance des traces et une infrastructure d'audit respectueuse de la confidentialité.

## Documentation

| Commencez ici | But |
|---|---|
| [Getting Started](docs/getting-started.md) | Installez, connectez un agent, vérifiez les preuves en direct et dépannez |
| [Architecture](docs/architecture.md) | Pipeline de collecte, limites de stockage, moteur de preuves et modèle de confiance |
| [Matrice des capacités de l'adaptateur](docs/adapter-capability-matrix.md) | Signaux exacts et limitations par agent/version |
| [Configuration de la plateforme d'observabilité](docs/observability-platform-setup.md) | Connectez les plates-formes compatibles OTLP et importez les traces prises en charge |
| [Modèle d'événement d'exécution](docs/runtime-event-model.md) | Vocabulaire d'événement stable, provenance, relations et niveaux de preuves |
| [Architecture des informations de l'interface utilisateur](docs/ui-information-architecture.md) | Vue d'ensemble, première limite, Panorama, Inspecteur, Comparaison et Inferred Analysis |

Références produits et recherche : [définition du produit](docs/product-definition.md), [Spécification MVP](docs/mvp-specification.md), [interopérabilité d'observabilité](docs/observability-interoperability.md), [philosophie de produit basée sur l'expérimentation](docs/experiment-driven-product-philosophy.md), [résultats de l'expérience](docs/experiment-results-2026-07-29.md) et le [programme de recherche](docs/research-paper-agenda.md).

## Feuille de route

1. **v0.2.0 — Disponible dès maintenant :** collecte en direct avec ouverture par échec, quatre adaptateurs d'agent versionnés, Runtime Overview, diagnostic de première limite, Panorama, Evidence Inspector, comparaison prenant en compte les capacités, Inferred Analysis et interopérabilité OTLP.
2. **Suivant — Renforcement des adaptateurs et des diagnostics :** couverture plus large des agents/versions, étalonnage des défauts réels, validation de la latence arrière multiplateforme et études de diagnostic des participants.
3. **Plus tard — Évaluation de l'effet :** évaluation couplée contrôlée avec/sans compétence, explicitement séparée du diagnostic à une seule analyse.

## Statut du projet

La version `v0.2.0` est publiée. Le moteur d'exécution comprend un inventaire de définition installé, des adaptateurs Hook officiels basés sur le consentement pour Codex, Claude Code et Qoder, un plugin OpenCode d'observation uniquement, une solution de repli de transcription étiquetée, une attribution de portée active, des chemins exacts de fichiers/artefacts, une rédaction, des couches source/relation/inférence séparées, Stockage SQLite, rétention, diagnostic déterministe, UI en direct et comparaison cross-run/cross-Agent. Les exportations OTLP/Phoenix, Langfuse, LangSmith, W&B Weave et Datadog peuvent être importées ; les preuves normalisées peuvent être exportées en direct via l'opt-in OTLP/HTTP.

La découverte de candidats à l'intérieur du modèle, les raisons de sélection internes au modèle, l'efficacité sémantique et les allégations de résultats causals restent explicitement non étayées à moins qu'une source ou une expérience contrôlée ne fournisse cette preuve.
