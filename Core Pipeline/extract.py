# extract.py - Updated with bulldozer Poppler handling
"""
OCR extraction module - converts PDFs to positioned text data.
Bulldozer approach: Always OCR for consistent positioning.
"""

import os
from typing import List, Dict, Any
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class OCRExtractor:
    """Handles PDF to text extraction with position data."""
    
    # Bulldozer Config: Hard-coded paths with fallbacks
    DEFAULT_POPPLER_PATHS = [
        r"C:\Users\mhartigan\tools\poppler-24.08.0\Library\bin",  # Current setup
        r"C:\tools\poppler\bin",                                   # Common location
        r"C:\Program Files\poppler\bin",                          # Standard install
    ]
    
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
            poppler_path: Override Poppler path (None = auto-detect)
        """
        self.confidence_threshold = confidence_threshold
        self.dpi = dpi
        self.tesseract_config = tesseract_config
        
        # Bulldozer Poppler Detection
        self.poppler_path = self._get_poppler_path(poppler_path)
        
        logger.info(f"OCRExtractor initialized:")
        logger.info(f"  Poppler: {self.poppler_path}")
        logger.info(f"  Tesseract config: {tesseract_config}")
    
    def _get_poppler_path(self, override_path: str = None) -> str:
        """
        Bulldozer approach: Find Poppler or fail loudly.
        
        Args:
            override_path: Explicit path override
            
        Returns:
            Valid Poppler path
            
        Raises:
            RuntimeError: If no valid Poppler found
        """
        # Check override first
        if override_path:
            if self._validate_poppler_path(override_path):
                logger.info(f"Using override Poppler path: {override_path}")
                return override_path
            else:
                raise RuntimeError(f"Invalid override Poppler path: {override_path}")
        
        # Check environment variable
        env_path = os.environ.get('POPPLER_PATH')
        if env_path and self._validate_poppler_path(env_path):
            logger.info(f"Using POPPLER_PATH env var: {env_path}")
            return env_path
        
        # Check default paths
        for path in self.DEFAULT_POPPLER_PATHS:
            if self._validate_poppler_path(path):
                logger.info(f"Found Poppler at: {path}")
                return path
        
        # Try without path (system PATH)
        logger.warning("No custom Poppler path found, trying system PATH")
        return None  # Let pdf2image use system PATH
    
    def _validate_poppler_path(self, path: str) -> bool:
        """
        Validate Poppler installation.
        
        Args:
            path: Path to check
            
        Returns:
            True if valid Poppler installation
        """
        if not path or not os.path.exists(path):
            return False
        
        # Check for required executables
        required_exes = ['pdftoppm.exe', 'pdftocairo.exe']
        for exe in required_exes:
            exe_path = os.path.join(path, exe)
            if not os.path.exists(exe_path):
                logger.debug(f"Missing Poppler executable: {exe_path}")
                return False
        
        return True
    
    def extract_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with positions from PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of text items with position data
        """

        print("📸 Using custom Tesseract path")
        print("🧭", pytesseract.pytesseract.tesseract_cmd)

        try:
            # Bulldozer PDF conversion with explicit error handling
            if self.poppler_path:
                images = convert_from_path(
                    pdf_path, 
                    dpi=self.dpi, 
                    poppler_path=self.poppler_path
                )
            else:
                # Fallback to system PATH
                images = convert_from_path(pdf_path, dpi=self.dpi)
                
        except Exception as e:
            # Loud failure with helpful context
            error_msg = f"PDF conversion failed: {e}"
            if self.poppler_path:
                error_msg += f"\nPoppler path: {self.poppler_path}"
                error_msg += f"\nCheck that Poppler binaries exist and are accessible"
            else:
                error_msg += f"\nUsing system PATH - ensure Poppler is installed"
            raise RuntimeError(error_msg)
        
        # Enforce single-page guard (existing logic)
        if len(images) > 1:
            logger.warning(f"Multi-page PDF detected ({len(images)} pages). Processing only page 1.")
            images = [images[0]]
        elif len(images) == 0:
            raise ValueError("No pages found in PDF.")
        
        extracted = []
        for page_num, img in enumerate(images):
            page_data = self._extract_from_image(img, page_num + 1)
            extracted.extend(page_data)
        
        return extracted
    
    def extract_from_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Extract text with positions from image file."""
        try:
            img = Image.open(image_path)
        except Exception as e:
            raise ValueError(f"Failed to open image: {e}")
        
        return self._extract_from_image(img, page=1)
    
    def _extract_from_image(self, img: Image.Image, page: int) -> List[Dict[str, Any]]:
        """Internal method to extract text from PIL Image."""

    def _extract_from_image(self, img: Image.Image, page: int) -> List[Dict[str, Any]]:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = r"C:\Users\mhartigan\tools\tesseract\tesseract.exe"
       
        try:
            data = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT, 
                config=self.tesseract_config
            )
        except Exception as e:
            raise RuntimeError(f"OCR failed on page {page}: {e}")
        
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
        
        return extracted