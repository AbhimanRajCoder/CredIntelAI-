"""
CAM Generator Agent for Intelli-Credit v2.0.
Generates a professional Credit Appraisal Memo as DOCX and JSON
with extended sections: trend analysis, fraud signals, reasoning trace, and data quality.
"""

import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.models.schemas import (
    CAMReport, LendingRecommendation, LoanDecision,
    FinancialMetrics, ResearchSignals, RiskAnalysis,
    RiskGrade, AnalysisStatus,
)
from app.services.groq_client import get_groq_client
from app.utils.prompts import (
    CAM_COMPANY_OVERVIEW_PROMPT,
    CAM_PROMOTER_BACKGROUND_PROMPT,
    CAM_FINANCIAL_ANALYSIS_PROMPT,
    CAM_INDUSTRY_OUTLOOK_PROMPT,
    CAM_RISK_ASSESSMENT_PROMPT,
    CAM_RECOMMENDATION_PROMPT,
)
from app.models.state import add_reasoning_step
from app.config import get_settings
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


async def _generate_section(groq, prompt: str, section_name: str) -> str:
    """Generate a single CAM section using the LLM."""
    try:
        result = await groq.generate(
            prompt=prompt,
            system_message="You are a senior credit analyst writing a professional Credit Appraisal Memo for a bank.",
            temperature=0.2,
        )
        logger.info(f"Generated CAM section: {section_name} ({len(result)} chars)")
        return result.strip()
    except Exception as e:
        logger.error(f"Failed to generate {section_name}: {e}")
        return f"[Section generation failed: {str(e)}]"


async def _generate_recommendation(
    groq, company_name: str, sector: str, loan_amount: Optional[float],
    risk_analysis: Dict, financial_metrics: Dict, research_signals: Dict,
    due_diligence_notes: str,
) -> LendingRecommendation:
    """Generate the lending recommendation using LLM."""
    try:
        prompt = CAM_RECOMMENDATION_PROMPT.format(
            company_name=company_name,
            sector=sector,
            loan_amount=loan_amount or "Not specified",
            risk_analysis=json.dumps(risk_analysis, indent=2, default=str),
            financial_metrics=json.dumps(financial_metrics, indent=2, default=str),
            research_signals=json.dumps(research_signals, indent=2, default=str),
            due_diligence_notes=due_diligence_notes or "None provided",
        )

        result = await groq.generate_json(
            prompt=prompt,
            system_message=(
                "You are a senior credit committee member at a leading Indian bank. "
                "Provide a definitive lending recommendation. Respond in valid JSON."
            ),
        )

        decision_str = result.get("decision", "CONDITIONAL_APPROVE").upper()
        if decision_str not in [d.value for d in LoanDecision]:
            decision_str = "CONDITIONAL_APPROVE"

        return LendingRecommendation(
            decision=LoanDecision(decision_str),
            suggested_loan_limit=result.get("suggested_loan_limit"),
            suggested_interest_rate=result.get("suggested_interest_rate"),
            explanation=result.get("explanation", "Recommendation generated."),
            conditions=result.get("conditions", []),
        )

    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        return LendingRecommendation(
            decision=LoanDecision.CONDITIONAL_APPROVE,
            explanation=f"Automated recommendation failed: {str(e)}. Manual review required.",
            conditions=["Manual review required due to system error"],
        )


# ─── New Section Generators ──────────────────────────────────────────────────

def _generate_executive_summary(
    company_name: str, sector: str,
    credit_score: Dict, risk_analysis: Dict,
    recommendation: LendingRecommendation,
) -> str:
    """Generate executive summary from structured data."""
    score = credit_score.get("total_score", "N/A")
    grade = credit_score.get("grade", "N/A")
    risk_level = credit_score.get("risk_level", "N/A")
    decision = recommendation.decision.value if recommendation else "PENDING"

    return (
        f"This Credit Appraisal Memo evaluates {company_name} operating in the "
        f"{sector} sector. The automated credit scoring engine assigned a score of "
        f"{score}/100 (Grade: {grade}, Risk Level: {risk_level}). "
        f"Lending Decision: {decision}."
    )


