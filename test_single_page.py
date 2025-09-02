# test_single_page.py
"""
Single page test - simplified version
"""

import logging
import sys
import pandas as pd
from smart_extract import SmartExtractor  # Fixed import
from slicer import TableSlicer
import json
import os

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('single_page_debug.log', mode='w')
    ]
)

def test_single_page():
    """Test one page with full debugging."""
    
    print("\n" + "="*80)
    print("BULLDOZER SINGLE PAGE TEST")
    print("="*80)
    
    # Configuration
    PDF_PATH = r"C:\Users\mhartigan\venv\pdf_extractor\DRISCOLL CF ORDERS FOR THE WEEK OF SEPTEMBER 8, 2025_page1.pdf"
    VENDOR = "newark"  # Using Newark template
    
    # Load template
    with open('vendor_templates.json', 'r') as f:
        templates = json.load(f)
    
    if VENDOR not in templates:
        print("ERROR: No template found for vendor:", VENDOR)
        return
    
    template = templates[VENDOR]
    table_box = template['table_box']
    columns = template['columns']
    
    print("\nTemplate Info:")
    print("  Table box:", table_box)
    print("  Number of columns:", len(columns)-1)
    print("  Column positions:", columns)
    
    # Extract text using SmartExtractor
    filename = os.path.basename(PDF_PATH)
    print("\nExtracting from:", filename)
    
    # Use SmartExtractor class
    extractor = SmartExtractor()
    extracted = extractor.extract(PDF_PATH)
    
    print("  Extracted", len(extracted), "text items")
    
    # Show first 10 text items
    print("\nFirst 10 text items:")
    for i, item in enumerate(extracted[:10]):
        x = item['x']
        width = item.get('width', 0)
        text = item['text'][:30] if len(item['text']) > 30 else item['text']
        print("  Item", i, ":", text, "at x=", x, "width=", width)
    
    # Process
    print("\nProcessing with slicer...")
    slicer = TableSlicer(row_threshold=30)
    df = slicer.slice_to_table(extracted, table_box, columns)
    
    print("\nResult shape:", df.shape)
    
    # Save
    output_file = "test_driscoll_page.xlsx"
    df.to_excel(output_file, index=False)
    print("\nSaved to:", output_file)
    
    # Show first few rows
    print("\nFirst 5 rows:")
    for idx, row in df.head(5).iterrows():
        print("Row", idx, ":", list(row)[:5], "...")  # Show first 5 columns
    
    print("\n" + "="*80)
    print("Check single_page_debug.log for details")
    print("="*80)

if __name__ == "__main__":
    test_single_page()