import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    AutoReplyDraftResponse,
    TicketAnalysisResponse,
    TicketApprovalResponse,
    TicketApproveRequest,
    TicketDBResponse,
    TicketDBUpdate,
    TicketIngestionRequest,
    TicketProcessResult,
    TicketResolutionResponse,
)
from app.services.auto_reply_generator import auto_reply_service, policy_manager
from app.services.ticket_analyzer import analyzer_service
from app.services.ticket_service import ticket_db_service

router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets & AI Triage"])
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


# =====================================================================
# PHASE 2 & 4: ANALYSIS & AUTO-REPLY DRAFTING
# =====================================================================

@router.post(
    "/analyze",
    response_model=TicketAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest and analyze a customer support ticket",
    description="Classifies category, detects priority and sentiment, extracts key entities, and detects missing information.",
)
def analyze_ticket_endpoint(ticket: TicketIngestionRequest) -> TicketAnalysisResponse:
    try:
        return analyzer_service.analyze_ticket(ticket)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ticket analysis failed: {str(exc)}",
        ) from exc


@router.post(
    "/draft-reply",
    response_model=AutoReplyDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate policy-grounded AI auto-reply draft",
    description="Matches the ticket to company policy and drafts an empathetic, policy-grounded email response.",
)
def draft_reply_endpoint(ticket: TicketIngestionRequest) -> AutoReplyDraftResponse:
    try:
        analysis = analyzer_service.analyze_ticket(ticket)
        draft = auto_reply_service.generate_draft(ticket, analysis)
        return AutoReplyDraftResponse(**draft)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-reply generation failed: {str(exc)}",
        ) from exc


@router.post(
    "/process",
    response_model=TicketProcessResult,
    status_code=status.HTTP_201_CREATED,
    summary="Complete end-to-end processing & SQLite persistence",
    description="Analyzes the ticket, matches company policy, generates draft reply, and persists to SQLite.",
)
def process_and_persist_ticket(
    ticket: TicketIngestionRequest,
    db: Session = Depends(get_db),
) -> TicketProcessResult:
    try:
        return ticket_db_service.process_and_save_ticket(db, ticket)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Processing ticket failed: {str(exc)}",
        ) from exc


@router.post(
    "/analyze-batch",
    response_model=List[TicketAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Batch analyze multiple support tickets",
)
def analyze_batch_endpoint(tickets: List[TicketIngestionRequest]) -> List[TicketAnalysisResponse]:
    return [analyzer_service.analyze_ticket(t) for t in tickets]


@router.get(
    "/sample-analysis",
    response_model=List[TicketAnalysisResponse],
    status_code=status.HTTP_200_OK,
    summary="Run AI analysis on sample tickets",
)
def run_sample_tickets_analysis() -> List[TicketAnalysisResponse]:
    sample_file = BACKEND_DIR / "sample_tickets.json"
    if not sample_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="sample_tickets.json not found.",
        )

    with open(sample_file, "r", encoding="utf-8") as f:
        samples = json.load(f)

    results = []
    for item in samples:
        ingestion_req = TicketIngestionRequest(
            ticket_id=item["id"],
            customer_name=item["customer_name"],
            customer_email=item["customer_email"],
            subject=item["subject"],
            message=item["body"],
        )
        analyzed = analyzer_service.analyze_ticket(ingestion_req)
        results.append(analyzed)

    return results


# =====================================================================
# PHASE 4: SQLITE TICKET DATABASE & HUMAN-IN-THE-LOOP CRUD
# =====================================================================

@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Get real-time dashboard statistics",
)
def get_stats_endpoint(db: Session = Depends(get_db)):
    return ticket_db_service.get_dashboard_stats(db)


@router.post(
    "/seed-samples",
    response_model=List[TicketDBResponse],
    status_code=status.HTTP_200_OK,
    summary="Seed sample tickets with full AI copilot analysis and auto-replies",
)
def seed_samples_endpoint(db: Session = Depends(get_db)) -> List[TicketDBResponse]:
    sample_file = BACKEND_DIR / "sample_tickets.json"
    return ticket_db_service.seed_sample_tickets(db, sample_file)


