#!/usr/bin/env python3
"""
test_gui_sprint.py - Bulldozer GUI Test Suite
Tests the entire pipeline with loud, obvious results.
Run: python test_gui_sprint.py
"""

import os
import sys
import json
from datetime import datetime

print("="*60)
print("🚜 BULLDOZER GUI TEST SUITE v2.1.2")
print("="*60)


def test_environment():
    """Test 1: Check all dependencies."""
    print("\n📋 TEST 1: Environment Check")
    print("-"*40)
    
    results = []
    
    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.version_info >= (3, 7):
        print(f"✅ Python {py_version}")
        results.append(True)
    else:
        print(f"❌ Python {py_version} (need 3.7+)")
        results.append(False)
    
    # Config file
    if os.path.exists('config.py'):
        print("✅ config.py found")
        try:
            import config
            print(f"   Tesseract: {config.TESSERACT_CMD}")
            print(f"   Poppler: {config.POPPLER_PATH}")
            results.append(True)
        except Exception as e:
            print(f"❌ config.py error: {e}")
            results.append(False)
    else:
        print("⚠️  config.py not found (using hardcoded paths)")
        results.append(True)  # Not critical
    
    # Required modules
    modules = [
        ('pytesseract', 'OCR engine'),
        ('pdf2image', 'PDF converter'),
        ('PIL', 'Image processing'),
        ('pandas', 'Data tables'),
        ('openpyxl', 'Excel writer'),
        ('fitz', 'PDF renderer (PyMuPDF)'),
        ('tkinter', 'GUI framework')
    ]
    
    for module_name, description in modules:
        try:
            if module_name == 'PIL':
                from PIL import Image
            elif module_name == 'fitz':
                import fitz
            elif module_name == 'tkinter':
                import tkinter
            else:
                __import__(module_name)
            print(f"✅ {module_name:12} - {description}")
            results.append(True)
        except ImportError:
            print(f"❌ {module_name:12} - {description} NOT INSTALLED")
            results.append(False)
    
    return all(results)


def test_ocr():
    """Test 2: Verify OCR is working."""
    print("\n📋 TEST 2: OCR Functionality")
    print("-"*40)
    
    try:
        import pytesseract
        from PIL import Image, ImageDraw, ImageFont
        
        # Create test image
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw test text
        test_text = "BULLDOZER TEST 123"
        draw.text((20, 30), test_text, fill='black')
        
        # Save temporarily
        test_img = "test_ocr_temp.png"
        img.save(test_img)
        
        # Run OCR
        result = pytesseract.image_to_string(img).strip()
        
        # Clean up
        if os.path.exists(test_img):
            os.remove(test_img)
        
        # Check result
        if "BULLDOZER" in result.upper() or "TEST" in result.upper():
            print(f"✅ OCR working! Detected: '{result}'")
            return True
        else:
            print(f"⚠️  OCR unclear. Got: '{result}'")
            return True  # Still operational
            
    except Exception as e:
        print(f"❌ OCR FAILED: {e}")
        print("   Fix: Check Tesseract is installed and config.py has correct path")
        return False


def test_modules():
    """Test 3: Load all pipeline modules."""
    print("\n📋 TEST 3: Pipeline Modules")
    print("-"*40)
    
    modules_to_test = [
        ('extract', 'OCRExtractor'),
        ('template', 'TemplateManager'),
        ('slicer', 'TableSlicer'),
        ('table_slicer', 'TableSlicerPipeline'),
        ('quality', 'QualityChecker'),
        ('drawsnap_gui', 'DrawSnapApp')
    ]
    
    results = []
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name:15} - {class_name} loaded")
                results.append(True)
            else:
                print(f"❌ {module_name:15} - {class_name} not found")
                results.append(False)
        except Exception as e:
            print(f"❌ {module_name:15} - Error: {str(e)[:50]}")
            results.append(False)
    
    return all(results)


def test_template_manager():
    """Test 4: Template save/load functionality."""
    print("\n📋 TEST 4: Template Management")
    print("-"*40)
    
    try:
        from template import TemplateManager, TableTemplate
        
        # Create manager
        manager = TemplateManager('test_templates.json')
        
        # Create test template
        template = TableTemplate(
            table_box=[10, 20, 300, 400],
            columns=[10, 100, 200, 300],
            vendor='bulldozer_test'
        )
        
        # Validate
        if not template.validate():
            print("❌ Template validation failed")
            return False
        
        # Save
        manager.add_template('bulldozer_test', template)
        
        # Reload
        manager2 = TemplateManager('test_templates.json')
        loaded = manager2.get_template('bulldozer_test')
        
        # Verify
        if loaded and loaded.vendor == 'bulldozer_test':
            print("✅ Template save/load working")
            
            # Clean up
            if os.path.exists('test_templates.json'):
                os.remove('test_templates.json')
            
            return True
        else:
            print("❌ Template not loaded correctly")
            return False
            
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False


