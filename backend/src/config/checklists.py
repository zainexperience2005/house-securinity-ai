"""Statutory map-scrutiny checklists and document-type labels.

Checklist dicts map stable ``check_id`` keys to human-readable requirements.
Jev grades each id as PASS / CORRECTION_REQUIRED / NOT_APPLICABLE / PENDING.
``DOC_TYPES`` is used at the gate so resumes and invoices never reach vision.
"""

ARCHITECTURAL_CHECKLIST = {
    "title_block": "Title block with project name, plot number, owner, location, sheet title, date/revision",
    "architect_seal": "Signature/stamp of the registered architect on the architectural sheet",
    "scale_north": "Drawing scale and north arrow",
    "site_plan": "Site/block plan showing plot boundary, adjoining road(s) and road width",
    "setbacks": "Front, rear and side setbacks/open spaces dimensioned",
    "floor_plans": "Ground, first (if any) and roof floor plans",
    "sections_elevations": "At least one building section and exterior elevation(s)",
    "area_schedule": "Schedule of areas (plot, covered area per floor, coverage %)",
    "tank_details": "U.G.W.T. and O.H.W.T. details with dimensions or capacity",
    "septic_detail": "Septic tank detail with plan and section",
    "boundary_wall": "Boundary wall section/detail with height",
}

STRUCTURAL_CHECKLIST = {
    "title_block": "Title block with project name, plot number, owner, location, sheet title, date/revision",
    "structural_engineer_seal": "Signature and official PEC stamp/seal of registered Structural Engineer on structural sheets",
    "foundation_plan": "Foundation/footing layout (raft/strip/pad) with dimensions and excavation depth",
    "column_schedule": "Column schedule detailing column cross-sections, longitudinal rebar count/diameter, and ties",
    "beam_schedule": "Beam schedule/framing detailing beam dimensions, main top/bottom rebar, and stirrup spacing",
    "slab_reinforcement": "Slab reinforcement detailing slab thickness, main/distribution bar diameter, and spacing",
    "structural_notes": "General structural notes specifying concrete compressive strength (fc'), steel yield strength (fy), and clear cover",
    "seismic_design_code": "Seismic zone designation (e.g. Zone 2A/2B, BCP/UBC) and design load specifications",
}

CERTIFICATE_CHECKLIST = {
    "stability_cert": "Structural stability certificate document present in the submission",
    "cert_pec_registration": "Pakistan Engineering Council (PEC) registration number of structural engineer stated on certificate",
    "cert_engineer_signature": "Physical/digital signature and official stamp/seal of the structural engineer on certificate",
    "cert_plot_reference": "Explicit plot, block, sector, and owner name match on the stability certificate",
    "cert_date_validity": "Certificate issuance date clearly stated",
    "cert_design_scope": "Clear structural design scope statement (vetted for structural & seismic stability)",
}

# Master combined checklist
CHECKLIST = {**ARCHITECTURAL_CHECKLIST, **STRUCTURAL_CHECKLIST, **CERTIFICATE_CHECKLIST}

# Document classifications
DOC_TYPES = {
    "architectural_drawing": "Architectural submission drawing: site/floor plans, elevations, sections, area schedule. Do not classify resumes, letters, invoices, reports, or contracts as drawings.",
    "structural_drawing": "Structural drawing: slab/beam/column/foundation layout, reinforcement, structural notes. Do not classify resumes, letters, invoices, reports, or contracts as drawings.",
    "stability_certificate": "Structural stability certificate or other signed certificate/letter",
    "other": "Any non-engineering PDF, including resumes/CVs, invoices, letters, contracts, reports, academic documents, photographs, forms, marketing material, and unrelated certificates.",
}

# Judgment outcomes
STATUS = {
    "PASS": "Requirement is clearly and legibly present in the evidence",
    "CORRECTION_REQUIRED": "Requirement is clearly missing, wrong, illegible or incomplete",
    "NOT_APPLICABLE": "Requirement does not apply to this document or project",
    "PENDING": "Might be sufficient but the evidence cannot be confirmed",
}