# =====================================================================
# PHASE 6: DATA EXPORTS (CSV & JSON)
# =====================================================================

@router.get(
    "/export/csv",
    status_code=status.HTTP_200_OK,
    summary="Export tickets as CSV file download",
    description="Generates a downloadable CSV with Ticket ID, Customer, Category, Priority, Sentiment, Missing entities, Status, and Final response.",
)
def export_tickets_csv_endpoint(
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    ticket_status: Optional[str] = Query(None, description="Filter by ticket status"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    db: Session = Depends(get_db),
):
    csv_content = ticket_db_service.export_tickets_csv(
        db,
        category=category,
        priority=priority,
        ticket_status=ticket_status,
        approval_status=approval_status,
    )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="tickets_export.csv"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.get(
    "/export/json",
    status_code=status.HTTP_200_OK,
    summary="Export tickets as JSON file download",
    description="Generates a downloadable JSON file containing complete ticket analysis and response details.",
)
def export_tickets_json_endpoint(
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    ticket_status: Optional[str] = Query(None, description="Filter by ticket status"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status"),
    db: Session = Depends(get_db),
):
    json_data = ticket_db_service.export_tickets_json(
        db,
        category=category,
        priority=priority,
        ticket_status=ticket_status,
        approval_status=approval_status,
    )
    return JSONResponse(
        content=json_data,
        headers={
            "Content-Disposition": 'attachment; filename="tickets_export.json"',
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


# =====================================================================
# PHASE 6: TICKET ACTIONS (APPROVE, RESOLVE, REGENERATE)
# =====================================================================

@router.post(
    "/{ticket_id}/approve",
    response_model=TicketApprovalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve response and mock send email",
    description="Saves approved response, records approval status, and provides mock sending notice.",
)
def approve_ticket_endpoint(
    ticket_id: str,
    payload: Optional[TicketApproveRequest] = None,
    db: Session = Depends(get_db),
) -> TicketApprovalResponse:
    edited_text = payload.edited_response if payload else None
    result = ticket_db_service.approve_ticket(db, ticket_id, edited_response=edited_text)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return result


@router.post(
    "/{ticket_id}/resolve",
    response_model=TicketResolutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark ticket as resolved",
    description="Updates ticket status to resolved in SQLite and updates ticket timestamp.",
)
def resolve_ticket_endpoint(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> TicketResolutionResponse:
    result = ticket_db_service.resolve_ticket(db, ticket_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return result


@router.post(
    "/{ticket_id}/regenerate",
    response_model=TicketDBResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate policy-grounded draft reply for a ticket",
)
def regenerate_reply_endpoint(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> TicketDBResponse:
    record = ticket_db_service.regenerate_reply(db, ticket_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )
    return record


@router.get(
    "",
    response_model=List[TicketDBResponse],
    status_code=status.HTTP_200_OK,
    summary="List all tickets with filtering",
)
def list_tickets_endpoint(
    category: Optional[str] = Query(None, description="Filter by category"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    ticket_status: Optional[str] = Query(None, description="Filter by ticket status (open, resolved, etc.)"),
    approval_status: Optional[str] = Query(None, description="Filter by approval status (pending, approved, rejected)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[TicketDBResponse]:
    return ticket_db_service.list_tickets(
        db,
        category=category,
        priority=priority,
        ticket_status=ticket_status,
        approval_status=approval_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketDBResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single ticket by ID",
)
def get_ticket_endpoint(
    ticket_id: str,
    db: Session = Depends(get_db),
) -> TicketDBResponse:
    record = ticket_db_service.get_ticket(db, ticket_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found.",
        )
    return record


@router.patch(
    "/{ticket_id}",
    response_model=TicketDBResponse,
    status_code=status.HTTP_200_OK,
    summary="Update ticket (Approval, Edit response, Change status)",
)
def update_ticket_endpoint(
    ticket_id: str,
    updates: TicketDBUpdate,
    db: Session = Depends(get_db),
) -> TicketDBResponse:
    record = ticket_db_service.update_ticket(db, ticket_id, updates)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' not found.",
        )
    return record
