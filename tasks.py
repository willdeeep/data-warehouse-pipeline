"""Project task runner (pyinvoke) — run ``uv run invoke --list`` to see all tasks.

Wraps the commands that need consistent env so a single word does the right thing. ``.env`` is
auto-loaded with the same semantics as ``set -a && source .env && set +a`` — including
``DBT_PROFILES_DIR``/``DBT_PROJECT_DIR`` (local ``pipeline/dbt`` paths; the container overrides them
in ``pipeline/docker-compose.yaml``) — so dbt resolves the project/profiles with no CLI flags, and
never silently reads an empty dataset from an unsourced ``.env``.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from invoke import task

ROOT = Path(__file__).parent
ENV_FILE = ROOT / ".env"
# The eBay competitor seed is excluded from `build` to avoid the seed/source race
# (seed it explicitly with `invoke seed` or `invoke refresh`).
EBAY_SEED = "transformed_competitor_data"


def _run(args: list[str]) -> None:
    """Run *args* from the repo root with ``.env`` auto-loaded; stream output, raise on failure."""
    env_file = shlex.quote(str(ENV_FILE))
    prefix = f"set -a; [ -f {env_file} ] && . {env_file}; set +a; "
    subprocess.run(["bash", "-c", prefix + shlex.join(args)], cwd=ROOT, check=True)


@task(help={"full_refresh": "Fully rebuild the seed (drop + recreate)."})
def seed(c, full_refresh=False):
    """dbt seed — load the eBay competitor seed into the warehouse dataset."""
    _run(["dbt", "seed", *(["--full-refresh"] if full_refresh else [])])


@task(help={"full_refresh": "Fully rebuild all models (drop + recreate)."})
def build(c, full_refresh=False):
    """dbt build — run models + tests (excludes the eBay seed to avoid the seed/source race)."""
    flags = ["--full-refresh"] if full_refresh else []
    _run(["dbt", "build", *flags, "--exclude", EBAY_SEED])


@task(help={"select": "dbt --select node selector (e.g. 'core' or 'rpt_transactions+')."})
def run(c, select=None):
    """dbt run — build models only (no tests)."""
    _run(["dbt", "run", *(["--select", select] if select else [])])


@task
def test(c):
    """dbt test — run all data tests."""
    _run(["dbt", "test"])


@task
def parse(c):
    """dbt parse — offline manifest/compile check (no warehouse connection)."""
    _run(["dbt", "parse"])


@task
def refresh(c):
    """Canonical green-build recipe: dbt seed then dbt build, both --full-refresh."""
    seed(c, full_refresh=True)
    build(c, full_refresh=True)


@task(name="build-container")
def build_container(c):
    """Build the pipeline container image(s) via docker compose."""
    _run(["docker", "compose", "-f", "pipeline/docker-compose.yaml", "build"])
