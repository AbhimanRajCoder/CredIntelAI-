"""
Enhanced Document Parser Service for Intelli-Credit.
Production-grade PDF extraction with:
  - Intelligent layout detection (headers, tables, narrative, footers)
  - OCR with confidence validation and text aggregation
  - Bbox-based table detection for scanned pages
  - Financial table reconstruction into structured JSON
  - Parallel page processing and smart chunking

Architecture:
  PDF Page
    ├─ Digital? → pdfplumber text + tables + layout detection
    └─ Scanned? → PaddleOCR
                    ├─ Confidence validation (reject < 0.65)
                    ├─ Text aggregation → page_text, text_length  ← CRITICAL
                    ├─ Layout detection on OCR text
                    ├─ Bbox-based table reconstruction
                    └─ Financial table classification
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict

import pdfplumber
import numpy as np

logger = logging.getLogger(__name__)

# ─── Lazy-loaded optional dependencies ────────────────────────────────────────
_ocr_engine = None
_camelot_available = False
_pdf2image_available = False

# ─── OCR confidence threshold (0.0 – 1.0) ────────────────────────────────────
OCR_CONFIDENCE_THRESHOLD = 0.65

# ─── Bbox table detection tuning ──────────────────────────────────────────────
BBOX_ROW_Y_TOLERANCE = 15        # pixels: lines within this Y-gap = same row
BBOX_MIN_TABLE_ROWS = 3          # minimum rows to qualify as a table
BBOX_MIN_TABLE_COLS = 2          # minimum columns per row to qualify as a table


def _get_ocr_engine():
    """Lazy-load PaddleOCR engine with angle classification."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=False,
            )
            logger.info("PaddleOCR engine initialized successfully")
        except ImportError:
            logger.warning("PaddleOCR not available – OCR extraction will be skipped.")
        except Exception as e:
            logger.warning(f"PaddleOCR initialization failed: {e}")
    return _ocr_engine


def _check_dependencies():
    """One-time check for optional heavy dependencies."""
    global _camelot_available, _pdf2image_available

    try:
        import camelot  # noqa: F401
        _camelot_available = True
        logger.info("Camelot-py available for advanced table extraction")
    except ImportError:
        logger.info("Camelot-py not available – pdfplumber fallback for tables")

    try:
        from pdf2image import convert_from_path  # noqa: F401
        _pdf2image_available = True
        logger.info("pdf2image available for page-level OCR")
    except ImportError:
        logger.info("pdf2image not available – OCR will use full PDF mode")


# ═════════════════════════════════════════════════════════════════════════════
# Data classes
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class OCRLineResult:
    """A single OCR-detected line with spatial and confidence data."""
    text: str
    confidence: float
    bbox: List[List[float]]    # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    center_x: float
    center_y: float
    width: float
    height: float


@dataclass
class OCRConfidenceReport:
    """Per-page confidence statistics produced by PaddleOCR."""
    page_num: int
    total_lines: int
    accepted_lines: int
    rejected_lines: int
    average_confidence: float
    min_confidence: float
    max_confidence: float
    low_confidence_texts: List[str] = field(default_factory=list)


@dataclass
class DetectedRegion:
    """A classified region on a page (heading / table / narrative / footer)."""
    region_type: str          # "heading", "sub_heading", "table", "narrative", "footer", "page_number"
    content: str
    bbox: Optional[Tuple[float, float, float, float]] = None  # x0, y0, x1, y1
    confidence: Optional[float] = None
    rows: Optional[int] = None       # for table regions
    columns: Optional[int] = None    # for table regions


@dataclass
class ReconstructedTable:
    """A financial table reconstructed from raw extraction into clean JSON."""
    page_num: int
    headers: List[str]
    rows: List[Dict[str, Any]]
    raw_grid: List[List[str]]
    table_type: str           # "balance_sheet", "pnl", "cashflow", "ratios", "generic"
    confidence: float
    source: str               # "pdfplumber", "camelot", "ocr_bbox"


@dataclass
class PageMetadata:
    """Metadata for a single PDF page."""
    page_num: int
    is_scanned: bool
    has_tables: bool
    has_images: bool
    text_length: int
    layout_regions: List[DetectedRegion] = field(default_factory=list)
    ocr_confidence: Optional[OCRConfidenceReport] = None


