"""Seeded random-number factories so generation is reproducible."""

from __future__ import annotations

import numpy as np
from faker import Faker


def make_rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def make_faker(seed: int) -> Faker:
    fake = Faker("en_US")
    Faker.seed(seed)
    return fake