def _generate_trend_section(trend_data: Dict) -> str:
    """Generate trend analysis narrative from structured data."""
    if not trend_data:
        return "Trend analysis was not performed due to insufficient multi-year data."

    parts = []
    years = trend_data.get("years_analyzed", 0)
    parts.append(f"Analysis covers {years} fiscal year(s).")

    cagr = trend_data.get("revenue_cagr")
    if cagr is not None:
        parts.append(f"Revenue CAGR: {cagr}%.")

    ebitda = trend_data.get("ebitda_trend", "unknown")
    if ebitda != "unknown":
        parts.append(f"EBITDA trend: {ebitda}.")

    debt_traj = trend_data.get("debt_trajectory", "unknown")
    if debt_traj != "unknown":
        parts.append(f"Debt trajectory: {debt_traj}.")

    volatility = trend_data.get("profit_volatility")
    if volatility is not None:
        parts.append(f"Profit volatility (CV): {volatility}%.")

    return " ".join(parts)


def _generate_fraud_section(fraud_data: Dict) -> str:
    """Generate fraud signals narrative from structured data."""
    if not fraud_data:
        return "No fraud detection was performed."

    flags = fraud_data.get("flags", [])
    score = fraud_data.get("fraud_score", 0)

    if not flags:
        return f"No fraud signals detected. Fraud score: {score}/100."

    parts = [f"Fraud score: {score}/100. {len(flags)} signal(s) detected:"]
    for flag in flags:
        severity = flag.get("severity", "medium")
        signal = flag.get("signal", "Unknown signal")
        parts.append(f"  • [{severity.upper()}] {signal}")

    return "\n".join(parts)


def _generate_trace_section(reasoning_trace: List[Dict]) -> str:
    """Generate reasoning trace narrative."""
    if not reasoning_trace:
        return "No reasoning trace recorded."

    parts = ["Agent decision trail:"]
    for step in reasoning_trace:
        agent = step.get("agent", "unknown")
        decision = step.get("decision", "")
        parts.append(f"  • {agent}: {decision}")

    return "\n".join(parts)


def _generate_quality_section(validation_data: Dict) -> str:
    """Generate data quality and confidence narrative."""
    if not validation_data:
        return "No data quality assessment was performed."

    quality = validation_data.get("quality_score", 0)
    confidence = validation_data.get("confidence_score", 0)
    ocr = validation_data.get("ocr_quality", 0)
    completeness = validation_data.get("data_completeness", 0)

    parts = [
        f"Overall quality score: {quality}/100.",
        f"Confidence score: {confidence:.2f}/1.0.",
        f"OCR quality: {ocr:.2f}, Data completeness: {completeness:.2f}.",
    ]

    checks = validation_data.get("checks", [])
    if checks:
        passed = sum(1 for c in checks if c.get("passed", False))
        parts.append(f"Quality checks: {passed}/{len(checks)} passed.")

    return " ".join(parts)


# ─── DOCX Report Generator ───────────────────────────────────────────────────

