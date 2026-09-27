import subprocess
import sys
from pathlib import Path

from pyforge.console.generator import scaffold_project


def test_scaffolded_project_pyproject_toml_is_actually_buildable(tmp_path: Path) -> None:
    """A generated project is a flat-layout application (main.py, routes/,
    config/ at the top level), not a `<project_name>/` package directory —
    hatchling can't auto-detect what to ship for that shape. Without
    `bypass-selection = true` in the generated pyproject.toml,
    `pip install .` fails for *every* freshly generated project (hatchling
    raises "Unable to determine which files to ship"), which went unnoticed
    until a real Dockerfile build was verified end-to-end. This builds the
    generated project's actual wheel metadata to prove hatchling accepts it,
    the same failure mode `pip install .` would hit inside the Dockerfile."""
    project_dir = tmp_path / "generated_app"
    scaffold_project(project_dir, project_name="generated_app")

    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(tmp_path / "dist")],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert list((tmp_path / "dist").glob("*.whl"))
