from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from auth import logout_button, require_login
from database import execute, get_projects, get_risks, get_signals, init_db, seed_demo_data
from reports import build_executive_report, dataframe_to_csv
from risk_model import FailureSignals, RiskInput, calculate_risk, failure_probability

st.set_page_config(
    page_title="IT Project Failure Analysis",
    page_icon="📊",
    layout="wide",
)

init_db()
seed_demo_data()


CUSTOM_CSS = """
<style>
.metric-card {
    border: 1px solid #e6e8eb;
    border-radius: 16px;
    padding: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.05);
}
.small-muted { color: #64748b; font-size: 0.9rem; }
.risk-pill {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 999px;
    background: #eef2ff;
    color: #3730a3;
    font-weight: 700;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


if not require_login():
    st.title("IT Project Failure Analysis & Risk Management Framework")
    st.info("Login or create an account from the sidebar to continue.")
    st.stop()

logout_button()

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose module",
    [
        "Executive Dashboard",
        "Project Portfolio",
        "Risk Register",
        "Failure Prediction",
        "Reports",
    ],
)


def render_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="small-muted">{label}</div>
            <h2 style="margin: 6px 0 2px 0;">{value}</h2>
            <div class="small-muted">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def draw_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(df[x_col].astype(str), df[y_col])
    ax.set_title(title)
    ax.set_xlabel(x_col.replace("_", " ").title())
    ax.set_ylabel(y_col.replace("_", " ").title())
    ax.tick_params(axis="x", rotation=30)
    st.pyplot(fig)


def draw_risk_matrix(risks: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    if risks.empty:
        ax.text(0.5, 0.5, "No risks recorded", ha="center", va="center")
    else:
        ax.scatter(risks["probability"], risks["impact"], s=risks["score"] * 8, alpha=0.65)
        for _, row in risks.head(8).iterrows():
            ax.annotate(str(row["id"]), (row["probability"], row["impact"]), fontsize=9)
    ax.set_xlim(0.5, 5.5)
    ax.set_ylim(0.5, 5.5)
    ax.set_xlabel("Probability")
    ax.set_ylabel("Impact")
    ax.set_title("Risk Matrix: Probability × Impact")
    ax.grid(True, alpha=0.25)
    st.pyplot(fig)


def selected_project(projects: pd.DataFrame):
    if projects.empty:
        st.warning("Create a project first.")
        return None
    options = {f"{row['name']} — {row['owner']}": int(row["id"]) for _, row in projects.iterrows()}
    label = st.selectbox("Project", list(options.keys()))
    return options[label]


projects = get_projects()
risks = get_risks()
signals = get_signals()

if page == "Executive Dashboard":
    render_header(
        "Executive Dashboard",
        "A management-level view of project health, risk exposure and failure probability.",
    )

    total_projects = len(projects)
    total_risks = len(risks)
    critical_risks = int((risks["level"] == "Critical").sum()) if not risks.empty else 0
    avg_score = round(float(risks["score"].mean()), 2) if not risks.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Projects", str(total_projects), "Portfolio size")
    with c2:
        metric_card("Active Risks", str(total_risks), "Registered risk items")
    with c3:
        metric_card("Critical Risks", str(critical_risks), "Immediate escalation")
    with c4:
        metric_card("Average Risk Score", f"{avg_score}%", "Normalized 0–100")

    st.divider()
    left, right = st.columns([1.1, 1])
    with left:
        if not risks.empty:
            grouped = risks.groupby("level", as_index=False)["id"].count().rename(columns={"id": "count"})
            draw_bar_chart(grouped, "level", "count", "Risks by Severity Level")
        else:
            st.info("No risks recorded yet.")
    with right:
        draw_risk_matrix(risks)

    st.subheader("Top Risk Items")
    if risks.empty:
        st.info("No risk register data available.")
    else:
        st.dataframe(
            risks[["id", "project_name", "category", "description", "score", "level", "owner", "status"]].head(10),
            use_container_width=True,
            hide_index=True,
        )

elif page == "Project Portfolio":
    render_header("Project Portfolio", "Create and track IT projects that will be assessed for failure risk.")

    with st.expander("Add new project", expanded=projects.empty):
        with st.form("project_form"):
            name = st.text_input("Project name")
            owner = st.text_input("Project owner")
            stage = st.selectbox("Stage", ["Initiation", "Planning", "Execution", "Testing", "Deployment", "Closed"])
            budget = st.number_input("Approved budget", min_value=0.0, step=1000.0)
            spent = st.number_input("Amount spent", min_value=0.0, step=1000.0)
            progress = st.slider("Progress %", 0, 100, 0)
            submitted = st.form_submit_button("Save project")
            if submitted:
                if not name or not owner:
                    st.warning("Project name and owner are required.")
                else:
                    execute(
                        "INSERT INTO projects(name, owner, stage, budget, spent, progress) VALUES (?, ?, ?, ?, ?, ?)",
                        (name, owner, stage, budget, spent, progress),
                    )
                    st.success("Project added.")
                    st.rerun()

    st.subheader("Projects")
    st.dataframe(projects, use_container_width=True, hide_index=True)

elif page == "Risk Register":
    render_header("Risk Register", "Log, score and prioritize project risks using an explainable scoring model.")

    project_id = selected_project(projects)
    if project_id:
        with st.form("risk_form"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox(
                    "Risk category",
                    ["Schedule", "Budget", "Scope", "Requirements", "Technical", "People", "Stakeholder", "Vendor"],
                )
                description = st.text_area("Risk description")
                mitigation = st.text_area("Mitigation plan")
                owner = st.text_input("Risk owner")
            with col2:
                probability = st.slider("Probability", 1, 5, 3)
                impact = st.slider("Impact", 1, 5, 3)
                exposure = st.slider("Exposure", 1, 5, 3)
                detectability = st.slider("Detectability difficulty", 1, 5, 3)
                control_strength = st.slider("Control strength", 1, 5, 3)
                weight = st.slider("Business priority weight", 0.5, 2.0, 1.0, 0.1)

            submitted = st.form_submit_button("Calculate and save risk")
            if submitted:
                if not description:
                    st.warning("Risk description is required.")
                else:
                    result = calculate_risk(
                        RiskInput(probability, impact, exposure, detectability, control_strength, weight)
                    )
                    execute(
                        """
                        INSERT INTO risk_register(
                            project_id, category, description, probability, impact, exposure,
                            detectability, control_strength, weight, score, level, mitigation, owner
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            project_id,
                            category,
                            description,
                            probability,
                            impact,
                            exposure,
                            detectability,
                            control_strength,
                            weight,
                            result["score"],
                            result["level"],
                            mitigation,
                            owner,
                        ),
                    )
                    st.success(f"Risk saved: {result['score']}% · {result['level']} · {result['priority']}")
                    st.rerun()

    st.subheader("Risk Register")
    if risks.empty:
        st.info("No risks saved yet.")
    else:
        level_filter = st.multiselect("Filter by level", sorted(risks["level"].unique()), default=list(sorted(risks["level"].unique())))
        filtered = risks[risks["level"].isin(level_filter)] if level_filter else risks
        st.dataframe(filtered, use_container_width=True, hide_index=True)

