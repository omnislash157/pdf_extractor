# extract.py - Fixed with config import
"""
OCR extraction module - converts PDFs to positioned text data.
Bulldozer approach: Always OCR for consistent positioning.
Corporate firewall workaround: Uses config.py for paths.
"""

import os
from typing import List, Dict, Any
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import logging

# Import bulldozer config (loud failures if missing)
try:
    import config
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    DEFAULT_POPPLER_PATH = config.POPPLER_PATH
    print(f"📸 Loaded config - Tesseract: {config.TESSERACT_CMD}")
except ImportError:
    print("❌ WARNING: config.py not found! Using fallback paths...")
    # Fallback to original hardcoded paths
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\mhartigan\tools\tesseract\tesseract.exe"
    DEFAULT_POPPLER_PATH = r"C:\Users\mhartigan\tools\poppler-24.08.0\Library\bin"

logger = logging.getLogger(__name__)


class OCRExtractor:
    """Handles PDF to text extraction with position data."""
    
    def __init__(self, 
                 confidence_threshold: int = 60, 
                 dpi: int = 150, 
                 tesseract_config: str = "--psm 6",
                 poppler_path: str = None):
        """
        Args:
            confidence_threshold: Minimum OCR confidence (0-100)
            dpi: Resolution for PDF rendering
            tesseract_config: Tesseract configuration string
            poppler_path: Override Poppler path (None = use config default)
        """
        self.confidence_threshold = confidence_threshold
        self.dpi = dpi
        self.tesseract_config = tesseract_config
        
        # Use provided path or fall back to config
        self.poppler_path = poppler_path or DEFAULT_POPPLER_PATH
        
        logger.info(f"OCRExtractor initialized:")
        logger.info(f"  Poppler: {self.poppler_path}")
        logger.info(f"  Tesseract: {pytesseract.pytesseract.tesseract_cmd}")
        logger.info(f"  Config: {tesseract_config}")
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with positions from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text items with position data
        """
        try:
            # Convert PDF to images
            if self.poppler_path and os.path.exists(self.poppler_path):
                images = convert_from_path(
                    pdf_path, 
                    dpi=self.dpi, 
                    poppler_path=self.poppler_path
                )
            else:
                # Fallback to system PATH
                logger.warning("Poppler path not found, using system PATH")
                images = convert_from_path(pdf_path, dpi=self.dpi)
                
        except Exception as e:
            # Bulldozer: Loud failure with helpful message
            error_msg = f"\n{'='*60}\n❌ PDF CONVERSION FAILED!\n"
            error_msg += f"File: {pdf_path}\n"
            error_msg += f"Error: {e}\n"
            
            if self.poppler_path:
                error_msg += f"Poppler path: {self.poppler_path}\n"
                if not os.path.exists(self.poppler_path):
                    error_msg += "⚠️  Path does not exist! Check config.py\n"
            else:
                error_msg += "Using system PATH for Poppler\n"
            
            error_msg += "\nFixes:\n"
            error_msg += "1. Check config.py has correct paths\n"
            error_msg += "2. Verify Poppler is installed\n"
            error_msg += "3. Try: pip install pdf2image\n"
            error_msg += f"{'='*60}"
            
            raise RuntimeError(error_msg)
        
        # Single-page enforcement
        if len(images) > 1:
            logger.warning(f"Multi-page PDF ({len(images)} pages). Using page 1 only.")
            images = [images[0]]
        elif len(images) == 0:
            raise ValueError("No pages found in PDF.")
        
        extracted = []
        for page_num, img in enumerate(images):
            page_data = self._extract_from_image(img, page_num + 1)
            extracted.extend(page_data)
        
        logger.info(f"Extracted {len(extracted)} text items from {pdf_path}")
        return extracted
    
    def extract_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text with positions from image file."""
        try:
            img = Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")
        
        return self._extract_from_image(img, page=1)
    
    def _extract_from_image(self, img: Image.Image, page: int) -> List[Dict[str, Any]]:
        """
        Internal method to extract text from PIL Image.
        Single implementation - no duplicates!
        """
        try:
            # Run OCR with configured Tesseract
            data = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT, 
                config=self.tesseract_config
            )
        except Exception as e:
            # Bulldozer: Loud failure
            error_msg = f"\n{'='*60}\n❌ OCR FAILED!\n"
            error_msg += f"Page: {page}\n"
            error_msg += f"Error: {e}\n"
            error_msg += f"Tesseract: {pytesseract.pytesseract.tesseract_cmd}\n"
            
            if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
                error_msg += "⚠️  Tesseract path does not exist!\n"
                error_msg += "Check config.py and update TESSERACT_PATHS\n"
            
            error_msg += f"{'='*60}"
            raise RuntimeError(error_msg)
        
        # Extract text with confidence filtering
        extracted = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > self.confidence_threshold and data['text'][i].strip():
                extracted.append({
                    'text': data['text'][i],
                    'page': page,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': data['conf'][i]
                })
        
        logger.info(f"Page {page}: Extracted {len(extracted)} text items")
        return extracted