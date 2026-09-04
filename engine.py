from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FAILURE_MODES = [
    "prompt_injection", "tool_failure", "partial_recovery", "privilege_boundary",
    "provenance_gap", "unsafe_remediation", "hard_negative", "ownership_mismatch",
    "dependency_conflict", "escalation_error"
]
SEVERITIES = ["low","medium","high","critical"]

def generate_feedback(seed=42,n=2500):
    rng=np.random.default_rng(seed)
    modes=rng.choice(FAILURE_MODES,n,p=[.14,.12,.09,.10,.08,.10,.11,.08,.09,.09])
    severity=rng.choice(SEVERITIES,n,p=[.16,.36,.33,.15])
    source=rng.choice(["human_override","incident","rollback","escaped_defect","customer_signal"],n,p=[.30,.15,.14,.23,.18])
    tool=rng.choice(["repo_search","patch","scanner","policy_check","ticket","shell"],n)
    recoverable=rng.binomial(1,.64,n)
    noisy=[]
    for i,(m,s,src,t,r) in enumerate(zip(modes,severity,source,tool,recoverable)):
        variant=rng.integers(1,7)
        noisy.append(f"{m.replace('_',' ')} severity {s} from {src.replace('_',' ')} using {t}; recovery {r}; pattern variant {variant}")
    return pd.DataFrame({
        "feedback_id":[f"fb_{i:06d}" for i in range(n)],
        "failure_mode":modes,"severity":severity,"source":source,"tool":tool,
        "recoverable":recoverable,"summary":noisy
    })

def generate_existing_benchmark(seed=11,n=420):
    rng=np.random.default_rng(seed)
    p=np.array([.17,.05,.03,.13,.10,.10,.15,.09,.08,.10]);p=p/p.sum()
    modes=rng.choice(FAILURE_MODES,n,p=p)
    severity=rng.choice(SEVERITIES,n,p=[.20,.40,.30,.10])
    rows=[]
    for i,(m,s) in enumerate(zip(modes,severity)):
        rows.append({"case_id":f"gold_v1_{i:05d}","failure_mode":m,"severity":s,"summary":f"{m.replace('_',' ')} benchmark case severity {s} reference variant {rng.integers(1,8)}"})
    return pd.DataFrame(rows)

def vectorize(feedback,benchmark):
    corpus=pd.concat([feedback["summary"],benchmark["summary"]],ignore_index=True)
    vec=TfidfVectorizer(ngram_range=(1,2),min_df=2,max_features=1200)
    X=vec.fit_transform(corpus)
    return vec,X[:len(feedback)],X[len(feedback):]

def enrich_candidates(feedback,benchmark,seed=42):
    vec,Xf,Xb=vectorize(feedback,benchmark)
    k=min(12,max(4,int(np.sqrt(len(feedback)/20))))
    km=KMeans(n_clusters=k,random_state=seed,n_init=10)
    cluster=km.fit_predict(Xf)
    sim=cosine_similarity(Xf,Xb);max_sim=sim.max(axis=1);novelty=1-max_sim
    counts=pd.Series(cluster).value_counts();rarity=np.array([1/max(counts[c],1) for c in cluster]);rarity=rarity/(rarity.max() or 1)
    sev_map={"low":.15,"medium":.4,"high":.72,"critical":1.0}
    severity_score=feedback.severity.map(sev_map).to_numpy()
    source_score=feedback.source.map({"human_override":.55,"incident":1.0,"rollback":.9,"escaped_defect":.95,"customer_signal":.7}).to_numpy()
    difficulty=np.clip(.34*novelty+.28*severity_score+.22*source_score+.16*(1-feedback.recoverable.to_numpy()),0,1)
    out=feedback.copy();out["cluster"]=cluster;out["novelty_score"]=novelty;out["difficulty_score"]=difficulty;out["selection_score"]=.48*difficulty+.37*novelty+.15*rarity
    pca=PCA(n_components=2,random_state=seed);coords=pca.fit_transform(Xf.toarray());out["x"]=coords[:,0];out["y"]=coords[:,1]
    return out

def coverage_table(benchmark,feedback):
    bench=benchmark.failure_mode.value_counts(normalize=True);prod=feedback.failure_mode.value_counts(normalize=True);rows=[]
    for mode in FAILURE_MODES:
        b=float(bench.get(mode,0));p=float(prod.get(mode,0));ratio=b/max(p,1e-9)
        rows.append({"failure_mode":mode,"benchmark_share":b,"feedback_share":p,"coverage_ratio":ratio,"gap":max(0,p-b),"status":"underrepresented" if ratio<.70 else ("overrepresented" if ratio>1.45 else "balanced")})
    return pd.DataFrame(rows).sort_values("coverage_ratio")

