# Agent Skill Runtime Intelligence

<!-- locale-switcher:start -->
[English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · **Français** ·
[Deutsch](README.de.md) · [Italiano](README.it.md) · [Español](README.es.md) · [日本語](README.ja.md) ·
[한국어](README.ko.md) · [Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) · [Türkçe](README.tr.md) ·
[Polski](README.pl.md) · [Čeština](README.cs.md) · [Magyar](README.hu.md)
<!-- locale-switcher:end -->


> Diagnostiquez où une compétence d'agent a divergé pour la première fois et inspectez les preuves
> derrière chaque conclusion.

Agent Skill Runtime Intelligenceest un système de preuve d'exécution et de diagnostic en lecture seule pour les compétences d'agent. Il combine les définitions de compétences, les événements d'exécution officiels de l'agent, les traces importées, le repli de session et les résultats observables de l'espace de travail dans un système évalué par des preuves.Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Démarrage rapide

Installez la dernière version autonome pour macOS ou Linux :

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

Ou exécutez directement à partir d'une extraction source :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Ouvrir[http://127.0.0.1:4317](http://127.0.0.1:4317). PourCodex, examinez et approuvez les commandes gérées dans`/hooks`, démarrez un nouveau tour d'agent, puis vérifiez :

```bash
.venv/bin/skill-runtime doctor
```

L'intégration devient **Vérifiée** uniquement après la réception d'un véritable événement de hook officiel. Un hook configuré est affiché comme **En attente**, jamais comme preuve réelle.

| Surface du produit | Ce à quoi il répond |
|---|---|
| Présentation de l'exécution | LequelSkillRunsbesoin d'attention ? |
| Première limite observable | Où les preuves ont-elles pour la première fois disparu ou échoué ? |
| Skill Run Panorama | Comment la demande, l’activation, les ressources, les outils, les artefacts et le résultat se sont-ils connectés ? |
| Inspecteur des preuves | Quelles capacités de source, de qualité, de base et d'adaptateur soutiennent cette affirmation ? |
| Comparer | Une différence est-elle comportementale, ou seulement une différence d’observabilité ? |
| Paramètres / Médecin | Qu'est-ce qui est lu, stocké, exporté, en attente et vérifié ? |

## Le problème

Installer une Skill ne prouve pas qu'un agent l'a découverte. La découverte ne prouve pas l'activation. L'activation ne prouve pas que les instructions et ressources complètes ont été chargées. L'exécution ne prouve pas que la compétence a amélioré le résultat.

Aujourd’hui, ces échecs sont souvent silencieux. Les développeurs se demandent :

- La compétence était-elle disponible pour cet agent ?
- A-t-il été activé pour cette demande ?
- Quelles instructions, références, scripts et ressources ont été chargés ?
- Quels outils,MCPdes appels, des sous-agents, des fichiers et des artefacts étaient impliqués ?
- Où l'exécution a-t-elle échoué, réessayée ou perdu le contexte ?
- La compétence a-t-elle aidé, ou n'a-t-elle fait qu'ajouter du coût et de la latence ?

## Direction du produit

Le premier produit est un **Skill Run Panorama** :

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

Le panorama est construit à partir de signaux réels et non d’auto-évaluations modélisées :

| Source | Exemples | Preuve |
|---|---|---|
| Fichiers de compétences | métadonnées, instructions, scripts, références, ressources | Observé |
| Événements d'exécution | Appels de compétences, appels d'outils, sous-agents, échecs, durée | Observé |
| Transcriptions des séances | invites, messages, entrées et sorties d'outils, commande | Observé |
| Résultats de l'espace de travail | modifications de fichiers,Gitdiff, rapports, artefacts générés | Observé |
| Corrélation | relations entre les événements, les ressources et les résultats | Dérivé ou déduit |

## Discipline de la preuve

LeUIne doit jamais présenter une inférence comme un fait d’exécution :

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

## Portée initiale

Le MVP prend en chargeClaude CodeetCodexet fournit :

- découverte et validation des compétences installées ;
- importation de session et observation locale en direct lorsque cela est pris en charge ;
- Activation des compétences, chargement des ressources et calendriers d'appel d'outils ;
- sous-agent,MCPles relations entre les fichiers et les artefacts ;
- résumés de durée, de jeton, d'erreur, de nouvelle tentative et d'état lorsqu'ils sont disponibles ;
- une liste d'exécutions, un DAG panoramique, une chronologie des événements et un inspecteur de nœuds.

Le MVP n'inclut **pas** de marché, d'exécution d'agent universel, d'application de la sécurité, de gouvernance d'entreprise ou de réclamations à effet causal.

## Installation détaillée

L'implémentation de base n'a aucune dépendance d'exécution au-delàPython3,9+. Depuis la racine du référentiel :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Puis ouvrez[http://127.0.0.1:4317](http://127.0.0.1:4317).

L'unique`install`commande:

1. analyse les emplacements de compétences des utilisateurs, des projets et des plugins mis en cache ;
2. détecteCodexetClaude Codesans changer leur configuration ;
3. indique quels chemins d'agent et de compétences seront lus ;
4. télécharge un expéditeur natif à faible démarrage vérifié par somme de contrôle pour la plate-forme actuelle, en revenant à une version C locale et enfin auPythonl'expéditeur et préchauffe un nouveau binaire natif une fois pendant l'installation ;
5. crée`~/.skill-runtime/config.json`et le localSQLiteindice.

Lorsqu'il est exécuté de manière interactive, il demande une fois avant d'ajouter des hooks d'agent d'ouverture en cas d'échec.`--no-hooks`conserve l'importation de la transcription comme solution de secours étiquetée, tandis que`--enable-hooks`enregistre le consentement explicite et installe uniquement les entrées gérées. PourCodex, ouvrir`/hooks`après l'installation, examinez les commandes gérées exactes et faites-leur confiance.Codexexige intentionnellement cette révision explicite pour les hooks ajoutés en dehors de la configuration d’entreprise gérée. Commencez un nouveau tour d'agent, puis exécutez :

```bash
.venv/bin/skill-runtime doctor
```

L'intégration devient **Live** seulement après que la base de données reçoive un véritable`official_hook`événement. Simplement écrire`~/.codex/hooks.json`s'affiche comme **En attente**, jamais connecté.`start`lance le collecteur, l'observateur de repli des transcriptions, le travailleur de rétention,SQLitemagasiner et vivreUIen tant que processus en arrière-plan géré. Aucune demande de modèle n'est proxy.

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

`uninstall`supprime uniquement les entrées Hook gérées etSkill Runtime-fichiers appartenant. Sans`--keep-data`, cela nécessite une confirmation interactive (ou`--yes`) avant de retirer`~/.skill-runtime`; Les sessions d'agent et les sources de compétences ne sont jamais supprimées.

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

Les profils d'importation versionnés reconnaissent actuellement OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, etDatadog JSONformes. Ils créent seulement unSkillRunlorsque la source porte une sémantique de compétence explicite ; les noms de span génériques ne sont pas traités comme une preuve d'activation.

Exportez des preuves d'exécution normalisées et spécifiques aux compétences vers n'importe quelOTLP/HTTPpoint de terminaison des traces :

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

L'exportation est désactivée sauf si un point de terminaison est explicitement configuré. Les points de contrôle, l’état des nouvelles tentatives et l’état de la destination sont affichés dans Paramètres. Les invites brutes, les charges utiles des outils, les informations d'identification et le contenu des ressources de compétences ne sont pas exportés. Pour une exportation en arrière-plan authentifiée, fournissez la norme`OTEL_EXPORTER_OTLP_HEADERS`dans l'environnement avant`skill-runtime start`; les en-têtes ne sont jamais écrits dansSkill Runtimearguments de configuration ou de processus.

## Envoyer des preuves d'exécution en direct

`skill-runtime start`comprend un collecteur local. Adaptateurs de télémétrie natifs, hooks officiels, hooks légers à ouverture en panne etSDKles intégrations peuvent ajouter un seul événement ou un lot limité à`POST /api/events`:

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

Le point de terminaison rédige les informations d'identification communes avant la persistance, les duplique par`event_id`, conserve une enveloppe brute rédigée distincte et renvoie le résultat`skill_run_ids`.`GET /api/collector/schema`expose le vocabulaire des événements et les modes de collecte pris en charge. LeUIécoute`/api/stream`en utilisant SSE, avec une interrogation uniquement comme solution de secours de reconnexion.

L'indicateur source distingue les preuves d'exécution primaires des`Transcript fallback`et des traces importées. Un point de terminaison Collector à lui seul ne revendique pas la télémétrie native : chaque producteur doit déclarer si son événement provient de la télémétrie native, d'un hook officiel, d'un hook léger ou d'unSDK.

### Hooks d’agent facultatifs

Inspectez d’abord les chemins et les événements exacts. Cette commande est en lecture seule :

```bash
.venv/bin/skill-runtime setup
```

L'installation du hook nécessite un indicateur explicite :

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

Le programme d'installation sauvegarde la configuration de l'agent, préserve les hooks existants et ajoute uniquement les entrées portant unSkill Runtimemarqueur de gestion. L'adaptateur de hook stocke un minimum de champs de cycle de vie plutôt que des invites complètes ou des charges utiles d'outils. Pendant que le runtime est actif, une autorisation restreinteUnixsocket est le chemin rapide ; un expéditeur natif facultatif évitePythondémarrer. Lorsque le moteur d'exécution n'est pas actif, le chemin d'ouverture en cas d'échec autonome ajoute des preuves expurgées à`~/.skill-runtime/queue/events.jsonl`.`skill-runtime start`relit cette file d'attente avec la déduplication de l'ID d'événement.

Codexles événements utilisent son Hook officielAPI(`SessionStart`,`SessionEnd`,`UserPromptSubmit`,`PreToolUse`,`PostToolUse`,`PreCompact`,`PostCompact`,`SubagentStart`,`SubagentStop`, et`Stop`).Codexexécute actuellement les hooks de commande de manière synchrone, doncSkill Runtimeutilise un localUnixsocket/expéditeur natif avec un délai d’attente limité. Tout échec de livraison est avalé et mis en file d'attente ; cela ne change jamais la décision d'un agent. Voir le[documentation officielle du Codex Hook](https://developers.openai.com/codex/config-advanced#hooks).

Supprimez uniquement les entrées gérées avec :

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

Le serveur se lie à`127.0.0.1`par défaut. Les messages de transcription complète et les charges utiles des outils ne sont pas copiés dans l’index. Les modèles secrets courants sont rédigés avant que les résumés normalisés ne soient conservés.

Exécutez la suite de tests sans dépendance avec :

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Ingénierie des versions

GitLes actions du hub s'exécutentPythonTests 3.9 à 3.13, validation JavaScript, compilation de l'expéditeur natif et un véritable test de fumée d'installation/démarrage/médecin/arrêt/désinstallation. UN`v*`tag crée des packages wheel/sdist ainsi que des expéditeurs natifs Linux et macOS protégés par somme de contrôle. Le programme d'installation CLI télécharge l'actif de version correspondant, les utilisateurs finaux n'ont donc pas besoin d'un compilateur.

Exécutez la première expérience de diagnostics liés au produit :

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

Il injecte des erreurs dans les preuves du cycle de vie, des échecs explicites, des exécutions incomplètes et des résultats non vérifiés, puis évalue le même moteur de diagnostic déterministe utilisé par leAPIetUI. Voir le[Plan d'expérimentation PAI-DSW](docs/pai-dsw-experiment-plan.md)pour l'échelle d'expérimentation, les tests de non-interférence et le contrat de reproductibilité.

Après avoir construit la roue, exécutez la fumée de cycle de vie emballée isolée avec :

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

Il s'installe dans un environnement virtuel temporaire et un domicile temporaire, exerce le cycle de vie local complet sans activer les hooks et vérifie la non-interférence de la configuration du projet et de l'agent.

## Conception de produits basée sur l'expérimentation

Le comportement du produit est limité par[philosophie de produit basée sur l'expérimentation](docs/experiment-driven-product-philosophy.md): preuves avant conclusions, première limite observable avant gravité, relations typées avant logs plats et reconstruction déterministe avant assistance probabiliste.

Les preuves locales reproductibles actuelles comprennent :

- 7/7 portes d'expérimentation locales franchies ;
- 2 400/2 400 événements collecteur acceptés sans mutation entrée/sortie ;
- 14/14 diagnostics déterministes de corpus de fautes sans affirmation causale non étayée ;
- représentation du diagnostic relationnel à 13/14 exact et F1 0,963, tandis que la récupération plate du cycle de vie a atteint 1/14 exact et F1 0,080 ;
- Les cas matériels d’étude du 11/11 placent la première limite observable en premier.

Ces résultats valident les mécanismes et les choix de représentation, et non la généralisation du déploiement ou le bénéfice humain. Les études sur les véritables seconds agents, la latence de queue multiplateforme, l'étalonnage des défauts réels et les études de diagnostic des participants restent des lacunes en matière de preuves.

L’orientation de la recherche s’appuie également sur des travaux primaires adjacents :[SkillsBench](https://arxiv.org/abs/2602.12670)et[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401)motiver le diagnostic car les effets des compétences varient et peuvent régresser ;[Harness-Bench](https://arxiv.org/abs/2605.27922)motive la comparaison entre agents tenant compte des capacités ; et le[enquête de provenance d'exécution](https://arxiv.org/abs/2606.04990)motive les relations avec les preuves dactylographiées, la provenance des traces et une infrastructure d’audit respectueuse de la confidentialité.

## Documentation

- [Définition du produit](docs/product-definition.md)
- [Spécification MVP](docs/mvp-specification.md)
- [Modèle d'événement d'exécution](docs/runtime-event-model.md)
- [Architecture des informations de l'interface utilisateur](docs/ui-information-architecture.md)
- [Matrice des capacités de l'adaptateur](docs/adapter-capability-matrix.md)
- [Interopérabilité de l'observabilité](docs/observability-interoperability.md)
- [Configuration de la plateforme d'observabilité](docs/observability-platform-setup.md)
- [Recherche et paysage concurrentiel](docs/research-and-competitive-landscape.md)
- [Ordre du jour des documents de recherche](docs/research-paper-agenda.md)
- [Philosophie produit basée sur l'expérimentation](docs/experiment-driven-product-philosophy.md)
- [Résultats de l'expérience](docs/experiment-results-2026-07-29.md)
- [Plan d'expérimentation PAI-DSW](docs/pai-dsw-experiment-plan.md)

## Feuille de route

1. **v0.1 — Preuves d'exécution et diagnostic :** collecte en direct,Skill Run Panorama, diagnostic de première limite, inspection des preuves, comparaison et interopérabilité OTLP.
2. **v0.2 — Études sur l'étendue de l'adaptateur et les diagnostics :** agents supplémentaires, expériences réelles entre agents et évaluation des participants.
3. **v0.3 — Évaluation des effets :** évaluation par paire contrôlée avec/sans compétence, séparée du diagnostic à une seule analyse.

## Statut du projet

UNSkillRun-le premier runtime est exécutable : inventaire de définition installé,Codexsolution de secours pour la transcription, basée sur le consentementCodexetClaude Codeadaptateurs de hook officiels, attribution de portée active, chemins exacts de fichiers/artefacts, rédaction, couches source/relation/inférence séparées,SQLitestockage, conservation, comparaison entre exécutions et entre agents, diagnostic déterministe et Panorama en directUI. OTLP/Phoenix,Langfuse,LangSmith,W&B Weave, etDatadogles exportations peuvent être importées ; les preuves normalisées peuvent être exportées en direct via opt-inOTLP/HTTP. La suite reproductible actuelle comporte sept portes d’expériences de passage. La découverte de candidats, les raisons de sélection internes au modèle, l'efficacité sémantique et les allégations de résultats causals restent explicitement non étayées.
