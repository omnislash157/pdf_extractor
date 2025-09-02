# smart_extract.py - SAVE THIS AS THE NEW CORE!
"""
Smart Extraction Module - Auto-detects PDF type and routes accordingly.
Bulldozer with a brain: Always produces output, but knows when to OCR vs Native.
"""

import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class SmartExtractor:
    """The bulldozer that knows when to use OCR vs Native."""
    
    def __init__(self, confidence_threshold: int = 60, dpi: int = 150):
        self.confidence_threshold = confidence_threshold
        self.dpi = dpi
        
        # Load config if available
        try:
            import config
            self.poppler_path = config.POPPLER_PATH
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
        except ImportError:
            self.poppler_path = None
    
    def detect_pdf_type(self, pdf_path: str) -> Tuple[str, float]:
        """
        Detect if PDF is native text or scanned image.
        
        Returns:
            (type, confidence): 'native' or 'scanned', confidence 0-1
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            
            # Check for text
            text = page.get_text()
            text_length = len(text.strip())
            
            # Check for images
            image_list = page.get_images()
            image_count = len(image_list)
            
            doc.close()
            
            # Decision logic (bulldozer simple)
            if text_length > 100:  # Meaningful text found
                confidence = min(1.0, text_length / 1000)
                return 'native', confidence
            elif image_count > 0:  # Images but no text = scanned
                return 'scanned', 0.9
            else:  # Edge case - empty or weird
                return 'scanned', 0.5
                
        except Exception as e:
            logger.warning(f"Detection failed, assuming scanned: {e}")
            return 'scanned', 0.5
    
    def extract_native(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract from native PDF with exact positioning."""
        logger.info(f"🎯 Using NATIVE extraction for {pdf_path}")
        
        doc = fitz.open(pdf_path)
        page = doc[0]  # Single page for now
        
        extracted = []
        blocks = page.get_text("dict")
        
        for block in blocks.get('blocks', []):
            if 'lines' not in block:
                continue
                
            for line in block['lines']:
                for span in line['spans']:
                    text = span['text'].strip()
                    if not text:
                        continue
                    
                    bbox = span['bbox']
                    extracted.append({
                        'text': text,
                        'page': 1,
                        'x': int(bbox[0]),
                        'y': int(bbox[1]),
                        'width': int(bbox[2] - bbox[0]),
                        'height': int(bbox[3] - bbox[1]),
                        'confidence': 100
                    })
        
        doc.close()
        logger.info(f"   Extracted {len(extracted)} text items natively")
        return extracted
    
    def extract_ocr(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract from scanned PDF using OCR."""
        logger.info(f"🔍 Using OCR extraction for {pdf_path}")
        
        # Convert to image
        if self.poppler_path:
            images = convert_from_path(pdf_path, dpi=self.dpi, poppler_path=self.poppler_path)
        else:
            images = convert_from_path(pdf_path, dpi=self.dpi)
        
        # OCR first page
        img = images[0]
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        extracted = []
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > self.confidence_threshold and data['text'][i].strip():
                extracted.append({
                    'text': data['text'][i],
                    'page': 1,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': data['conf'][i]
                })
        
        logger.info(f"   Extracted {len(extracted)} text items via OCR")
        return extracted
    
    def extract(self, pdf_path: str, force_mode: str = None) -> List[Dict[str, Any]]:
        """
        Smart extraction - auto-detects and routes.
        
        Args:
            pdf_path: Path to PDF
            force_mode: Optional 'native' or 'ocr' to override detection
            
        Returns:
            List of extracted text items with positions
        """
        # Allow manual override
        if force_mode:
            if force_mode == 'native':
                return self.extract_native(pdf_path)
            elif force_mode == 'ocr':
                return self.extract_ocr(pdf_path)
        
        # Auto-detect
        pdf_type, confidence = self.detect_pdf_type(pdf_path)
        logger.info(f"📋 Detected: {pdf_type} PDF (confidence: {confidence:.0%})")
        
        # Route to appropriate extractor
        if pdf_type == 'native':
            return self.extract_native(pdf_path)
        else:
            return self.extract_ocr(pdf_path)