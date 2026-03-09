"""
Intelli-Credit: Automated Corporate Credit Appraisal Engine
FastAPI Application Entry Point — Production Architecture

State Management:
  - Redis for shared analysis state across workers
  - Supabase for persistent database records
  - Local filesystem for temporary file processing only
"""

import logging
import uuid
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Header, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import jwt

from app.config import get_settings, ensure_directories
from app.models.schemas import (
    AnalyzeCompanyRequest,
    UploadResponse,
    AnalysisResponse,
    ReportResponse,
    AnalysisStatus,
    CAMReport,
)
from app.graph.workflow import run_credit_appraisal
from app.agents.research import research_agent
from app.agents.data_ingestor_agent import data_ingestor_agent
from app.db.supabase_client import get_supabase_client, is_supabase_configured
from app.db.supabase_repository import get_supabase_repository
from app.services.redis_state import get_redis_state
from app.services.storage_service import get_storage_service

# ─── Logging Configuration ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("app.main")


def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user_id from Supabase JWT token in Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    try:
        settings = get_settings()
        token = authorization.split(" ")[1]
        
        # Secure verification if secret is provided and not the placeholder
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")
        
        if settings.SUPABASE_JWT_SECRET and settings.SUPABASE_JWT_SECRET != "your_jwt_secret_here":
            try:
                payload = jwt.decode(
                    token, 
                    settings.SUPABASE_JWT_SECRET, 
                    algorithms=[alg], 
                    options={"verify_aud": False} 
                )
            except ValueError as e:
                # ECC (ES256) requires a proper public key payload, not a string UUID.
                logger.warning(f"Key format mismatch for algorithm '{alg}': {e}. Falling back to insecure decoding.")
                payload = jwt.decode(token, options={"verify_signature": False}, algorithms=[alg])
        else:
            logger.warning("SUPABASE_JWT_SECRET not configured or is placeholder. Insecurely decoding JWT without signature verification.")
            payload = jwt.decode(token, options={"verify_signature": False}, algorithms=[alg])

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub claim")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"JWT decode error: {e}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    ensure_directories()

    # Connect Redis
    redis_state = get_redis_state()
    try:
        await redis_state.connect()
        redis_ok = True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}. Falling back to degraded mode.")
        redis_ok = False

    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  {settings.APP_DESCRIPTION}")
    logger.info(f"  LLM Model: {settings.LLM_MODEL}")
    logger.info(f"  Supabase: {'✓ Connected' if is_supabase_configured() else '✗ Not configured'}")
    logger.info(f"  Redis:    {'✓ Connected' if redis_ok else '✗ Unavailable'}")
    logger.info(f"  Workers:  {settings.WORKERS}")
    logger.info("=" * 60)

    yield

    # Shutdown: disconnect Redis
    await redis_state.disconnect()
    logger.info("Intelli-Credit shutting down...")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — Configurable from environment
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background Task Runner ──────────────────────────────────────────────────

async def _run_workflow_background(
    analysis_id: str,
    company_name: str,
    sector: str,
    due_diligence_notes: str,
    loan_amount_requested: Optional[float],
):
    """Run the credit appraisal workflow in the background."""
    redis_state = get_redis_state()
    repo = get_supabase_repository()
    storage = get_storage_service()

    # Resolve document paths: Redis → Supabase → Local filesystem
    document_paths = await redis_state.get_documents(analysis_id)
    if not document_paths and repo.is_available:
        docs = await repo.get_documents_for_analysis(analysis_id)
        document_paths = [d["file_path"] for d in docs if d.get("file_path")]
    if not document_paths:
        document_paths = storage.get_local_paths(analysis_id)

    # Set processing status in Redis + Supabase
    await redis_state.set_status(analysis_id, AnalysisStatus.PROCESSING.value)
    await repo.update_analysis_status(analysis_id, AnalysisStatus.PROCESSING.value)

    logger.info(f"Background workflow started for analysis {analysis_id}")

    try:
        result = await run_credit_appraisal(
            analysis_id=analysis_id,
            company_name=company_name,
            sector=sector,
            document_paths=document_paths,
            due_diligence_notes=due_diligence_notes,
            loan_amount_requested=loan_amount_requested,
        )

        # Persist results to Redis (shared across workers)
        final_status = result.get("status", AnalysisStatus.COMPLETED.value)
        await redis_state.set_result(analysis_id, result)
        await redis_state.set_status(analysis_id, final_status)
        logger.info(f"Workflow completed for {analysis_id}: {final_status}")

    except Exception as e:
        logger.error(f"Workflow failed for {analysis_id}: {str(e)}")
        failed_result = {
            "status": AnalysisStatus.FAILED.value,
            "errors": [str(e)],
        }
        await redis_state.set_status(analysis_id, AnalysisStatus.FAILED.value)
        await redis_state.set_result(analysis_id, failed_result)
        await repo.update_analysis_status(analysis_id, AnalysisStatus.FAILED.value)


