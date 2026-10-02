"""Pydantic models, typed literals, and LangGraph state.

These types are the contract between vision extraction, Jev checklist judging,
and the compiled verdict. Vision output is validated as ``Extraction`` so
downstream auditors never consume free-form JSON.
"""

from typing import Literal, TypedDict

from pydantic import BaseModel

# Numeric architectural fields that feed bylaw_check (setbacks, height, tanks, …).

ValueKey = Literal[
    "plot_area_marla",
    "front_setback_ft",
    "rear_setback_ft",
    "left_setback_ft",
    "right_setback_ft",
    "total_height_ft",
    "storeys",
    "ground_coverage_pct",
    "plinth_height_ft",
    "basement",
    "parking_bays",
    "boundary_wall_height_ft",
    "ugwt_gallons",
    "ohwt_gallons",
    "septic_length_ft",
    "septic_width_ft",
    "septic_depth_ft",
    "trees",
    "projection_ft",
]

# Structural engineering parameters (grades, schedules, seismic notes).
StructuralKey = Literal[
    "slab_thickness_in",
    "foundation_depth_ft",
    "concrete_grade_psi",
    "steel_grade_psi",
    "column_schedule_present",
    "beam_schedule_present",
    "slab_rebar_detail_present",
    "structural_notes_present",
    "seismic_zone_stated",
]

# Checklist item ids shared by architectural, structural, and certificate reviews.
CheckId = Literal[
    "title_block",
    "architect_seal",
    "scale_north",
    "site_plan",
    "setbacks",
    "floor_plans",
    "sections_elevations",
    "area_schedule",
    "tank_details",
    "septic_detail",
    "boundary_wall",
    "structural_engineer_seal",
    "foundation_plan",
    "column_schedule",
    "beam_schedule",
    "slab_reinforcement",
    "structural_notes",
    "seismic_design_code",
    "stability_cert",
    "cert_pec_registration",
    "cert_engineer_signature",
    "cert_plot_reference",
    "cert_date_validity",
    "cert_design_scope",
]


class RevisionEntry(BaseModel):
    """One row from a drawing revision table or title-block revision stamp."""

    revision_id: str = "Rev 0"
    date: str | None = None
    sheet_number: str | None = None
    description: str | None = None
    approved_by: str | None = None
    page: int | None = None


class Val(BaseModel):
    """A single extracted architectural design value with citation metadata."""

    key: ValueKey
    value: float | None
    evidence: str
    page: int | None = None
    bbox: list[float] | None = None
    context_span: str | None = None


class StructVal(BaseModel):
    """A single extracted structural parameter (numeric or 0/1 presence flags)."""

    key: StructuralKey
    value: float | None
    evidence: str
    page: int | None = None
    bbox: list[float] | None = None
    context_span: str | None = None


class StabilityCertData(BaseModel):
    """Fields pulled from a PEC stability certificate or covering letter."""

    engineer_name: str | None = None
    pec_registration_no: str | None = None
    cert_number: str | None = None
    cert_date: str | None = None
    plot_reference: str | None = None
    owner_name: str | None = None
    has_signature: bool | None = None
    has_stamp: bool | None = None
    scope: str | None = None
    soil_report_referenced: bool | None = None
    page: int | None = None
    bbox: list[float] | None = None


class Obs(BaseModel):
    """Vision observation for one checklist id (seen yes/no/unclear + evidence)."""

    check_id: CheckId
    seen: Literal["yes", "no", "unclear"]
    evidence: str
    page: int | None = None
    bbox: list[float] | None = None
    crop_label: str | None = None
    context_snippet: str | None = None


class Extraction(BaseModel):
    """Structured OpenAI vision payload merged across page batches."""

    values: list[Val] = []
    structural_values: list[StructVal] = []
    certificate_details: StabilityCertData | None = None
    observations: list[Obs] = []
    flags: list[str] = []
    revision: str | None = None
    revisions_table: list[RevisionEntry] = []


class S(TypedDict, total=False):
    """LangGraph state: keys are optional because nodes fill them incrementally."""

    pdf: str  # Filepath to the input PDF
    authority: str | None  # Target authority / society (DHA_Lahore, CDA_Islamabad, etc.)
    pages: list  # Page-by-page extracted data (text, annots, hidden text, hints)
    meta: dict  # PDF document metadata (Creator, CreationDate, etc.)
    embedded: list  # List of embedded files/attachments in the PDF
    layers: list  # Vector CAD & OCG layers (rebar, beams, columns, etc.)
    flags: list  # System flags (unreadable runs, hidden text, warnings)
    unreadable: bool  # Flag indicating if the PDF has no readable content
    doc_type: dict  # Classification result from TypeSafe Jev
    document_eligibility: str  # ELIGIBLE, UNSUPPORTED_DOCUMENT, or CLASSIFICATION_UNAVAILABLE
    shots: list  # Base64 rendered crops sent to vision model
    page_coverage: dict  # Complete page coverage tracking (page 1..N representation & metrics)
    security_audit: list  # Structured security audit records for prompt injection / scrubbed anomalies
    cad_geometry: dict  # True vector CAD drawing paths (lines, polylines, rects, curves, polygons)
    revisions_audit: dict  # Structured revision history and cross-sheet consistency audit
    evidence_chain: dict  # Source-level audit trail linking requirement -> evidence -> bbox -> tier -> decision
    duplicates_audit: dict  # Multi-signal duplicate page detection audit (text + CAD + visual hash)
    extraction: dict  # Raw parsed JSON from OpenAI Vision
    checks: dict  # Judgments per checklist item from TypeSafe Jev
    verdict: dict  # Final compiled audit report and compliance status
    token_usage: dict  # High-level token metrics
    jev_judge_usage: dict  # TypeSafe Jev usage during checklist evaluation (judge)
    openai_usage: dict  # OpenAI token usage metadata during vision extraction
    active_model: str | None  # Active multimodal model identifier (e.g. gpt-4o, gemini-1.5-flash)
