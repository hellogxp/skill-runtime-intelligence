#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = path.resolve(import.meta.dirname, "..");
const sourcePath = path.join(root, "src/skill_runtime_intelligence/web/i18n.js");
const outputPath = path.join(root, "src/skill_runtime_intelligence/web/locale-packs.js");
const localeTargets = {
  "zh-TW": "zh-TW", fr: "fr", de: "de", it: "it", es: "es", ja: "ja",
  ko: "ko", ru: "ru", "pt-BR": "pt", tr: "tr", pl: "pl", cs: "cs", hu: "hu",
};

const reviewedOverrides = {
  "zh-TW": {
    Language: "語言", Runs: "執行紀錄", Skills: "技能", Settings: "設定",
    Observed: "已觀察", Derived: "衍生", Inferred: "推論", Experimental: "實驗性",
    Evidence: "證據", Lifecycle: "生命週期", "Runtime Settings": "執行階段設定",
    "Collection health": "採集健康狀態", "Data & privacy": "資料與隱私",
    "Save settings": "儲存設定",
    "ui selection": "介面選擇", "slash command": "斜線指令",
    "instruction evidence": "指令證據", "instruction access": "指令存取",
    "resource access": "資源存取",
  },
  fr: {
    Language: "Langue", Runs: "Exécutions", Skills: "Skills", Settings: "Paramètres",
    Observed: "Observé", Derived: "Dérivé", Inferred: "Inféré", Experimental: "Expérimental",
    Evidence: "Preuves", Lifecycle: "Cycle de vie", "Runtime Settings": "Paramètres d’exécution",
    "Collection health": "État de la collecte", "Data & privacy": "Données et confidentialité",
    "Save settings": "Enregistrer",
  },
  de: {
    Language: "Sprache", Runs: "Ausführungen", Skills: "Skills", Settings: "Einstellungen",
    Observed: "Beobachtet", Derived: "Abgeleitet", Inferred: "Gefolgert", Experimental: "Experimentell",
    Evidence: "Evidenz", Lifecycle: "Lebenszyklus", "Runtime Settings": "Laufzeiteinstellungen",
    "Collection health": "Erfassungsstatus", "Data & privacy": "Daten & Datenschutz",
    "Save settings": "Einstellungen speichern",
  },
  it: {
    Language: "Lingua", Runs: "Esecuzioni", Skills: "Skill", Settings: "Impostazioni",
    Observed: "Osservato", Derived: "Derivato", Inferred: "Inferito", Experimental: "Sperimentale",
    Evidence: "Evidenza", Lifecycle: "Ciclo di vita", "Runtime Settings": "Impostazioni runtime",
    "Collection health": "Stato della raccolta", "Data & privacy": "Dati e privacy",
    "Save settings": "Salva impostazioni",
  },
  es: {
    Language: "Idioma", Runs: "Ejecuciones", Skills: "Skills", Settings: "Configuración",
    Observed: "Observado", Derived: "Derivado", Inferred: "Inferido", Experimental: "Experimental",
    Evidence: "Evidencia", Lifecycle: "Ciclo de vida", "Runtime Settings": "Configuración de ejecución",
    "Collection health": "Estado de recopilación", "Data & privacy": "Datos y privacidad",
    "Save settings": "Guardar configuración",
  },
  ja: {
    Language: "言語", Runs: "実行", Skills: "スキル", Settings: "設定",
    Observed: "観測済み", Derived: "導出", Inferred: "推論", Experimental: "実験",
    Evidence: "エビデンス", Lifecycle: "ライフサイクル", "Runtime Settings": "ランタイム設定",
    "Collection health": "収集状態", "Data & privacy": "データとプライバシー",
    "Save settings": "設定を保存",
  },
  ko: {
    Language: "언어", Runs: "실행", Skills: "스킬", Settings: "설정",
    Observed: "관측됨", Derived: "도출됨", Inferred: "추론됨", Experimental: "실험적",
    Evidence: "증거", Lifecycle: "수명 주기", "Runtime Settings": "런타임 설정",
    "Collection health": "수집 상태", "Data & privacy": "데이터 및 개인정보",
    "Save settings": "설정 저장",
  },
  ru: {
    Language: "Язык", Runs: "Запуски", Skills: "Навыки", Settings: "Настройки",
    Observed: "Наблюдаемое", Derived: "Производное", Inferred: "Предполагаемое", Experimental: "Экспериментальное",
    Evidence: "Доказательства", Lifecycle: "Жизненный цикл", "Runtime Settings": "Настройки среды выполнения",
    "Collection health": "Состояние сбора", "Data & privacy": "Данные и конфиденциальность",
    "Save settings": "Сохранить настройки",
  },
  "pt-BR": {
    Language: "Idioma", Runs: "Execuções", Skills: "Skills", Settings: "Configurações",
    Observed: "Observado", Derived: "Derivado", Inferred: "Inferido", Experimental: "Experimental",
    Evidence: "Evidência", Lifecycle: "Ciclo de vida", "Runtime Settings": "Configurações de execução",
    "Collection health": "Estado da coleta", "Data & privacy": "Dados e privacidade",
    "Save settings": "Salvar configurações",
  },
  tr: {
    Language: "Dil", Runs: "Çalıştırmalar", Skills: "Yetenekler", Settings: "Ayarlar",
    Observed: "Gözlemlendi", Derived: "Türetildi", Inferred: "Çıkarım", Experimental: "Deneysel",
    Evidence: "Kanıt", Lifecycle: "Yaşam döngüsü", "Runtime Settings": "Çalışma zamanı ayarları",
    "Collection health": "Toplama durumu", "Data & privacy": "Veri ve gizlilik",
    "Save settings": "Ayarları kaydet",
  },
  pl: {
    Language: "Język", Runs: "Uruchomienia", Skills: "Umiejętności", Settings: "Ustawienia",
    Observed: "Zaobserwowane", Derived: "Wyprowadzone", Inferred: "Wnioskowane", Experimental: "Eksperymentalne",
    Evidence: "Dowody", Lifecycle: "Cykl życia", "Runtime Settings": "Ustawienia środowiska",
    "Collection health": "Stan zbierania", "Data & privacy": "Dane i prywatność",
    "Save settings": "Zapisz ustawienia",
  },
  cs: {
    Language: "Jazyk", Runs: "Běhy", Skills: "Dovednosti", Settings: "Nastavení",
    Observed: "Pozorované", Derived: "Odvozené", Inferred: "Odvozené úsudkem", Experimental: "Experimentální",
    Evidence: "Důkazy", Lifecycle: "Životní cyklus", "Runtime Settings": "Nastavení běhu",
    "Collection health": "Stav sběru", "Data & privacy": "Data a soukromí",
    "Save settings": "Uložit nastavení",
  },
  hu: {
    Language: "Nyelv", Runs: "Futtatások", Skills: "Készségek", Settings: "Beállítások",
    Observed: "Megfigyelt", Derived: "Származtatott", Inferred: "Kikövetkeztetett", Experimental: "Kísérleti",
    Evidence: "Bizonyíték", Lifecycle: "Életciklus", "Runtime Settings": "Futásidejű beállítások",
    "Collection health": "Gyűjtés állapota", "Data & privacy": "Adatok és adatvédelem",
    "Save settings": "Beállítások mentése",
  },
};

