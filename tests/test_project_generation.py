import subprocess
from typing import Any

import pytest
import toml
import yaml
from pathlib import Path

from cookiecutter.main import cookiecutter

TEMPLATE_DIR = str(Path(__file__).parent.parent)
CONTEXT_FILE = Path(__file__).parent / "context.yaml"

with open(CONTEXT_FILE) as file_handler:
    content = yaml.safe_load(file_handler)

EXAMPLE_CONTEXT = content["default_context"]
PROJECT_NAME = EXAMPLE_CONTEXT["project_name"]


def render_template(output_path: Path, context: dict[str, Any]) -> Path:
    return Path(
        cookiecutter(
            TEMPLATE_DIR,
            no_input=True,
            extra_context=context,
            output_dir=output_path,
        ))


@pytest.fixture
def generated_project_path(tmp_path) -> Path:
    """
    :return: path to newly generated project
    """
    return render_template(tmp_path, EXAMPLE_CONTEXT)

def test_generate_new_project(tmp_path, generated_project_path):
    assert generated_project_path == tmp_path / PROJECT_NAME


def test_uses_hatchling_build_system(generated_project_path):
    pyproject_toml_content = generated_project_path.joinpath(
        "pyproject.toml"
    ).read_text()

    assert '[build-system]' in pyproject_toml_content
    assert 'hatchling' in pyproject_toml_content
    assert 'poetry' not in pyproject_toml_content


def test_uses_dependency_groups(generated_project_path):
    pyproject_toml_content = generated_project_path.joinpath(
        "pyproject.toml"
    ).read_text()

    assert '[dependency-groups]' in pyproject_toml_content
    assert 'pyrefly' in pyproject_toml_content
    assert 'prek' in pyproject_toml_content


def test_python_version_is_correctly_included_in_ruff_config(generated_project_path):
    parsed_pyproject_toml = toml.loads(
        generated_project_path.joinpath("pyproject.toml").read_text()
    )

    assert parsed_pyproject_toml["tool"]["ruff"]["target-version"] == "py39"


# for gh test workflow
def test_python_version_is_correctly_included_in_github_workflow(
        generated_project_path,
):
    parsed_github_workflow = yaml.safe_load(
        generated_project_path.joinpath(".github/workflows/test.yml").read_text()
    )

    assert parsed_github_workflow["jobs"]["test"]["strategy"]["matrix"][
               "python-version"
           ] == ["3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]


def test_specific_files_and_packages_are_not_include_if_package_is_meant_to_be_not_releasable(tmp_path):
    context = EXAMPLE_CONTEXT | {"releasable": False}
    project_path = render_template(tmp_path, context)
    for filename in ["CHANGELOG.md", "release.yml", "draft_release.yml"]:
        assert filename in (project_path / ".gitignore").read_text()

    parsed_pyproject_toml = toml.loads(
        project_path.joinpath("pyproject.toml").read_text()
    )
    dev_deps = parsed_pyproject_toml.get("dependency-groups", {}).get("dev", [])
    assert "python-kacl" not in dev_deps
    assert "pypi" not in Path(project_path / "README.md").read_text().lower()


def test_dependencies_can_be_installed(generated_project_path):
    """Verify that all dependencies in the generated project can be installed with uv sync."""
    result = subprocess.run(
        ["uv", "sync"],
        cwd=generated_project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"uv sync failed: {result.stderr}"


def test_precommit_hooks_pass(generated_project_path):
    """Verify that all pre-commit hooks pass on the generated project."""
    subprocess.run(
        ["git", "init"],
        cwd=generated_project_path,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=generated_project_path,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["uv", "run", "prek", "run", "--all-files"],
        cwd=generated_project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"prek run failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