elif page == "Failure Prediction":
    render_header(
        "Failure Prediction",
        "Estimate project failure probability from schedule, budget, scope, technical and people signals.",
    )

    project_id = selected_project(projects)
    if project_id:
        with st.form("failure_form"):
            c1, c2 = st.columns(2)
            with c1:
                schedule_slippage = st.slider("Schedule slippage %", 0, 100, 15)
                budget_variance = st.slider("Budget variance %", 0, 100, 10)
                scope_creep = st.slider("Scope creep", 1, 5, 3)
                requirement_volatility = st.slider("Requirement volatility", 1, 5, 3)
            with c2:
                technical_complexity = st.slider("Technical complexity", 1, 5, 3)
                team_turnover = st.slider("Team turnover risk", 1, 5, 2)
                stakeholder_engagement = st.slider("Stakeholder engagement", 1, 5, 3)
                vendor_dependency = st.slider("Vendor dependency", 1, 5, 2)

            submitted = st.form_submit_button("Predict failure probability")
            if submitted:
                result = failure_probability(
                    FailureSignals(
                        schedule_slippage=schedule_slippage,
                        budget_variance=budget_variance,
                        scope_creep=scope_creep,
                        requirement_volatility=requirement_volatility,
                        technical_complexity=technical_complexity,
                        team_turnover=team_turnover,
                        stakeholder_engagement=stakeholder_engagement,
                        vendor_dependency=vendor_dependency,
                    )
                )
                execute(
                    """
                    INSERT INTO project_signals(
                        project_id, schedule_slippage, budget_variance, scope_creep,
                        requirement_volatility, technical_complexity, team_turnover,
                        stakeholder_engagement, vendor_dependency, failure_probability, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        schedule_slippage,
                        budget_variance,
                        scope_creep,
                        requirement_volatility,
                        technical_complexity,
                        team_turnover,
                        stakeholder_engagement,
                        vendor_dependency,
                        result["failure_probability"],
                        result["status"],
                    ),
                )
                st.success(f"Failure probability: {result['failure_probability']}% — {result['status']}")
                st.subheader("Top Drivers")
                st.dataframe(pd.DataFrame(result["drivers"]), use_container_width=True, hide_index=True)
                st.subheader("Recommended Actions")
                for item in result["recommendations"]:
                    st.write(f"- {item}")

    st.subheader("Failure Signal History")
    if signals.empty:
        st.info("No prediction history yet.")
    else:
        st.dataframe(signals, use_container_width=True, hide_index=True)
        latest = signals.sort_values("created_at").groupby("project_name").tail(1)
        draw_bar_chart(latest, "project_name", "failure_probability", "Latest Failure Probability by Project")

elif page == "Reports":
    render_header("Reports", "Export risk data and generate an executive management report.")

    report_text = build_executive_report(projects, risks, signals)
    st.markdown(report_text)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "Download Executive Report",
            report_text.encode("utf-8"),
            file_name="executive_risk_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Download Risk Register CSV",
            dataframe_to_csv(risks),
            file_name="risk_register.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=risks.empty,
        )
    with c3:
        st.download_button(
            "Download Failure Signals CSV",
            dataframe_to_csv(signals),
            file_name="failure_signals.csv",
            mime="text/csv",
            use_container_width=True,
            disabled=signals.empty,
        )