const productIntelligenceOverrides = {
  "zh-TW": {
    "RUNTIME OVERVIEW": "執行階段總覽",
    "Boundary-first attention": "邊界優先關注",
    "FIRST OBSERVABLE BOUNDARY": "首個可觀察邊界",
    "ATTENTION QUEUE": "關注佇列",
    "INFERRED ANALYSIS": "推論分析",
    "Evidence-bounded investigation candidates": "受證據邊界約束的調查候選",
    "Same Skill behavior": "相同 Skill 行為",
    "Skill version change": "Skill 版本變更",
    "Same evaluation task": "相同評估任務",
    "COMPARABILITY MASK": "可比較性遮罩",
  },
  fr: {
    "RUNTIME OVERVIEW": "VUE D’ENSEMBLE DE L’EXÉCUTION",
    "Boundary-first attention": "Priorité aux frontières",
    "FIRST OBSERVABLE BOUNDARY": "PREMIÈRE FRONTIÈRE OBSERVABLE",
    "ATTENTION QUEUE": "FILE D’ATTENTION",
    "INFERRED ANALYSIS": "ANALYSE INFÉRÉE",
    "Evidence-bounded investigation candidates": "Pistes d’investigation limitées par les preuves",
    "Same Skill behavior": "Comportement du même Skill",
    "Skill version change": "Changement de version du Skill",
    "Same evaluation task": "Même tâche d’évaluation",
    "COMPARABILITY MASK": "MASQUE DE COMPARABILITÉ",
  },
  de: {
    "RUNTIME OVERVIEW": "LAUFZEITÜBERSICHT",
    "Boundary-first attention": "Grenzen zuerst beachten",
    "FIRST OBSERVABLE BOUNDARY": "ERSTE BEOBACHTBARE GRENZE",
    "ATTENTION QUEUE": "PRÜFWARTESCHLANGE",
    "INFERRED ANALYSIS": "ABGELEITETE ANALYSE",
    "Evidence-bounded investigation candidates": "Evidenzbegrenzte Untersuchungshinweise",
    "Same Skill behavior": "Verhalten desselben Skills",
    "Skill version change": "Änderung der Skill-Version",
    "Same evaluation task": "Gleiche Evaluierungsaufgabe",
    "COMPARABILITY MASK": "VERGLEICHBARKEITSMASKE",
  },
  it: {
    "RUNTIME OVERVIEW": "PANORAMICA RUNTIME",
    "Boundary-first attention": "Priorità al primo confine",
    "FIRST OBSERVABLE BOUNDARY": "PRIMO CONFINE OSSERVABILE",
    "ATTENTION QUEUE": "CODA DI ATTENZIONE",
    "INFERRED ANALYSIS": "ANALISI INFERITA",
    "Evidence-bounded investigation candidates": "Ipotesi d’indagine limitate dalle evidenze",
    "Same Skill behavior": "Comportamento dello stesso Skill",
    "Skill version change": "Cambio di versione dello Skill",
    "Same evaluation task": "Stesso compito di valutazione",
    "COMPARABILITY MASK": "MASCHERA DI COMPARABILITÀ",
  },
  es: {
    "RUNTIME OVERVIEW": "RESUMEN DE EJECUCIÓN",
    "Boundary-first attention": "Atención primero al límite",
    "FIRST OBSERVABLE BOUNDARY": "PRIMER LÍMITE OBSERVABLE",
    "ATTENTION QUEUE": "COLA DE ATENCIÓN",
    "INFERRED ANALYSIS": "ANÁLISIS INFERIDO",
    "Evidence-bounded investigation candidates": "Candidatos de investigación acotados por evidencia",
    "Same Skill behavior": "Comportamiento del mismo Skill",
    "Skill version change": "Cambio de versión del Skill",
    "Same evaluation task": "Misma tarea de evaluación",
    "COMPARABILITY MASK": "MÁSCARA DE COMPARABILIDAD",
  },
  ja: {
    "RUNTIME OVERVIEW": "ランタイム概要",
    "Boundary-first attention": "境界を優先して確認",
    "FIRST OBSERVABLE BOUNDARY": "最初の観測可能な境界",
    "ATTENTION QUEUE": "確認キュー",
    "INFERRED ANALYSIS": "推論分析",
    "Evidence-bounded investigation candidates": "エビデンスに制約された調査候補",
    "Same Skill behavior": "同一 Skill の動作",
    "Skill version change": "Skill バージョン変更",
    "Same evaluation task": "同一の評価タスク",
    "COMPARABILITY MASK": "比較可能性マスク",
  },
  ko: {
    "RUNTIME OVERVIEW": "런타임 개요",
    "Boundary-first attention": "경계를 우선 확인",
    "FIRST OBSERVABLE BOUNDARY": "최초 관측 가능 경계",
    "ATTENTION QUEUE": "확인 대기열",
    "INFERRED ANALYSIS": "추론 분석",
    "Evidence-bounded investigation candidates": "증거로 제한된 조사 후보",
    "Same Skill behavior": "동일 Skill 동작",
    "Skill version change": "Skill 버전 변경",
    "Same evaluation task": "동일 평가 작업",
    "COMPARABILITY MASK": "비교 가능성 마스크",
  },
  ru: {
    "RUNTIME OVERVIEW": "ОБЗОР ВЫПОЛНЕНИЯ",
    "Boundary-first attention": "Сначала граница наблюдения",
    "FIRST OBSERVABLE BOUNDARY": "ПЕРВАЯ НАБЛЮДАЕМАЯ ГРАНИЦА",
    "ATTENTION QUEUE": "ОЧЕРЕДЬ ПРОВЕРКИ",
    "INFERRED ANALYSIS": "АНАЛИЗ ПРЕДПОЛОЖЕНИЙ",
    "Evidence-bounded investigation candidates": "Направления проверки, ограниченные доказательствами",
    "Same Skill behavior": "Поведение одного Skill",
    "Skill version change": "Изменение версии Skill",
    "Same evaluation task": "Одна задача оценки",
    "COMPARABILITY MASK": "МАСКА СОПОСТАВИМОСТИ",
  },
  "pt-BR": {
    "RUNTIME OVERVIEW": "VISÃO GERAL DA EXECUÇÃO",
    "Boundary-first attention": "Atenção primeiro ao limite",
    "FIRST OBSERVABLE BOUNDARY": "PRIMEIRO LIMITE OBSERVÁVEL",
    "ATTENTION QUEUE": "FILA DE ATENÇÃO",
    "INFERRED ANALYSIS": "ANÁLISE INFERIDA",
    "Evidence-bounded investigation candidates": "Candidatos de investigação limitados por evidências",
    "Same Skill behavior": "Comportamento do mesmo Skill",
    "Skill version change": "Mudança de versão do Skill",
    "Same evaluation task": "Mesma tarefa de avaliação",
    "COMPARABILITY MASK": "MÁSCARA DE COMPARABILIDADE",
  },
  tr: {
    "RUNTIME OVERVIEW": "ÇALIŞMA ZAMANI ÖZETİ",
    "Boundary-first attention": "Önce sınıra odaklan",
    "FIRST OBSERVABLE BOUNDARY": "İLK GÖZLEMLENEBİLİR SINIR",
    "ATTENTION QUEUE": "İNCELEME KUYRUĞU",
    "INFERRED ANALYSIS": "ÇIKARIMSAL ANALİZ",
    "Evidence-bounded investigation candidates": "Kanıtla sınırlandırılmış inceleme adayları",
    "Same Skill behavior": "Aynı Skill davranışı",
    "Skill version change": "Skill sürümü değişikliği",
    "Same evaluation task": "Aynı değerlendirme görevi",
    "COMPARABILITY MASK": "KARŞILAŞTIRILABİLİRLİK MASKESİ",
  },
  pl: {
    "RUNTIME OVERVIEW": "PRZEGLĄD DZIAŁANIA",
    "Boundary-first attention": "Najpierw granica obserwacji",
    "FIRST OBSERVABLE BOUNDARY": "PIERWSZA OBSERWOWALNA GRANICA",
    "ATTENTION QUEUE": "KOLEJKA UWAGI",
    "INFERRED ANALYSIS": "ANALIZA WNIOSKOWANA",
    "Evidence-bounded investigation candidates": "Kierunki badania ograniczone dowodami",
    "Same Skill behavior": "Zachowanie tego samego Skill",
    "Skill version change": "Zmiana wersji Skill",
    "Same evaluation task": "To samo zadanie oceny",
    "COMPARABILITY MASK": "MASKA PORÓWNYWALNOŚCI",
  },
  cs: {
    "RUNTIME OVERVIEW": "PŘEHLED BĚHU",
    "Boundary-first attention": "Nejprve hranice pozorování",
    "FIRST OBSERVABLE BOUNDARY": "PRVNÍ POZOROVATELNÁ HRANICE",
    "ATTENTION QUEUE": "FRONTA K PROVĚŘENÍ",
    "INFERRED ANALYSIS": "ODVOZENÁ ANALÝZA",
    "Evidence-bounded investigation candidates": "Směry šetření omezené důkazy",
    "Same Skill behavior": "Chování stejného Skill",
    "Skill version change": "Změna verze Skill",
    "Same evaluation task": "Stejná evaluační úloha",
    "COMPARABILITY MASK": "MASKA POROVNATELNOSTI",
  },
  hu: {
    "RUNTIME OVERVIEW": "FUTÁSI ÁTTEKINTÉS",
    "Boundary-first attention": "Először a megfigyelési határ",
    "FIRST OBSERVABLE BOUNDARY": "ELSŐ MEGFIGYELHETŐ HATÁR",
    "ATTENTION QUEUE": "VIZSGÁLATI SOR",
    "INFERRED ANALYSIS": "KÖVETKEZTETETT ELEMZÉS",
    "Evidence-bounded investigation candidates": "Bizonyítékokkal korlátozott vizsgálati irányok",
    "Same Skill behavior": "Azonos Skill viselkedése",
    "Skill version change": "Skill-verzió változása",
    "Same evaluation task": "Azonos értékelési feladat",
    "COMPARABILITY MASK": "ÖSSZEHASONLÍTHATÓSÁGI MASZK",
  },
};

