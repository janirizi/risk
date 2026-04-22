"""Reporting helpers for risk dashboard exports."""

from __future__ import annotations

from datetime import datetime
from io import StringIO

import pandas as pd


def dataframe_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def build_executive_report(projects: pd.DataFrame, risks: pd.DataFrame, signals: pd.DataFrame) -> str:
    report = StringIO()
    report.write("# IT Project Failure Analysis & Risk Management Report\n\n")
    report.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

    report.write("## Executive Summary\n")
    report.write(f"- Total projects reviewed: {len(projects)}\n")
    report.write(f"- Total active risks: {len(risks)}\n")

    if not risks.empty:
        critical = int((risks["level"] == "Critical").sum())
        high = int((risks["level"] == "High").sum())
        average_score = round(float(risks["score"].mean()), 2)
        report.write(f"- Critical risks: {critical}\n")
        report.write(f"- High risks: {high}\n")
        report.write(f"- Average risk score: {average_score}\n")

    if not signals.empty:
        latest = signals.sort_values("created_at").groupby("project_name").tail(1)
        worst = latest.sort_values("failure_probability", ascending=False).head(3)
        report.write("\n## Highest Failure Probability Projects\n")
        for _, row in worst.iterrows():
            report.write(f"- {row['project_name']}: {row['failure_probability']}% — {row['status']}\n")

    if not risks.empty:
        report.write("\n## Top Risks\n")
        top_risks = risks.sort_values("score", ascending=False).head(5)
        for _, row in top_risks.iterrows():
            report.write(
                f"- {row['project_name']} · {row['category']} · {row['score']}% "
                f"({row['level']}): {row['description']}\n"
            )

    report.write("\n## Recommended Governance Actions\n")
    report.write("- Review Critical and High risks in the next steering committee meeting.\n")
    report.write("- Assign owners and due dates to every mitigation plan.\n")
    report.write("- Recalculate failure signals after every major milestone.\n")
    report.write("- Use the risk matrix to prioritize budget, scope and schedule interventions.\n")

    return report.getvalue()
