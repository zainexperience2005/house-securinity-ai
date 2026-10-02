"""House Scrutiny AI application package.

This package implements the drawing-scrutiny pipeline: PDF ingestion, sheet
classification, multimodal extraction, deterministic auditors, LangGraph
orchestration, and PDF reporting. Subpackages:

* ``config`` — bylaws, checklists, prompts, Pydantic schemas, env settings
* ``core`` — PDF parsing, injection scrubbing, Jev client, SQLite case store
* ``vision`` — title-block crops, keyword clustering, OpenAI vision batches
* ``auditors`` — bylaws, completeness, conflicts, evidence, revisions, sheets
* ``pipeline`` — LangGraph nodes and compiled graph
* ``reporting`` — ReportLab audit certificates
"""
