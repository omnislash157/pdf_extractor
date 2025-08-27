#!/usr/bin/env python3
"""
DrawSnap Parser v1 - CLI Table Extraction Tool
===============================================
Bulldozer approach: Always produces output, logs everything, fails loudly.

Extracts tables from single-page PDFs using vendor-specific templates.
Supports both native PDF text extraction and OCR for scanned documents.

Usage:
    python extract.py --pdf invoice.pdf --vendor sysco --output result.xlsx
    python extract.py --pdf scan.pdf --vendor amazon --output result.xlsx --ocr

Author: DrawSnap Team
Version: 1.0.0
"""

import argparse
import json
import os
import sys
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from statistics import median
from dataclasses import dataclass

# Third-party imports
import pandas as pd
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import fitz  # PyMuPDF for native extraction

# ============================================================================
# CONFIGURATION
# ============================================================================

# Logging setup - bulldozer style (loud and clear)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('drawsnap_parser')

# Constants
DEFAULT_DPI = 150
DEFAULT_CONFIDENCE = 60
DEFAULT_ROW_THRESHOLD = 20
LOG_DIR = 'logs'
LOG_FILE = 'parser_log.txt'
TEMPLATES_FILE = 'vendor_templates.json'
HEADER_MAPPINGS_FILE = 'header_mappings.json'

# Tool paths configuration
# TODO: Move to central config module when refactoring
try:
    import config
    TESSERACT_CMD = config.TESSERACT_CMD
    POPPLER_PATH = config.POPPLER_PATH
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    logger.info(f"Loaded config - Tesseract: {TESSERACT_CMD}")
except ImportError:
    logger.warning("No config.py found - using fallback paths")
    # Hardcoded fallbacks for corporate environment
    TESSERACT_CMD = r"C:\Users\mhartigan\tools\tesseract\tesseract.exe"
    POPPLER_PATH = r"C:\Users\mhartigan\tools\poppler-24.08.0\Library\bin"
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ExtractedText:
    """Container for extracted text with position data."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float
    page: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for compatibility."""
        return {
            'text': self.text,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'confidence': self.confidence,
            'page': self.page
        }


# ============================================================================
# OCR EXTRACTION
# ============================================================================

