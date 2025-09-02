# debug_extraction.py - See what's actually happening
from extract import OCRExtractor
import fitz  # PyMuPDF

pdf_path = "DRISCOLL CF ORDERS FOR THE WEEK OF SEPTEMBER 8, 2025_page1.pdf"

# Test 1: OCR extraction (what you're using now)
print("=" * 50)
print("OCR EXTRACTION:")
extractor = OCRExtractor()
ocr_result = extractor.extract_from_pdf(pdf_path)
print(f"Found {len(ocr_result)} items via OCR")
if ocr_result:
    print(f"First item: {ocr_result[0]}")
    print(f"X-coordinate range: {min(r['x'] for r in ocr_result)} to {max(r['x'] for r in ocr_result)}")

# Test 2: Native extraction
print("=" * 50)  
print("NATIVE EXTRACTION:")
doc = fitz.open(pdf_path)
page = doc[0]
blocks = page.get_text("dict")
text_count = sum(len(b.get('lines', [])) for b in blocks.get('blocks', []) if 'lines' in b)
print(f"Found {text_count} text lines natively")