@dataclass
class DocumentMetadata:
    """Metadata for the entire parsed document."""
    file_name: str
    total_pages: int
    text_pages: int
    scanned_pages: int
    tables_detected: int
    images_detected: int
    total_characters: int
    reconstructed_tables: List[ReconstructedTable] = field(default_factory=list)
    page_metadata: List[PageMetadata] = field(default_factory=list)
    ocr_summary: Optional[Dict[str, Any]] = None


# ═════════════════════════════════════════════════════════════════════════════
# Core parser
# ═════════════════════════════════════════════════════════════════════════════

class EnhancedDocumentParser:
    """Production-grade document parser with layout detection, OCR confidence
    validation, table detection, and financial table reconstruction.

    Key guarantees:
      - OCR text is ALWAYS aggregated into page_text and text_length
      - Layout detection runs on BOTH digital and scanned pages
      - Table detection works on scanned PDFs via bounding-box analysis
      - Every table is reconstructed into typed JSON
    """

    # ── Financial header keywords used for layout + table classification ──
    FINANCIAL_KEYWORDS = {
        "balance_sheet": [
            "balance sheet", "assets", "liabilities", "equity", "shareholders fund",
            "reserves and surplus", "non-current assets", "current assets",
            "total assets", "total liabilities",
        ],
        "pnl": [
            "profit and loss", "income statement", "statement of profit",
            "revenue from operations", "total income", "total expenses",
            "profit before tax", "profit after tax", "ebitda", "pat",
        ],
        "cashflow": [
            "cash flow", "cashflow", "operating activities",
            "investing activities", "financing activities",
            "net cash", "cash and cash equivalents",
        ],
        "ratios": [
            "financial ratios", "key ratios", "debt equity",
            "current ratio", "interest coverage", "return on equity",
            "net profit margin", "operating margin",
        ],
    }

    def __init__(self, chunk_size: int = 2000, preserve_structure: bool = True):
        self.chunk_size = chunk_size
        self.preserve_structure = preserve_structure
        _check_dependencies()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. SCANNED-PAGE DETECTION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_scanned_page(page) -> bool:
        """Heuristic: decide whether a pdfplumber page is scanned (image-only)."""
        text = page.extract_text()

        if not text or len(text.strip()) < 30:
            return True

        # Large images covering > 60 % of page area ⇒ scanned
        if page.images:
            page_area = page.width * page.height
            image_area = sum(
                (img["x1"] - img["x0"]) * (img["y1"] - img["y0"])
                for img in page.images
            )
            if page_area > 0 and (image_area / page_area) > 0.6:
                return True

        # Extremely short average word length ⇒ garbage text layer
        words = text.split()
        if words:
            avg_word_len = len(text.replace(" ", "")) / len(words)
            if avg_word_len < 2:
                return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # 2. LAYOUT DETECTION (works on raw text — digital OR OCR)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_layout_from_text(self, text: str, page_num: int) -> List[DetectedRegion]:
        """Classify every line of text into layout regions.

        Works identically for pdfplumber-extracted text and OCR-aggregated text.

        Categories:
          - heading / sub_heading – bold or large-font lines / financial section titles
          - table                – lines with ≥ 3 columns separated by 2+ spaces
          - narrative            – free-flowing paragraph text
          - footer / page_number – bottom-of-page artifacts
        """
        regions: List[DetectedRegion] = []
        if not text or not text.strip():
            return regions

        lines = text.split("\n")
        total_lines = max(len(lines), 1)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            y_ratio = idx / total_lines

            # ── Footer / page number ──
            if y_ratio > 0.92 and (
                re.match(r"^\d{1,3}$", stripped)
                or re.match(r"^page\s*\d+", stripped, re.IGNORECASE)
                or len(stripped) < 10
            ):
                regions.append(DetectedRegion(region_type="page_number", content=stripped))
                continue

            # ── Heading detection ──
            is_heading = False
            if stripped.isupper() and len(stripped) < 80:
                is_heading = True
            if re.match(r"^(schedule|note|annexure|appendix|part)\s", stripped, re.IGNORECASE):
                is_heading = True
            lower = stripped.lower()
            for _cat, kws in self.FINANCIAL_KEYWORDS.items():
                if any(kw in lower for kw in kws):
                    is_heading = True
                    break

            if is_heading:
                rtype = "heading" if y_ratio < 0.15 or stripped.isupper() else "sub_heading"
                regions.append(DetectedRegion(region_type=rtype, content=stripped))
                continue

            # ── Inline table heuristic: ≥ 3 columns separated by 2+ spaces ──
            cols = re.split(r"\s{2,}", stripped)
            if len(cols) >= 3:
                regions.append(DetectedRegion(region_type="table", content=stripped))
                continue

            # ── Default: narrative ──
            regions.append(DetectedRegion(region_type="narrative", content=stripped))

        return regions

    # ─────────────────────────────────────────────────────────────────────────
    # 3. OCR WITH CONFIDENCE VALIDATION + RAW BBOX PRESERVATION
    # ─────────────────────────────────────────────────────────────────────────

    def _parse_ocr_lines(self, raw_ocr_page: list) -> List[OCRLineResult]:
        """Parse raw PaddleOCR output into structured OCRLineResult objects."""
        results: List[OCRLineResult] = []
        if not raw_ocr_page:
            return results

        for line in raw_ocr_page:
            if not line or len(line) < 2:
                continue
            bbox = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            text = line[1][0]
            conf = float(line[1][1])

            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            results.append(OCRLineResult(
                text=text,
                confidence=conf,
                bbox=bbox,
                center_x=(min(xs) + max(xs)) / 2,
                center_y=(min(ys) + max(ys)) / 2,
                width=max(xs) - min(xs),
                height=max(ys) - min(ys),
            ))
        return results

    def _filter_by_confidence(
        self, ocr_lines: List[OCRLineResult], page_num: int
    ) -> Tuple[List[OCRLineResult], OCRConfidenceReport]:
        """Filter OCR lines by confidence threshold.
        Returns accepted lines AND a detailed confidence report."""
        accepted: List[OCRLineResult] = []
        rejected_texts: List[str] = []
        all_confs = [l.confidence for l in ocr_lines]

        for line in ocr_lines:
            if line.confidence >= OCR_CONFIDENCE_THRESHOLD:
                accepted.append(line)
            else:
                rejected_texts.append(f"[conf={line.confidence:.2f}] {line.text}")

        report = OCRConfidenceReport(
            page_num=page_num,
            total_lines=len(ocr_lines),
            accepted_lines=len(accepted),
            rejected_lines=len(rejected_texts),
            average_confidence=round(sum(all_confs) / len(all_confs), 4) if all_confs else 0.0,
            min_confidence=round(min(all_confs), 4) if all_confs else 0.0,
            max_confidence=round(max(all_confs), 4) if all_confs else 0.0,
            low_confidence_texts=rejected_texts[:10],
        )

        logger.info(
            f"OCR page {page_num}: {report.accepted_lines}/{report.total_lines} "
            f"lines accepted (avg conf {report.average_confidence:.2f}, "
            f"threshold {OCR_CONFIDENCE_THRESHOLD})"
        )
        return accepted, report

    def _aggregate_ocr_text(self, accepted_lines: List[OCRLineResult]) -> str:
        """Join accepted OCR lines into a single text string (sorted by Y, then X).

        THIS IS THE CRITICAL STEP that was missing:
           OCR lines → sorted text → page_text → text_length
        """
        if not accepted_lines:
            return ""

        # Sort by vertical position (top→bottom), then horizontal (left→right)
        sorted_lines = sorted(accepted_lines, key=lambda l: (l.center_y, l.center_x))
        return "\n".join(line.text for line in sorted_lines)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. BBOX-BASED TABLE DETECTION (for scanned pages)
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_tables_from_bboxes(
        self, ocr_lines: List[OCRLineResult], page_num: int
    ) -> List[ReconstructedTable]:
        """Detect tables from OCR bounding box positions.

        Algorithm:
          1. Group lines by Y-coordinate (± tolerance) → rows
          2. Within each row, sort by X-coordinate → columns
          3. If ≥ BBOX_MIN_TABLE_ROWS consecutive rows have ≥ BBOX_MIN_TABLE_COLS → table
          4. Reconstruct into grid and then into ReconstructedTable
        """
        if not ocr_lines:
            return []

        # ── Step 1: cluster lines into rows by Y-position ──
        sorted_by_y = sorted(ocr_lines, key=lambda l: l.center_y)
        rows: List[List[OCRLineResult]] = []
        current_row: List[OCRLineResult] = [sorted_by_y[0]]

        for line in sorted_by_y[1:]:
            if abs(line.center_y - current_row[-1].center_y) <= BBOX_ROW_Y_TOLERANCE:
                current_row.append(line)
            else:
                rows.append(current_row)
                current_row = [line]
        rows.append(current_row)

        # ── Step 2: sort each row by X-position ──
        for row in rows:
            row.sort(key=lambda l: l.center_x)

        # ── Step 3: find consecutive multi-column rows (table candidates) ──
        tables: List[ReconstructedTable] = []
        table_start = None
        consecutive_multi_col: List[List[OCRLineResult]] = []

        for i, row in enumerate(rows):
            if len(row) >= BBOX_MIN_TABLE_COLS:
                consecutive_multi_col.append(row)
            else:
                # End of a table candidate
                if len(consecutive_multi_col) >= BBOX_MIN_TABLE_ROWS:
                    table = self._reconstruct_table_from_bbox_rows(
                        consecutive_multi_col, page_num
                    )
                    if table:
                        tables.append(table)
                consecutive_multi_col = []

        # Handle table at end of page
        if len(consecutive_multi_col) >= BBOX_MIN_TABLE_ROWS:
            table = self._reconstruct_table_from_bbox_rows(
                consecutive_multi_col, page_num
            )
            if table:
                tables.append(table)

        if tables:
            logger.info(f"Bbox table detection found {len(tables)} table(s) on page {page_num}")

        return tables

    def _reconstruct_table_from_bbox_rows(
        self, bbox_rows: List[List[OCRLineResult]], page_num: int
    ) -> Optional[ReconstructedTable]:
        """Convert clustered bbox rows into a ReconstructedTable."""
        if not bbox_rows:
            return None

        # Determine the maximum number of columns
        max_cols = max(len(row) for row in bbox_rows)

        # Build raw grid
        raw_grid: List[List[str]] = []
        for row in bbox_rows:
            cells = [line.text for line in row]
            # Pad to max_cols
            while len(cells) < max_cols:
                cells.append("")
            raw_grid.append(cells)

        # Average confidence of all lines in the table
        all_confs = [line.confidence for row in bbox_rows for line in row]
        avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0

        # Use the shared reconstruction logic
        rt = self._reconstruct_table(raw_grid, page_num)
        if rt:
            rt.confidence = round(avg_conf, 4)
            rt.source = "ocr_bbox"
        return rt

    # ─────────────────────────────────────────────────────────────────────────
    # 5. TABLE RECONSTRUCTION (shared logic)
    # ─────────────────────────────────────────────────────────────────────────

    def _classify_table_type(self, headers: List[str], rows: List[List[str]]) -> str:
        """Map a table to a financial category based on its header keywords."""
        header_text = " ".join(h.lower() for h in headers if h)
        all_text = header_text + " " + " ".join(
            " ".join(str(c).lower() for c in r if c) for r in rows[:5]
        )
        for cat, kws in self.FINANCIAL_KEYWORDS.items():
            if any(kw in all_text for kw in kws):
                return cat
        return "generic"

    @staticmethod
    def _clean_cell(cell: Any) -> str:
        """Normalise a single table cell value."""
        if cell is None:
            return ""
        s = str(cell).strip()
        s = re.sub(r"\s+", " ", s)
        return s

    @staticmethod
    def _parse_numeric(value: str) -> Any:
        """Attempt to coerce a string to a numeric Python type."""
        if not value:
            return None
        cleaned = re.sub(r"[₹$,\s]", "", value)
        cleaned = cleaned.replace("(", "-").replace(")", "")
        multiplier = 1
        lower = cleaned.lower()
        if lower.endswith("cr") or lower.endswith("crore"):
            cleaned = re.sub(r"(cr|crore)$", "", lower)
            multiplier = 1e7
        elif lower.endswith("l") or lower.endswith("lakh"):
            cleaned = re.sub(r"(l|lakh)$", "", lower)
            multiplier = 1e5
        try:
            return round(float(cleaned) * multiplier, 2)
        except (ValueError, TypeError):
            return value

    def _reconstruct_table(
        self, raw_table: List[List[str]], page_num: int
    ) -> Optional[ReconstructedTable]:
        """Convert a raw grid into a structured ReconstructedTable with typed values."""
        if not raw_table or len(raw_table) < 2:
            return None

        cleaned = [[self._clean_cell(c) for c in row] for row in raw_table]

        # Identify header row – first row with ≥2 non-empty cells
        header_idx = 0
        for i, row in enumerate(cleaned):
            non_empty = sum(1 for c in row if c)
            if non_empty >= 2:
                header_idx = i
                break

        headers = cleaned[header_idx]
        final_headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
        data_rows = cleaned[header_idx + 1:]

        dict_rows: List[Dict[str, Any]] = []
        for row in data_rows:
            if not any(c for c in row):
                continue
            entry: Dict[str, Any] = {}
            for col_idx, header in enumerate(final_headers):
                raw_val = row[col_idx] if col_idx < len(row) else ""
                entry[header] = self._parse_numeric(raw_val) if raw_val else None
            dict_rows.append(entry)

        if not dict_rows:
            return None

        table_type = self._classify_table_type(final_headers, data_rows)

        return ReconstructedTable(
            page_num=page_num,
            headers=final_headers,
            rows=dict_rows,
            raw_grid=cleaned,
            table_type=table_type,
            confidence=1.0,
            source="pdfplumber",
        )

    def _extract_tables_from_text_layer(
        self, file_path: str
    ) -> Tuple[List[ReconstructedTable], int]:
        """Extract tables from PDF text layer (Camelot → pdfplumber fallback).
        Only works for digital PDFs with a text layer."""
        reconstructed: List[ReconstructedTable] = []
        raw_count = 0

        if _camelot_available:
            try:
                import camelot
                cam_tables = camelot.read_pdf(
                    file_path, pages="all", flavor="stream", edge_tol=50,
                )
                for ct in cam_tables:
                    raw_count += 1
                    grid = ct.df.values.tolist()
                    rt = self._reconstruct_table(grid, page_num=ct.page)
                    if rt:
                        rt.source = "camelot"
                        reconstructed.append(rt)
                logger.info(f"Camelot extracted {raw_count} raw tables → {len(reconstructed)} reconstructed")
                return reconstructed, raw_count
            except Exception as e:
                logger.warning(f"Camelot failed ({e}), falling back to pdfplumber")

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    for table in (page.extract_tables() or []):
                        raw_count += 1
                        rt = self._reconstruct_table(table, page_num=page_num)
                        if rt:
                            rt.source = "pdfplumber"
                            reconstructed.append(rt)
            logger.info(f"pdfplumber extracted {raw_count} raw tables → {len(reconstructed)} reconstructed")
        except Exception as e:
            logger.error(f"Text-layer table extraction failed: {e}")

        return reconstructed, raw_count

    # ─────────────────────────────────────────────────────────────────────────
    # 6. TEXT CLEANING
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted/OCR text for LLM consumption."""
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\s+\.", ".", text)
        text = re.sub(r"\s+,", ",", text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        # Common OCR mis-reads
        text = text.replace("|", "I")
        text = re.sub(r"(\d)\s+,\s+(\d)", r"\1,\2", text)
        return text.strip()

    # ─────────────────────────────────────────────────────────────────────────
    # 7. METADATA EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_metadata_from_text(text: str, file_name: str) -> Dict[str, Any]:
        """Pull dates, currencies, and candidate company names from text."""
        metadata: Dict[str, Any] = {
            "file_name": file_name,
            "dates_found": [],
            "currencies_found": [],
            "potential_company_names": [],
        }
        date_patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
        ]
        for pat in date_patterns:
            metadata["dates_found"].extend(re.findall(pat, text, re.IGNORECASE))

        metadata["currencies_found"] = list(
            set(re.findall(r"[$€£¥₹]|USD|EUR|GBP|INR", text))
        )

        first_sec = text[:500]
        candidates = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b", first_sec)
        metadata["potential_company_names"] = list(set(candidates[:5]))
        return metadata

    # ─────────────────────────────────────────────────────────────────────────
    # 8. PAGE PROCESSING (async, for digital pages only)
    # ─────────────────────────────────────────────────────────────────────────

    async def _process_page_async(
        self, page, page_num: int
    ) -> Tuple[str, PageMetadata]:
        """Process a single digital page: extract text, detect layout, flag scanned."""
        is_scanned = self._is_scanned_page(page)
        has_images = len(page.images) > 0

        if not is_scanned:
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            text = text.strip()

            # Layout detection on digital text
            layout_regions = self._detect_layout_from_text(text, page_num)

            tables = page.extract_tables()
            has_tables = bool(tables)

            if self.preserve_structure:
                formatted = f"# Page {page_num}\n\n{text}"
                if tables:
                    formatted += "\n\n## Tables\n"
                    for i, table in enumerate(tables, 1):
                        formatted += f"\n### Table {i}\n"
                        for row in table[:10]:
                            formatted += " | ".join(str(c) for c in row if c) + "\n"
            else:
                formatted = text

            meta = PageMetadata(
                page_num=page_num,
                is_scanned=False,
                has_tables=has_tables,
                has_images=has_images,
                text_length=len(text),
                layout_regions=layout_regions,
            )
        else:
            # Scanned page — text will be populated AFTER OCR in the main pipeline
            formatted = ""  # placeholder, will be replaced
            meta = PageMetadata(
                page_num=page_num,
                is_scanned=True,
                has_tables=False,  # will be updated after bbox table detection
                has_images=has_images,
                text_length=0,    # ← WILL BE UPDATED after OCR text aggregation
                layout_regions=[], # ← WILL BE UPDATED after OCR layout detection
            )

        return formatted, meta

    # ─────────────────────────────────────────────────────────────────────────
    # 9. FULL OCR PIPELINE (for scanned pages)
    # ─────────────────────────────────────────────────────────────────────────

    def _run_ocr_on_pages(
        self, file_path: str, scanned_page_nums: List[int]
    ) -> Dict[int, List]:
        """Run PaddleOCR on specific pages, return raw results keyed by page number.
        Each value is the raw ocr page result (list of lines with bboxes)."""
        ocr = _get_ocr_engine()
        if not ocr:
            return {pn: [] for pn in scanned_page_nums}

        page_results: Dict[int, List] = {}

        if _pdf2image_available:
            try:
                from pdf2image import convert_from_path
                images = convert_from_path(
                    file_path,
                    first_page=min(scanned_page_nums),
                    last_page=max(scanned_page_nums),
                    dpi=300,
                )
                for page_num in scanned_page_nums:
                    img_idx = page_num - min(scanned_page_nums)
                    if img_idx < len(images):
                        img_array = np.array(images[img_idx])
                        result = ocr.ocr(img_array, cls=True)
                        page_results[page_num] = result[0] if result else []
                    else:
                        page_results[page_num] = []
                return page_results
            except Exception as e:
                logger.error(f"pdf2image OCR failed: {e}, trying full-PDF fallback")

        # Fallback: OCR entire PDF
        try:
            result = ocr.ocr(file_path, cls=True)
            if result:
                for page_num in scanned_page_nums:
                    idx = page_num - 1
                    page_results[page_num] = result[idx] if idx < len(result) and result[idx] else []
            else:
                page_results = {pn: [] for pn in scanned_page_nums}
        except Exception as e:
            logger.error(f"Full-PDF OCR failed: {e}")
            page_results = {pn: [] for pn in scanned_page_nums}

        return page_results

    def _process_scanned_page(
        self, raw_ocr_data: list, page_num: int
    ) -> Tuple[str, OCRConfidenceReport, List[DetectedRegion], List[ReconstructedTable]]:
        """Full processing pipeline for a single scanned page.

        Returns:
          - page_text:   the aggregated, cleaned OCR text
          - report:      OCR confidence report
          - regions:     layout regions detected from OCR text
          - tables:      tables detected from OCR bounding boxes
        """
        # ── Step A: Parse raw OCR into structured line objects ──
        ocr_lines = self._parse_ocr_lines(raw_ocr_data)

        # ── Step B: Filter by confidence ──
        accepted_lines, confidence_report = self._filter_by_confidence(ocr_lines, page_num)

        # ── Step C: AGGREGATE OCR TEXT (the critical missing step) ──
        page_text = self._aggregate_ocr_text(accepted_lines)
        page_text = self._clean_text(page_text) if page_text else ""

        # ── Step D: Layout detection on OCR text ──
        layout_regions = self._detect_layout_from_text(page_text, page_num)

        # ── Step E: Table detection from bounding boxes ──
        bbox_tables = self._detect_tables_from_bboxes(accepted_lines, page_num)

        # Add table regions to layout
        for table in bbox_tables:
            layout_regions.append(DetectedRegion(
                region_type="table",
                content=f"[Table: {table.table_type}, {len(table.rows)} rows × {len(table.headers)} cols]",
                rows=len(table.rows),
                columns=len(table.headers),
            ))

        return page_text, confidence_report, layout_regions, bbox_tables

    # ─────────────────────────────────────────────────────────────────────────
    # 10. CHUNKING
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        """Chunk with overlap, breaking on sentence boundaries when possible."""
        if len(text) <= chunk_size:
            return [text]

        chunks: List[str] = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                window = text[max(end - 100, start):min(end + 100, len(text))]
                for brk in [".", "!", "?", "\n\n"]:
                    pos = window.rfind(brk)
                    if pos > 50:
                        end = max(end - 100, start) + pos + 1
                        break
            chunks.append(text[start:end].strip())
            start = end - overlap
        return chunks

    # ─────────────────────────────────────────────────────────────────────────
    # 11. MAIN EXTRACTION ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    async def extract_text_from_pdf(
        self,
        file_path: str,
        include_tables: bool = True,
        include_metadata: bool = True,
    ) -> Tuple[str, Optional[DocumentMetadata]]:
        """
        Full extraction pipeline:
          1. Parallel page processing (digital pages → text + layout)
          2. OCR scanned pages with confidence validation
          3. Aggregate OCR text → page_text, text_length   ← FIXED
          4. Layout detection on OCR text                   ← FIXED
          5. Bbox-based table detection for scanned pages   ← FIXED
          6. Text-layer table detection for digital pages
          7. Combine, clean, and assemble metadata
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        logger.info(f"Starting enhanced extraction for: {path.name}")

        all_texts: List[str] = []
        page_meta_list: List[PageMetadata] = []
        scanned_pages: List[int] = []
        all_reconstructed_tables: List[ReconstructedTable] = []

        # ── Step 1: parallel page processing (classifies digital vs scanned) ──
        try:
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                tasks = [
                    self._process_page_async(page, pn)
                    for pn, page in enumerate(pdf.pages, start=1)
                ]
                results = await asyncio.gather(*tasks)

                for pn, (text, meta) in enumerate(results, start=1):
                    if meta.is_scanned:
                        scanned_pages.append(pn)
                    else:
                        all_texts.append(text)
                    page_meta_list.append(meta)
        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            raise

        # ── Step 2: OCR + text aggregation + layout + table detection for scanned pages ──
        ocr_reports: List[OCRConfidenceReport] = []
        if scanned_pages:
            logger.info(f"Running full OCR pipeline on {len(scanned_pages)} scanned pages")

            # 2a: Run OCR (get raw bboxes + text + confidence)
            raw_ocr_results = self._run_ocr_on_pages(file_path, scanned_pages)

            # 2b: Process each scanned page
            for page_num in scanned_pages:
                raw_data = raw_ocr_results.get(page_num, [])

                page_text, report, layout_regions, bbox_tables = (
                    self._process_scanned_page(raw_data, page_num)
                )

                ocr_reports.append(report)

                # ── UPDATE PageMetadata with OCR results (THE CRITICAL FIX) ──
                for pm in page_meta_list:
                    if pm.page_num == page_num:
                        pm.text_length = len(page_text)         # ← WAS 0, NOW CORRECT
                        pm.layout_regions = layout_regions       # ← WAS [], NOW POPULATED
                        pm.has_tables = len(bbox_tables) > 0     # ← WAS False, NOW CORRECT
                        pm.ocr_confidence = report
                        break

                # Collect bbox-detected tables
                all_reconstructed_tables.extend(bbox_tables)

                # Build formatted text for this page
                if self.preserve_structure:
                    header = f"# Page {page_num} (OCR — avg confidence {report.average_confidence:.0%})"
                    formatted_ocr = f"{header}\n\n{page_text}" if page_text else f"{header}\n\n[OCR produced no text]"
                else:
                    formatted_ocr = page_text or "[OCR produced no text]"

                all_texts.insert(page_num - 1, formatted_ocr)

                logger.info(
                    f"Page {page_num}: text_length={len(page_text)}, "
                    f"layout_regions={len(layout_regions)}, "
                    f"tables_from_bbox={len(bbox_tables)}"
                )

        # ── Step 3: Text-layer table detection for digital pages ──
        text_layer_tables: List[ReconstructedTable] = []
        text_layer_table_count = 0
        has_digital_pages = len(scanned_pages) < total_pages
        if include_tables and has_digital_pages:
            text_layer_tables, text_layer_table_count = self._extract_tables_from_text_layer(file_path)
            all_reconstructed_tables.extend(text_layer_tables)

        total_tables_detected = text_layer_table_count + sum(
            1 for pm in page_meta_list if pm.is_scanned and pm.has_tables
        )

        # ── Step 4: combine & clean all text ──
        final_text = "\n\n".join(all_texts)
        final_text = self._clean_text(final_text)

        # ── Step 5: assemble metadata ──
        metadata = None
        if include_metadata:
            _doc_meta = self._extract_metadata_from_text(final_text, path.name)

            ocr_summary = None
            if ocr_reports:
                all_conf = [r.average_confidence for r in ocr_reports if r.total_lines > 0]
                ocr_summary = {
                    "pages_ocr_processed": len(ocr_reports),
                    "total_lines_scanned": sum(r.total_lines for r in ocr_reports),
                    "total_lines_accepted": sum(r.accepted_lines for r in ocr_reports),
                    "total_lines_rejected": sum(r.rejected_lines for r in ocr_reports),
                    "overall_average_confidence": round(sum(all_conf) / len(all_conf), 4) if all_conf else 0.0,
                    "confidence_threshold_used": OCR_CONFIDENCE_THRESHOLD,
                }

            metadata = DocumentMetadata(
                file_name=path.name,
                total_pages=total_pages,
                text_pages=total_pages - len(scanned_pages),
                scanned_pages=len(scanned_pages),
                tables_detected=total_tables_detected + len(all_reconstructed_tables),
                images_detected=sum(1 for pm in page_meta_list if pm.has_images),
                total_characters=len(final_text),
                reconstructed_tables=all_reconstructed_tables,
                page_metadata=page_meta_list,
                ocr_summary=ocr_summary,
            )

            logger.info(f"""
PDF Parsing Summary
====================
File: {path.name}
Total Pages: {metadata.total_pages}
Text Pages: {metadata.text_pages}
Scanned Pages (OCR): {metadata.scanned_pages}
Tables Detected: {metadata.tables_detected}
  └─ Text-layer tables: {text_layer_table_count}
  └─ OCR bbox tables: {len(all_reconstructed_tables) - len(text_layer_tables)}
Reconstructed Tables: {len(all_reconstructed_tables)}
Images Detected: {metadata.images_detected}
Total Characters: {metadata.total_characters}
OCR Summary: {ocr_summary}
Per-page text lengths: {[(pm.page_num, pm.text_length) for pm in page_meta_list]}
            """.strip())

        return final_text, metadata

    # ─────────────────────────────────────────────────────────────────────────
    # 12. MULTI-FILE EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    async def extract_text_from_multiple(
        self,
        file_paths: List[str],
        combine: bool = True,
    ) -> Tuple[str, List[DocumentMetadata]]:
        """Extract from multiple PDFs, optionally combining all text."""
        results: List[str] = []
        all_metadata: List[DocumentMetadata] = []

        for fp in file_paths:
            try:
                text, meta = await self.extract_text_from_pdf(fp)
                fname = Path(fp).name
                if combine:
                    results.append(f"{'=' * 80}\nDocument: {fname}\n{'=' * 80}\n\n{text}")
                else:
                    results.append(text)
                if meta:
                    all_metadata.append(meta)
            except Exception as e:
                logger.error(f"Failed to extract from {fp}: {e}")
                results.append(f"[EXTRACTION FAILED: {Path(fp).name}]")

        final_text = "\n\n".join(results) if combine else results
        return final_text, all_metadata

    # ─────────────────────────────────────────────────────────────────────────
    # 13. UTILITY: RECONSTRUCTED TABLES → JSON
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def tables_to_json(tables: List[ReconstructedTable]) -> List[Dict[str, Any]]:
        """Serialize reconstructed tables into JSON-friendly dicts."""
        return [
            {
                "page": t.page_num,
                "table_type": t.table_type,
                "confidence": t.confidence,
                "source": t.source,
                "headers": t.headers,
                "data": t.rows,
            }
            for t in tables
        ]

    def chunk_for_llm(self, text: str) -> List[str]:
        """Chunk text for LLM context windows."""
        return self._chunk_text(text, self.chunk_size)


