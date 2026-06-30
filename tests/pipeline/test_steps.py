"""The frozen step registry: shape, ordering, dependency integrity."""

from claudes_ears.pipeline.steps import (
    ORCHESTRATED_STEPS,
    STEP_BY_NAME,
    STEPS,
    InputKind,
    Phase,
)


def test_registry_has_no_duplicate_names() -> None:
    names = [s.name for s in STEPS]
    assert len(names) == len(set(names))


def test_every_dependency_references_a_known_step() -> None:
    known = set(STEP_BY_NAME)
    for step in STEPS:
        assert set(step.depends_on) <= known, step.name


def test_dependencies_precede_dependents_in_order() -> None:
    """A step's deps must appear earlier in the ordered registry."""
    seen: set[str] = set()
    for step in STEPS:
        assert set(step.depends_on) <= seen, f"{step.name} depends on a later step"
        seen.add(step.name)


def test_twenty_one_orchestrated_steps() -> None:
    assert len(ORCHESTRATED_STEPS) == 21
    # The three standalone library/pair tools are excluded.
    assert {s.name for s in STEPS} - {s.name for s in ORCHESTRATED_STEPS} == {
        "genome_map",
        "temporal_genome",
        "version_compare",
    }


def test_separation_is_first_and_required() -> None:
    first = STEPS[0]
    assert first.name == "separation"
    assert first.phase is Phase.SEPARATION
    assert first.optional is False


def test_derived_steps_consume_upstream_dicts() -> None:
    for name in ("music_theory", "harmonic_rhythm", "emotional_trajectory"):
        assert STEP_BY_NAME[name].input is InputKind.UPSTREAM
        assert STEP_BY_NAME[name].depends_on
