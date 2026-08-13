import pytest
from loom_datagen.application.build import build_all
from loom_datagen.infrastructure.config import DatagenConfig


@pytest.fixture(scope="session")
def cfg():
    return DatagenConfig(
        project_id="test-project",
        n_products=50,
        n_users=200,
        start_date="2024-01-01",
        end_date="2024-03-31",
        avg_sessions_per_day=30,
    )


@pytest.fixture(scope="session")
def frames(cfg):
    return build_all(cfg)
