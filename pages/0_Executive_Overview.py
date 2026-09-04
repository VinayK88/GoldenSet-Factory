from __future__ import annotations
import numbers
import streamlit as st
import pandas as pd
import plotly.express as px
from engine import run

st.set_page_config(page_title="GoldenSet Factory · Executive Overview", page_icon="◇", layout="wide")
CSS="""
<style>
:root{--ink:#1d1d1f;--muted:#6e6e73;--soft:#f5f5f7;--line:#e8e8ed;--blue:#0071e3}
html,body,[class*="css"],.stApp,p,li,div,span,button,input,label{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Helvetica Neue",Helvetica,Arial,sans-serif!important;-webkit-font-smoothing:antialiased;color:var(--ink);font-size:16px}.stApp{background:linear-gradient(180deg,#fff,#fbfbfd)}.block-container{max-width:1500px;padding:2.3rem 2.2rem 5rem}#MainMenu,footer,header{visibility:hidden}[data-testid="stSidebar"]{background:#f5f5f7;border-right:1px solid var(--line)}[data-testid="stSidebar"] *{font-size:15px!important}.hero{background:radial-gradient(circle at 8% 0%,rgba(0,113,227,.16),transparent 32%),linear-gradient(155deg,#fff,#f5f5f7);border:1px solid var(--line);border-radius:36px;padding:54px 56px 48px;box-shadow:0 18px 48px rgba(0,0,0,.045)}.hero h1{font-size:3.65rem;line-height:.98;letter-spacing:-.062em;margin:.55rem 0 .9rem;font-weight:720;max-width:1040px}.hero p{color:var(--muted);font-size:1.12rem;line-height:1.6;max-width:970px;margin:0}.eyebrow{color:var(--blue);font-weight:760;font-size:.78rem;letter-spacing:.13em;text-transform:uppercase}.pills{margin-top:22px;display:flex;flex-wrap:wrap;gap:9px}.pill{background:#fff;border:1px solid var(--line);border-radius:999px;padding:8px 13px;color:#515154;font-size:.8rem}.section{font-size:1.72rem;letter-spacing:-.04em;font-weight:720;margin:32px 0 6px}.sub{color:var(--muted);font-size:.96rem;margin-bottom:16px}.kpi{background:#fff;border:1px solid var(--line);border-radius:26px;padding:20px;min-height:122px;box-shadow:0 8px 24px rgba(0,0,0,.028)}.kpi-label{color:var(--muted);font-size:.70rem;font-weight:760;letter-spacing:.08em;text-transform:uppercase}.kpi-value{font-size:1.62rem;line-height:1.03;font-weight:720;letter-spacing:-.045em;margin-top:12px}.callout{background:#fff;border:1px solid var(--line);border-radius:28px;padding:24px;min-height:162px;box-shadow:0 8px 24px rgba(0,0,0,.025)}.callout .cap{color:var(--blue);font-size:.70rem;font-weight:760;letter-spacing:.1em;text-transform:uppercase}.callout h3{font-size:1.25rem;letter-spacing:-.03em;margin:.55rem 0 .45rem}.callout p{color:var(--muted);font-size:.92rem;line-height:1.55;margin:0}</style>
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
        row=st.columns(cols)
        for i,(k,v) in enumerate(items[s:s+cols]):row[i].markdown(f'<div class="kpi"><div class="kpi-label">{k}</div><div class="kpi-value">{fmt(v)}</div></div>',unsafe_allow_html=True)

def style(fig,h=420):
    fig.update_layout(template="plotly_white",height=h,paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family='-apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial',size=14,color="#1d1d1f"),title_font=dict(size=20),margin=dict(l=12,r=12,t=60,b=12),legend_title_text="")
    fig.update_xaxes(gridcolor="#ececf0");fig.update_yaxes(gridcolor="#ececf0");return fig

with st.sidebar:
    st.markdown("### GoldenSet Factory")
    seed=st.number_input("Synthetic seed",1,9999,42)
    n=st.slider("Feedback items",1200,7000,2500,100)
    target=st.slider("Candidate additions",60,300,120,10)
    st.caption("Executive view uses the same benchmark-lifecycle engine as the main dashboard.")

feedback,benchmark,candidates,coverage,selected,manifest,base=run(seed,n,target)
crit_share=float((feedback.severity=="critical").mean())
incident_share=float((feedback.source=="incident").mean())
rollback_share=float((feedback.source=="rollback").mean())
escaped_share=float((feedback.source=="escaped_defect").mean())
nonrecoverable=float((feedback.recoverable==0).mean())
mean_cov=float(coverage.coverage_ratio.mean())
min_cov=float(coverage.coverage_ratio.min())
max_gap=float(coverage.gap.max())
selected_sources=int(selected.source.nunique())
selected_modes=int(selected.failure_mode.nunique())
selected_clusters=int(selected.cluster.nunique())

kpis=dict(base)
kpis.update({
    "Critical feedback share":crit_share,"Incident share":incident_share,"Rollback share":rollback_share,"Escaped-defect share":escaped_share,"Non-recoverable share":nonrecoverable,
    "Unique feedback modes":int(feedback.failure_mode.nunique()),"Unique tools":int(feedback.tool.nunique()),"Feedback source diversity":int(feedback.source.nunique()),"Mean coverage ratio":mean_cov,"Minimum coverage ratio":min_cov,
    "Maximum coverage gap":max_gap,"Overrepresented modes":int((coverage.status=="overrepresented").sum()),"Coverage bonus share":float((selected.coverage_bonus>0).mean()),"Selection rate":float(len(selected)/len(feedback)),
    "P95 candidate novelty":float(selected.novelty_score.quantile(.95)),"P95 candidate difficulty":float(selected.difficulty_score.quantile(.95)),"Max candidate novelty":float(selected.novelty_score.max()),"Max candidate difficulty":float(selected.difficulty_score.max()),
    "High-novelty candidates":int((selected.novelty_score>.60).sum()),"High-difficulty candidates":int((selected.difficulty_score>.65).sum()),"Selected modes":selected_modes,"Selected clusters":selected_clusters,"Selected source diversity":selected_sources,
    "Mean final score":float(selected.final_score.mean()),"P95 final score":float(selected.final_score.quantile(.95)),"Critical selection share":float((selected.severity=="critical").mean()),"Escaped-defect selection share":float((selected.source=="escaped_defect").mean()),
    "Incident selection share":float((selected.source=="incident").mean()),"Human-override selection share":float((selected.source=="human_override").mean()),"Benchmark growth rate":float(len(selected)/len(benchmark)),
    "Base benchmark size":int(len(benchmark)),"Candidate target":int(target),"Candidate realized":int(len(selected)),"Resulting benchmark size":int(manifest["resulting_size"]),"Approval gate":"Human","Auto-promotion":"Disabled","Synthetic feedback":"Yes"
})

st.markdown('''<div class="hero"><div class="eyebrow">GoldenSet Factory · Executive benchmark intelligence</div><h1>Know whether the benchmark still represents production reality.</h1><p>A product-level view of feedback composition, coverage gaps, novelty, difficulty, candidate diversity, benchmark growth, and human approval.</p><div class="pills"><span class="pill">45+ KPIs</span><span class="pill">Coverage gaps</span><span class="pill">Novelty</span><span class="pill">Difficulty</span><span class="pill">Human approval</span></div></div>''',unsafe_allow_html=True)
st.markdown('<div class="section">Executive scorecard</div><div class="sub">Expanded feedback, coverage, candidate-quality, diversity, and governance metrics with stronger typography.</div>',unsafe_allow_html=True)
cards(list(kpis.items()),5)

st.markdown('<div class="section">Three things to notice</div>',unsafe_allow_html=True)
worst=coverage.sort_values("coverage_ratio").iloc[0]
best=selected.sort_values("final_score",ascending=False).iloc[0]
c=st.columns(3)
c[0].markdown(f'<div class="callout"><div class="cap">Coverage gap</div><h3>{worst.failure_mode.replace("_"," ")}</h3><p>Coverage ratio <b>{worst.coverage_ratio:.2f}</b>. This mode is underrepresented relative to observed synthetic feedback.</p></div>',unsafe_allow_html=True)
c[1].markdown(f'<div class="callout"><div class="cap">Top candidate</div><h3>{best.failure_mode.replace("_"," ")}</h3><p>Final score <b>{best.final_score:.3f}</b>, combining novelty, difficulty, and coverage-gap priority.</p></div>',unsafe_allow_html=True)
c[2].markdown(f'<div class="callout"><div class="cap">Governance</div><h3>{len(selected)} candidates</h3><p>Candidate cases are prepared for review, but benchmark promotion remains explicitly human-approved.</p></div>',unsafe_allow_html=True)

c1,c2=st.columns(2)
with c1:
    fig=px.bar(coverage.sort_values("coverage_ratio"),x="coverage_ratio",y="failure_mode",color="status",orientation="h",title="Benchmark coverage by failure mode");fig.add_vline(x=.70,line_dash="dash",line_color="#ff9f0a");st.plotly_chart(style(fig,460),use_container_width=True)
with c2:
    counts=selected.failure_mode.value_counts().rename_axis("failure_mode").reset_index(name="count");fig=px.bar(counts.sort_values("count"),x="count",y="failure_mode",orientation="h",title="Selected candidate mix");st.plotly_chart(style(fig,460),use_container_width=True)

st.caption("All feedback and benchmark cases are synthetic. Novelty, difficulty, and coverage are triage signals; expert review remains the promotion boundary.")
