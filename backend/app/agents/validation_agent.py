"""
Validation Agent (Quality Gate) for Intelli-Credit.
Checks data completeness, OCR quality, and minimum thresholds before analysis.
"""

import logging
from typing import Any, Dict

from app.config import get_settings
from app.models.state import QualityCheck, ValidationResult, add_reasoning_step
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


@track_agent(timeout=15)
async def validation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validation Agent: Quality gate after document ingestion.

    Checks:
        1. Extracted text length ≥ 500 chars
        2. At least 3 critical financial metrics non-null
        3. No fatal parsing errors
        4. OCR confidence ≥ threshold

    Output: ValidationResult with quality_score and confidence_score.
    If quality is below threshold, routes to manual review.
    """
    logger.info("VALIDATION AGENT: Running quality checks")

    settings = get_settings()
    extracted_text = state.get("extracted_text", "")
    financial_metrics = state.get("financial_metrics", {})
    errors = list(state.get("errors", []))

    checks = []
    passed_count = 0
    total_checks = 4

    # ── Check 1: Text length ──────────────────────────────────────────────
    text_len = len(extracted_text)
    text_check = QualityCheck(
        check_name="text_length",
        passed=text_len >= 500,
        details=f"Extracted {text_len} characters (min: 500)",
    )
    checks.append(text_check)
    if text_check.passed:
        passed_count += 1

    # ── Check 2: Financial metrics completeness ───────────────────────────
    critical_fields = ["revenue", "profit", "debt", "cashflow", "bank_loans"]
    non_null = sum(
        1 for f in critical_fields
        if financial_metrics.get(f) is not None
    )
    metrics_check = QualityCheck(
        check_name="financial_metrics",
        passed=non_null >= 3,
        details=f"{non_null}/{len(critical_fields)} critical metrics present (min: 3)",
    )
    checks.append(metrics_check)
    if metrics_check.passed:
        passed_count += 1

    # ── Check 3: No fatal parsing errors ──────────────────────────────────
    fatal_errors = [e for e in errors if "fatal" in e.lower() or "critical" in e.lower()]
    error_check = QualityCheck(
        check_name="no_fatal_errors",
        passed=len(fatal_errors) == 0,
        details=f"{len(fatal_errors)} fatal errors found" if fatal_errors else "No fatal errors",
    )
    checks.append(error_check)
    if error_check.passed:
        passed_count += 1

    # ── Check 4: OCR confidence (if applicable) ──────────────────────────
    # Check if there are any OCR metadata hints in state
    has_documents = state.get("has_documents", False)
    if has_documents and text_len > 0:
        # Assume reasonable OCR if we got text
        ocr_confidence = min(1.0, text_len / 5000)  # Heuristic
        ocr_check = QualityCheck(
            check_name="ocr_confidence",
            passed=ocr_confidence >= settings.OCR_CONFIDENCE_THRESHOLD,
            details=f"OCR confidence proxy: {ocr_confidence:.2f} (threshold: {settings.OCR_CONFIDENCE_THRESHOLD})",
        )
    else:
        ocr_confidence = 1.0 if not has_documents else 0.0
        ocr_check = QualityCheck(
            check_name="ocr_confidence",
            passed=True,
            details="No documents — OCR check skipped" if not has_documents else "No text extracted",
        )
    checks.append(ocr_check)
    if ocr_check.passed:
        passed_count += 1

    # ── Compute composite scores ──────────────────────────────────────────
    quality_score = (passed_count / total_checks) * 100

    # Confidence score: composite of OCR quality, data completeness, source reliability
    ocr_quality = min(1.0, text_len / 5000) if has_documents else 0.8
    data_completeness = non_null / len(critical_fields)
    source_reliability = 1.0 if len(fatal_errors) == 0 else 0.3

    confidence_score = (
        ocr_quality * 0.35 +
        data_completeness * 0.45 +
        source_reliability * 0.20
    )

    is_acceptable = quality_score >= settings.MIN_QUALITY_SCORE

    validation_result = ValidationResult(
        quality_score=round(quality_score, 1),
        confidence_score=round(confidence_score, 3),
        ocr_quality=round(ocr_quality, 3),
        data_completeness=round(data_completeness, 3),
        source_reliability=round(source_reliability, 3),
        checks=checks,
        is_acceptable=is_acceptable,
        summary=(
            f"Quality: {quality_score:.0f}/100, Confidence: {confidence_score:.2f}. "
            f"{passed_count}/{total_checks} checks passed."
        ),
    )

    # Route to manual review if below threshold
    new_status = state.get("status", "processing")
    if not is_acceptable:
        new_status = "needs_review"
        logger.warning(
            f"VALIDATION AGENT: Quality below threshold "
            f"({quality_score:.0f} < {settings.MIN_QUALITY_SCORE}). "
            f"Routing to manual review."
        )

    reasoning_trace = add_reasoning_step(
        state,
        agent="validation_agent",
        decision=f"Quality: {quality_score:.0f}/100, Acceptable: {is_acceptable}",
        evidence=f"Checks: {', '.join(c.check_name + ('✓' if c.passed else '✗') for c in checks)}",
    )

    logger.info(f"VALIDATION AGENT: Complete — {validation_result.summary}")

    return {
        **state,
        "validation_result": validation_result.model_dump(),
        "status": new_status,
        "current_agent": "validation_agent",
        "reasoning_trace": reasoning_trace,
    }
