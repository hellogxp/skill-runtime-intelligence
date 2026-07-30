import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src" / "skill_runtime_intelligence" / "web"
EXPECTED_LOCALES = {
    "en",
    "zh-CN",
    "zh-TW",
    "fr",
    "de",
    "it",
    "es",
    "ja",
    "ko",
    "ru",
    "pt-BR",
    "tr",
    "pl",
    "cs",
    "hu",
}


class InternationalizationTests(unittest.TestCase):
    def test_language_selector_exposes_all_supported_locales(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        selector = re.search(
            r'<select id="locale-select">(.*?)</select>', html, re.DOTALL
        ).group(1)
        locales = set(re.findall(r'<option value="([^"]+)">', selector))
        self.assertEqual(locales, EXPECTED_LOCALES)
        self.assertLess(
            html.index('src="/locale-packs.js"'),
            html.index('src="/i18n.js"'),
        )
        self.assertLess(
            html.index('src="/i18n.js"'),
            html.index('src="/app.js"'),
        )

    def test_diagnostic_controls_are_present_in_the_localized_surface(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        for control_id in (
            "run-agent-filter",
            "run-project-filter",
            "run-skill-filter",
            "run-grade-filter",
            "run-date-filter",
            "run-error-filter",
            "event-filter",
            "event-type-filter",
            "event-skill-filter",
            "event-grade-filter",
        ):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn('<option value="discovery">Discovery</option>', html)
        self.assertIn('class="raw-record"', app)
        self.assertIn("Show redacted normalized JSON", app)

    def test_generated_catalogs_are_complete_and_token_free(self):
        source = (WEB / "locale-packs.js").read_text(encoding="utf-8")
        prefix = "window.SkillRuntimeLocalePacks = "
        payload = source[source.index(prefix) + len(prefix):].strip()
        self.assertTrue(payload.endswith(";"))
        catalogs = json.loads(payload[:-1])
        self.assertEqual(set(catalogs), EXPECTED_LOCALES - {"en", "zh-CN"})
        canonical = (WEB / "i18n.js").read_text(encoding="utf-8")
        dictionary = canonical[
            canonical.index("const zh = {"):canonical.index("\n  };", canonical.index("const zh = {"))
        ]
        expected_message_count = len(re.findall(r'^    "(?:[^"\\]|\\.)*": ', dictionary, re.MULTILINE))
        message_counts = {len(pack["messages"]) for pack in catalogs.values()}
        pattern_counts = {len(pack["patterns"]) for pack in catalogs.values()}
        self.assertEqual(message_counts, {expected_message_count})
        self.assertEqual(pattern_counts, {20})
        for locale, pack in catalogs.items():
            serialized = json.dumps(pack, ensure_ascii=False)
            self.assertNotRegex(serialized, r"(?:ZXQ|SRI_)")
            self.assertEqual(pack["messages"]["Language"].strip(), pack["messages"]["Language"])
            self.assertNotEqual(pack["messages"]["Runs"], "Runs", locale)
            self.assertNotEqual(pack["messages"]["Settings"], "Settings", locale)

    def test_runtime_locale_matching_includes_region_fallbacks(self):
        source = (WEB / "i18n.js").read_text(encoding="utf-8")
        for locale in EXPECTED_LOCALES:
            self.assertIn(f'"{locale}"', source)
        self.assertIn('lower.includes("hant")', source)
        self.assertIn('lower.startsWith("pt")', source)

    def test_localized_readmes_preserve_quickstart_links_and_code(self):
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        expected_fences = english.count("```")
        for locale in EXPECTED_LOCALES - {"en"}:
            path = ROOT / f"README.{locale}.md"
            self.assertTrue(path.exists(), locale)
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("```"), expected_fences, locale)
            self.assertIn("<!-- locale-switcher:start -->", text)
            self.assertIn("docs/assets/skill-run-panorama.png", text)
            self.assertIn("docs/assets/runtime-architecture.svg", text)
            self.assertIn("docs/getting-started.md", text)
            self.assertIn(".venv/bin/skill-runtime install --enable-hooks", text)
            self.assertIn("docs/experiment-driven-product-philosophy.md", text)
            self.assertIn("Inferred Analysis", text)
            self.assertNotRegex(text, r"(?:ZXQ|SRI_|TKN|TKNT|T901)")
            self.assertNotRegex(text, r"⟦L\s*\d+⟧")
            self.assertNotRegex(text, r"\]\s+\(")


if __name__ == "__main__":
    unittest.main()
