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

const source = fs.readFileSync(sourcePath, "utf8");
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
  live_hook_count: "{count} live hooks",
  pending_hook_count: "{count} hooks pending",
  activation_run_count: "{count} SkillRuns contain activation or instruction evidence.",
  definition_count: "{count} installed definitions",
  metadata_difference_count: "{count} metadata fields differ.",
  overlap_percent: "{percent}% term overlap",
  official_events: "{count} official events · live evidence verified · fail-open",
  configured_events: "{count} events configured · awaiting Agent trust or a new run",
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

function protect(value) {
  return value.replace(
    protectedPattern,
    (term) => `<span class="notranslate">${term}</span>`,
  );
}

async function translateOne(value, target, attempt = 0) {
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
    throw new Error(`Translation request failed: ${response.status}`);
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

async function translateCatalog(target) {
  const values = [...keys, ...Object.values(patternTemplates)];
  const translated = [];
  for (let index = 0; index < values.length; index += 16) {
    translated.push(...await translateBatch(values.slice(index, index + 16), target));
  }
  const messages = Object.fromEntries(keys.map((key, index) => [key, translated[index]]));
  const patternValues = translated.slice(keys.length);
  const patterns = Object.fromEntries(
    Object.keys(patternTemplates).map((key, index) => [key, patternValues[index]])
  );
  return {messages, patterns};
}

const catalogs = {};
for (const [locale, target] of Object.entries(localeTargets)) {
  process.stdout.write(`Generating ${locale}…\n`);
  catalogs[locale] = await translateCatalog(target);
  Object.assign(catalogs[locale].messages, reviewedOverrides[locale]);
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
