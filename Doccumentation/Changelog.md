# CHANGELOG - Table Slicer

All notable changes to Table Slicer are documented here. Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [2.1.1] - 2024-01-15

**Status:** 🟢 PRODUCTION READY - Bulldozer Gold Standard

### Added - Claude

- **QualityReport Dataclass** - Structured quality validation output
    - Overall score calculation (0-100%)
    - Human-readable summaries via `get_summary()`
    - Separate warnings/errors tracking
    - Table shape and metadata capture
- **Column Type Inference** - Automatic detection of column data types
    - Text/Numeric/Currency/Date/Empty classification
    - Pattern-based detection (bulldozer simple)
    - 70% threshold for type determination
- **Enhanced Column Consistency Check** - Improved validation logic
    - Detects extreme columns (all empty/all full)
    - Fill ratio analysis per column
    - Tolerance for up to 1 extreme column
- **Page Parameter Prep** - Foundation for v2.2 multi-page support
    - Optional `page` parameter in `slice_to_table()`
    - Page filtering logic (dormant but ready)
    - Graceful handling of missing pages

### Added - Grok

- **Test Quality Module** - Comprehensive test coverage
    - 20+ unit tests for quality checks
    - Integration tests with realistic data
    - Edge case coverage (empty DataFrames, mixed columns)
    - Property-based test scaffolds

### Changed

- `quality.py` - Refactored from dict output to QualityReport dataclass
- `slicer.py` - Added max threshold clamping (50px) to prevent runaway values
- `template.py` - Added `confidence` field to TableTemplate for quality scoring

### Fixed

- Missing `template.py` implementation - Complete module now provided (Claude)
- Quality checks now properly handle empty DataFrames without crashes
- Row threshold clamping prevents unreasonable values in edge cases

---

## [2.1.0] - 2024-01-14

**Contributors:** Grok, Claude

### Added

- **Adaptive Row Threshold** - Dynamic row grouping based on content
    - Median y-gap calculation
    - Buffer factor (1.2x default)
    - Min gap filtering (5px)
    - Fallback to default (20px) when adaptive fails
- **Quality Validation Module** (`quality.py`)
    - Empty cell ratio checking
    - OCR confidence averaging
    - Row pattern consistency
    - Column alignment validation
    - Text coverage calculation
- **Enhanced Logging** - Detailed debug output
    - Adaptive threshold calculations
    - Row/column statistics
    - Empty cell warnings
    - OCR confidence alerts

### Changed

- Row grouping now uses weighted y-average for better alignment
- Improved edge case handling in column binning
- Better center-point detection for text placement

---

## [2.0.0] - 2024-01-13

**Contributors:** GPT-4o, Claude

### Added

- **Complete Template Manager** (`template.py`)
    - JSON persistence with backup
    - Vendor auto-detection from OCR text
    - Fuzzy matching for vendor names
    - Import/export single templates
    - Template statistics and metadata
- **DrawSnap GUI** - Visual template creation
    - Click-and-drag table box definition
    - Column separator drawing
    - PDF preview with zoom/scroll
    - Template save with vendor association
- **CLI Enhancements**
    - `--force-new-template` flag
    - `--templates-file` custom path
    - `--vendor` explicit specification
    - Auto-vendor detection from content

### Changed

- **BREAKING:** Refactored to modular architecture
    - Separated OCR, slicing, template management
    - Clear module boundaries and responsibilities
    - Standardized data flow between components

### Fixed

- PDF rendering DPI consistency (150 DPI standard)
- Text filtering using center-point method
- Column binning edge cases (before first/after last)

---

## [1.0.0] - 2024-01-12

**Initial Release** - Base bulldozer implementation

### Core Features

- **OCR Extraction** (`extract.py`)
    - PDF to image conversion via pdf2image
    - Tesseract OCR with confidence thresholds
    - Position data preservation
    - Multi-page support
