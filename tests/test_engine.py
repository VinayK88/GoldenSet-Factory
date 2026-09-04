import pandas as pd
import pytest

from engine import (
    coverage_table,
    deduplicate,
    enrich_candidates,
    generate_existing_benchmark,
    generate_feedback,
    run,
    select_golden_candidates,
    version_manifest,
)


def test_feedback_contract_and_reproducibility():
    first = generate_feedback(seed=2, n=120)
    second = generate_feedback(seed=2, n=120)
    assert first.equals(second)
    assert {"feedback_id", "observed_time", "failure_mode", "summary"}.issubset(first.columns)
    assert first["feedback_id"].is_unique
    assert first["observed_time"].is_monotonic_increasing


def test_candidate_selection_size_and_ids():
    feedback = generate_feedback(seed=3, n=900)
    benchmark = generate_existing_benchmark(seed=4, n=240)
    candidates = enrich_candidates(feedback, benchmark, seed=3)
    coverage = coverage_table(benchmark, feedback)
    selected = select_golden_candidates(candidates, coverage, target_size=80)
    assert 1 <= len(selected) <= 80
    assert selected["candidate_case_id"].is_unique


def test_similarity_threshold_changes_deduplication():
    candidates = pd.DataFrame([
        {"failure_mode": "prompt_injection", "severity": "high", "tool": "shell", "summary": "prompt injection from untrusted document using shell tool", "selection_score": .9},
        {"failure_mode": "prompt_injection", "severity": "high", "tool": "shell", "summary": "prompt injection from an untrusted document using shell command", "selection_score": .8},
        {"failure_mode": "tool_failure", "severity": "medium", "tool": "scanner", "summary": "scanner timeout during dependency scan", "selection_score": .7},
    ])
    strict = deduplicate(candidates, threshold=.99)
    broad = deduplicate(candidates, threshold=.40)
    assert len(broad) < len(strict)


def test_deduplication_threshold_is_validated():
    with pytest.raises(ValueError):
        deduplicate(pd.DataFrame(), threshold=1.1)


def test_coverage_has_all_modes():
    feedback = generate_feedback(seed=5, n=1000)
    benchmark = generate_existing_benchmark(seed=6, n=260)
    coverage = coverage_table(benchmark, feedback)
    assert len(coverage) == 10
    assert set(coverage.status).issubset({"underrepresented", "balanced", "overrepresented"})


def test_manifest_is_deterministic_and_hashed():
    *_, selected, manifest, _ = run(seed=7, n_feedback=1100, target_size=90)
    regenerated = version_manifest(generate_existing_benchmark(seed=8, n=420), selected)
    assert manifest["candidate_sha256"] == regenerated["candidate_sha256"]
    assert len(manifest["candidate_sha256"]) == 64
    assert manifest["requires_human_approval"] is True
