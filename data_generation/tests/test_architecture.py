"""Architectural fitness: the domain layer must stay pure (Close the Context Gap, §Fitness)."""

from pytest_archon import archrule


def test_domain_layer_is_pure():
    (
        archrule("domain stays independent of technical layers")
        .match("loom_datagen.domain*")
        .should_not_import("loom_datagen.infrastructure*")
        .should_not_import("loom_datagen.validation*")
        .should_not_import("loom_datagen.application*")
        .check("loom_datagen")
    )


def test_infrastructure_does_not_import_application():
    (
        archrule("infrastructure never reaches up to orchestration")
        .match("loom_datagen.infrastructure*")
        .should_not_import("loom_datagen.application*")
        .check("loom_datagen")
    )
