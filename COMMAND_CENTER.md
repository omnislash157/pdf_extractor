# PDF Extractor — Command Center

**Version:** v2.5 | **Status:** Production Ready | **Architecture:** Bulldozer (Draw → OCR → Slice → Excel)

Modular, deterministic table slicer powered by OCR and human-drawn templates.

---

## 🎯 Quick Start

### For AI Agents
**Read this file completely before taking any action.** This document contains the canonical project state, architecture, and development rules. Never assume system behavior without verifying against this command center.

### For Developers
1. Review [System Architecture](#system-architecture)
2. Check [Requirements](#requirements) 
3. Run [Primary Entry Points](#primary-entry-points)
4. Select from [Development Branches](#development-branches)

---

## 📁 Project Structure

**Current State:** All files in root directory (flat structure for development)  
**TODO:** Organize into folders after stabilization

```
pdf_extractor/ (all files currently in root)
├── 🔧 Core Pipeline Modules
│   ├── table_slicer.py      # Main modular pipeline orchestrator
│   ├── extract.py           # OCR engine (Tesseract + Poppler)
│   ├── slicer.py           # Table binning logic
│   ├── template.py         # Template manager & auto-detection
│   ├── quality.py          # Extraction scoring & diagnostics
│   └── config.py           # Path configuration
│
├── 🎯 Standalone CLI
│   └── drawsnap_cli.py      # All-in-one CLI tool (NEW in v2.4)
│
├── 🎨 GUI Components  
│   ├── launch_gui.py        # GUI launcher
│   └── drawsnap_gui.py      # Visual template editor v2.3 (vendor dropdown)
│
├── 🧪 Testing
│   ├── test_pipeline.py     # Integration tests
│   ├── test_quality.py      # Unit tests for quality scoring
│   └── test_gui_sprint.py   # GUI sprint test suite
│
├── ⚙️ Configuration
│   ├── vendor_templates.json # Human-drawn layout definitions
│   ├── header_mappings.json  # Column header mappings (optional)
│   ├── requirements.txt      # Python dependencies
│   └── logs/                 # Extraction logs (auto-created)
│
└── 📚 Documentation
    └── COMMAND_CENTER.md     # This file (single source of truth)
```

### File Organization Plan (Post-Dev)
```
Future structure:
- core/          → Pipeline modules
- cli/           → Standalone tools  
- gui/           → GUI components
- tests/         → Test suite
- config/        → Configuration files
- docs/          → Documentation
```

---

## 🏗️ System Architecture

### Three Parallel Systems

1. **Modular Pipeline** (`table_slicer.py` + modules)
   - For integration and programmatic use
   - Modules can be imported separately
   - Full quality checking available

2. **Standalone CLI** (`drawsnap_cli.py`)
   - Single-file distribution
   - No module dependencies
   - Includes everything inline
   - Perfect for deployment

3. **GUI Template Creator** (`drawsnap_gui.py`)
   - Visual template drawing
   - Vendor dropdown with auto-load
   - Saves to `vendor_templates.json`

### Input Support
- **PDF:** Single-page (native or image-based)
- **Images:** PNG, JPG, TIFF
- **Multi-page:** Manual split by page (planned automation)

### Processing Pipeline
1. **OCR Processing** → Extract text with positions
2. **Template Matching** → Load vendor-specific layout
3. **Data Slicing** → Bin text into rows/columns
4. **Excel Export** → Timestamped `.xlsx` output
5. **Quality Analysis** → Optional validation scoring

---

## 🚀 Primary Entry Points

### Modular Pipeline (Programmatic)
```python
from table_slicer import TableSlicerPipeline

pipeline = TableSlicerPipeline()
output = pipeline.process("invoice.pdf", vendor="sysco")
```

### Standalone CLI (Command Line)
```bash
# Extract with native PDF text
python drawsnap_cli.py --pdf invoice.pdf --vendor sysco --output result.xlsx

# Force OCR for scanned PDFs  
python drawsnap_cli.py --pdf scan.pdf --vendor amazon --output result.xlsx --ocr

# List available vendors
python drawsnap_cli.py --list-vendors
```

### GUI Template Creator
```bash
# Launch interactive template creator
python launch_gui.py

# Or direct with parameters
python -c "from drawsnap_gui import create_template_gui; create_template_gui('invoice.pdf', 'vendor_name')"
```

---

## 🔧 Requirements

### Python Dependencies
```bash
pip install -r requirements.txt
```
- pytesseract (0.3.10)
- pdf2image (1.16.3)
- PyMuPDF (1.23.8)
- Pillow (10.2.0)
- pandas (2.2.0)
- openpyxl (3.1.2)
- numpy (1.24.3)

### External Binaries
**Manual installation required:**
- **Tesseract OCR** (latest stable)
- **Poppler** (e.g., poppler-24.08.0)

**Configuration:** Edit `config.py` with your tool paths:
```python
TESSERACT_PATHS = {
    'your_username': r"C:\path\to\tesseract.exe",
    ...
}
```

---

## ✅ Component Status

| Component | Status | Version | Notes |
|-----------|--------|---------|-------|
| **Modular Pipeline** | ✅ Stable | 2.1 | Full extraction pipeline |
| **Standalone CLI** | ✅ Stable | 1.0 | Single-file tool |
| **DrawSnap GUI** | ✅ Stable | 2.3 | Vendor dropdown, auto-load |
| **OCR Engine** | ✅ Stable | 2.1 | Native + OCR modes |
| **Template System** | ✅ Stable | 2.0 | JSON persistence |
| **Quality Scoring** | ✅ Stable | 2.0 | Full validation suite |
| **Config System** | ✅ Stable | 1.0 | Path management |
| **Vendor Detection** | ✅ Stable | 1.0 | Keyword matching |
| **Header Mapping** | ✅ Stable | 1.0 | Optional column names |
| **Multi-Page** | 🟡 Manual | - | Split PDFs by vendor_page1.pdf |
| **FastAPI Server** | 🟡 Planned | - | Next sprint priority |
| **Batch Processing** | 🟡 Planned | - | Bulk operations wrapper |

---

## 📋 Recent Changes

### v2.5 (Current)
- **🏗️ Three Systems:** Modular pipeline, standalone CLI, and GUI all working
- **📁 Flat Structure:** All files in root for easier development
- **🎯 DrawSnap CLI:** Complete standalone tool with all features inline
- **✅ Production Ready:** All core features stable and tested

### v2.4
- **🎯 Standalone CLI:** Created `drawsnap_cli.py` as single-file tool
- **📝 Documentation:** Comprehensive docstrings and inline comments
- **🧪 Test Coverage:** Full test suite with `test_gui_sprint.py`

### v2.3  
- **🎨 GUI Enhancement:** Added vendor dropdown with auto-load
- **📊 Metadata:** Templates now include timestamps and scale info
- **🔧 Modular Refactor:** DrawSnap GUI split into components

### v2.1.3
- **🔧 Path Configuration:** Added `config.py` for tool paths
- **🐛 Bug Fixes:** Removed duplicate methods, fixed coordinates
- **📝 Documentation:** Corporate firewall workaround notes

---

## 🚀 Development Branches

**Scope Lock:** Select ONE branch per sprint to maintain focus.

| Branch | Priority | Description | Next Steps |
|--------|----------|-------------|------------|
| **1. Folder Organization** | High | Move files to proper directories | Create folder structure, update imports |
| **2. FastAPI Wrapper** | High | REST API with `/upload` endpoint | Drag-drop upload support |
| **3. Multi-Page Automation** | Medium | Handle multi-page PDFs | Page detection and splitting |
| **4. Batch Processing** | Medium | Process entire directories | `process_all.py` script |
| **5. Header Mapping UI** | Low | GUI for column naming | Add to DrawSnap GUI |
| **6. Cloud Deployment** | Low | Docker + cloud ready | Containerize application |
| **7. RAG Integration** | Experimental | Vector search for docs | LangChain integration |

---

## 🤖 AI Agent Instructions

### Critical Context
- **THREE separate systems** exist: modular pipeline, standalone CLI, and GUI
- **All files currently flat** in root directory (intentional for dev)
- **DrawSnap GUI v2.3** has vendor dropdown functionality
- **Config.py** handles all tool paths (Tesseract, Poppler)

### Behavior Rules
1. **Check file existence** before suggesting imports
2. **Verify current structure** - everything is in root now
3. **Test changes** with both pipeline and CLI versions
4. **Update this file** after any architectural changes
5. **Maintain bulldozer philosophy** - always produce output

### Common Tasks

#### Add New Vendor
1. Draw template with GUI: `python launch_gui.py`
2. Template saves to `vendor_templates.json`
3. Both pipeline and CLI will auto-detect

#### Process Invoice
```bash
# Using standalone CLI (recommended for single files)
python drawsnap_cli.py --pdf invoice.pdf --vendor sysco --output result.xlsx

# Using modular pipeline (for integration)
python table_slicer.py invoice.pdf --vendor sysco
```

#### Run Tests
```bash
# Full test suite
python test_gui_sprint.py

# Individual components
python test_pipeline.py
python test_quality.py
```

---

## 📖 Key Files Reference

| File | Purpose | Entry Point |
|------|---------|-------------|
| **drawsnap_cli.py** | Standalone CLI tool | `main()` |
| **table_slicer.py** | Modular pipeline orchestrator | `TableSlicerPipeline.process()` |
| **drawsnap_gui.py** | Visual template creator | `create_template_gui()` |
| **extract.py** | OCR text extraction module | `OCRExtractor.extract_from_pdf()` |
| **slicer.py** | Table structure parser | `TableSlicer.slice_to_table()` |
| **template.py** | Template management | `TemplateManager.get_template()` |
| **quality.py** | Extraction validation | `QualityChecker.check_extraction()` |
| **config.py** | Tool path configuration | `TESSERACT_CMD, POPPLER_PATH` |

---

## 🎯 Project Philosophy

**Bulldozer Approach:** Deterministic, reproducible extraction that always produces output.

- ✅ **Always returns something** (even if "No text found")
- ✅ **Logs everything** (successes and failures)  
- ✅ **Human templates** over AI guessing
- ✅ **Modular but integrated** (use pieces or the whole)
- ✅ **Loud failures** (clear error messages)

---

## 📊 Current Metrics

- **Files:** 33 total (15 Python modules, rest config/tests)
- **Vendors:** 2 configured (test, sysco)
- **Test Coverage:** 6 test categories, all passing
- **Dependencies:** 8 Python packages, 2 system binaries
- **Supported Formats:** PDF (native/scanned), PNG, JPG, TIFF

---

## 🔮 Next Session Checklist

When returning to this project:

1. Run `python test_gui_sprint.py` to verify system state
2. Check `vendor_templates.json` for available vendors
3. Review `logs/parser_log.txt` for recent extractions
4. Confirm tool paths in `config.py` still valid
5. Select ONE development branch to work on

---

**Maintainer Note:** This Command Center is the single source of truth. Update immediately after any architectural changes. It serves as README, roadmap, state tracker, and AI coordination in one canonical location.

---

Command Center v2.5 — Bulldozer Mode Engaged 🚜