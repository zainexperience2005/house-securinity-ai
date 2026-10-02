"""Review cases, persistent SQLite packages, drawing page rendering, and engineer sign-offs."""

from fastapi import APIRouter, HTTPException, Response

from src.api.schemas import ReviewDecision
from src.core.case_store import add_review, get_case, list_cases, render_case_page

router = APIRouter(prefix="/api/v1/cases", tags=["Review Cases"])


@router.get("", summary="List recent review cases")
def list_cases_endpoint(limit: int = 50):
    """List recent persistent review cases."""
    cases = list_cases(limit=limit)
    return {"count": len(cases), "cases": cases}


@router.get("/{case_id}", summary="Get case details and review history")
def get_case_endpoint(case_id: str):
    """Return the persisted audit package, verdict, and engineer review history."""
    case = get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.get("/{case_id}/evidence/{page_number}", summary="Render drawing page for inspection")
def get_case_evidence(case_id: str, page_number: int):
    """Render a source drawing page for an engineer to inspect a cited finding."""
    try:
        image = render_case_page(case_id, page_number)
        return Response(content=image, media_type="image/png")
    except KeyError:
        raise HTTPException(status_code=404, detail="Case not found.")
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{case_id}/reviews", summary="Record engineer review decision")
def create_review(case_id: str, review: ReviewDecision):
    """Record an engineer's decision without modifying the original AI verdict."""
    try:
        return add_review(case_id, review.reviewer_name, review.decision, review.note)
    except KeyError:
        raise HTTPException(status_code=404, detail="Case not found.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