const source = fs.readFileSync(sourcePath, "utf8");
let existingCatalogs = {};
if (fs.existsSync(outputPath)) {
  const existingSource = fs.readFileSync(outputPath, "utf8");
  const prefix = "window.SkillRuntimeLocalePacks = ";
  const start = existingSource.indexOf(prefix);
  if (start >= 0) {
    existingCatalogs = JSON.parse(
      existingSource.slice(start + prefix.length).trim().replace(/;$/, "")
    );
  }
}
const dictionaryStart = source.indexOf("const zh = {");
const dictionaryEnd = source.indexOf("\n  };", dictionaryStart);
if (dictionaryStart < 0 || dictionaryEnd < 0) {
  throw new Error("Unable to locate the canonical UI message list in i18n.js");
}
const keys = [];
for (const match of source.slice(dictionaryStart, dictionaryEnd).matchAll(
  /^    ("(?:[^"\\]|\\.)*"): /gm
)) {
  keys.push(JSON.parse(match[1]));
}

const patternTemplates = {
  skills_count: "{count} Skills",
  runs_resources: "{runs} runs · {resources} resources",
  percent_events: "{percent}% · {events} events",
  evidence_coverage: "Evidence coverage {percent}%",
  primary_count: "{count} primary",
  fallback_count: "{count} fallback",
  import_count: "{count} imports",
  live_integration_count: "{count} live integrations",
  pending_integration_count: "{count} integrations pending",
  activation_run_count: "{count} SkillRuns contain activation or instruction evidence.",
  definition_count: "{count} installed definitions",
  metadata_difference_count: "{count} metadata fields differ.",
  overlap_percent: "{percent}% term overlap",
  runtime_events: "{count} runtime events · live evidence verified · fail-open",
  configured_events: "{count} events configured · awaiting Agent restart/trust or a new run",
  exported_failed: "{exported} exported · {failed} failed",
  attribution_edges: "{count} attribution edges",
  evidence_records: "{count} evidence records",
  stage_records: "{count} evidence records support this lifecycle stage.",
  no_comparable_run: "No comparable {status} run",
};