class OCRExtractor:
    """
    Handles OCR-based text extraction from PDFs.
    Uses Tesseract for optical character recognition on rendered pages.
    
    TODO: Extract to separate ocr_engine.py module
    """
    
    def __init__(self, 
                 confidence_threshold: int = DEFAULT_CONFIDENCE, 
                 dpi: int = DEFAULT_DPI, 
                 tesseract_config: str = "--psm 6",
                 poppler_path: str = POPPLER_PATH):
        """
        Initialize OCR extractor.
        
        Args:
            confidence_threshold: Minimum confidence for text (0-100)
            dpi: Resolution for PDF rendering
            tesseract_config: Tesseract page segmentation mode
            poppler_path: Path to Poppler binaries
        """
        self.confidence_threshold = confidence_threshold
        self.dpi = dpi
        self.tesseract_config = tesseract_config
        self.poppler_path = poppler_path
        
        logger.info(f"OCRExtractor initialized - DPI: {dpi}, Confidence: {confidence_threshold}")
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from PDF using OCR.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text items with position data
            
        Raises:
            RuntimeError: If PDF conversion fails
            ValueError: If PDF has no pages
        """
        # Convert PDF to images
        try:
            if self.poppler_path and os.path.exists(self.poppler_path):
                logger.info(f"Converting PDF with Poppler at: {self.poppler_path}")
                images = convert_from_path(pdf_path, dpi=self.dpi, poppler_path=self.poppler_path)
            else:
                logger.warning("Poppler path not found, using system PATH")
                images = convert_from_path(pdf_path, dpi=self.dpi)
        except Exception as e:
            error_msg = f"PDF conversion failed for {pdf_path}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Handle multi-page PDFs (bulldozer: just use first page)
        if len(images) > 1:
            logger.warning(f"Multi-page PDF detected ({len(images)} pages) - using page 1 only")
            # TODO: Add multi-page support with page parameter
            images = [images[0]]
        elif len(images) == 0:
            raise ValueError(f"No pages found in PDF: {pdf_path}")
        
        # Extract text from image
        extracted = []
        for page_num, img in enumerate(images, 1):
            page_text = self._extract_from_image(img, page_num)
            extracted.extend(page_text)
            logger.info(f"Extracted {len(page_text)} text items from page {page_num}")
        
        return extracted
    
    def _extract_from_image(self, img: Image.Image, page_num: int) -> List[Dict[str, Any]]:
        """
        Extract text from a single image using Tesseract.
        
        Args:
            img: PIL Image object
            page_num: Page number for tracking
            
        Returns:
            List of extracted text items
        """
        # Run Tesseract OCR
        try:
            data = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT, 
                config=self.tesseract_config
            )
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return []
        
        # Filter and structure results
        extracted = []
        for i in range(len(data['text'])):
            confidence = int(data['conf'][i])
            text = data['text'][i].strip()
            
            # Apply confidence threshold and skip empty text
            if confidence > self.confidence_threshold and text:
                extracted.append({
                    'text': text,
                    'page': page_num,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': confidence
                })
        
        return extracted


# ============================================================================
# NATIVE PDF EXTRACTION
# ============================================================================

def extract_native(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text from native PDF (non-scanned) using PyMuPDF.
    Much faster than OCR and preserves exact text.
    
    TODO: Move to pdf_engine.py module
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of text items with position data
    """
    logger.info(f"Attempting native extraction from: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        raise
    
    # Handle multi-page (bulldozer: use first page)
    if len(doc) > 1:
        logger.warning(f"Multi-page PDF ({len(doc)} pages) - using page 1 only")
        # TODO: Add page parameter support
    
    page = doc[0]
    
    # Extract text blocks with positions
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception as e:
        logger.error(f"Failed to extract text blocks: {e}")
        doc.close()
        raise
    
    extracted = []
    
    # Process each text block
    for block in blocks:
        if "lines" not in block:
            continue
            
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                
                # Get bounding box
                bbox = span["bbox"]
                extracted.append({
                    'text': text,
                    'page': 1,
                    'x': int(bbox[0]),
                    'y': int(bbox[1]),
                    'width': int(bbox[2] - bbox[0]),
                    'height': int(bbox[3] - bbox[1]),
                    'confidence': 100  # Native text has perfect confidence
                })
    
    doc.close()
    logger.info(f"Native extraction found {len(extracted)} text items")
    
    return extracted


# ============================================================================
# TABLE SLICING
# ============================================================================

class TableSlicer:
    """
    Converts positioned text into structured table using template boundaries.
    Core bulldozer logic - bins text into rows and columns.
    
    TODO: Extract to table_slicer.py module
    """
    
    def __init__(self, 
                 row_threshold: int = DEFAULT_ROW_THRESHOLD, 
                 adaptive_threshold: bool = True, 
                 buffer_factor: float = 1.2):
        """
        Initialize table slicer.
        
        Args:
            row_threshold: Default pixel threshold for row grouping
            adaptive_threshold: Use adaptive threshold based on text gaps
            buffer_factor: Multiplier for adaptive threshold
        """
        self.default_row_threshold = row_threshold
        self.adaptive_threshold = adaptive_threshold
        self.buffer_factor = buffer_factor
        logger.info(f"TableSlicer initialized - Adaptive: {adaptive_threshold}")
    
    def slice_to_table(self, 
                       extracted: List[Dict[str, Any]], 
                       table_box: List[int], 
                       columns: List[int], 
                       page: int = 1) -> pd.DataFrame:
        """
        Slice extracted text into table structure.
        
        Bulldozer guarantee: Always returns a DataFrame, even if empty.
        
        Args:
            extracted: List of extracted text items
            table_box: [x1, y1, x2, y2] defining table region
            columns: X-positions of column separators
            page: Page number to process
            
        Returns:
            DataFrame with table data
        """
        # Filter for specified page
        extracted = [item for item in extracted if item.get('page', 1) == page]
        if not extracted:
            logger.warning(f"No text found on page {page}")
            return pd.DataFrame([['No text found']])
        
        # Filter text within table box
        in_box = self._filter_in_box(extracted, table_box)
        if not in_box:
            logger.warning("No text found within table boundaries")
            return pd.DataFrame([['No text in box']])
        
        logger.info(f"Found {len(in_box)} text items in table region")
        
        # Determine row grouping threshold
        if self.adaptive_threshold:
            row_threshold = self._get_adaptive_row_threshold(in_box)
            logger.info(f"Using adaptive row threshold: {row_threshold:.1f}px")
        else:
            row_threshold = self.default_row_threshold
        
        # Group text into rows
        rows = self._group_into_rows(in_box, row_threshold)
        if not rows:
            logger.warning("Could not form any rows from text")
            return pd.DataFrame([['No rows formed']])
        
        logger.info(f"Grouped text into {len(rows)} rows")
        
        # Bin rows into columns
        table_data = self._bin_into_columns(rows, columns)
        
        # Ensure consistent column count
        if table_data:
            max_cols = max(len(row) for row in table_data)
            for row in table_data:
                while len(row) < max_cols:
                    row.append('')
        
        return pd.DataFrame(table_data)
    
    def _filter_in_box(self, 
                      extracted: List[Dict[str, Any]], 
                      table_box: List[int]) -> List[Dict[str, Any]]:
        """Filter text items within table boundaries."""
        x1, y1, x2, y2 = table_box
        in_box = []
        
        for item in extracted:
            # Use center point for more forgiving matching
            center_x = item['x'] + item.get('width', 0) / 2
            center_y = item['y'] + item.get('height', 0) / 2
            
            if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                in_box.append(item)
        
        return in_box
    
    def _get_adaptive_row_threshold(self, 
                                   text_boxes: List[Dict[str, Any]], 
                                   min_gap: float = 5.0, 
                                   max_threshold: float = 50.0) -> float:
        """Calculate adaptive threshold based on text spacing."""
        if not text_boxes:
            return self.default_row_threshold
        
        # Get unique y-coordinates
        y_coords = sorted(set(box.get('y', 0) for box in text_boxes))
        
        if len(y_coords) < 2:
            return self.default_row_threshold
        
        # Calculate gaps between consecutive y-positions
        gaps = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords) - 1)]
        
        # Filter significant gaps
        significant_gaps = [g for g in gaps if g >= min_gap]
        
        if not significant_gaps:
            return self.default_row_threshold
        
        # Use median gap with buffer
        median_gap = median(significant_gaps)
        threshold = median_gap * self.buffer_factor
        
        # Clamp to reasonable range
        return min(max(threshold, min_gap), max_threshold)
    
    def _group_into_rows(self, 
                        items: List[Dict[str, Any]], 
                        row_threshold: float) -> List[List[Dict[str, Any]]]:
        """Group text items into rows based on y-position."""
        if not items:
            return []
        
        # Sort by y-position
        items = sorted(items, key=lambda x: x['y'])
        
        rows = []
        current_row = [items[0]]
        current_row_y = items[0]['y']
        
        for item in items[1:]:
            # Check if item belongs to current row
            if abs(item['y'] - current_row_y) <= row_threshold:
                current_row.append(item)
                # Update row y as weighted average (optional refinement)
                # TODO: Consider using median y instead
            else:
                # Start new row
                rows.append(current_row)
                current_row = [item]
                current_row_y = item['y']
        
        # Add last row
        if current_row:
            rows.append(current_row)
        
        return rows
    
    def _bin_into_columns(self, 
                         rows: List[List[Dict[str, Any]]], 
                         columns: List[int]) -> List[List[str]]:
        """Bin text items in each row into columns."""
        if not columns or len(columns) < 2:
            # No valid columns - put everything in single column
            logger.warning("Invalid column definition - creating single column")
            return [[' '.join(item['text'] for item in row)] for row in rows]
        
        num_cols = len(columns) - 1
        table_data = []
        
        for row_idx, row in enumerate(rows):
            # Sort items left to right
            row = sorted(row, key=lambda x: x['x'])
            
            # Initialize column texts
            col_texts = [''] * num_cols
            
            for item in row:
                # Find column by center position
                center_x = item['x'] + item.get('width', 0) / 2
                
                # Find appropriate column
                placed = False
                for c in range(num_cols):
                    if columns[c] <= center_x < columns[c + 1]:
                        if col_texts[c]:
                            col_texts[c] += ' '
                        col_texts[c] += item['text']
                        placed = True
                        break
                
                # Handle edge cases (text outside columns)
                if not placed:
                    if center_x < columns[0]:
                        # Before first column
                        col_texts[0] = item['text'] + ' ' + col_texts[0] if col_texts[0] else item['text']
                    elif center_x >= columns[-1]:
                        # After last column
                        if col_texts[-1]:
                            col_texts[-1] += ' '
                        col_texts[-1] += item['text']
            
            # Clean up column texts
            col_texts = [text.strip() for text in col_texts]
            table_data.append(col_texts)
        
        return table_data


