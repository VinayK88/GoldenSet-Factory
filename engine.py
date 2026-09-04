from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FAILURE_MODES = [
    "prompt_injection", "tool_failure", "partial_recovery", "privilege_boundary",
    "provenance_gap", "unsafe_remediation", "hard_negative", "ownership_mismatch",
    "dependency_conflict", "escalation_error",
]
SEVERITIES = ["low", "medium", "high", "critical"]


def generate_feedback(seed: int = 42, n: int = 2500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    modes = rng.choice(FAILURE_MODES, n, p=[.14, .12, .09, .10, .08, .10, .11, .08, .09, .09])
    severity = rng.choice(SEVERITIES, n, p=[.16, .36, .33, .15])
    source = rng.choice(
        ["human_override", "incident", "rollback", "escaped_defect", "customer_signal"],
        n,
        p=[.30, .15, .14, .23, .18],
    )
    tool = rng.choice(["repo_search", "patch", "scanner", "policy_check", "ticket", "shell"], n)
    recoverable = rng.binomial(1, .64, n)
    observed_time = pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC")
    summaries = [
        f"{m.replace('_', ' ')} severity {s} from {src.replace('_', ' ')} using {t}; "
        f"recovery {r}; pattern variant {rng.integers(1, 7)}"
        for m, s, src, t, r in zip(modes, severity, source, tool, recoverable)
    ]
    return pd.DataFrame({
        "feedback_id": [f"fb_{i:06d}" for i in range(n)],
        "observed_time": observed_time,
        "failure_mode": modes,
        "severity": severity,
        "source": source,
        "tool": tool,
        "recoverable": recoverable,
        "summary": summaries,
    })


def generate_existing_benchmark(seed: int = 11, n: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    probabilities = np.array([.17, .05, .03, .13, .10, .10, .15, .09, .08, .10])
    probabilities = probabilities / probabilities.sum()
    modes = rng.choice(FAILURE_MODES, n, p=probabilities)
    severity = rng.choice(SEVERITIES, n, p=[.20, .40, .30, .10])
    rows = []
    for i, (mode, level) in enumerate(zip(modes, severity)):
        rows.append({
            "case_id": f"gold_v1_{i:05d}",
            "failure_mode": mode,
            "severity": level,
            "summary": (
                f"{mode.replace('_', ' ')} benchmark case severity {level} "
                f"reference variant {rng.integers(1, 8)}"
            ),
        })
    return pd.DataFrame(rows)


def vectorize(feedback: pd.DataFrame, benchmark: pd.DataFrame):
    corpus = pd.concat([feedback["summary"], benchmark["summary"]], ignore_index=True)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=1200)
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix[:len(feedback)], matrix[len(feedback):]


def enrich_candidates(feedback: pd.DataFrame, benchmark: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    _, feedback_matrix, benchmark_matrix = vectorize(feedback, benchmark)
    cluster_count = min(12, max(4, int(np.sqrt(len(feedback) / 20))))
    clusters = KMeans(n_clusters=cluster_count, random_state=seed, n_init=10).fit_predict(feedback_matrix)
    maximum_similarity = cosine_similarity(feedback_matrix, benchmark_matrix).max(axis=1)
    novelty = 1 - maximum_similarity
    counts = pd.Series(clusters).value_counts()
    rarity = np.array([1 / max(counts[c], 1) for c in clusters])
    rarity = rarity / max(float(rarity.max()), 1.0)
    severity_score = feedback.severity.map({"low": .15, "medium": .4, "high": .72, "critical": 1.0}).to_numpy()
    source_score = feedback.source.map({
        "human_override": .55, "incident": 1.0, "rollback": .9,
        "escaped_defect": .95, "customer_signal": .7,
    }).to_numpy()
    difficulty = np.clip(
        .34 * novelty + .28 * severity_score + .22 * source_score
        + .16 * (1 - feedback.recoverable.to_numpy()),
        0,
        1,
    )
    output = feedback.copy()
    output["cluster"] = clusters
    output["novelty_score"] = novelty
    output["difficulty_score"] = difficulty
    output["selection_score"] = .48 * difficulty + .37 * novelty + .15 * rarity

    # TruncatedSVD operates directly on sparse TF-IDF data and avoids a dense
    # production-memory spike from calling toarray().
    coordinates = TruncatedSVD(n_components=2, random_state=seed).fit_transform(feedback_matrix)
    output["x"], output["y"] = coordinates[:, 0], coordinates[:, 1]
    return output


def coverage_table(benchmark: pd.DataFrame, feedback: pd.DataFrame) -> pd.DataFrame:
    benchmark_share = benchmark.failure_mode.value_counts(normalize=True)
    feedback_share = feedback.failure_mode.value_counts(normalize=True)
    rows = []
    for mode in FAILURE_MODES:
        b = float(benchmark_share.get(mode, 0))
        p = float(feedback_share.get(mode, 0))
        ratio = b / max(p, 1e-9)
        rows.append({
            "failure_mode": mode,
            "benchmark_share": b,
            "feedback_share": p,
            "coverage_ratio": ratio,
            "gap": max(0, p - b),
            "status": "underrepresented" if ratio < .70 else ("overrepresented" if ratio > 1.45 else "balanced"),
        })
    return pd.DataFrame(rows).sort_values("coverage_ratio")


def deduplicate(candidates: pd.DataFrame, threshold: float = .92) -> pd.DataFrame:
    """Keep high-value candidates while removing near duplicates within a mode/tool pair."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    ordered = candidates.sort_values("selection_score", ascending=False).copy()
    if ordered.empty:
        return ordered

    matrix = TfidfVectorizer(ngram_range=(1, 2), min_df=1).fit_transform(ordered["summary"].fillna(""))
    keep_positions: list[int] = []
    for position, (_, row) in enumerate(ordered.iterrows()):
        comparable = [
            kept for kept in keep_positions
            if ordered.iloc[kept]["failure_mode"] == row["failure_mode"]
            and ordered.iloc[kept].get("tool") == row.get("tool")
        ]
        if comparable:
            similarity = float(cosine_similarity(matrix[position], matrix[comparable]).max())
            if similarity >= threshold:
                continue
        keep_positions.append(position)
    return ordered.iloc[keep_positions].copy()


def select_golden_candidates(
    candidates: pd.DataFrame,
    coverage: pd.DataFrame,
    target_size: int = 120,
    dedupe_threshold: float = .92,
) -> pd.DataFrame:
    deduplicated = deduplicate(candidates, threshold=dedupe_threshold)
    underrepresented = set(coverage.loc[coverage.status.eq("underrepresented"), "failure_mode"])
    deduplicated["coverage_bonus"] = deduplicated.failure_mode.isin(underrepresented).astype(float) * .22
    deduplicated["final_score"] = deduplicated.selection_score + deduplicated.coverage_bonus

    chosen = []
    per_mode = max(3, target_size // (len(FAILURE_MODES) * 3))
    for mode in FAILURE_MODES:
        chosen.extend(
            deduplicated[deduplicated.failure_mode.eq(mode)]
            .nlargest(per_mode, "final_score")
            .index.tolist()
        )
    unique = list(dict.fromkeys(chosen))
    remaining_slots = max(0, target_size - len(unique))
    remaining = (
        deduplicated.drop(index=unique, errors="ignore")
        .nlargest(remaining_slots, "final_score")
        .index.tolist()
    )
    selected = deduplicated.loc[list(dict.fromkeys(unique + remaining))[:target_size]]
    selected = selected.sort_values("final_score", ascending=False).copy()
    selected["candidate_case_id"] = [f"candidate_{i:04d}" for i in range(len(selected))]
    return selected


def _selection_sha256(selected: pd.DataFrame) -> str:
    columns = ["candidate_case_id", "feedback_id", "failure_mode", "severity", "source", "tool"]
    stable = selected[columns].sort_values("candidate_case_id").to_csv(index=False)
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def version_manifest(existing: pd.DataFrame, selected: pd.DataFrame, version: str = "v1.1") -> dict:
    return {
        "schema_version": 1,
        "version": version,
        "base_cases": int(len(existing)),
        "candidate_additions": int(len(selected)),
        "resulting_size": int(len(existing) + len(selected)),
        "failure_modes_added": selected.failure_mode.value_counts().to_dict(),
        "candidate_sha256": _selection_sha256(selected),
        "requires_human_approval": True,
        "source": "synthetic production-style feedback",
        "evaluation_boundary": "Synthetic benchmark-lifecycle evidence only; no automatic promotion.",
    }


def run(seed: int = 42, n_feedback: int = 2500, target_size: int = 120):
    feedback = generate_feedback(seed, n_feedback)
    benchmark = generate_existing_benchmark(seed + 1, 420)
    candidates = enrich_candidates(feedback, benchmark, seed)
    coverage = coverage_table(benchmark, feedback)
    selected = select_golden_candidates(candidates, coverage, target_size)
    manifest = version_manifest(benchmark, selected)
    metrics = {
        "Feedback items": int(len(feedback)),
        "Current benchmark cases": int(len(benchmark)),
        "Failure modes": len(FAILURE_MODES),
        "Clusters discovered": int(candidates.cluster.nunique()),
        "Underrepresented modes": int((coverage.status == "underrepresented").sum()),
        "Candidate additions": int(len(selected)),
        "Critical candidates": int((selected.severity == "critical").sum()),
        "Mean novelty": float(selected.novelty_score.mean()),
        "Mean difficulty": float(selected.difficulty_score.mean()),
        "Resulting version size": manifest["resulting_size"],
        "Candidate SHA-256": manifest["candidate_sha256"],
        "Human approval required": "Yes",
        "Auto-promotion enabled": "No",
        "Synthetic feedback": "Yes",
    }
    return feedback, benchmark, candidates, coverage, selected, manifest, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="GoldenSet Factory benchmark lifecycle runner")
    parser.add_argument("--out", default="artifacts")
    parser.add_argument("--feedback", type=int, default=2500)
    parser.add_argument("--target", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    feedback, benchmark, candidates, coverage, selected, manifest, metrics = run(
        args.seed, args.feedback, args.target
    )
    coverage.to_csv(output / "coverage.csv", index=False)
    selected.to_csv(output / "candidate_cases.csv", index=False)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    pd.Series(metrics).to_json(output / "metrics.json", indent=2)
    print(pd.Series(metrics).to_string())


if __name__ == "__main__":
    main()
