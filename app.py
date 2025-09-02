# app.py - DrawSnap API Service Layer v2.6
"""
FastAPI wrapper for DrawSnap table extraction pipeline.
Thin HTTP layer - no business logic, just translation.
Bulldozer philosophy: Always return something, fail loud in logs.
"""

import os
import shutil
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uvicorn

# Existing pipeline imports - treating as black boxes
from table_slicer import TableSlicerPipeline
from template import TemplateManager

# ============================================================================
# CONFIGURATION
# ============================================================================

# Logging - bulldozer style
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('drawsnap_api')

# Directory structure
UPLOAD_DIR = Path('uploads')
INCOMING_DIR = UPLOAD_DIR / 'incoming'
PROCESSED_DIR = UPLOAD_DIR / 'processed'
LOG_DIR = Path('logs')

# Settings
TTL_HOURS = 1  # File retention period
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
ALLOWED_EXTENSIONS = {'.pdf'}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Create required directories
for dir_path in [INCOMING_DIR, PROCESSED_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Initialize pipeline components
pipeline = TableSlicerPipeline()
template_manager = TemplateManager()

# Create FastAPI app
app = FastAPI(
    title="DrawSnap API",
    version="2.6.0",
    description="PDF table extraction service using human-drawn templates"
)

# Mount static directory for downloads
app.mount("/download", StaticFiles(directory=str(PROCESSED_DIR)), name="download")

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def cleanup_old_files(directory: Path = PROCESSED_DIR, ttl_hours: int = TTL_HOURS):
    """Remove files older than TTL."""
    now = datetime.now()
    cleaned = 0
    
    for file_path in directory.glob('*'):
        if file_path.is_file():
            age = now - datetime.fromtimestamp(file_path.stat().st_mtime)
            if age > timedelta(hours=ttl_hours):
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned expired file: {file_path.name}")
                    cleaned += 1
                except Exception as e:
                    logger.warning(f"Failed to clean {file_path}: {e}")
    
    if cleaned > 0:
        logger.info(f"Cleanup complete: removed {cleaned} files")


@contextmanager
def temporary_upload(upload_file: UploadFile, request_id: str):
    """Context manager for safe temporary file handling."""
    temp_path = INCOMING_DIR / f"{request_id}_{upload_file.filename}"
    
    try:
        # Save uploaded file
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
        logger.info(f"Saved upload: {temp_path.name}")
        yield temp_path
        
    finally:
        # Always cleanup temp file
        if temp_path.exists():
            try:
                temp_path.unlink()
                logger.debug(f"Cleaned temp file: {temp_path.name}")
            except Exception as e:
                logger.warning(f"Failed to clean temp file: {e}")


def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file meets requirements."""
    # Check extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file type: {file_ext}. Only PDF supported.")
    
    # Check size (if content_length available)
    if file.size and file.size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {file.size} bytes. Max: {MAX_FILE_SIZE}")


def process_extraction(
    pdf_path: Path,
    vendor: Optional[str],
    output_dir: Path
) -> Dict[str, Any]:
    """
    Process PDF through pipeline and return metadata.
    
    Returns:
        Dict with output_path, vendor, and shape info
    """
    # Run pipeline
    output_path = pipeline.process(
        str(pdf_path),
        output_dir=str(output_dir),
        vendor=vendor
    )
    
    # Read result to get dimensions
    df = pd.read_excel(output_path, header=None)
    rows, cols = df.shape
    
    # Detect vendor if it was auto-detected
    if not vendor:
        # Try to extract from output filename pattern
        # Format: TableSlice_vendor_original_timestamp.xlsx
        filename_parts = Path(output_path).stem.split('_')
        if len(filename_parts) >= 2:
            vendor = filename_parts[1]
        else:
            vendor = "auto-detected"
    
    return {
        "output_path": Path(output_path),
        "vendor": vendor,
        "rows": rows,
        "columns": cols,
        "dataframe": df  # Include for quality check
    }


def check_quality(df: pd.DataFrame, vendor: str) -> Optional[float]:
    """
    Run quality check if module available.
    
    Returns:
        Quality score or None if unavailable
    """
    try:
        from quality import QualityChecker
        
        # Need proper extraction data for real quality check
        # For now, return a simplified score based on emptiness
        checker = QualityChecker()
        
        # Calculate simple metrics
        total_cells = df.size
        empty_cells = df.isnull().sum().sum() + (df == '').sum().sum()
        empty_ratio = empty_cells / total_cells if total_cells > 0 else 1.0
        
        # Simple score (inverse of empty ratio)
        score = (1 - empty_ratio) * 100
        
        logger.info(f"Quality check: {score:.1f}% (empty ratio: {empty_ratio:.2%})")
        return round(score, 1)
        
    except ImportError:
        logger.debug("Quality module not available")
        return None
    except Exception as e:
        logger.warning(f"Quality check failed: {e}")
        return None


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("DrawSnap API starting up...")
    cleanup_old_files()
    logger.info(f"Ready. Available vendors: {template_manager.list_vendors()}")


@app.get("/health")
async def health_check(background_tasks: BackgroundTasks):
    """
    System health check endpoint.
    
    Returns:
        API status and version
    """
    # Schedule cleanup as side effect
    background_tasks.add_task(cleanup_old_files)
    
    return {
        "status": "operational",
        "version": "2.6.0",
        "pipeline": "ready",
        "vendors_loaded": len(template_manager.list_vendors())
    }


@app.get("/vendors")
async def list_vendors():
    """
    List available vendor templates.
    
    Returns:
        Array of vendor names
    """
    try:
        vendors = template_manager.list_vendors()
        return {"vendors": vendors, "count": len(vendors)}
        
    except Exception as e:
        logger.error(f"Failed to list vendors: {e}")
        raise HTTPException(status_code=500, detail="Failed to load vendor list")


@app.get("/templates/{vendor}")
async def get_template(vendor: str):
    """
    Get specific vendor template configuration.
    
    Args:
        vendor: Vendor name
        
    Returns:
        Template configuration dict
    """
    template = template_manager.get_template(vendor)
    
    if not template:
        available = template_manager.list_vendors()
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"No template for vendor: {vendor}",
                "available_vendors": available
            }
        )
    
    # Convert to dict (assuming method exists)
    return template.to_dict()


@app.post("/upload")
async def upload_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    vendor: Optional[str] = Form(None),
    force_ocr: bool = Form(False),
    quality_check: bool = Form(False)
):
    """
    Upload PDF and extract table to Excel.
    
    Args:
        file: PDF file upload
        vendor: Optional vendor name (auto-detect if not provided)
        force_ocr: Force OCR mode (reserved for future)
        quality_check: Include quality score in response
        
    Returns:
        Success: extraction results with download URL
        Error: helpful error message with available vendors
    """
    # Schedule cleanup
    background_tasks.add_task(cleanup_old_files)
    
    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    
    try:
        # Validate upload
        validate_upload(file)
        
        # Process with context manager for safe cleanup
        with temporary_upload(file, request_id) as temp_path:
            
            # Run extraction
            result = process_extraction(
                temp_path,
                vendor,
                PROCESSED_DIR
            )
            
            # Build response
            output_file = result["output_path"].name
            response = {
                "status": "success",
                "request_id": request_id,
                "vendor": result["vendor"],
                "output_file": output_file,
                "download_url": f"/download/{output_file}",
                "rows_extracted": result["rows"],
                "columns_extracted": result["columns"]
            }
            
            # Optional quality check
            if quality_check:
                score = check_quality(result["dataframe"], result["vendor"])
                if score is not None:
                    response["quality_score"] = score
            
            logger.info(f"Successfully processed {file.filename} -> {output_file}")
            return response
    
    except ValueError as ve:
        # Validation errors (bad file type, too large, etc)
        logger.warning(f"Validation error [{request_id}]: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    
    except RuntimeError as re:
        # Pipeline errors (no template, OCR failure, etc)
        logger.error(f"Pipeline error [{request_id}]: {re}")
        
        # Check if it's a missing template error
        if "template" in str(re).lower():
            available = template_manager.list_vendors()
            return JSONResponse(
                status_code=422,
                content={
                    "status": "error",
                    "request_id": request_id,
                    "message": str(re),
                    "available_vendors": available,
                    "hint": "Use /vendors to see available templates or create one with GUI"
                }
            )
        
        # Other runtime errors
        raise HTTPException(status_code=500, detail=f"Processing failed: {re}")
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error [{request_id}]: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Internal server error - check logs for details"
        )


@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download processed Excel file.
    
    Args:
        filename: Name of processed file
        
    Returns:
        File download response
    """
    file_path = PROCESSED_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting DrawSnap API server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )