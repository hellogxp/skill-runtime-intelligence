#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = path.resolve(import.meta.dirname, "..");
const sourcePath = path.join(root, "README.md");
const localeTargets = {
  // Simplified Chinese is maintained by hand because it is the primary
  // non-English product documentation. The remaining locale files are
  // reproducible translations of the canonical English README.
  "zh-TW": "zh-TW", fr: "fr", de: "de", it: "it",
  es: "es", ja: "ja", ko: "ko", ru: "ru", "pt-BR": "pt", tr: "tr",
  pl: "pl", cs: "cs", hu: "hu",
};
const localeNames = {
  en: "English", "zh-CN": "简体中文", "zh-TW": "繁體中文", fr: "Français",
  de: "Deutsch", it: "Italiano", es: "Español", ja: "日本語", ko: "한국어",
  ru: "Русский", "pt-BR": "Português (Brasil)", tr: "Türkçe", pl: "Polski",
  cs: "Čeština", hu: "Magyar",
};

function filename(locale) {
  return locale === "en" ? "README.md" : `README.${locale}.md`;
}

function localeSwitcher(active) {
  const links = Object.entries(localeNames).map(([locale, label]) =>
    locale === active ? `**${label}**` : `[${label}](${filename(locale)})`
  );
  return [
    "<!-- locale-switcher:start -->",
    links.slice(0, 4).join(" · ") + " ·",
    links.slice(4, 8).join(" · ") + " ·",
    links.slice(8, 12).join(" · ") + " ·",
    links.slice(12).join(" · "),
    "<!-- locale-switcher:end -->",
  ];
}

const protectedTerms = [
  "Agent Skill Runtime Intelligence",
  "OTEL_EXPORTER_OTLP_HEADERS",
  "OTEL_EXPORTER_OTLP_ENDPOINT",
  "skill-runtime",
  "Skill Run Panorama", "Skill Runtime", "SkillRuns", "SkillRun", "OTLP/HTTP",
  "OpenTelemetry", "SQLite", "Codex", "Claude Code", "MCP", "SDK",
  "SkillsBench", "SWE-Skills-Bench", "Harness-Bench",
  "Phoenix", "Langfuse", "LangSmith", "W&B Weave", "Datadog", "Grafana",
  "Python", "Unix", "Git", "JSON", "API", "UI",
];
const protectedSegmentPattern = new RegExp(
  "`[^`]+`|\\[([^\\]]+)\\]\\(([^)]+)\\)|" +
  protectedTerms
    .sort((left, right) => right.length - left.length)
    .map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|"),
  "g",
);

async function translatePlain(value, target, attempt = 0) {
  if (!value.trim()) return value;
  const url = new URL("https://translate.googleapis.com/translate_a/single");
  url.searchParams.set("client", "gtx");
  url.searchParams.set("sl", "en");
  url.searchParams.set("tl", target);
  url.searchParams.set("dt", "t");
  url.searchParams.set("q", value);
  const response = await fetch(url, {
    headers: {"User-Agent": "skill-runtime-intelligence-localization-builder/1"},
  });
  if (!response.ok) {
    if (attempt < 3 && [429, 500, 502, 503].includes(response.status)) {
      await new Promise((resolve) => setTimeout(resolve, 500 * (2 ** attempt)));
      return translatePlain(value, target, attempt + 1);
    }
    throw new Error(`Translation request failed: ${response.status}`);
  }
  const payload = await response.json();
  if (!Array.isArray(payload[0])) return value;
  return payload[0].map((segment) => segment[0]).join("");
}

async function translate(value, target) {
  if (!value.trim()) return value;
  const parts = [];
  let cursor = 0;
  for (const match of value.matchAll(protectedSegmentPattern)) {
    if (match.index > cursor) {
      parts.push({kind: "text", value: value.slice(cursor, match.index)});
    }
    if (match[1] !== undefined) {
      parts.push({
        kind: "link",
        label: match[1],
        target: match[2],
      });
    } else {
      parts.push({kind: "literal", value: match[0]});
    }
    cursor = match.index + match[0].length;
  }
  if (cursor < value.length) {
    parts.push({kind: "text", value: value.slice(cursor)});
  }
  const translated = await Promise.all(parts.map(async (part) => {
    if (part.kind === "literal") return part.value;
    if (part.kind === "link") {
      const label = protectedTerms.includes(part.label)
        ? part.label
        : await translatePlain(part.label, target);
      return `[${label}](${part.target})`;
    }
    return translatePlain(part.value, target);
  }));
  return translated.join("").replace(/\]\s+\(/g, "](");
}

function classifyLine(line, inCode) {
  if (line.startsWith("```")) return {kind: "fence", value: line};
  if (inCode || !line.trim() || line.startsWith("<!--") || line.startsWith("!["))
    return {kind: "literal", value: line};
  if (/^\|?[\s|:-]+\|?$/.test(line)) return {kind: "literal", value: line};
  const match = line.match(/^(\s*(?:#{1,6}|>|[-*]|\d+\.)\s+)(.*)$/);
  if (match) return {kind: "prefixed", prefix: match[1], value: match[2]};
  if (line.startsWith("|") && line.endsWith("|")) return {kind: "table", value: line};
  return {kind: "text", value: line};
}

function compactMarkdownParagraphs(lines) {
  const output = [];
  let inCode = false;
  const isBoundary = (line) =>
    !line.trim()
    || /^(```|<!--|!\[|\||#{1,6}\s|>\s|[-*]\s|\d+\.\s)/.test(line);
  for (let index = 0; index < lines.length;) {
    const line = lines[index];
    if (line.startsWith("```")) {
      output.push(line);
      inCode = !inCode;
      index += 1;
      continue;
    }
    if (inCode || !line.trim() || /^(<!--|!\[|\|)/.test(line)) {
      output.push(line);
      index += 1;
      continue;
    }
    const prefixMatch = line.match(/^(\s*(?:>|[-*]|\d+\.)\s+)(.*)$/);
    if (prefixMatch) {
      const parts = [prefixMatch[2].trim()];
      index += 1;
      while (index < lines.length && !isBoundary(lines[index])) {
        parts.push(lines[index].trim());
        index += 1;
      }
      output.push(`${prefixMatch[1]}${parts.join(" ")}`);
      continue;
    }
    if (/^#{1,6}\s/.test(line)) {
      output.push(line);
      index += 1;
      continue;
    }
    const parts = [line.trim()];
    index += 1;
    while (index < lines.length && !isBoundary(lines[index])) {
      parts.push(lines[index].trim());
      index += 1;
    }
    output.push(parts.join(" "));
  }
  return output;
}

async function translateTable(line, target) {
  const cells = line.slice(1, -1).split("|");
  const translated = await Promise.all(cells.map((cell) => translate(cell.trim(), target)));
  return `| ${translated.join(" | ")} |`;
}

async function generate(locale, target) {
  const allLines = fs.readFileSync(sourcePath, "utf8").split("\n");
  const start = allLines.indexOf("<!-- locale-switcher:start -->");
  const end = allLines.indexOf("<!-- locale-switcher:end -->");
  const sourceLines = start >= 0 && end >= start
    ? [...allLines.slice(0, start), ...allLines.slice(end + 1)]
    : allLines;
  const lines = compactMarkdownParagraphs(sourceLines);
  lines.splice(1, 0, "", ...localeSwitcher(locale));

  const classified = [];
  let inCode = false;
  let inLocaleSwitcher = false;
  for (const line of lines) {
    if (line === "<!-- locale-switcher:start -->") inLocaleSwitcher = true;
    const item = inLocaleSwitcher
      ? {kind: "literal", value: line}
      : classifyLine(line, inCode);
    classified.push(item);
    if (item.kind === "fence") inCode = !inCode;
    if (line === "<!-- locale-switcher:end -->") inLocaleSwitcher = false;
  }
  const output = new Array(classified.length);
  for (let index = 0; index < classified.length; index += 12) {
    const slice = classified.slice(index, index + 12);
    const translated = await Promise.all(slice.map(async (item) => {
      if (item.kind === "literal" || item.kind === "fence") return item.value;
      if (item.kind === "table") return translateTable(item.value, target);
      const value = await translate(item.value, target);
      return item.kind === "prefixed" ? `${item.prefix}${value}` : value;
    }));
    translated.forEach((value, offset) => {
      output[index + offset] = value;
    });
  }
  const destination = path.join(root, filename(locale));
  fs.writeFileSync(destination, `${output.join("\n").trim()}\n`);
  process.stdout.write(`Wrote ${path.basename(destination)}\n`);
}

const requested = new Set(process.argv.slice(2));
for (const [locale, target] of Object.entries(localeTargets)) {
  if (requested.size && !requested.has(locale)) continue;
  await generate(locale, target);
}