# ============================================================================
# EXCEL EXPORT
# ============================================================================

def apply_header_mapping(df: pd.DataFrame, vendor: str) -> Tuple[pd.DataFrame, bool]:
    """
    Apply header mapping if available for vendor.
    
    TODO: Move to export_engine.py module
    
    Args:
        df: DataFrame to apply headers to
        vendor: Vendor name for mapping lookup
        
    Returns:
        Tuple of (modified DataFrame, success flag)
    """
    if not os.path.exists(HEADER_MAPPINGS_FILE):
        logger.info("No header mappings file found")
        return df, False
    
    try:
        with open(HEADER_MAPPINGS_FILE, 'r') as f:
            mappings = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Failed to load header mappings: {e}")
        return df, False
    
    if vendor not in mappings:
        logger.info(f"No header mapping for vendor: {vendor}")
        return df, False
    
    mapping = mappings[vendor]
    
    # Validate mapping length
    if len(mapping) != len(df.columns):
        logger.warning(f"Header mapping mismatch - Expected {len(df.columns)}, got {len(mapping)}")
        return df, False
    
    # Apply headers
    df.columns = mapping
    logger.info(f"Applied header mapping for {vendor}: {mapping}")
    
    return df, True


def export_to_excel(df: pd.DataFrame, output_path: str, include_headers: bool = True) -> None:
    """
    Export DataFrame to Excel file.
    
    Args:
        df: DataFrame to export
        output_path: Path for output Excel file
        include_headers: Whether to include column headers
        
    Raises:
        IOError: If export fails
    """
    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # Export to Excel
        df.to_excel(output_path, index=False, header=include_headers)
        logger.info(f"Exported {df.shape[0]} rows x {df.shape[1]} cols to: {output_path}")
        
    except Exception as e:
        error_msg = f"Failed to export to Excel: {e}"
        logger.error(error_msg)
        raise IOError(error_msg)