const protectedTerms = [
  "OTEL_EXPORTER_OTLP_ENDPOINT", "--otlp-endpoint",
  "SkillRuns", "SkillRun", "Skills", "Skill", "Agent", "OTLP/HTTP", "SQLite",
  "MCP", "SDK", "{count}", "{runs}", "{resources}", "{percent}", "{events}",
  "{exported}", "{failed}", "{status}",
];
const protectedPattern = new RegExp(
  protectedTerms
    .sort((left, right) => right.length - left.length)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|"),
  "g",
);
let translationUnavailable = false;

function protect(value) {
  return value.replace(
    protectedPattern,
    (term) => `<span class="notranslate">${term}</span>`,
  );
}

async function translateOne(value, target, attempt = 0) {
  if (translationUnavailable) return value;
  const url = new URL("https://translate.googleapis.com/translate_a/single");
  url.searchParams.set("client", "gtx");
  url.searchParams.set("sl", "en");
  url.searchParams.set("tl", target);
  url.searchParams.set("dt", "t");
  url.searchParams.set("format", "html");
  url.searchParams.set("q", protect(value));
  const response = await fetch(url, {
    headers: {"User-Agent": "skill-runtime-intelligence-localization-builder/1"},
  });
  if (!response.ok) {
    if (attempt < 3 && [429, 500, 502, 503].includes(response.status)) {
      await new Promise((resolve) => setTimeout(resolve, 500 * (2 ** attempt)));
      return translateOne(value, target, attempt + 1);
    }
    process.stderr.write(
      `Translation unavailable (${response.status}); preserving English fallback.\n`
    );
    translationUnavailable = true;
    return value;
  }
  const payload = await response.json();
  if (!Array.isArray(payload[0])) return value;
  const translated = payload[0].map((segment) => segment[0]).join("").trim();
  if (/<\/?span\b/i.test(translated) || /(?:ZXQ|SRI_)/.test(translated)) {
    throw new Error(`Translation protection leaked into: ${translated}`);
  }
  return translated;
}