# ─── API Endpoints ───────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "description": settings.APP_DESCRIPTION,
        "supabase_connected": is_supabase_configured(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    repo = get_supabase_repository()
    supabase_connected = repo.is_available

    # Check Redis connectivity
    redis_state = get_redis_state()
    try:
        await redis_state.pool.ping()
        redis_connected = True
    except Exception:
        redis_connected = False

    # Count from Supabase if available
    active_count = 0
    completed_count = 0
    review_count = 0

    if supabase_connected:
        analyses_list = await repo.list_analyses(limit=1000)
        active_count = len(analyses_list)
        completed_count = sum(1 for a in analyses_list if a.get("status") == AnalysisStatus.COMPLETED.value)
        review_count = sum(1 for a in analyses_list if a.get("status") == AnalysisStatus.NEEDS_REVIEW.value)

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "supabase_connected": supabase_connected,
        "redis_connected": redis_connected,
        "active_analyses": active_count,
        "completed_analyses": completed_count,
        "needs_review": review_count,
    }


@app.post("/upload-documents", response_model=UploadResponse, tags=["Documents"])
async def upload_documents(
    files: List[UploadFile] = File(...),
    analysis_id: Optional[str] = Form(None),
    user_id: Optional[str] = Depends(get_current_user_id),
):
    """
    Upload financial documents for analysis.

    Accepts PDF files. Returns an analysis_id to use with /analyze-company.
    """
    if not analysis_id:
        analysis_id = str(uuid.uuid4())

    repo = get_supabase_repository()
    redis_state = get_redis_state()
    storage = get_storage_service()

    # Create analysis record in Supabase (status=queued)
    if repo.is_available:
        placeholder = f"Draft ({files[0].filename[:20]}...)" if files else "New Appraisal"
        await repo.create_analysis(
            analysis_id=analysis_id,
            company_name=placeholder,
            sector="Drafting...",
            user_id=user_id,
            status=AnalysisStatus.QUEUED.value,
        )

    uploaded_files = []

    for file in files:
        if not file.filename:
            continue

        # Validate file type
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are accepted. Got: {file.filename}",
            )

        content = await file.read()

        # Save via storage service (local + Supabase Storage)
        local_path, storage_path = await storage.save_upload(
            analysis_id=analysis_id,
            file_name=file.filename,
            file_content=content,
        )

        uploaded_files.append(local_path)
        logger.info(f"Uploaded: {file.filename} ({len(content)} bytes)")

        # Create document record in Supabase
        if repo.is_available:
            await repo.create_document(
                analysis_id=analysis_id,
                file_name=file.filename,
                file_path=local_path,
                storage_path=storage_path,
                file_size=len(content),
            )

    # Store document paths in Redis (shared across workers)
    await redis_state.add_documents(analysis_id, uploaded_files)
    await redis_state.set_status(analysis_id, AnalysisStatus.PENDING.value)

    return UploadResponse(
        message=f"Successfully uploaded {len(uploaded_files)} document(s)",
        analysis_id=analysis_id,
        uploaded_files=[Path(f).name for f in uploaded_files],
        file_count=len(uploaded_files),
    )


@app.post("/analyze-company", response_model=AnalysisResponse, tags=["Analysis"])
async def analyze_company(
    request: AnalyzeCompanyRequest,
    background_tasks: BackgroundTasks,
    analysis_id: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
):
    """
    Trigger company credit appraisal analysis.

    Runs the full LangGraph multi-agent workflow:
    Router → Data Ingestor → Research → Risk Analysis → CAM Generator

    The workflow runs in the background. Use GET /report/{id} to check status.
    """
    redis_state = get_redis_state()

    if not analysis_id:
        analysis_id = str(uuid.uuid4())

    repo = get_supabase_repository()

    await redis_state.set_status(analysis_id, AnalysisStatus.PROCESSING.value)
    created_at = None

    # Update or create analysis record in Supabase with company details
    if repo.is_available:
        existing = await repo.get_analysis(analysis_id)
        if existing:
            # Check ownership
            if existing.get("user_id") and str(existing.get("user_id")) != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized access to this analysis")
                
            await repo.update_analysis_results(
                analysis_id=analysis_id,
                company_name=request.company_name,
                sector=request.sector,
                status=AnalysisStatus.PROCESSING.value,
            )
            created_at = existing.get("created_at")
        else:
            new_record = await repo.create_analysis(
                analysis_id=analysis_id,
                company_name=request.company_name,
                sector=request.sector,
                status=AnalysisStatus.PROCESSING.value,
                loan_amount_requested=request.loan_amount_requested,
                due_diligence_notes=request.due_diligence_notes or "",
                user_id=user_id,
            )
            if new_record:
                created_at = new_record.get("created_at")

    # Launch background workflow
    background_tasks.add_task(
        _run_workflow_background,
        analysis_id=analysis_id,
        company_name=request.company_name,
        sector=request.sector,
        due_diligence_notes=request.due_diligence_notes or "",
        loan_amount_requested=request.loan_amount_requested,
    )

    logger.info(f"Analysis triggered for {request.company_name} (ID: {analysis_id})")

    return AnalysisResponse(
        message=f"Credit appraisal workflow started for {request.company_name}",
        analysis_id=analysis_id,
        status=AnalysisStatus.PROCESSING,
        created_at=created_at,
    )