def _create_docx_report(report: CAMReport, output_path: str) -> str:
    """Generate a professional DOCX Credit Appraisal Memo v2.0."""
    doc = Document()

    # ── Title ────────────────────────────────────────────────────────────────
    title = doc.add_heading("CREDIT APPRAISAL MEMORANDUM", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0, 51, 102)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(f"Confidential | {report.company_name}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 51, 102)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    meta.add_run(f"Report ID: {report.report_id}").font.size = Pt(9)
    meta.add_run(f" | Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}").font.size = Pt(9)

    doc.add_paragraph("")

    # ── Table of Contents ────────────────────────────────────────────────────
    doc.add_heading("Table of Contents", level=1)
    sections = [
        "1. Executive Summary",
        "2. Company Overview",
        "3. Promoter Background",
        "4. Financial Analysis",
        "5. Multi-Year Trend Analysis",
        "6. Industry Outlook",
        "7. Risk Assessment",
        "8. Fraud Signals Review",
        "9. Reasoning Trace & Explainability",
        "10. Data Quality & Confidence",
        "11. Lending Recommendation",
    ]
    for s in sections:
        p = doc.add_paragraph(s)
        p.style = "List Number"

    doc.add_page_break()

    # ── Section 1: Executive Summary ─────────────────────────────────────────
    doc.add_heading("1. Executive Summary", level=1)
    doc.add_paragraph(report.executive_summary or "Not available.")

    # ── Credit Score Summary Table ───────────────────────────────────────────
    if report.credit_score:
        cs = report.credit_score
        doc.add_heading("Credit Score Summary", level=2)
        score_table = doc.add_table(rows=5, cols=2)
        score_table.style = "Table Grid"
        rows_data = [
            ("Total Score", f"{cs.get('total_score', 'N/A')}/100"),
            ("Grade", str(cs.get("grade", "N/A"))),
            ("Risk Level", str(cs.get("risk_level", "N/A"))),
            ("Financial Score", f"{cs.get('financial_score', 'N/A')}/100"),
            ("Sector Score", f"{cs.get('sector_score', 'N/A')}/100"),
        ]
        for i, (label, val) in enumerate(rows_data):
            score_table.rows[i].cells[0].text = label
            score_table.rows[i].cells[1].text = val

    # ── Section 2: Company Overview ──────────────────────────────────────────
    doc.add_heading("2. Company Overview", level=1)
    doc.add_paragraph(report.company_overview or "Not available.")

    # ── Section 3: Promoter Background ───────────────────────────────────────
    doc.add_heading("3. Promoter Background", level=1)
    doc.add_paragraph(report.promoter_background or "Not available.")

    # ── Section 4: Financial Analysis ────────────────────────────────────────
    doc.add_heading("4. Financial Analysis", level=1)
    doc.add_paragraph(report.financial_analysis or "Not available.")

    if report.financial_metrics:
        fm = report.financial_metrics
        doc.add_heading("Key Financial Metrics", level=2)
        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        hdr = table.rows[0].cells
        hdr[0].text = "Metric"
        hdr[1].text = "Value"
        for cell in hdr:
            cell.paragraphs[0].runs[0].bold = True if cell.paragraphs[0].runs else False

        metrics_data = [
            ("Revenue (INR)", fm.revenue),
            ("Net Profit (INR)", fm.profit),
            ("Total Debt (INR)", fm.debt),
            ("Cash Flow (INR)", fm.cashflow),
            ("Bank Loans (INR)", fm.bank_loans),
            ("Debt-to-Equity Ratio", fm.debt_to_equity_ratio),
            ("Current Ratio", fm.current_ratio),
            ("Interest Coverage Ratio", fm.interest_coverage_ratio),
            ("Net Profit Margin (%)", fm.net_profit_margin),
            ("Return on Equity (%)", fm.return_on_equity),
            ("Litigation Mentions", fm.litigation_mentions),
        ]

        for name, value in metrics_data:
            row = table.add_row().cells
            row[0].text = name
            if value is not None:
                if isinstance(value, float) and abs(value) >= 10000:
                    row[1].text = f"₹{value:,.2f}"
                elif isinstance(value, float):
                    row[1].text = f"{value:.2f}"
                else:
                    row[1].text = str(value)
            else:
                row[1].text = "N/A"

    # ── Section 5: Multi-Year Trend Analysis ─────────────────────────────────
    doc.add_heading("5. Multi-Year Trend Analysis", level=1)
    doc.add_paragraph(report.trend_analysis_section or "Not available.")

    # ── Section 6: Industry Outlook ──────────────────────────────────────────
    doc.add_heading("6. Industry Outlook", level=1)
    doc.add_paragraph(report.industry_outlook or "Not available.")

    # ── Section 7: Risk Assessment ───────────────────────────────────────────
    doc.add_heading("7. Risk Assessment", level=1)
    doc.add_paragraph(report.risk_assessment or "Not available.")

    if report.risk_analysis:
        ra = report.risk_analysis
        doc.add_heading("Risk Summary", level=2)

        risk_table = doc.add_table(rows=3, cols=2)
        risk_table.style = "Table Grid"
        risk_table.rows[0].cells[0].text = "Risk Score"
        risk_table.rows[0].cells[1].text = f"{ra.risk_score}/100"
        risk_table.rows[1].cells[0].text = "Risk Grade"
        risk_table.rows[1].cells[1].text = ra.risk_grade.value if isinstance(ra.risk_grade, RiskGrade) else str(ra.risk_grade)
        risk_table.rows[2].cells[0].text = "Assessment"
        risk_table.rows[2].cells[1].text = ra.explanation or ""

        if ra.key_risks:
            doc.add_heading("Key Risk Factors", level=3)
            for risk in ra.key_risks:
                doc.add_paragraph(risk, style="List Bullet")

        if ra.strengths:
            doc.add_heading("Key Strengths", level=3)
            for strength in ra.strengths:
                doc.add_paragraph(strength, style="List Bullet")

    # ── Section 7b: Intelligence Trail ───────────────────────────────────────
    if report.research_signals:
        rs = report.research_signals
        doc.add_heading("Intelligence Trail", level=2)
        p = doc.add_paragraph()
        p.add_run("Due Diligence Coverage: ").bold = True
        p.add_run(f"Analyzed {rs.articles_analyzed} articles across {rs.sources_used} unique credible sources.")

        p2 = doc.add_paragraph()
        p2.add_run("Research Score: ").bold = True
        p2.add_run(f"{rs.research_score}/100")

    # ── Section 8: Fraud Signals Review ──────────────────────────────────────
    doc.add_heading("8. Fraud Signals Review", level=1)
    doc.add_paragraph(report.fraud_signals_section or "Not available.")

    # ── Section 9: Reasoning Trace ───────────────────────────────────────────
    doc.add_heading("9. Reasoning Trace & Explainability", level=1)
    doc.add_paragraph(report.reasoning_trace_section or "Not available.")

    # ── Section 10: Data Quality & Confidence ────────────────────────────────
    doc.add_heading("10. Data Quality & Confidence", level=1)
    doc.add_paragraph(report.data_quality_section or "Not available.")

    # ── Section 11: Lending Recommendation ───────────────────────────────────
    doc.add_heading("11. Lending Recommendation", level=1)
    doc.add_paragraph(report.lending_recommendation_text or "Not available.")

    if report.recommendation:
        rec = report.recommendation
        doc.add_heading("Recommendation Summary", level=2)

        rec_table = doc.add_table(rows=4, cols=2)
        rec_table.style = "Table Grid"
        rec_table.rows[0].cells[0].text = "Decision"
        decision_val = rec.decision.value if isinstance(rec.decision, LoanDecision) else str(rec.decision)
        rec_table.rows[0].cells[1].text = decision_val
        rec_table.rows[1].cells[0].text = "Suggested Loan Limit"
        rec_table.rows[1].cells[1].text = f"₹{rec.suggested_loan_limit:,.2f}" if rec.suggested_loan_limit else "N/A"
        rec_table.rows[2].cells[0].text = "Suggested Interest Rate"
        rec_table.rows[2].cells[1].text = f"{rec.suggested_interest_rate}%" if rec.suggested_interest_rate else "N/A"
        rec_table.rows[3].cells[0].text = "Explanation"
        rec_table.rows[3].cells[1].text = rec.explanation

        if rec.conditions:
            doc.add_heading("Conditions", level=3)
            for cond in rec.conditions:
                doc.add_paragraph(cond, style="List Bullet")

    # ── Disclaimer ───────────────────────────────────────────────────────────
    doc.add_page_break()
    doc.add_heading("Disclaimer", level=2)
    doc.add_paragraph(
        "This Credit Appraisal Memorandum has been generated by the Intelli-Credit "
        "AI system v2.0. While the analysis leverages deterministic credit scoring, "
        "structured financial extraction, fraud detection, and multi-year trend analysis, "
        "this document should be reviewed by qualified credit professionals before making "
        "lending decisions. The AI system's recommendations are advisory in nature and "
        "do not constitute final credit approval."
    )

    doc.save(output_path)
    logger.info(f"DOCX report saved to: {output_path}")
    return output_path


# ─── Main Agent ───────────────────────────────────────────────────────────────

@track_agent(timeout=180)
async def cam_generator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    CAM Generator Agent v2.0: Generate professional Credit Appraisal Memo.

    Sections:
        1. Executive Summary (NEW)
        2. Company Overview
        3. Promoter Background
        4. Financial Analysis
        5. Multi-Year Trend Analysis (NEW)
        6. Industry Outlook
        7. Risk Assessment
        8. Fraud Signals Review (NEW)
        9. Reasoning Trace (NEW)
        10. Data Quality & Confidence (NEW)
        11. Lending Recommendation

    Exports as DOCX and JSON.
    """
    logger.info("CAM GENERATOR AGENT v2.0: Starting memo generation")

    settings = get_settings()
    company_name = state.get("company_name", "")
    sector = state.get("sector", "")
    analysis_id = state.get("analysis_id", "")
    due_diligence_notes = state.get("due_diligence_notes", "")
    loan_amount = state.get("loan_amount_requested")
    errors = list(state.get("errors", []))

    # v2.0 structured data
    credit_score_data = state.get("credit_score", {})
    trend_data = state.get("trend_analysis", {})
    fraud_data = state.get("fraud_signals", {})
    validation_data = state.get("validation_result", {})
    reasoning_trace = state.get("reasoning_trace", [])

    # ── Reconstruct data models ─────────────────────────────────────────────
    financial_metrics_dict = state.get("financial_metrics", {})
    research_signals_dict = state.get("research_signals", {})
    risk_analysis_dict = state.get("risk_analysis", {})

    try:
        financial_metrics = FinancialMetrics(**financial_metrics_dict) if financial_metrics_dict else FinancialMetrics()
    except Exception:
        financial_metrics = FinancialMetrics()

    try:
        research_signals = ResearchSignals(**research_signals_dict) if research_signals_dict else ResearchSignals()
    except Exception:
        research_signals = ResearchSignals()

    try:
        if risk_analysis_dict:
            rg = risk_analysis_dict.get("risk_grade", "BBB")
            if isinstance(rg, str):
                risk_analysis_dict["risk_grade"] = rg.upper()
            risk_analysis = RiskAnalysis(**risk_analysis_dict)
        else:
            risk_analysis = RiskAnalysis(risk_score=50, risk_grade=RiskGrade.BBB, key_risks=[], strengths=[])
    except Exception:
        risk_analysis = RiskAnalysis(risk_score=50, risk_grade=RiskGrade.BBB, key_risks=[], strengths=[])

    groq = get_groq_client()
    fm_json = json.dumps(financial_metrics.model_dump(), indent=2, default=str)
    rs_json = json.dumps(research_signals.model_dump(), indent=2, default=str)
    ra_json = json.dumps(risk_analysis.model_dump(), indent=2, default=str)

    # ── Generate CAM Sections in Parallel ───────────────────────────────────
    try:
        # Define tasks for parallel execution
        tasks = [
            _generate_section(
                groq,
                CAM_COMPANY_OVERVIEW_PROMPT.format(
                    company_name=company_name, sector=sector,
                    financial_summary=fm_json, research_info=rs_json,
                ),
                "Company Overview",
            ),
            _generate_section(
                groq,
                CAM_PROMOTER_BACKGROUND_PROMPT.format(
                    company_name=company_name, research_info=rs_json,
                    due_diligence_notes=due_diligence_notes or "None provided",
                ),
                "Promoter Background",
            ),
            _generate_section(
                groq,
                CAM_FINANCIAL_ANALYSIS_PROMPT.format(
                    company_name=company_name, financial_metrics=fm_json,
                ),
                "Financial Analysis",
            ),
            _generate_section(
                groq,
                CAM_INDUSTRY_OUTLOOK_PROMPT.format(sector=sector, research_info=rs_json),
                "Industry Outlook",
            ),
            _generate_section(
                groq,
                CAM_RISK_ASSESSMENT_PROMPT.format(
                    company_name=company_name, risk_analysis=ra_json,
                    financial_metrics=fm_json, research_signals=rs_json,
                ),
                "Risk Assessment",
            ),
        ]

        # Prepare all tasks including the recommendation for maximum parallel speed
        rec_task = _generate_recommendation(
            groq, company_name, sector, loan_amount,
            risk_analysis.model_dump(), financial_metrics.model_dump(),
            research_signals.model_dump(), due_diligence_notes,
        )
        
        # Execute all tasks concurrently (5 sections + 1 recommendation)
        *sections, recommendation = await asyncio.gather(*tasks, rec_task)
        
        # Unpack the section results
        company_overview, promoter_background, financial_analysis, industry_outlook, risk_assessment = sections

        lending_recommendation_text = (
            f"Decision: {recommendation.decision.value}\n\n"
            f"{recommendation.explanation}"
        )

    except Exception as e:
        error_msg = f"CAM generation error: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

        company_overview = "Generation failed"
        promoter_background = "Generation failed"
        financial_analysis = "Generation failed"
        industry_outlook = "Generation failed"
        risk_assessment = "Generation failed"
        lending_recommendation_text = "Generation failed"
        recommendation = LendingRecommendation(
            decision=LoanDecision.CONDITIONAL_APPROVE,
            explanation="Report generation encountered errors. Manual review required.",
        )

    # ── Generate v2.0 sections from structured data ──────────────────────────
    executive_summary = _generate_executive_summary(
        company_name, sector, credit_score_data, risk_analysis_dict, recommendation,
    )
    trend_section = _generate_trend_section(trend_data)
    fraud_section = _generate_fraud_section(fraud_data)
    trace_section = _generate_trace_section(reasoning_trace)
    quality_section = _generate_quality_section(validation_data)

    # ── Build CAM Report ────────────────────────────────────────────────────
    cam_report = CAMReport(
        report_id=analysis_id,
        company_name=company_name,
        sector=sector,
        executive_summary=executive_summary,
        company_overview=company_overview,
        promoter_background=promoter_background,
        financial_analysis=financial_analysis,
        industry_outlook=industry_outlook,
        risk_assessment=risk_assessment,
        lending_recommendation_text=lending_recommendation_text,
        trend_analysis_section=trend_section,
        fraud_signals_section=fraud_section,
        reasoning_trace_section=trace_section,
        data_quality_section=quality_section,
        financial_metrics=financial_metrics,
        research_signals=research_signals,
        risk_analysis=risk_analysis,
        recommendation=recommendation,
        credit_score=credit_score_data,
        trend_analysis_data=trend_data,
        fraud_signals_data=fraud_data,
        validation_result=validation_data,
        reasoning_trace=reasoning_trace,
    )

    # ── Export files ─────────────────────────────────────────────────────────
    reports_dir = Path(settings.REPORTS_DIR)
    reports_dir.mkdir(parents=True, exist_ok=True)

    try:
        json_path = str(reports_dir / f"CAM_{analysis_id}.json")
        with open(json_path, "w") as f:
            json.dump(cam_report.model_dump(mode="json"), f, indent=2, default=str)
        cam_report.json_path = json_path
        logger.info(f"JSON report saved: {json_path}")
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
        errors.append(f"JSON export failed: {str(e)}")

    # Reasoning trace
    updated_trace = add_reasoning_step(
        state,
        agent="cam_generator_agent",
        decision=f"Generated CAM report with {11} sections",
        evidence=f"JSON: {cam_report.json_path}",
    )

    logger.info("CAM GENERATOR AGENT v2.0: Complete")

    return {
        **state,
        "cam_report": cam_report.model_dump(mode="json"),
        "status": AnalysisStatus.COMPLETED.value,
        "current_agent": "cam_generator_agent",
        "errors": errors,
        "reasoning_trace": updated_trace,
    }