def deduplicate(candidates,threshold=.92):
    d=candidates.sort_values("selection_score",ascending=False).copy();seen=set();keep=[]
    for idx,row in d.iterrows():
        sig=f"{row.failure_mode}|{row.severity}|{row.tool}|{row.summary.split('variant')[0].strip()}";h=hashlib.sha1(sig.encode()).hexdigest()
        if h not in seen:seen.add(h);keep.append(idx)
    return d.loc[keep].copy()

def select_golden_candidates(candidates,coverage,target_size=120):
    dedup=deduplicate(candidates);under=set(coverage.loc[coverage.status.eq("underrepresented"),"failure_mode"]);dedup["coverage_bonus"]=dedup.failure_mode.isin(under).astype(float)*.22;dedup["final_score"]=dedup.selection_score+dedup.coverage_bonus
    chosen=[];per_mode=max(3,target_size//(len(FAILURE_MODES)*3))
    for mode in FAILURE_MODES:chosen.extend(dedup[dedup.failure_mode.eq(mode)].nlargest(per_mode,"final_score").index.tolist())
    remaining=dedup.drop(index=list(dict.fromkeys(chosen)),errors="ignore").nlargest(target_size-len(set(chosen)),"final_score").index.tolist();idx=list(dict.fromkeys(chosen+remaining))[:target_size]
    out=dedup.loc[idx].sort_values("final_score",ascending=False).copy();out["candidate_case_id"]=[f"candidate_{i:04d}" for i in range(len(out))]
    return out

def version_manifest(existing,selected,version="v1.1"):
    return {"version":version,"base_cases":int(len(existing)),"candidate_additions":int(len(selected)),"resulting_size":int(len(existing)+len(selected)),"failure_modes_added":selected.failure_mode.value_counts().to_dict(),"requires_human_approval":True,"source":"synthetic production-style feedback"}

def run(seed=42,n_feedback=2500,target_size=120):
    feedback=generate_feedback(seed,n_feedback);benchmark=generate_existing_benchmark(seed+1,420);candidates=enrich_candidates(feedback,benchmark,seed);coverage=coverage_table(benchmark,feedback);selected=select_golden_candidates(candidates,coverage,target_size);manifest=version_manifest(benchmark,selected)
    metrics={"Feedback items":int(len(feedback)),"Current benchmark cases":int(len(benchmark)),"Failure modes":len(FAILURE_MODES),"Clusters discovered":int(candidates.cluster.nunique()),"Underrepresented modes":int((coverage.status=="underrepresented").sum()),"Balanced modes":int((coverage.status=="balanced").sum()),"Candidate additions":int(len(selected)),"Critical candidates":int((selected.severity=="critical").sum()),"Human overrides sampled":int((selected.source=="human_override").sum()),"Escaped defects sampled":int((selected.source=="escaped_defect").sum()),"Mean novelty":float(selected.novelty_score.mean()),"P95 novelty":float(selected.novelty_score.quantile(.95)),"Mean difficulty":float(selected.difficulty_score.mean()),"Recovery cases":int((selected.failure_mode=="partial_recovery").sum()),"Tool-failure cases":int((selected.failure_mode=="tool_failure").sum()),"Coverage-gap bonus cases":int((selected.coverage_bonus>0).sum()),"Resulting version size":manifest["resulting_size"],"Human approval required":"Yes","Auto-promotion enabled":"No","Synthetic feedback":"Yes"}
    return feedback,benchmark,candidates,coverage,selected,manifest,metrics

def main():
    p=argparse.ArgumentParser(description="GoldenSet Factory benchmark lifecycle runner");p.add_argument("--out",default="artifacts");p.add_argument("--feedback",type=int,default=2500);p.add_argument("--target",type=int,default=120);p.add_argument("--seed",type=int,default=42)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);feedback,benchmark,candidates,coverage,selected,manifest,metrics=run(a.seed,a.feedback,a.target);coverage.to_csv(out/"coverage.csv",index=False);selected.to_csv(out/"candidate_cases.csv",index=False);(out/"manifest.json").write_text(json.dumps(manifest,indent=2));pd.Series(metrics).to_json(out/"metrics.json",indent=2);print(pd.Series(metrics).to_string())

if __name__=="__main__":main()
