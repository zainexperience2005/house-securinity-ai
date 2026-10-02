"""PDF ingestion, injection defense, Jev calls, orientation, duplicates, and the SQLite review store."""

from .case_store import (
    add_review,
    create_case,
    get_case,
    list_reviews,
    merge_pdf_documents,
    render_case_page,
)
from .client import jev_call
from .duplicates import detect_duplicate_pages
from .orientation import get_page_effective_rotation, png
from .pdf_parser import extract_cad_vector_geometry, hidden_text, pack
from .security import scrub
