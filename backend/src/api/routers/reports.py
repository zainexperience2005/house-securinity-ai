"""Reports and statutory municipal bylaws endpoints."""

import io
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from pdf_generator import create_scrutiny_pdf_report
from src.api.common import raise_if_ineligible
from src.config.bylaws import BYLAW_DATABASE, get_bylaws_for_plot

router = APIRouter(tags=["Reports & Bylaws"])


@router.post("/api/v1/reports/pdf", summary="Generate official PDF scrutiny audit report")
async def generate_pdf_report(verdict: dict[str, Any]):
    """Generates a formal, downloadable PDF compliance scrutiny report from a verdict payload."""
    try:
        raise_if_ineligible(verdict)
        pdf_res = create_scrutiny_pdf_report(verdict)
        if isinstance(pdf_res, io.BytesIO):
            pdf_res.seek(0)
            stream = pdf_res
        else:
            stream = io.BytesIO(pdf_res)
        return StreamingResponse(
            stream,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=House_Scrutiny_Audit_Report.pdf"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF report generation failed: {e!s}")


@router.get("/api/v1/bylaws", summary="Retrieve statutory municipal bylaws")
def get_bylaws_endpoint(authority: str | None = None):
    """Retrieve bylaw standards, setbacks, and limits for supported municipal authorities."""
    if authority and authority in BYLAW_DATABASE:
        return {authority: BYLAW_DATABASE[authority]}
    return {"authorities": list(BYLAW_DATABASE.keys()) if BYLAW_DATABASE else [], "database": BYLAW_DATABASE}


@router.get("/api/v1/bylaws/{authority}", summary="Retrieve bylaws for specific authority and plot")
def get_authority_bylaws_endpoint(authority: str, marla: float | None = None):
    """Retrieves active society bylaws for a given authority and optional plot size."""
    rules, pkey, pdisp = get_bylaws_for_plot(marla, authority=authority)
    return {"authority": authority, "plot_category": pkey, "display_name": pdisp, "rules": rules}