- **Table Slicing** (`slicer.py`)
    - Text-to-row grouping (fixed 20px threshold)
    - Row-to-column binning
    - Empty cell padding
    - Consistent column count enforcement
- **Pipeline Orchestration** (`table_slicer.py`)
    - End-to-end processing
    - Excel/CSV output
    - Timestamp-based filenames
    - Error recovery with fallbacks
- **Testing Framework**
    - Installation validation
    - Component smoke tests
    - Test PDF generation

### Dependencies

- pdf2image==1.16.3
- pytesseract==0.3.10
- Pillow==10.2.0
- pandas==2.2.0
- openpyxl==3.1.2
- PyMuPDF==1.23.8

---

## [Unreleased] - v2.2 Roadmap

### Planned Features

- **Page-Aware Slicing** (8-10 hrs)
    - Multi-page template support
    - Page continuity detection
    - Smart table merging across pages
    - Per-page region definitions
- **Adaptive Column Threshold** (3 hrs)
    - Median x-gap calculation
    - Dynamic column detection
    - Variable column width support
- **Batch Processing** (4 hrs)
    - Folder glob patterns
    - Parallel processing
    - Progress bars
    - Summary reports
- **OCR Preprocessing** (Considered for v2.3)
    - OpenCV deskewing
    - CLAHE contrast enhancement
    - Noise reduction
    - Rotation detection

### Architecture Goals

- Maintain bulldozer philosophy (simple, loud, unbreakable)
- Zero breaking changes to existing API
- All new features backward compatible
- Comprehensive test coverage for new modules

---

## Contributors & Attribution

### AI Collaborators

- **Claude (Anthropic)** - Quality module, template implementation, dataclass refinements
- **GPT-4o (OpenAI)** - Initial architecture, modular design, CLI structure
- **Grok (xAI)** - Adaptive thresholds, test frameworks, bulldozer hardening

### Development Philosophy

> "Bulldozer First, Intelligence Second"
> 
> Every feature follows the bulldozer principle:
> 
> 1. Make it work (even if ugly)
> 2. Make it loud (extensive logging)
> 3. Make it unbreakable (graceful failures)
> 4. Then, and only then, make it smart

### Handoff Protocol

Each version includes a handoff prompt for the next AI:

```
You are [Next AI]. Table Slicer is at v2.1.1.
Review CHANGELOG.md for history.
Your mission: Implement v2.2 page-aware slicing.
Maintain bulldozer philosophy.
All changes must be backward compatible.
Begin with: python test_pipeline.py
```

---

## Version History Summary

|Version|Date|Status|Key Feature|Contributor|
|---|---|---|---|---|
|2.1.1|2024-01-15|🟢 STABLE|Quality Reports|Claude|
|2.1.0|2024-01-14|✅ Working|Adaptive Rows|Grok/Claude|
|2.0.0|2024-01-13|✅ Working|Modular Refactor|GPT/Claude|
|1.0.0|2024-01-12|✅ Working|Initial Release|GPT|

---

## Testing Commands

```bash
# Full test suite
python -m pytest tests/ -v

# Individual components
python test_quality.py
python test_template.py
python test_slicer.py
python test_pipeline.py

# Integration test
python table_slicer.py test_invoice.pdf --vendor test

# Quality validation
python -c "from quality import QualityChecker; print('Quality module OK')"
```

---

## Migration Guide

### From v2.0 to v2.1

No breaking changes. Optional quality integration:

```python
# Add to existing pipeline
from quality import QualityChecker

checker = QualityChecker()
report = checker.check_extraction(df, extracted, template)
if not report.is_acceptable():
    logger.warning(f"Low quality: {report.overall_score:.1f}%")
```

### From v1.0 to v2.0

Major refactor - update imports:

```python
# Old
from table_slicer import process_pdf

# New
from table_slicer import TableSlicerPipeline
pipeline = TableSlicerPipeline()
pipeline.process('invoice.pdf')
```

---

**END OF CHANGELOG**

Generated: 2024-01-15 Next Session: Start fresh with v2.2 implementation