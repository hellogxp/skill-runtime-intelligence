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
        self.assertNotIn('src="locale-packs.js', html)
        self.assertLess(
            html.index('src="i18n.js'),
            html.index('src="app.js'),
        )

    def test_product_assets_and_api_support_path_prefixed_deployments(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        for asset in (
            'href="favicon.svg',
            'href="styles.css',
            'href="runtime-detail-v2.css',
            'src="i18n.js',
            'src="app.js',
        ):
            self.assertIn(asset, html)
        i18n = (WEB / "i18n.js").read_text(encoding="utf-8")
        self.assertIn('script.src = "locale-packs.js', i18n)
        self.assertIn('const appBaseUrl = new URL("./", window.location.href);', app)
        self.assertIn("fetch(endpointUrl(path)", app)
        self.assertIn("new EventSource(endpointUrl(", app)
        self.assertIn("const isRemoteViewer = !new Set", app)
        self.assertIn("Boolean(deployment.viewer_read_only) || isRemoteViewer", app)

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

    def test_run_assessment_separates_expectation_from_evidence_coverage(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        for control_id in (
            "assessment-verdict",
            "assessment-title",
            "assessment-summary",
            "diagnosis-counts",
            "diagnosis-attention",
            "diagnosis-limits",
            "diagnosis-facts",
            "diagnosis-reasoning-steps",
            "behavior-counts",
            "behavior-list",
            "behavior-limitation",
            "assessment-checks",
            "assessment-discipline",
        ):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn("Expected evidence", html)
        self.assertIn("Actually observed", html)
        self.assertIn("Attribution is association, not causality.", html)
        self.assertIn("function renderAssessment(run)", app)
        self.assertIn("function diagnosisReasoningStep", app)
        self.assertIn("function renderDiagnosisList", app)
        self.assertIn("Evidence coverage is not a pass score", app)

    def test_runtime_overview_keeps_unobserved_stages_neutral(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn("Skill runtime overview", html)
        self.assertIn("A stage may be optional or outside adapter coverage", html)
        self.assertIn("Only explicit failures, incomplete runs", html)
        self.assertIn('run.result_type === "explicit_failure"', app)
        self.assertNotIn("run.first_gap && run.first_gap !== systemicBoundary", app)
        self.assertIn("runSummary.stage_counts", app)
        self.assertIn("runSummary.stage_supported_totals", app)
        self.assertIn("Current sources do not provide this signal", app)
        self.assertIn("Information collected at each stage", html)
        self.assertIn("not success", html)
        self.assertIn('id="result-composition"', html)
        self.assertNotIn("Average evidence coverage", app)
        self.assertLess(
            html.index('class="panel overview-boundaries"'),
            html.index('class="panel attention-panel overview-attention-wide"'),
        )

    def test_run_activity_summary_exposes_concrete_objects(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="activity-summary"', html)
        self.assertIn('id="activity-discipline"', html)
        self.assertIn("Concrete objects, not just event counts", html)
        self.assertIn("function renderActivitySummary(run)", app)
        self.assertIn("function inspectActivityEntry(entry, run)", app)

    def test_slow_integration_probe_is_not_on_the_initial_render_path(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        initial_load = app[
            app.index("async function loadIndex"):
            app.index("function ensureSkillsData")
        ]
        settings_load = app[
            app.index("function ensureSettingsData"):
            app.index("function sourceModeLabel")
        ]
        self.assertNotIn('/api/integrations', initial_load)
        self.assertIn('getJSON("/api/integrations")', settings_load)
        self.assertIn("ensureSettingsData().catch", app)

    def test_compare_control_reveals_a_nearby_accessible_panel(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        app = (WEB / "app.js").read_text(encoding="utf-8")
        styles = (WEB / "styles.css").read_text(encoding="utf-8")
        toggle = re.search(
            r'<button\s+id="compare-toggle".*?</button>', html, re.DOTALL
        ).group(0)
        panel = re.search(
            r'<section\s+id="compare-panel".*?</section>', html, re.DOTALL
        ).group(0)

        self.assertIn('aria-controls="compare-panel"', toggle)
        self.assertIn('aria-expanded="false"', toggle)
        self.assertIn('aria-hidden="true"', panel)
        self.assertIn('tabindex="-1"', panel)
        self.assertLess(
            html.index('id="compare-panel"'),
            html.index('class="panel assessment-panel"'),
        )
        self.assertIn("function setComparePanelOpen(open)", app)
        self.assertIn('panel.scrollIntoView({', app)
        self.assertIn('button.setAttribute("aria-expanded", String(open))', app)
        self.assertIn('.compare-toggle[aria-expanded="true"]', styles)

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
            self.assertIn("docs/assets/sri-runtime-overview-cn.png", text)
            self.assertIn("docs/assets/runtime-architecture.svg", text)
            self.assertIn("docs/getting-started.md", text)
            self.assertIn(".venv/bin/skill-runtime install --enable-hooks", text)
            self.assertIn("docs/experiment-results-2026-07-29.md", text)
            self.assertIn("Inferred Analysis", text)
            self.assertNotRegex(text, r"(?:ZXQ|SRI_|TKN|TKNT|T901)")
            self.assertNotRegex(text, r"⟦L\s*\d+⟧")
            self.assertNotRegex(text, r"[⟦⟧⧦]")
            self.assertNotRegex(text, r"\]\s+\(")


if __name__ == "__main__":
    unittest.main()
