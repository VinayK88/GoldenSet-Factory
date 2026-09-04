from engine import generate_feedback, generate_existing_benchmark, enrich_candidates, coverage_table, select_golden_candidates, run

def test_candidate_selection_size():
    feedback=generate_feedback(seed=3,n=900);benchmark=generate_existing_benchmark(seed=4,n=240);candidates=enrich_candidates(feedback,benchmark,seed=3);coverage=coverage_table(benchmark,feedback);selected=select_golden_candidates(candidates,coverage,target_size=80);assert 50 <= len(selected) <= 80;assert selected["candidate_case_id"].is_unique

def test_coverage_has_all_modes():
    feedback=generate_feedback(seed=5,n=1000);benchmark=generate_existing_benchmark(seed=6,n=260);coverage=coverage_table(benchmark,feedback);assert len(coverage)==10;assert set(coverage.status).issubset({"underrepresented","balanced","overrepresented"})

def test_run_boundaries():
    *_,manifest,metrics=run(seed=7,n_feedback=1100,target_size=90);assert manifest["requires_human_approval"] is True;assert metrics["Auto-promotion enabled"]=="No";assert metrics["Synthetic feedback"]=="Yes"
