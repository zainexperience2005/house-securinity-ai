"""Vision: title-block detection, keyword crop clusters, and batched OpenAI extraction."""

from .crop_selector import find_intelligent_sheet_crops, nearby
from .extractor import run_vision_extraction_batch
from .title_block import detect_title_block_regions
