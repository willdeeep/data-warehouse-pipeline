"""Load generated DataFrames into BigQuery (idempotent WRITE_TRUNCATE, explicit schema)."""
from __future__ import annotations

import pandas as pd
from google.cloud import bigquery

from .schema import SCHEMAS


def load_frames(frames: dict[str, pd.DataFrame], cfg) -> dict[str, int]:
    """Load each frame into <project>.<source_dataset>.<table>, replacing existing data."""
    client = bigquery.Client(project=cfg.project_id, location=cfg.bq_location)
    counts: dict[str, int] = {}

    for name, df in frames.items():
        table_id = f"{cfg.project_id}.{cfg.source_dataset}.{name}"
        job_config = bigquery.LoadJobConfig(
            schema=SCHEMAS[name],
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result()
        counts[name] = len(df)

    return counts