@app.post("/research-only", tags=["Research"])
async def debug_research_only(
    request: AnalyzeCompanyRequest,
):
    """
    Execute ONLY the Research Agent intelligence pipeline.
    
    Returns the structured research signals and risk score without
    triggering the full credit appraisal workflow or requiring documents.
    """
    analysis_id = f"debug_{uuid.uuid4().hex[:8]}"
    logger.info(f"Manual research trigger for {request.company_name} (ID: {analysis_id})")

    # Initial state for research agent
    state = {
        "analysis_id": analysis_id,
        "company_name": request.company_name,
        "sector": request.sector,
        "errors": [],
    }

    try:
        # Execute the upgraded research agent orchestrator
        result = await research_agent(state)
        
        return {
            "analysis_id": analysis_id,
            "company_name": request.company_name,
            "sector": request.sector,
            "research_signals_summary": result.get("research_signals", {}),
            "full_research_report": result.get("research_report", {}),
            "articles_analyzed": result.get("research_signals", {}).get("articles_analyzed", 0),
            "sources_used": result.get("research_signals", {}).get("sources_used", 0),
            "errors": result.get("errors", []),
        }
    except Exception as e:
        logger.error(f"Research-only endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.post("/ingestion-only/{analysis_id}", tags=["Documents"])
async def debug_ingestion_only(analysis_id: str):
    """
    Execute ONLY the Data Ingestor Agent for a specific analysis.
    
    Requires that documents have already been uploaded for this analysis_id.
    Returns the extracted text and financial metrics.
    """
    redis_state = get_redis_state()
    storage = get_storage_service()

    # Resolve documents: Redis → Supabase → Local
    document_paths = await redis_state.get_documents(analysis_id)
    if not document_paths:
        repo = get_supabase_repository()
        if repo.is_available:
            docs = await repo.get_documents_for_analysis(analysis_id)
            document_paths = [d["file_path"] for d in docs if d.get("file_path")]
    if not document_paths:
        document_paths = storage.get_local_paths(analysis_id)

    if not document_paths:
        raise HTTPException(
            status_code=404, 
            detail=f"No documents found for analysis_id '{analysis_id}'. Please upload documents first."
        )

    logger.info(f"Manual ingestion trigger for ID: {analysis_id}")

    # Initial state for ingestor agent
    state = {
        "analysis_id": analysis_id,
        "document_paths": document_paths,
        "errors": [],
    }

    try:
        # Execute the data ingestor agent
        result = await data_ingestor_agent(state)
        
        return {
            "analysis_id": analysis_id,
            "document_count": len(document_paths),
            "extracted_text_snippet": result.get("extracted_text", "")[:1000] + "...",
            "financial_metrics": result.get("financial_metrics", {}),
            "errors": result.get("errors", []),
            "status": result.get("status"),
        }
    except Exception as e:
        logger.error(f"Ingestion-only endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/parser-only", tags=["Documents"])
async def debug_parser_only(file: UploadFile = File(...)):
    """
    Execute ONLY the Enhanced Document Parser for an uploaded PDF.
    
    Returns the advanced metadata (OCR status, tables, images) and text
    without running any LLM agents.
    """
    from app.services.document_parser import get_enhanced_parser
    import tempfile
    import os
    
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    logger.info(f"Manual parser trigger for file: {file.filename}")

    # Save to temp file for processing
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        content = await file.read()
        with os.fdopen(tmp_fd, "wb") as f:
            f.write(content)
            
        parser = get_enhanced_parser()
        text, metadata = await parser.extract_text_from_pdf(tmp_path)
        
        return {
            "filename": file.filename,
            "metadata": metadata,
            "text_preview": text[:2000] + "..." if text else None,
            "message": "Parser metadata retrieved successfully."
        }
    except Exception as e:
        logger.error(f"Parser-only endpoint failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.get("/report/{analysis_id}", response_model=ReportResponse, tags=["Reports"])
async def get_report(analysis_id: str, user_id: str = Depends(get_current_user_id)):
    """
    Retrieve the generated Credit Appraisal Memo report.

    Returns the full CAM report with all sections, financial metrics,
    risk analysis, and lending recommendation.
    """
    redis_state = get_redis_state()
    repo = get_supabase_repository()

    # Priority: Redis → Supabase
    status = await redis_state.get_status(analysis_id)
    result = await redis_state.get_result(analysis_id) or {}
    created_at = None
    updated_at = None

    if repo.is_available:
        db_analysis = await repo.get_analysis(analysis_id)
        if db_analysis:
            # Check ownership
            if db_analysis.get("user_id") and str(db_analysis.get("user_id")) != user_id:
                raise HTTPException(status_code=403, detail="Unauthorized access to this analysis")
                
            status = status or db_analysis.get("status")
            created_at = db_analysis.get("created_at")
            updated_at = db_analysis.get("updated_at")

        db_report = await repo.get_report(analysis_id)
        if db_report and db_report.get("json_report"):
            result = result or {"cam_report": db_report["json_report"]}
            if not updated_at:
                updated_at = db_report.get("updated_at")

    if status is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis ID '{analysis_id}' not found",
        )

    # Build CAM report from result if available
    cam_data = result.get("cam_report")
    cam_report = None
    docx_url = None
    pdf_url = None

    if cam_data:
        try:
            cam_report = CAMReport(**cam_data)
        except Exception as e:
            logger.error(f"Failed to parse CAM report: {e}")

    return ReportResponse(
        analysis_id=analysis_id,
        status=AnalysisStatus(status),
        created_at=created_at,
        updated_at=updated_at,
        report=cam_report,
        docx_download_url=docx_url,
        pdf_download_url=pdf_url,
        errors=result.get("errors", []),
    )


@app.get("/analyses", tags=["Analysis"])
async def list_analyses(user_id: Optional[str] = Depends(get_current_user_id)):
    """List all analyses and their statuses."""
    repo = get_supabase_repository()

    if repo.is_available:
        # Fetch from Supabase, filtered by user_id
        db_analyses = await repo.list_analyses(limit=50, user_id=user_id)
        analyses = []
        for a in db_analyses:
            analyses.append({
                "analysis_id": a.get("id"),
                "status": a.get("status"),
                "company_name": a.get("company_name", "Unknown"),
                "sector": a.get("sector", ""),
                "risk_score": a.get("risk_score"),
                "credit_grade": a.get("credit_grade"),
                "created_at": a.get("created_at"),
                "has_report": a.get("status") == AnalysisStatus.COMPLETED.value,
            })
        return {"analyses": analyses, "total": len(analyses)}

    # Fallback: check Redis for any known analyses
    redis_state = get_redis_state()
    analysis_ids = await redis_state.list_analysis_ids()
    analyses = []
    for aid in analysis_ids:
        s = await redis_state.get_status(aid) or "unknown"
        r = await redis_state.get_result(aid) or {}
        cam = r.get("cam_report", {})
        analyses.append({
            "analysis_id": aid,
            "status": s,
            "company_name": cam.get("company_name", r.get("company_name", "Unknown")),
            "has_report": bool(cam),
        })
    return {"analyses": analyses, "total": len(analyses)}


@app.get("/metrics/{analysis_id}", tags=["Observability"])
async def get_agent_metrics(analysis_id: str):
    """
    Get agent performance metrics for a completed analysis.

    Returns timing, status, and error information for each agent
    that participated in the workflow.
    """
    redis_state = get_redis_state()
    result = await redis_state.get_result(analysis_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Analysis '{analysis_id}' not found")

    agent_metrics = result.get("agent_metrics", {})
    reasoning_trace = result.get("reasoning_trace", [])
    credit_score = result.get("credit_score", {})
    validation = result.get("validation_result", {})

    return {
        "analysis_id": analysis_id,
        "workflow_version": result.get("workflow_version", "unknown"),
        "status": result.get("status"),
        "agent_metrics": agent_metrics,
        "reasoning_trace": reasoning_trace,
        "credit_score": credit_score,
        "validation_result": validation,
        "errors": result.get("errors", []),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level="info",
    )