# ═════════════════════════════════════════════════════════════════════════════
# Factory & backwards-compatible wrappers
# ═════════════════════════════════════════════════════════════════════════════

def get_enhanced_parser(chunk_size: int = 2000) -> EnhancedDocumentParser:
    """Get an instance of the enhanced document parser."""
    return EnhancedDocumentParser(chunk_size=chunk_size)


class DocumentParser:
    """Backwards-compatible wrapper for existing agent code."""

    @staticmethod
    async def extract_text_from_pdf(file_path: str) -> str:
        parser = get_enhanced_parser()
        text, _ = await parser.extract_text_from_pdf(file_path, include_metadata=False)
        return text

    @staticmethod
    async def extract_text_from_multiple(file_paths: List[str]) -> str:
        parser = get_enhanced_parser()
        text, _ = await parser.extract_text_from_multiple(file_paths)
        return text

    @staticmethod
    async def extract_tables_from_pdf(file_path: str) -> List[List[List[str]]]:
        parser = get_enhanced_parser()
        tables, _ = parser._extract_tables_from_text_layer(file_path)
        return [t.raw_grid for t in tables]


# Singleton
_parser: Optional[DocumentParser] = None


def get_document_parser() -> DocumentParser:
    """Get the document parser singleton (backwards compatible)."""
    global _parser
    if _parser is None:
        _parser = DocumentParser()
    return _parser