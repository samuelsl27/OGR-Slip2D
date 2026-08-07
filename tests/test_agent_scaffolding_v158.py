# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Samuel Sáez López — Universidad Politécnica de Cartagena
"""
v0.1.58 — Agent scaffolding.

The repository now ships the contract an AI agent works under: AGENTS.md,
custom commands, skills, SDD templates and editor configuration.

These files are **documentation that behaves like configuration**: an
agent reads them and acts on them, so they can go stale the same way code
does — silently, and with nobody noticing until a rule stops being
followed. The tests here pin the parts that would be actively harmful if
they drifted:

* the seven rules must all still be stated, since AGENTS.md is the only
  place they live;
* the reference documentation folder must stay OUT of version control —
  it is third-party copyrighted material, and publishing it in an AGPL
  repository would be an infringement;
* CLAUDE.md must not duplicate the rules, because a rule written twice
  goes stale in one of the two copies.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


class TestAgentsFile:
    def test_exists_and_is_substantial(self):
        text = _read("AGENTS.md")
        assert len(text) > 4000
        # The guidance says a rules file should stay under 500 lines to
        # avoid becoming noise the agent skims past.
        assert len(text.splitlines()) < 500

    def test_states_all_seven_rules(self):
        text = _read("AGENTS.md")
        for fragment in ("validad", "tr()", "menú", "SPDX",
                         "filtran estado", "anomalías", "no hacer nada"):
            assert fragment.lower() in text.lower(), fragment

    def test_documents_the_test_command_with_offscreen(self):
        """Forgetting QT_QPA_PLATFORM is the first thing that goes wrong
        for a newcomer, human or otherwise."""
        assert "QT_QPA_PLATFORM=offscreen" in _read("AGENTS.md")

    def test_warns_against_pytest(self):
        """The runner supplies a simulated pytest; the real one is not
        installed and the test modules cannot be imported without it."""
        assert "pytest" in _read("AGENTS.md")

    def test_forbids_referencing_commercial_products(self):
        text = _read("AGENTS.md")
        assert "docs/reference/" in text
        assert "fuente científica original" in text

    def test_lists_the_stack_and_the_layout(self):
        text = _read("AGENTS.md")
        for pkg in ("ogr_core", "ogr_slip2d", "ogr_fem2d", "ogr_gui"):
            assert pkg in text


class TestClaudeMdDoesNotDuplicate:
    def test_points_at_agents_md(self):
        text = _read("CLAUDE.md")
        assert "AGENTS.md" in text

    def test_stays_short(self):
        """A rule written in two places goes stale in one of them."""
        assert len(_read("CLAUDE.md").splitlines()) < 20


class TestCommandsAndSkills:
    def test_commands_present(self):
        for name in ("test", "validar", "revisar", "release", "feature"):
            assert (_ROOT / ".claude" / "commands" / f"{name}.md").exists()

    def test_every_command_has_front_matter(self):
        for path in (_ROOT / ".claude" / "commands").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            assert text.startswith("---"), path.name
            assert "description:" in text.split("---")[1], path.name

    def test_skills_present_with_front_matter(self):
        skills = list((_ROOT / ".claude" / "skills").glob("*/SKILL.md"))
        assert len(skills) >= 3
        for path in skills:
            text = path.read_text(encoding="utf-8")
            assert "name:" in text and "description:" in text, path

    def test_validation_command_rejects_snapshots(self):
        """The command exists precisely to catch the failure mode the
        project cares most about."""
        text = _read(".claude/commands/validar.md")
        assert "instantánea" in text or "snapshot" in text


class TestSettings:
    def test_settings_is_valid_json_and_gates_the_risky_commands(self):
        data = json.loads(_read(".claude/settings.json"))
        perms = data["permissions"]
        joined = " ".join(perms.get("ask", []) + perms.get("deny", []))
        for risky in ("pip install", "git push", "rm"):
            assert risky in joined, risky

    def test_secrets_are_denied(self):
        data = json.loads(_read(".claude/settings.json"))
        assert any(".env" in rule for rule in data["permissions"]["deny"])

    def test_local_settings_are_not_versioned(self):
        """Personal paths must not land in the shared repository."""
        assert ".claude/settings.local.json" in _read(".gitignore")
        assert (_ROOT / ".claude"
                / "settings.local.json.example").exists()

    def test_mcp_config_has_no_inline_key(self):
        """An API key committed to a public repository is a leaked key."""
        text = _read(".mcp.json")
        json.loads(text)
        assert "${CONTEXT7_API_KEY}" in text
        assert "sk-" not in text


class TestReferenceFolderIsNotPublished:
    def test_gitignored(self):
        """Third-party copyrighted material: publishing it in an AGPL
        repository would be an infringement, however free the code is."""
        assert "docs/reference/" in _read(".gitignore")

    def test_readme_explains_why(self):
        text = _read("docs/reference/README.md")
        assert "gitignore" in text.lower()
        assert "opyright" in text


class TestSpecStructure:
    def test_constitution_present(self):
        for name in ("mission", "tech-stack", "roadmap"):
            assert (_ROOT / "spec" / "constitution"
                    / f"{name}.md").exists(), name

    def test_feature_template_present(self):
        base = _ROOT / "spec" / "features" / "000-plantilla"
        for name in ("spec", "plan", "tasks"):
            assert (base / f"{name}.md").exists(), name

    def test_template_demands_measurable_criteria(self):
        text = _read("spec/features/000-plantilla/spec.md")
        assert "Criterios de aceptación" in text
        assert "no es un criterio" in text

    def test_template_demands_a_validation_reference(self):
        assert "referencia externa" in \
            _read("spec/features/000-plantilla/spec.md")

    def test_tech_stack_records_why_not_just_what(self):
        """The reasons are what stops a decision being undone by someone
        who never learnt why it was taken."""
        text = _read("spec/constitution/tech-stack.md")
        assert "triangle" in text        # licence incompatibility
        assert "HDF5" in text            # results are recomputed
        assert "AGPL" in text


class TestEditorConfig:
    def test_vscode_settings_force_offscreen(self):
        data = json.loads(
            "\n".join(line for line in
                      _read(".vscode/settings.json").splitlines()
                      if not line.strip().startswith("//")))
        for key in ("terminal.integrated.env.linux",
                    "terminal.integrated.env.windows"):
            assert data[key]["QT_QPA_PLATFORM"] == "offscreen"

    def test_reference_folder_excluded_from_search(self):
        text = _read(".vscode/settings.json")
        assert "docs/reference" in text

    def test_recommends_the_python_and_agent_extensions(self):
        data = json.loads(_read(".vscode/extensions.json"))
        joined = " ".join(data["recommendations"])
        assert "ms-python.python" in joined
        assert "claude" in joined.lower()


class TestNamingIsConsistent:
    """v0.1.59 — the distributable package is the PROGRAM, not the suite.

    It was called `ogr-suite` while containing a single program, which
    would have collided the moment a second one appeared and, worse, made
    `pip install ogr-suite` deliver something that is not the suite.
    """

    def test_package_is_named_after_the_program(self):
        text = _read("pyproject.toml")
        assert 'name = "ogr-slip2d"' in text
        assert 'name = "ogr-suite"' not in text

    def test_about_dialog_reads_the_same_package_name(self):
        """A mismatch here made the version fall back silently."""
        assert '_pkg_version("ogr-slip2d")' in \
            _read("ogr_gui/dialogs/misc_dialogs.py")

    def test_agents_md_explains_the_two_levels(self):
        text = _read("AGENTS.md")
        assert "OpenGeoRock" in text and "OGR Slip2D" in text
        assert "ogr-slip2d" in text

    def test_no_stale_repository_urls(self):
        """The old URLs pointed at a user account that does not exist."""
        for name in ("pyproject.toml", "README.md",
                     "ogr_gui/main_window.py"):
            assert "samuelsaez/ogr-suite" not in _read(name), name


class TestValidationCaseInfrastructure:
    def test_folder_and_readme_exist(self):
        assert (_ROOT / "validacion" / "README.md").is_file()
        assert (_ROOT / "validacion" / "casos").is_dir()

    def test_template_case_present(self):
        base = _ROOT / "validacion" / "casos" / "000-plantilla"
        assert (base / "caso.md").is_file()
        assert (base / "esperado.json").is_file()

    def test_readme_separates_what_may_be_published(self):
        """The `.ogr` and the expected number are the author's; a
        third-party native file and report are not."""
        text = _read("validacion/README.md")
        assert "copyright" in text.lower()
        assert "comparación no es una validación" in text

    def test_template_forces_the_source_to_be_declared(self):
        text = _read("validacion/casos/000-plantilla/caso.md")
        assert "Fuente" in text
        assert "Tipo de referencia" in text

    def test_runner_exists_so_new_cases_need_no_code(self):
        """The friction of writing a test is what stops cases being
        added."""
        assert (_ROOT / "tests" / "test_validation_cases.py").is_file()


class TestRepositoryTidiness:
    def test_changelogs_are_not_loose_in_the_root(self):
        loose = list(_ROOT.glob("CHANGELOG_v*.md"))
        assert not loose, [p.name for p in loose]

    def test_changelogs_are_archived(self):
        archived = list((_ROOT / "docs" / "changelog").glob("CHANGELOG_v*.md"))
        assert len(archived) > 30

    def test_root_keeps_only_the_entry_documents(self):
        # README.es.md joined the list for the first public release: the
        # site and CONTRIBUTING are in English, so README.md is English and
        # the Spanish text lives beside it. Everything else that is not an
        # entry document still belongs under docs/.
        names = {p.name for p in _ROOT.glob("*.md")}
        assert names == {"README.md", "README.es.md", "AGENTS.md",
                         "CLAUDE.md", "CONTRIBUTING.md", "CONTRIBUTORS.md",
                         "CLA.md"}, names
