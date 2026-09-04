from __future__ import annotations
import numbers
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run

st.set_page_config(page_title="GoldenSet Factory", page_icon="◇", layout="wide")

CSS="""
<style>
html,body,[class*="css"],.stApp{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;color:#1d1d1f}
.stApp{background:linear-gradient(180deg,#ffffff 0%,#fbfbfd 100%)}
.block-container{max-width:1480px;padding-top:2rem;padding-bottom:5rem}
#MainMenu,footer,header{visibility:hidden}
[data-testid="stSidebar"]{background:#f5f5f7;border-right:1px solid #e8e8ed}
.hero{position:relative;overflow:hidden;background:radial-gradient(circle at 9% 0%,rgba(0,113,227,.15),transparent 31%),linear-gradient(155deg,#fff,#f5f5f7);border:1px solid #e8e8ed;border-radius:34px;padding:50px 52px 44px;margin-bottom:18px;box-shadow:0 18px 48px rgba(0,0,0,.045)}
.hero:after{content:"";position:absolute;width:290px;height:290px;right:-90px;top:-105px;border-radius:50%;background:rgba(0,113,227,.05)}
.eyebrow{color:#0071e3;font-weight:750;font-size:.76rem;letter-spacing:.12em;text-transform:uppercase}.hero h1{font-size:3.45rem;letter-spacing:-.06em;line-height:.98;margin:.55rem 0 .8rem;font-weight:730;max-width:1000px}.hero p{color:#6e6e73;max-width:980px;font-size:1.08rem;line-height:1.58;margin:0}.pills{margin-top:20px;display:flex;gap:8px;flex-wrap:wrap}.pill{background:rgba(255,255,255,.9);color:#515154;border:1px solid #e8e8ed;padding:7px 12px;border-radius:999px;font-size:.79rem}
.status-row{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 24px}.status{display:inline-flex;align-items:center;gap:8px;padding:9px 13px;background:#fff;border:1px solid #e8e8ed;border-radius:999px;font-size:.79rem;color:#515154;box-shadow:0 6px 18px rgba(0,0,0,.025)}.dot{width:8px;height:8px;border-radius:50%;background:#34c759;display:inline-block}
.section-title{font-size:1.55rem;letter-spacing:-.035em;margin:30px 0 13px;font-weight:720}.section-sub{color:#6e6e73;font-size:.91rem;margin-top:-6px;margin-bottom:15px}
.kpi{background:rgba(255,255,255,.97);border:1px solid #e8e8ed;border-radius:25px;padding:18px;min-height:116px;box-shadow:0 8px 24px rgba(0,0,0,.028)}.kpi:hover{box-shadow:0 12px 30px rgba(0,0,0,.045);transform:translateY(-1px);transition:.16s ease}.kpi-label{color:#6e6e73;text-transform:uppercase;letter-spacing:.075em;font-size:.67rem;font-weight:760}.kpi-value{font-size:1.46rem;font-weight:730;letter-spacing:-.04em;margin-top:10px;line-height:1.05}
.insight{background:#fff;border:1px solid #e8e8ed;border-radius:26px;padding:22px 23px;min-height:148px;box-shadow:0 8px 24px rgba(0,0,0,.025)}.insight .cap{color:#0071e3;text-transform:uppercase;letter-spacing:.09em;font-size:.68rem;font-weight:760}.insight h3{font-size:1.15rem;letter-spacing:-.025em;margin:.55rem 0 .45rem}.insight p{color:#6e6e73;font-size:.88rem;line-height:1.48;margin:0}.note{color:#6e6e73;font-size:.84rem}
div[data-baseweb="tab-list"]{gap:8px}button[data-baseweb="tab"]{border-radius:999px;padding-left:14px;padding-right:14px}
</style>
"""
st.markdown(CSS,unsafe_allow_html=True)


def fmt(v):
    if isinstance(v,bool): return "Yes" if v else "No"
    if isinstance(v,numbers.Integral): return f"{int(v):,}"
    if isinstance(v,numbers.Real):
        v=float(v)
        if -1<=v<=1:return f"{v:.3f}"
        if abs(v)>=1000:return f"{v:,.0f}"
        return f"{v:,.2f}"
    return str(v).replace("_"," ")


def cards(items,cols=5):
    for s in range(0,len(items),cols):
        cs=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):
            cs[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)


def style_fig(fig,height=430):
    fig.update_layout(template="plotly_white",height=height,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family='-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial',color="#1d1d1f"),title_font=dict(size=18),margin=dict(l=12,r=12,t=58,b=12),legend_title_text="")
    fig.update_xaxes(gridcolor="#eeeeF2",zerolinecolor="#eeeeF2")
    fig.update_yaxes(gridcolor="#eeeeF2",zerolinecolor="#eeeeF2")
    return fig


