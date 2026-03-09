"""
Data Ingestor Agent for Intelli-Credit.
Parses uploaded PDFs, detects document sections, applies PII redaction,
and stores structured chunks in Pinecone.
"""

import logging
from typing import Any, Dict, List

from app.models.schemas import AnalysisStatus
from app.models.state import add_reasoning_step
from app.services.document_parser import get_document_parser
from app.services.section_detector import (
    detect_sections_from_text,
    get_detected_section_types,
    get_section_for_page,
)
from app.db.pinecone_store import get_pinecone_store
from app.utils.pii_redactor import redact_pii
from app.utils.observability import track_agent

logger = logging.getLogger(__name__)


@track_agent(timeout=60)
async def data_ingestor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Data Ingestor Agent: Parse documents, detect sections, apply PII redaction,
    and store structured chunks in ChromaDB.

    Responsibilities:
        - Parse uploaded PDFs using pdfplumber + PaddleOCR
        - Detect document sections (Balance Sheet, P&L, etc.)
        - Apply PII redaction before storing
        - Store metadata-tagged chunks in Pinecone
        - Pass reconstructed tables to Financial Extraction Agent

    Output:
        extracted_text, detected_sections, reconstructed_tables → state
    """
    logger.info("DATA INGESTOR AGENT: Starting document processing")

    document_paths = state.get("document_paths", [])
    analysis_id = state.get("analysis_id", "")
    errors = list(state.get("errors", []))

    extracted_text = ""
    reconstructed_tables: List[Dict[str, Any]] = []
    detected_sections: List[str] = []
    page_texts: List[str] = []

    # ── Step 1: Extract text from documents ─────────────────────────────────
    if document_paths:
        try:
            parser = get_document_parser()

            # Extract text and metadata from all documents
            all_page_texts = []
            for doc_path in document_paths:
                try:
                    result = await parser.extract_text_with_metadata(doc_path)
                    if isinstance(result, dict):
                        all_page_texts.extend(result.get("page_texts", []))
                        reconstructed_tables.extend(result.get("tables", []))
                    else:
                        # Fallback: treat as plain text
                        text = await parser.extract_text(doc_path)
                        all_page_texts.append(text)
                except AttributeError:
                    # Parser doesn't have extract_text_with_metadata
                    text = await parser.extract_text_from_multiple([doc_path])
                    all_page_texts.append(text)
                except Exception as e:
                    error_msg = f"Failed to parse {doc_path}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            page_texts = all_page_texts
            extracted_text = "\n\n".join(t for t in page_texts if t)

            logger.info(
                f"Extracted {len(extracted_text)} chars from {len(document_paths)} docs, "
                f"{len(reconstructed_tables)} tables found"
            )
        except Exception as e:
            error_msg = f"Document extraction failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

            # Try simpler extraction as last resort
            try:
                parser = get_document_parser()
                extracted_text = await parser.extract_text_from_multiple(document_paths)
                page_texts = [extracted_text]
            except Exception as e2:
                errors.append(f"Fallback extraction also failed: {str(e2)}")
    else:
        logger.warning("No documents provided — skipping extraction")
        extracted_text = "No financial documents were uploaded for this analysis."

    # ── Step 2: Detect document sections ─────────────────────────────────────
    if page_texts:
        try:
            sections = detect_sections_from_text(page_texts)
            detected_sections = get_detected_section_types(sections)
            logger.info(f"Detected sections: {detected_sections}")
        except Exception as e:
            logger.warning(f"Section detection failed: {e}")

    # ── Step 3: PII redaction ────────────────────────────────────────────────
    redacted_text = redact_pii(extracted_text)

    # ── Step 4: Store structured chunks in Pinecone ──────────────────────────
    if redacted_text and analysis_id and redacted_text != "No financial documents were uploaded for this analysis.":
        try:
            vector_store = get_pinecone_store()

            # Build structured chunks with metadata
            structured_chunks = []
            if page_texts and len(page_texts) > 1:
                sections_list = detect_sections_from_text(page_texts) if page_texts else []
                for page_idx, page_text in enumerate(page_texts):
                    if not page_text or not page_text.strip():
                        continue
                    section = get_section_for_page(sections_list, page_idx)
                    redacted_page = redact_pii(page_text)
                    structured_chunks.append({
                        "text": redacted_page,
                        "type": "financial_table" if section in ("balance_sheet", "pnl", "cash_flow") else "narrative",
                        "page_num": page_idx,
                        "section": section or "",
                    })

                if structured_chunks:
                    vector_store.store_structured_chunks(
                        chunks=structured_chunks,
                        analysis_id=analysis_id,
                    )
            else:
                # Fall back to simple chunking
                vector_store.store_extracted_text(
                    text=redacted_text,
                    analysis_id=analysis_id,
                    chunk_size=1000,
                    overlap=200,
                )

            logger.info(f"Stored document chunks in Pinecone for {analysis_id}")
        except Exception as e:
            logger.warning(f"Pinecone storage failed (non-critical): {str(e)}")

    # ── Step 5: Reasoning trace ──────────────────────────────────────────────
    reasoning_trace = add_reasoning_step(
        state,
        agent="data_ingestor_agent",
        decision=(
            f"Ingested {len(document_paths)} documents: "
            f"{len(extracted_text)} chars, {len(reconstructed_tables)} tables, "
            f"sections: {detected_sections}"
        ),
        evidence=f"Documents: {', '.join(document_paths)}" if document_paths else "No documents",
    )

    logger.info("DATA INGESTOR AGENT: Complete")

    return {
        **state,
        "extracted_text": extracted_text,
        "reconstructed_tables": [
            t if isinstance(t, dict) else {} for t in reconstructed_tables
        ],
        "detected_sections": detected_sections,
        "status": AnalysisStatus.INGESTING.value,
        "current_agent": "data_ingestor_agent",
        "errors": errors,
        "reasoning_trace": reasoning_trace,
    }
