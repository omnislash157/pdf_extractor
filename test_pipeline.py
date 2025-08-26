# test_pipeline.py
"""
Test script to validate Table Slicer installation and basic functionality.
Run: python test_pipeline.py
"""

import sys
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import pandas as pd


def create_test_pdf():
    """Create a simple test PDF with table."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed. Skipping PDF test.")
        return None
    
    # Create a simple PDF with table
    doc = fitz.open()
    page = doc.new_page()
    
    # Add simple table text
    text = """
    INVOICE #12345
    
    Item            Quantity    Price
    Widget A        10          $50.00
    Widget B        5           $25.00
    Widget C        2           $100.00
    
    Total: $325.00
    """
    
    page.insert_text((50, 50), text, fontsize=12)
    
    # Save to temp file
    pdf_path = "test_invoice.pdf"
    doc.save(pdf_path)
    doc.close()
    
    print(f"✅ Created test PDF: {pdf_path}")
    return pdf_path


def test_ocr():
    """Test OCR functionality."""
    try:
        import pytesseract
        
        # Create simple test image
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "TEST OCR", fill='black')
        
        # Test OCR
        text = pytesseract.image_to_string(img)
        
        if "TEST" in text or "OCR" in text:
            print("✅ OCR is working")
            return True
        else:
            print("⚠️ OCR returned unexpected result:", text)
            return False
            
    except Exception as e:
        print(f"❌ OCR test failed: {e}")
        print("   Make sure tesseract is installed: apt-get install tesseract-ocr")
        return False


def test_modules():
    """Test module imports."""
    modules_ok = True
    
    try:
        from extract import OCRExtractor
        print("✅ extract.py loaded")
    except Exception as e:
        print(f"❌ Failed to load extract.py: {e}")
        modules_ok = False
    
    try:
        from template import TemplateManager, TableTemplate
        print("✅ template.py loaded")
    except Exception as e:
        print(f"❌ Failed to load template.py: {e}")
        modules_ok = False
    
    try:
        from slicer import TableSlicer
        print("✅ slicer.py loaded")
    except Exception as e:
        print(f"❌ Failed to load slicer.py: {e}")
        modules_ok = False
    
    try:
        from table_slicer import TableSlicerPipeline
        print("✅ table_slicer.py loaded")
    except Exception as e:
        print(f"❌ Failed to load table_slicer.py: {e}")
        modules_ok = False
    
    try:
        import tkinter
        from drawsnap_gui import DrawSnapApp
        print("✅ GUI modules available")
    except:
        print("⚠️ GUI not available (optional)")
    
    return modules_ok


def test_pipeline():
    """Test basic pipeline functionality."""
    try:
        from table_slicer import TableSlicerPipeline
        from template import TableTemplate
        
        # Create pipeline
        pipeline = TableSlicerPipeline()
        
        # Create test template
        template = TableTemplate(
            table_box=[50, 100, 400, 300],
            columns=[50, 200, 350, 400],
            vendor='test_vendor'
        )
        
        # Validate template
        if template.validate():
            print("✅ Template validation working")
        else:
            print("❌ Template validation failed")
            return False
        
        # Test vendor detection
        test_text = [{'text': 'Amazon', 'x': 10, 'y': 10, 'width': 50, 'height': 10}]
        vendor = pipeline.template_manager.detect_vendor(test_text, pipeline.vendor_keywords)
        
        if vendor == 'amazon':
            print("✅ Vendor detection working")
        else:
            print(f"⚠️ Vendor detection returned: {vendor}")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("Table Slicer Installation Test")
    print("=" * 50)
    
    results = []
    
    # Test imports
    print("\n1. Testing module imports...")
    results.append(test_modules())
    
    # Test OCR
    print("\n2. Testing OCR...")
    results.append(test_ocr())
    
    # Test pipeline
    print("\n3. Testing pipeline components...")
    results.append(test_pipeline())
    
    # Create test PDF
    print("\n4. Creating test PDF...")
    pdf_path = create_test_pdf()
    
    # Summary
    print("\n" + "=" * 50)
    if all(results):
        print("✅ All tests passed! Table Slicer is ready to use.")
        print("\nUsage:")
        print("  python table_slicer.py <pdf_path>")
        if pdf_path:
            print(f"\nTry it now:")
            print(f"  python table_slicer.py {pdf_path}")
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        print("\nCommon fixes:")
        print("  - Install tesseract: apt-get install tesseract-ocr")
        print("  - Install Python deps: pip install -r requirements.txt")
    
    print("=" * 50)
    
    # Cleanup
    if pdf_path and os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except:
            pass


if __name__ == '__main__':
    main()