# ============================================================================
# LOGGING
# ============================================================================

def log_run(pdf_path: str, vendor: str, success: bool, error: Optional[str] = None) -> None:
    """
    Log extraction run to persistent log file.
    
    Args:
        pdf_path: Input PDF path
        vendor: Vendor name used
        success: Whether extraction succeeded
        error: Error message if failed
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    timestamp = datetime.datetime.now().isoformat()
    
    # Build log entry
    status = "SUCCESS" if success else "FAIL"
    entry = f"{timestamp} | {pdf_path} | {vendor} | {status}"
    
    if error:
        entry += f" | {error}"
    
    entry += "\n"
    
    # Append to log
    try:
        with open(log_path, 'a') as f:
            f.write(entry)
    except IOError as e:
        logger.warning(f"Failed to write to log file: {e}")


# ============================================================================
# MAIN CLI
# ============================================================================

def load_template(vendor: str) -> Dict[str, Any]:
    """
    Load vendor template from JSON file.
    
    Args:
        vendor: Vendor name
        
    Returns:
        Template dictionary
        
    Raises:
        FileNotFoundError: If templates file not found
        ValueError: If vendor not found
    """
    if not os.path.exists(TEMPLATES_FILE):
        raise FileNotFoundError(f"Templates file not found: {TEMPLATES_FILE}")
    
    with open(TEMPLATES_FILE, 'r') as f:
        templates = json.load(f)
    
    if vendor not in templates:
        available = ', '.join(sorted(templates.keys()))
        raise ValueError(f"No template for vendor '{vendor}'. Available: {available}")
    
    return templates[vendor]


def main():
    """Main CLI entry point."""
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="DrawSnap Parser v1 - Extract tables from single-page PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract using native PDF text
  %(prog)s --pdf invoice.pdf --vendor sysco --output result.xlsx
  
  # Force OCR mode for scanned PDFs
  %(prog)s --pdf scan.pdf --vendor amazon --output result.xlsx --ocr
  
  # List available vendors
  %(prog)s --list-vendors
        """
    )
    
    parser.add_argument('--pdf', help='Path to single-page PDF')
    parser.add_argument('--vendor', help='Vendor name for template selection')
    parser.add_argument('--output', help='Output Excel file path')
    parser.add_argument('--ocr', action='store_true', 
                       help='Force OCR mode (for scanned PDFs)')
    parser.add_argument('--list-vendors', action='store_true',
                       help='List available vendor templates')
    
    args = parser.parse_args()
    
    # Handle list vendors
    if args.list_vendors:
        try:
            with open(TEMPLATES_FILE, 'r') as f:
                templates = json.load(f)
            vendors = sorted(templates.keys())
            print("Available vendors:")
            for v in vendors:
                print(f"  - {v}")
            return 0
        except Exception as e:
            print(f"Error listing vendors: {e}")
            return 1
    
    # Validate required arguments
    if not all([args.pdf, args.vendor, args.output]):
        parser.error("--pdf, --vendor, and --output are required")
    
    # Main extraction flow
    try:
        # Load template
        logger.info(f"Loading template for vendor: {args.vendor}")
        template = load_template(args.vendor)
        table_box = template['table_box']
        columns = template['columns']
        
        # Extract text
        logger.info(f"Extracting from PDF: {args.pdf}")
        if args.ocr:
            logger.info("Using OCR extraction mode")
            extractor = OCRExtractor()
            extracted = extractor.extract_from_pdf(args.pdf)
        else:
            logger.info("Using native PDF extraction mode")
            extracted = extract_native(args.pdf)
        
        logger.info(f"Total text items extracted: {len(extracted)}")
        
        # Slice to table
        logger.info("Slicing text into table structure")
        slicer = TableSlicer()
        df = slicer.slice_to_table(extracted, table_box, columns, page=1)
        
        logger.info(f"Table shape: {df.shape}")
        
        # Apply header mapping if available
        df, headers_applied = apply_header_mapping(df, args.vendor)
        
        # Export to Excel
        export_to_excel(df, args.output, include_headers=headers_applied)
        
        # Log success
        log_run(args.pdf, args.vendor, success=True)
        
        # Success message (bulldozer style - loud and clear)
        print(f"✅ SUCCESS: Table extracted to {args.output}")
        print(f"   Shape: {df.shape[0]} rows x {df.shape[1]} columns")
        if headers_applied:
            print(f"   Headers: Applied from mapping")
        
        return 0
        
    except Exception as e:
        # Log failure
        log_run(args.pdf if 'args' in locals() else 'unknown', 
               args.vendor if 'args' in locals() else 'unknown',
               success=False, 
               error=str(e))
        
        # Error message (bulldozer style - fail loudly)
        print(f"❌ FAILED: {e}")
        logger.error(f"Extraction failed: {e}", exc_info=True)
        
        return 1


if __name__ == '__main__':
    sys.exit(main()


# ============================================================================
# TODO: Future Modularization Plan
# ============================================================================
"""
When ready to split into modules:

1. ocr_engine.py
   - OCRExtractor class
   - Image preprocessing functions
   - Confidence filtering logic

2. pdf_engine.py  
   - extract_native function
   - PyMuPDF utilities
   - Multi-page support

3. table_slicer.py
   - TableSlicer class  
   - Row/column detection algorithms
   - Adaptive threshold logic

4. export_engine.py
   - Excel export functions
   - Header mapping logic
   - CSV export option

5. config.py
   - All configuration constants
   - Tool paths
   - Default parameters

6. extract.py (this file)
   - CLI interface only
   - Orchestration logic
   - Logging coordination
"""