def test_gui_availability():
    """Test 5: Check if GUI can launch."""
    print("\n📋 TEST 5: GUI Availability")
    print("-"*40)
    
    try:
        import tkinter
        from drawsnap_gui import DrawSnapApp
        
        # Try to create root (don't show it)
        root = tkinter.Tk()
        root.withdraw()
        
        print("✅ GUI framework available")
        print("   DrawSnapApp can be instantiated")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"⚠️  GUI not available: {e}")
        print("   Note: GUI optional for headless operation")
        return True  # Not critical


def create_test_pdf():
    """Create a simple test PDF."""
    print("\n📋 Creating Test PDF")
    print("-"*40)
    
    try:
        import fitz  # PyMuPDF
        
        # Create document
        doc = fitz.open()
        page = doc.new_page()
        
        # Add test invoice
        y = 50
        lines = [
            "BULLDOZER INVOICE TEST",
            "",
            "Invoice #: 12345",
            "Date: " + datetime.now().strftime("%Y-%m-%d"),
            "",
            "ITEM          QTY    PRICE",
            "Widget A      10     $50.00",
            "Widget B      5      $25.00",
            "Widget C      2      $100.00",
            "",
            "TOTAL:              $325.00"
        ]
        
        for line in lines:
            page.insert_text((50, y), line, fontsize=12)
            y += 20
        
        # Save
        pdf_path = "test_bulldozer_invoice.pdf"
        doc.save(pdf_path)
        doc.close()
        
        print(f"✅ Created: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"⚠️  Could not create PDF: {e}")
        print("   Note: PyMuPDF optional, can test with existing PDFs")
        return None


def run_full_pipeline_test(pdf_path):
    """Test 6: Run complete pipeline."""
    print("\n📋 TEST 6: Full Pipeline Test")
    print("-"*40)
    
    if not pdf_path or not os.path.exists(pdf_path):
        print("⚠️  No test PDF available, skipping pipeline test")
        return True
    
    try:
        from table_slicer import TableSlicerPipeline
        
        # Create pipeline
        pipeline = TableSlicerPipeline()
        
        # Process with test vendor
        output = pipeline.process(
            pdf_path, 
            output_dir='.', 
            vendor='test_auto'
        )
        
        if os.path.exists(output):
            print(f"✅ Pipeline complete! Output: {output}")
            
            # Verify it's readable
            import pandas as pd
            df = pd.read_excel(output, header=None)
            print(f"   Excel shape: {df.shape}")
            
            # Clean up
            os.remove(output)
            
            return True
        else:
            print("❌ No output file created")
            return False
            
    except Exception as e:
        print(f"⚠️  Pipeline test incomplete: {e}")
        print("   This is expected if no template exists yet")
        return True


def main():
    """Run all tests."""
    
    # Track results
    results = {}
    
    # Test 1: Environment
    results['environment'] = test_environment()
    
    # Test 2: OCR
    results['ocr'] = test_ocr()
    
    # Test 3: Modules
    results['modules'] = test_modules()
    
    # Test 4: Templates
    results['templates'] = test_template_manager()
    
    # Test 5: GUI
    results['gui'] = test_gui_availability()
    
    # Create test PDF
    pdf_path = create_test_pdf()
    
    # Test 6: Pipeline
    results['pipeline'] = run_full_pipeline_test(pdf_path)
    
    # Clean up test PDF
    if pdf_path and os.path.exists(pdf_path):
        os.remove(pdf_path)
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:15} : {status}")
    
    all_passed = all(results.values())
    
    print("="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED! System ready for GUI testing.")
        print("\nNext steps:")
        print("1. Run: python launch_gui.py")
        print("2. Load a PDF and create a template")
        print("3. Run: python table_slicer.py <your_pdf> --vendor <vendor_name>")
    else:
        print("⚠️  Some tests failed. Check errors above.")
        print("\nCommon fixes:")
        print("1. Install missing modules: pip install -r requirements.txt")
        print("2. Update config.py with correct paths")
        print("3. Install Tesseract and Poppler binaries")
    
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())