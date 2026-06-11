"""Tests for TemplateRegistry — template loading, search, and YAML parsing."""

from pathlib import Path

import pytest

from app.skill.template_registry import TemplateRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill_md(path: Path, name: str, description: str = "",
                   domains: list = None) -> Path:
    """Create a template directory with a SKILL.md file."""
    template_dir = path / name
    template_dir.mkdir(parents=True, exist_ok=True)

    domains_str = ""
    if domains:
        domains_lines = "\n".join(
            f"    - {{domain: {d}}}" for d in domains
        )
        domains_str = f"domains:\n{domains_lines}"

    content = f"""---
name: {name}
description: "{description}"
version: 1.0.0
{domains_str}
---
"""
    skill_md = template_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    return skill_md


def _make_main_py(template_dir: Path) -> Path:
    """Create a main.py inside a template directory."""
    main_py = template_dir / "main.py"
    main_py.write_text("print('hello')", encoding="utf-8")
    return main_py


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_with_custom_paths(self, tmp_path):
        """Custom paths are used instead of defaults."""
        (tmp_path / "custom").mkdir()
        reg = TemplateRegistry(paths=[tmp_path / "custom"])

        assert reg.paths == [tmp_path / "custom"]

    def test_load_all_empty_paths(self, tmp_path):
        """No templates when paths are empty."""
        p = tmp_path / "empty"
        p.mkdir()
        reg = TemplateRegistry(paths=[p])

        assert reg.templates == {}


# ---------------------------------------------------------------------------
# find_similar
# ---------------------------------------------------------------------------

class TestFindSimilar:
    def test_find_similar_no_match(self, tmp_path):
        """No keyword overlap → []."""
        _make_skill_md(tmp_path, "weather", description="weather forecast tools")
        reg = TemplateRegistry(paths=[tmp_path])

        results = reg.find_similar("completely unrelated topic")

        assert results == []

    def test_find_similar_with_match(self, tmp_path):
        """Keyword overlap > 2 → ordered results."""
        _make_skill_md(tmp_path, "weather", description="weather forecast tools")
        _make_skill_md(tmp_path, "climate", description="climate and weather analysis")
        reg = TemplateRegistry(paths=[tmp_path])

        results = reg.find_similar("weather forecast climate analysis")

        assert len(results) >= 1
        # First result should have highest overlap
        assert results[0]["overlap"] >= results[-1]["overlap"]


# ---------------------------------------------------------------------------
# find_by_domain
# ---------------------------------------------------------------------------

class TestFindByDomain:
    def test_find_by_domain(self, tmp_path):
        """Match by domain."""
        _make_skill_md(tmp_path, "light-skill", description="Light control",
                       domains=["lighting"])
        _make_skill_md(tmp_path, "temp-skill", description="Temperature control",
                       domains=["climate"])
        reg = TemplateRegistry(paths=[tmp_path])

        results = reg.find_by_domain("lighting")

        assert len(results) == 1
        assert results[0]["template"] == "light-skill"

    def test_find_by_domain_no_match(self, tmp_path):
        """No template matches domain → []."""
        _make_skill_md(tmp_path, "test", description="Something",
                       domains=["other"])
        reg = TemplateRegistry(paths=[tmp_path])

        assert reg.find_by_domain("lighting") == []


# ---------------------------------------------------------------------------
# get_template_code
# ---------------------------------------------------------------------------

class TestGetTemplateCode:
    def test_get_template_code_missing(self, tmp_path):
        """Template not found → None."""
        reg = TemplateRegistry(paths=[tmp_path])
        assert reg.get_template_code("nonexistent") is None

    def test_get_template_code_present(self, tmp_path):
        """Existing main.py → its content."""
        template_dir = tmp_path / "mytemplate"
        template_dir.mkdir()
        _make_skill_md(tmp_path, "mytemplate", description="test")
        _make_main_py(template_dir)
        reg = TemplateRegistry(paths=[tmp_path])

        code = reg.get_template_code("mytemplate")

        assert code == "print('hello')"

    def test_get_template_code_no_main_py(self, tmp_path):
        """Template exists but no main.py → None."""
        _make_skill_md(tmp_path, "empty-template", description="no code")
        reg = TemplateRegistry(paths=[tmp_path])

        assert reg.get_template_code("empty-template") is None


# ---------------------------------------------------------------------------
# _extract_summary
# ---------------------------------------------------------------------------

class TestExtractSummary:
    def test_extract_summary(self, tmp_path):
        """Parse description from YAML frontmatter."""
        reg = TemplateRegistry(paths=[tmp_path])
        content = '---\ndescription: "My test template"\n---\n'
        assert reg._extract_summary(content) == "My test template"

    def test_extract_summary_no_frontmatter(self):
        """No YAML frontmatter → empty string."""
        reg = TemplateRegistry(paths=[])
        assert reg._extract_summary("no frontmatter here") == ""

    def test_extract_summary_no_description(self):
        """Frontmatter without description → empty string."""
        reg = TemplateRegistry(paths=[])
        content = "---\nname: foo\nversion: 1.0\n---"
        assert reg._extract_summary(content) == ""


# ---------------------------------------------------------------------------
# _extract_domains
# ---------------------------------------------------------------------------

class TestExtractDomains:
    def test_extract_domains(self):
        """Parse domains list from YAML frontmatter."""
        reg = TemplateRegistry(paths=[])
        content = """---
domains:
  - {domain: lighting}
  - {domain: climate}
---
"""
        assert reg._extract_domains(content) == ["lighting", "climate"]

    def test_extract_domains_no_frontmatter(self):
        """No YAML frontmatter → []."""
        reg = TemplateRegistry(paths=[])
        assert reg._extract_domains("plain text") == []

    def test_extract_domains_no_domains_key(self):
        """Frontmatter without domains key → []."""
        reg = TemplateRegistry(paths=[])
        content = "---\nname: foo\n---"
        assert reg._extract_domains(content) == []
