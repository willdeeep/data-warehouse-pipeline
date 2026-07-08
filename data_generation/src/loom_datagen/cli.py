"""CLI: `loom-datagen generate|validate`."""

from __future__ import annotations

import os
from pathlib import Path

import typer
import yaml

from .build import build_all
from .config import DatagenConfig

app = typer.Typer(help="Generate synthetic Loom source data and load it into BigQuery.")

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.yaml"


def _scale_overrides(scale: str) -> dict:
    if not _CONFIG_PATH.exists():
        return {}
    presets = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
    if scale not in presets:
        raise typer.BadParameter(f"unknown scale '{scale}'; choose from {list(presets)}")
    return presets[scale]


def _config(scale: str, *, allow_missing_project: bool = False) -> DatagenConfig:
    if allow_missing_project:
        os.environ.setdefault("LOOM_PROJECT_ID", "dry-run-project")
    return DatagenConfig(**_scale_overrides(scale))


@app.command()
def generate(scale: str = "small", dry_run: bool = False):
    """Build all source tables and (unless --dry-run) load them into BigQuery."""
    cfg = _config(scale, allow_missing_project=dry_run)
    frames = build_all(cfg)

    if dry_run:
        for name, df in frames.items():
            typer.echo(f"{name}: {len(df)} rows")
        raise typer.Exit()

    from .loader import load_frames

    counts = load_frames(frames, cfg)
    typer.echo(f"Loaded into {cfg.project_id}.{cfg.source_dataset}: {counts}")


@app.command()
def validate(scale: str = "small"):
    """Query BigQuery to confirm the loaded data honours integrity + accepted values."""
    from .validate import validate_bigquery

    report = validate_bigquery(_config(scale))
    typer.echo(report)
    if report["orphans"] or report["violations"]:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