@st.cache_data(show_spinner=False)
def load(seed,n,target): return run(seed,n,target)


with st.sidebar:
    st.markdown("### GoldenSet Factory")
    st.caption("Production feedback → benchmark")
    seed=st.number_input("Synthetic seed",1,9999,42)
    n=st.slider("Feedback items",1200,7000,2500,100)
    target=st.slider("Candidate additions",60,300,120,10)
    st.divider()
    st.caption("Candidates are never auto-promoted. Human approval remains the benchmark promotion boundary.")


feedback,benchmark,candidates,coverage,selected,manifest,metrics=load(seed,n,target)

critical_feedback_share=float((feedback.severity=="critical").mean())
incident_share=float((feedback.source=="incident").mean())
rollback_share=float((feedback.source=="rollback").mean())
escaped_share=float((feedback.source=="escaped_defect").mean())
recoverable_share=float(feedback.recoverable.mean())
mean_coverage=float(coverage.coverage_ratio.mean())
min_coverage=float(coverage.coverage_ratio.min())
max_gap=float(coverage.gap.max())
overrepresented=int((coverage.status=="overrepresented").sum())
selection_rate=float(len(selected)/max(len(feedback),1))
growth_rate=float(len(selected)/max(len(benchmark),1))
high_novelty=int((selected.novelty_score>=.45).sum())
high_difficulty=int((selected.difficulty_score>=.60).sum())
p95_difficulty=float(selected.difficulty_score.quantile(.95)) if len(selected) else 0.0
selected_modes=int(selected.failure_mode.nunique())
selected_clusters=int(selected.cluster.nunique())
source_diversity=int(selected.source.nunique())
coverage_bonus_share=float((selected.coverage_bonus>0).mean()) if len(selected) else 0.0
nonrecoverable_selected=int((selected.recoverable==0).sum())
critical_selected_share=float((selected.severity=="critical").mean()) if len(selected) else 0.0
selected_mean_score=float(selected.final_score.mean()) if len(selected) else 0.0
candidate_mean_novelty=float(candidates.novelty_score.mean())
selected_novelty_uplift=float(selected.novelty_score.mean()-candidate_mean_novelty) if len(selected) else 0.0
candidate_mean_difficulty=float(candidates.difficulty_score.mean())
selected_difficulty_uplift=float(selected.difficulty_score.mean()-candidate_mean_difficulty) if len(selected) else 0.0
cluster_counts=candidates.cluster.value_counts(normalize=True)
largest_cluster_share=float(cluster_counts.iloc[0]) if len(cluster_counts) else 0.0

extended=dict(metrics)
extended.update({
    "Critical feedback share":critical_feedback_share,
    "Incident share":incident_share,
    "Rollback share":rollback_share,
    "Escaped-defect share":escaped_share,
    "Recoverable feedback share":recoverable_share,
    "Mean coverage ratio":mean_coverage,
    "Minimum coverage ratio":min_coverage,
    "Maximum coverage gap":max_gap,
    "Overrepresented modes":overrepresented,
    "Candidate selection rate":selection_rate,
    "Benchmark growth rate":growth_rate,
    "High-novelty candidates":high_novelty,
    "High-difficulty candidates":high_difficulty,
    "P95 difficulty":p95_difficulty,
    "Selected unique modes":selected_modes,
    "Selected unique clusters":selected_clusters,
    "Selected source diversity":source_diversity,
    "Coverage-bonus share":coverage_bonus_share,
    "Nonrecoverable selected":nonrecoverable_selected,
    "Critical selected share":critical_selected_share,
    "Mean final candidate score":selected_mean_score,
    "Novelty uplift vs pool":selected_novelty_uplift,
    "Difficulty uplift vs pool":selected_difficulty_uplift,
    "Largest cluster share":largest_cluster_share,
})

st.markdown("""<div class="hero"><div class="eyebrow">Benchmark lifecycle · Production feedback</div><h1>Turn failures into the next evaluation set.</h1><p>GoldenSet Factory converts production-style overrides, incidents, rollbacks, escaped defects, and edge cases into reviewable benchmark candidates through clustering, novelty, difficulty, coverage-gap analysis, deduplication, diversity controls, and explicit human approval.</p><div class="pills"><span class="pill">Failure clustering</span><span class="pill">Novelty</span><span class="pill">Difficulty</span><span class="pill">Coverage gaps</span><span class="pill">Deduplication</span><span class="pill">Version manifest</span><span class="pill">Human approval</span></div></div><div class="status-row"><div class="status"><span class="dot"></span>Synthetic feedback pipeline healthy</div><div class="status">Human approval required</div><div class="status">Auto-promotion disabled</div></div>""",unsafe_allow_html=True)

