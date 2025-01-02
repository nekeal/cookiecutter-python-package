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


def test_poetry_uses_dev_group(generated_project_path):
    pyproject_toml_content = generated_project_path.joinpath(
        "pyproject.toml"
    ).read_text()

    assert "dev-dependencies" not in pyproject_toml_content
    assert "[tool.poetry.group.dev.dependencies]" in pyproject_toml_content.splitlines()


def test_python_version_is_correctly_included_in_black_config(generated_project_path):
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
           ] == ["3.9", "3.10", "3.11", "3.12", "3.13"]


def test_specific_files_and_packages_are_not_include_if_package_is_meant_to_be_not_releasable(tmp_path):
    context = EXAMPLE_CONTEXT | {"releasable": False}
    project_path = render_template(tmp_path, context)
    for filename in ["CHANGELOG.md", "release.yml", "draft_release.yml"]:
        assert filename in (project_path / ".gitignore").read_text()

    parsed_pyproject_toml = toml.loads(
        project_path.joinpath("pyproject.toml").read_text()
    )
    assert "python-kacl" not in parsed_pyproject_toml["tool"]["poetry"]["group"]["dev"]["dependencies"]
    assert "pypi" not in Path(project_path / "README.md").read_text().lower()
