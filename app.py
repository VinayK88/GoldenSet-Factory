from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run

st.set_page_config(page_title="GoldenSet Factory", page_icon="◇", layout="wide")
CSS="""<style>html,body,[class*="css"],.stApp{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif;color:#1d1d1f}.stApp{background:#fff}.block-container{max-width:1440px;padding-top:2.2rem;padding-bottom:4rem}#MainMenu,footer,header{visibility:hidden}.hero{background:radial-gradient(circle at 12% 9%,rgba(0,113,227,.12),transparent 31%),linear-gradient(180deg,#fff,#f5f5f7);border:1px solid #e8e8ed;border-radius:32px;padding:44px 48px 40px;margin-bottom:22px;box-shadow:0 12px 34px rgba(0,0,0,.035)}.eyebrow{color:#0071e3;font-weight:700;font-size:.78rem;letter-spacing:.11em;text-transform:uppercase}.hero h1{font-size:3.15rem;letter-spacing:-.055em;line-height:1.02;margin:.45rem 0 .7rem;font-weight:700}.hero p{color:#6e6e73;max-width:950px;font-size:1.06rem;line-height:1.55;margin:0}.pills{margin-top:18px;display:flex;gap:8px;flex-wrap:wrap}.pill{background:#fff;color:#515154;border:1px solid #e8e8ed;padding:7px 11px;border-radius:999px;font-size:.79rem}.kpi{background:#f5f5f7;border:1px solid #ececf0;border-radius:24px;padding:18px;min-height:116px;box-shadow:0 8px 22px rgba(0,0,0,.025)}.kpi-label{color:#6e6e73;text-transform:uppercase;letter-spacing:.075em;font-size:.68rem;font-weight:700}.kpi-value{font-size:1.44rem;font-weight:700;letter-spacing:-.035em;margin-top:9px}.section-title{font-size:1.5rem;letter-spacing:-.03em;margin:26px 0 12px;font-weight:700}.note{color:#6e6e73;font-size:.85rem}</style>"""
st.markdown(CSS,unsafe_allow_html=True)

def fmt(v):
    if isinstance(v,int):return f"{v:,}"
    if isinstance(v,float):
        if 0<=v<=1:return f"{v:.3f}"
        return f"{v:,.1f}"
    return str(v).replace("_"," ")

def cards(items,cols=5):
    for s in range(0,len(items),cols):
        cs=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):cs[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def load(seed,n,target): return run(seed,n,target)

with st.sidebar:
    st.markdown("### GoldenSet Factory");seed=st.number_input("Synthetic seed",1,9999,42);n=st.slider("Feedback items",1200,7000,2500,100);target=st.slider("Candidate additions",60,300,120,10);st.caption("Candidates are never auto-promoted. Human approval is an explicit boundary.")

feedback,benchmark,candidates,coverage,selected,manifest,metrics=load(seed,n,target)
st.markdown("""<div class="hero"><div class="eyebrow">Benchmark lifecycle · Production feedback</div><h1>Turn failures into the next evaluation set.</h1><p>GoldenSet Factory clusters production-style feedback, measures novelty and difficulty, finds benchmark coverage gaps, deduplicates candidates, and prepares a human-approved versioned golden-set update.</p><div class="pills"><span class="pill">Failure clustering</span><span class="pill">Novelty</span><span class="pill">Difficulty</span><span class="pill">Coverage gaps</span><span class="pill">Deduplication</span><span class="pill">Human approval</span></div></div>""",unsafe_allow_html=True)
st.markdown('<div class="section-title">Benchmark health</div>',unsafe_allow_html=True);cards(list(metrics.items()),5)
tabs=st.tabs(["Coverage gaps","Candidate landscape","Selected additions","Version manifest","Feedback"])
with tabs[0]:
    fig=px.bar(coverage.sort_values("coverage_ratio"),x="coverage_ratio",y="failure_mode",color="status",orientation="h",title="Benchmark representation vs production-style feedback");fig.add_vline(x=.70,line_dash="dash");fig.update_layout(template="plotly_white",height=470,legend_title_text="");st.plotly_chart(fig,use_container_width=True);st.dataframe(coverage,hide_index=True,use_container_width=True)
with tabs[1]:
    sample=candidates.sample(min(2200,len(candidates)),random_state=7);fig=px.scatter(sample,x="x",y="y",color="failure_mode",size="difficulty_score",hover_data=["feedback_id","severity","source","novelty_score"],title="Failure-pattern landscape (TF-IDF → PCA)");fig.update_layout(template="plotly_white",height=520,legend_title_text="");st.plotly_chart(fig,use_container_width=True)
with tabs[2]:
    c1,c2=st.columns([1.2,.8])
    with c1:st.dataframe(selected[["candidate_case_id","failure_mode","severity","source","novelty_score","difficulty_score","final_score"]],hide_index=True,use_container_width=True,height=460)
    with c2:
        counts=selected.failure_mode.value_counts().rename_axis("failure_mode").reset_index(name="count");fig=px.bar(counts.sort_values("count"),x="count",y="failure_mode",orientation="h",title="Candidate additions by mode");fig.update_layout(template="plotly_white",height=460);st.plotly_chart(fig,use_container_width=True)
    st.download_button("Export candidate golden cases",selected.to_csv(index=False),"goldenset_candidates.csv","text/csv")
with tabs[3]:
    st.json(manifest);st.info("Promotion boundary: a human reviewer must approve candidate cases before they become part of the versioned golden benchmark.")
with tabs[4]:st.dataframe(feedback.sample(min(800,len(feedback)),random_state=7),hide_index=True,use_container_width=True)
st.markdown('<p class="note">All production-style feedback and benchmark cases are synthetic. Clustering/novelty scores are triage aids, not substitutes for expert benchmark review.</p>',unsafe_allow_html=True)