st.markdown('<div class="section-title">Benchmark health</div>',unsafe_allow_html=True)
st.markdown('<div class="section-sub">30+ coverage, novelty, difficulty, feedback, versioning, and governance KPIs.</div>',unsafe_allow_html=True)
cards(list(extended.items()),5)

st.markdown('<div class="section-title">Executive readout</div>',unsafe_allow_html=True)
ins=st.columns(3)
worst=coverage.sort_values("coverage_ratio").iloc[0]
ins[0].markdown(f'<div class="insight"><div class="cap">Coverage gap</div><h3>{worst.failure_mode.replace("_"," ")}</h3><p>Lowest representation ratio: <b>{worst.coverage_ratio:.2f}</b>. Underrepresented modes receive explicit selection pressure.</p></div>',unsafe_allow_html=True)
ins[1].markdown(f'<div class="insight"><div class="cap">Candidate quality</div><h3>{metrics["Mean novelty"]:.3f} mean novelty</h3><p>Selected cases are compared against the current benchmark so duplicate-like additions do not consume the benchmark budget.</p></div>',unsafe_allow_html=True)
ins[2].markdown(f'<div class="insight"><div class="cap">Governance</div><h3>{len(selected)} candidate additions</h3><p>Every candidate remains reviewable. The manifest requires human approval and explicitly disables auto-promotion.</p></div>',unsafe_allow_html=True)


tabs=st.tabs(["Coverage gaps","Candidate landscape","Selected additions","Version manifest","Feedback"])

with tabs[0]:
    fig=px.bar(coverage.sort_values("coverage_ratio"),x="coverage_ratio",y="failure_mode",color="status",orientation="h",title="Benchmark representation vs production-style feedback")
    fig.add_vline(x=.70,line_dash="dash",line_color="#ff9f0a")
    fig.add_vline(x=1.45,line_dash="dot",line_color="#6e6e73")
    st.plotly_chart(style_fig(fig,490),use_container_width=True)
    st.dataframe(coverage,hide_index=True,use_container_width=True)

with tabs[1]:
    sample=candidates.sample(min(2400,len(candidates)),random_state=7)
    fig=px.scatter(sample,x="x",y="y",color="failure_mode",size="difficulty_score",hover_data=["feedback_id","severity","source","novelty_score","recoverable"],title="Failure-pattern landscape (TF-IDF → PCA)")
    st.plotly_chart(style_fig(fig,540),use_container_width=True)
    c1,c2=st.columns(2)
    with c1:
        fig=px.histogram(candidates,x="novelty_score",nbins=35,title="Candidate novelty distribution")
        st.plotly_chart(style_fig(fig,350),use_container_width=True)
    with c2:
        fig=px.histogram(candidates,x="difficulty_score",nbins=35,title="Candidate difficulty distribution")
        st.plotly_chart(style_fig(fig,350),use_container_width=True)

with tabs[2]:
    c1,c2=st.columns([1.2,.8])
    with c1:
        st.dataframe(selected[["candidate_case_id","failure_mode","severity","source","novelty_score","difficulty_score","coverage_bonus","final_score"]],hide_index=True,use_container_width=True,height=470)
    with c2:
        counts=selected.failure_mode.value_counts().rename_axis("failure_mode").reset_index(name="count")
        fig=px.bar(counts.sort_values("count"),x="count",y="failure_mode",orientation="h",title="Candidate additions by failure mode")
        st.plotly_chart(style_fig(fig,470),use_container_width=True)
    st.download_button("Export candidate golden cases",selected.to_csv(index=False),"goldenset_candidates.csv","text/csv")

with tabs[3]:
    st.markdown("#### Version manifest")
    st.json(manifest)
    st.info("Promotion boundary: a human reviewer must approve candidate cases before they become part of the versioned golden benchmark. The factory creates evidence packages, not autonomous benchmark truth.")

with tabs[4]:
    st.markdown("#### Production-style feedback sample")
    st.dataframe(feedback.sample(min(900,len(feedback)),random_state=7),hide_index=True,use_container_width=True)
    source_counts=feedback.source.value_counts().rename_axis("source").reset_index(name="count")
    fig=px.bar(source_counts,x="source",y="count",title="Feedback sources")
    st.plotly_chart(style_fig(fig,360),use_container_width=True)

st.markdown('<p class="note">All production-style feedback and benchmark cases are synthetic. Clustering, novelty, difficulty, and coverage scores are triage aids, not substitutes for expert benchmark review.</p>',unsafe_allow_html=True)