async function translateBatch(values, target) {
  return Promise.all(values.map((value) => translateOne(value, target)));
}

async function translateCatalog(locale, target) {
  const existing = existingCatalogs[locale] || {messages: {}, patterns: {}};
  const missingKeys = keys.filter((key) => !Object.hasOwn(existing.messages, key));
  const missingPatternKeys = Object.keys(patternTemplates).filter(
    (key) => !Object.hasOwn(existing.patterns, key)
  );
  const values = [
    ...missingKeys,
    ...missingPatternKeys.map((key) => patternTemplates[key]),
  ];
  const translated = [];
  for (let index = 0; index < values.length; index += 4) {
    translated.push(...await translateBatch(values.slice(index, index + 4), target));
  }
  const messages = {...existing.messages};
  missingKeys.forEach((key, index) => {
    messages[key] = translated[index];
  });
  const patterns = {...existing.patterns};
  const patternValues = translated.slice(missingKeys.length);
  missingPatternKeys.forEach((key, index) => {
    patterns[key] = patternValues[index];
  });
  return {messages, patterns};
}

const catalogs = {};
for (const [locale, target] of Object.entries(localeTargets)) {
  process.stdout.write(`Generating ${locale}…\n`);
  catalogs[locale] = await translateCatalog(locale, target);
  Object.assign(catalogs[locale].messages, reviewedOverrides[locale]);
  Object.assign(catalogs[locale].messages, productIntelligenceOverrides[locale]);
}
const banner = [
  "/* Generated by scripts/generate_ui_locales.mjs.",
  " * Runtime translation is fully local; do not edit generated messages by hand.",
  " */",
];
fs.writeFileSync(
  outputPath,
  `${banner.join("\n")}\nwindow.SkillRuntimeLocalePacks = ${JSON.stringify(catalogs, null, 2)};\n`
);
process.stdout.write(`Wrote ${outputPath}\n`);
