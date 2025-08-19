# PDF Extractor — Command Center

**Version:** v2.1.2 | **Status:** Stable | **Architecture:** Bulldozer (Draw → OCR → Slice → Excel)

Modular, deterministic table slicer powered by OCR and human-drawn templates.

---

## 🎯 Quick Start

### For AI Agents
**Read this file completely before taking any action.** This document contains the canonical project state, architecture, and development rules. Never assume system behavior without verifying against this command center.

### For Developers
1. Review [System Architecture](#system-architecture)
2. Check [Requirements](#requirements) 
3. Run [Primary Entry Point](#primary-entry-point)
4. Select from [Development Branches](#development-branches)

---

## 📁 Project Structure

```
pdf_extractor/
├── 🔧 Core Pipeline
│   ├── table_slicer.py      # Main CLI pipeline entry point
│   ├── extract.py           # OCR engine (Tesseract + Poppler)
│   ├── slicer.py           # Table binning logic
│   ├── template.py         # Template manager & auto-detection
│   └── quality.py          # Extraction scoring & diagnostics
│
├── 🎨 GUI Components  
│   ├── launch_gui.py        # GUI launcher
│   └── drawsnap_gui.py      # Visual template editor (Tkinter)
│
├── 🧪 Testing
│   ├── test_pipeline.py     # Integration tests + dummy PDF builder
│   └── test_quality.py      # Unit tests for quality scoring
│
├── 📂 Data Directories
│   ├── incoming/            # Drop PDFs here for processing
│   ├── processed/           # Output Excel files
│   ├── txt_docs/           # Optional raw text dumps
│   └── tests/              # Test assets
│
├── ⚙️ Configuration
│   ├── vendor_templates.json # Human-drawn layout definitions
│   ├── REQUIREMENTS.txt     # Python dependencies
│   └── venv/               # Python virtual environment
│
└── 📚 Documentation
    ├── README.md           # Public overview
    ├── COMMAND_CENTER.md   # This file
    └── changelog.md        # Version history
```

---

## 🏗️ System Architecture

### Input Support
- **PDF:** Single-page (native or image-based)
- **Images:** PNG, JPG, TIFF

### Processing Pipeline
1. **OCR Processing** → `extract.py` (Tesseract with confidence filtering)
2. **Template Matching** → `template.py` (from `vendor_templates.json`)
3. **Data Slicing** → `slicer.py` (bins positioned text into columns)
4. **Excel Export** → `table_slicer.py` (timestamped results)
5. **Quality Analysis** → `quality.py` (optional evaluation)

### Primary Entry Point

```python
from table_slicer import TableSlicerPipeline

pipeline = TableSlicerPipeline()
pipeline.process("incoming/sysco_invoice.pdf", vendor="sysco")
```

---

## 🔧 Requirements

### Python Dependencies
Install via `pip install -r REQUIREMENTS.txt`:
- pytesseract
- pdf2image  
- PyMuPDF
- Pillow
- openpyxl
- pandas

### External Binaries
Manual installation required:
- **Tesseract OCR** (latest stable)
- **Poppler** (e.g., poppler-24.08.0)

---

## ✅ Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| GUI System | ✅ Stable | DrawSnap GUI functional, saves JSON |
| OCR Engine | ✅ Stable | Single-page processing, auto Poppler detection |
| Template System | ✅ Stable | Auto/fuzzy vendor matching + manual drawing |
| Data Slicer | ✅ Stable | Adaptive row and column binning |
| CLI Pipeline | ✅ Stable | Complete end-to-end processing |
| Quality Scoring | ✅ Stable | Available but not surfaced in UI |
| FastAPI Server | 🟡 Planned | Next sprint priority |
| Batch Processing | 🟡 Planned | Optional wrapper for bulk operations |

---

## 🚀 Development Branches

**Scope Lock:** Select ONE branch per sprint to maintain focus.

| Branch | Priority | Description | Scope |
|--------|----------|-------------|-------|
| 1. Batch CLI | Medium | `process_incoming.py` | Process all `/incoming/` files sequentially |
| 2. FastAPI Wrapper | High | `app.py` with `/upload` endpoint | REST API for drag-and-drop uploads |
| 3. Quality Surfacing | Low | Surface quality reports | Return/log quality metrics post-slice |
| 4. GitHub Preparation | Medium | Repo cleanup for public release | Documentation, licensing, CI setup |
| 5. Vendor Test Harness | Low | Automated testing framework | Repeatable test folders per vendor |
| 6. React Frontend | Low | Web UI (post-API) | Tailwind interface for upload + preview |
| 7. RAG Indexing | Experimental | Vector search integration | Index documentation for agent queries |

---

## 📋 Recent Changes (v2.1.2)

- **🎨 GUI Integration:** DrawSnap visual template tool added
- **🧠 Modular Refactor:** Separated concerns into focused modules  
- **🧪 Quality System:** Comprehensive scoring with unit tests
- **📦 CLI Completion:** Full extract → match → slice → Excel flow
- **🔐 Template Persistence:** Vendor layouts saved in JSON format
- **🧪 Test Coverage:** End-to-end functionality verified

---

## 🤖 AI Agent Instructions

### Behavior Rules
1. **Always reference this file** as the source of truth for project state
2. **Never assume system behavior** without verifying module implementation
3. **Only modify pipeline logic** if this Command Center authorizes the change
4. **Confirm branch selection** before beginning any development work
5. **Update this file** with any architectural changes made

### Parsing Guidelines
- Use file structure as navigation map
- Reference component status table for current capabilities
- Check development branches for approved work streams
- Validate against requirements before suggesting changes

### Session Initialization
When starting work, always begin with:
```
Reference: COMMAND_CENTER.md in pdf_extractor repo
Selected Branch: [branch number and name]
Scope: [brief description of planned work]
```

---

## 📖 File Reference

| File | Purpose | Key Functions |
|------|---------|---------------|
| `table_slicer.py` | Main pipeline orchestration | `TableSlicerPipeline.process()` |
| `extract.py` | OCR text extraction | Tesseract + Poppler integration |
| `slicer.py` | Data structure parsing | Text positioning and binning |
| `template.py` | Layout pattern matching | Template loading and detection |
| `quality.py` | Result validation | Extraction accuracy scoring |
| `drawsnap_gui.py` | Template creation interface | Visual layout definition tool |
| `vendor_templates.json` | Layout definitions | Human-drawn template storage |

---

## 🎯 Project Philosophy

This system prioritizes **deterministic, reproducible extraction** over AI-based guessing. Human-drawn templates ensure consistent results across document variations while maintaining full control over the extraction process.

**Maintainer Note:** Keep this Command Center updated with any architectural changes. It serves as README, roadmap, changelog, and AI coordination document in one canonical location.

---

*Command Center v2.1.2 — The OS of the PDF Extractor Project*