import streamlit as st
from agent.core import run_agent

st.set_page_config(page_title="DD Agent — Together Fund", layout="wide")
st.title("🔍 Due Diligence Research Agent")
st.caption("Together Fund · Autonomous multi-step research loop")

with st.form("input_form"):
    company = st.text_input("Company Name", placeholder="e.g. Sarvam AI")
    description = st.text_area("One-line Description", placeholder="e.g. Indian LLM for regional languages")
    founder_linkedin = st.text_input("Founder LinkedIn URL", placeholder="https://linkedin.com/in/...")
    submitted = st.form_submit_button("Run Due Diligence")

if submitted and company and description:
    col_log, col_memo = st.columns([1, 1], gap="large")

    with col_log:
        st.subheader("🧠 Agent Reasoning Log")
        log_container = st.container()

    with col_memo:
        st.subheader("📄 Due Diligence Memo")
        memo_placeholder = st.empty()

    log_lines = []

    for event in run_agent(company, description, founder_linkedin or "Not provided"):
        if event["type"] == "step":
            step, query, results = event["step"], event["query"], event["results"]
            log_lines.append(f"**[STEP {step}]** Searching: `{query}`")
            log_lines.append(f"```\n{results[:400]}\n```")
            with log_container:
                for line in log_lines:
                    st.markdown(line)

        elif event["type"] == "error":
            log_lines.append(f"⚠️ **Step {event['step']} error:** {event['message']}")
            with log_container:
                st.warning(log_lines[-1])

        elif event["type"] == "memo":
            memo = event["memo"]
            log_lines.append("✅ **[VERDICT]** Memo generated.")
            with log_container:
                st.markdown(log_lines[-1])

            with memo_placeholder.container():
                confidence_color = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}.get(memo.confidence, "⚪")
                st.markdown(f"### {company} — {confidence_color} Confidence: {memo.confidence}")

                for section, icon in [
                    ("market",      "📊 Market"),
                    ("competition", "⚔️ Competition"),
                    ("founder",     "👤 Founder"),
                    ("traction",    "📈 Traction"),
                    ("red_flags",   "🚩 Red Flags"),
                    ("verdict",     "⚖️ Verdict"),
                ]:
                    with st.expander(icon, expanded=True):
                        st.write(getattr(memo, section))

                if memo.sources:
                    with st.expander("🔗 Sources (search queries used)"):
                        for s in memo.sources:
                            st.markdown(f"- `{s}`")