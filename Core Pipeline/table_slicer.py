# table_slicer.py
"""
Table Slicer - Modular PDF table extraction pipeline.
Bulldozer approach: deterministic, modular, unstoppable.

Usage:
    python table_slicer.py <pdf_path> [--output-dir OUTPUT_DIR] [--vendor VENDOR]
    
    As module:
    from table_slicer import TableSlicerPipeline
    pipeline = TableSlicerPipeline()
    output = pipeline.process('invoice.pdf')
"""

import os
import sys
import argparse
from typing import Optional, Dict, List, Any
import pandas as pd
from datetime import datetime

# Import modules
from extract import OCRExtractor
from template import TemplateManager, TableTemplate
from slicer import TableSlicer

# Try import GUI
GUI_AVAILABLE = True
try:
    from drawsnap_gui import create_template_gui
    import tkinter as tk
except ImportError:
    GUI_AVAILABLE = False
    print("Warning: GUI not available. Install tkinter for visual template creation.")


class TableSlicerPipeline:
    """
    Main orchestrator for table extraction pipeline.
    Coordinates OCR, template management, and table slicing.
    """
    
    # Default vendor keywords for auto-detection
    DEFAULT_VENDOR_KEYWORDS = {
        'amazon': ['Amazon', 'AWS', 'Amazon Web Services', 'AMZN'],
        'google': ['Google', 'GCP', 'Google Cloud', 'Alphabet'],
        'microsoft': ['Microsoft', 'Azure', 'MSFT', 'Office 365'],
        'apple': ['Apple', 'AAPL', 'iTunes', 'App Store'],
        'walmart': ['Walmart', 'WMT', 'Sam\'s Club'],
        'target': ['Target', 'TGT', 'Target Corporation'],
        # Add more as needed
    }
    
    def __init__(self, 
                 templates_file: str = 'vendor_templates.json',
                 confidence_threshold: int = 60,
                 row_threshold: int = 20,
                 dpi: int = 150):
        """
        Initialize pipeline components.
        
        Args:
            templates_file: Path to templates JSON file
            confidence_threshold: OCR confidence threshold (0-100)
            row_threshold: Pixel threshold for row grouping
            dpi: DPI for PDF rendering
        """
        self.extractor = OCRExtractor(confidence_threshold, dpi)
        self.template_manager = TemplateManager(templates_file)
        self.slicer = TableSlicer(row_threshold)
        self.vendor_keywords = self.DEFAULT_VENDOR_KEYWORDS.copy()
    
    def add_vendor_keywords(self, vendor: str, keywords: List[str]):
        """
        Add or update vendor keywords for auto-detection.
        
        Args:
            vendor: Vendor identifier
            keywords: List of keywords to match
        """
        self.vendor_keywords[vendor] = keywords
    
    def process(self, 
                input_path: str, 
                output_dir: str = '.', 
                vendor: Optional[str] = None,
                force_new_template: bool = False) -> str:
        """
        Process PDF/image to extract table to Excel.
        
        Args:
            input_path: Path to PDF or image file
            output_dir: Directory for output Excel file
            vendor: Optional vendor name (auto-detect if not provided)
            force_new_template: Force creation of new template
            
        Returns:
            Path to output Excel file
            
        Raises:
            ValueError: If input file not found or invalid
            RuntimeError: If processing fails
        """
        # Validate input
        if not os.path.exists(input_path):
            raise ValueError(f"Input file not found: {input_path}")
        
        # Determine file type and extract
        print(f"[1/5] Extracting text from: {input_path}")
        
        if input_path.lower().endswith('.pdf'):
            extracted = self.extractor.extract_from_pdf(input_path)
        elif input_path.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
            extracted = self.extractor.extract_from_image(input_path)
        else:
            raise ValueError(f"Unsupported file type: {input_path}")
        
        print(f"[2/5] Extracted {len(extracted)} text elements")
        
        # Detect or get vendor
        if not vendor:
            vendor = self.template_manager.detect_vendor(extracted, self.vendor_keywords)
            if vendor:
                print(f"[3/5] Auto-detected vendor: {vendor}")
            else:
                vendor = self._prompt_vendor()
        else:
            print(f"[3/5] Using specified vendor: {vendor}")
        
        # Get or create template
        template = None if force_new_template else self.template_manager.get_template(vendor)
        
        if not template:
            print(f"[4/5] Creating new template for vendor: {vendor}")
            template = self._create_template(vendor, input_path)
            self.template_manager.add_template(vendor, template)
        else:
            print(f"[4/5] Using existing template for vendor: {vendor}")
        
        # Apply template to slice table
        print(f"[5/5] Slicing table using template")
        df = self.slicer.slice_to_table(
            extracted, 
            template.table_box, 
            template.columns
        )
        
        # Generate output filename
        base_name = os.path.basename(input_path).rsplit('.', 1)[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"TableSlice_{vendor}_{base_name}_{timestamp}.xlsx"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save to Excel
        try:
            df.to_excel(output_path, index=False, header=False)
            print(f"✅ Output saved: {output_path}")
        except Exception as e:
            # Fallback to CSV if Excel fails
            output_path = output_path.replace('.xlsx', '.csv')
            df.to_csv(output_path, index=False, header=False)
            print(f"⚠️ Excel save failed, saved as CSV: {output_path}")
        
        return output_path
    
    def _prompt_vendor(self) -> str:
        """Prompt user for vendor name."""
        vendor = input("Vendor not detected. Enter vendor name: ").strip()
        return vendor if vendor else 'unknown'
    
    def _create_template(self, vendor: str, pdf_path: str) -> TableTemplate:
        """
        Create new template using GUI or CLI.
        
        Args:
            vendor: Vendor name
            pdf_path: Path to PDF for template creation
            
        Returns:
            Created TableTemplate
            
        Raises:
            RuntimeError: If template creation fails
        """
        if GUI_AVAILABLE:
            # Use GUI
            print("Opening template creation GUI...")
            success = create_template_gui(pdf_path, vendor)
            
            if success:
                # Reload templates and get the new one
                self.template_manager.load_templates()
                template = self.template_manager.get_template(vendor)
                if template:
                    return template
            
            raise RuntimeError(f"Template creation cancelled or failed for vendor: {vendor}")
        
        else:
            # Fallback to CLI
            print("GUI not available. Using CLI for template creation.")
            print("Enter table box coordinates [x1,y1,x2,y2]:")
            box_input = input().strip()
            
            try:
                table_box = [int(x) for x in box_input.split(',')]
                if len(table_box) != 4:
                    raise ValueError("Box requires 4 coordinates")
            except Exception as e:
                raise RuntimeError(f"Invalid box coordinates: {e}")
            
            print("Enter column separator x-positions (e.g., 0,150,300,450):")
            col_input = input().strip()
            
            try:
                columns = [int(x) for x in col_input.split(',')]
                if len(columns) < 2:
                    raise ValueError("At least 2 column positions required")
            except Exception as e:
                raise RuntimeError(f"Invalid column positions: {e}")
            
            template = TableTemplate(
                table_box=table_box,
                columns=columns,
                vendor=vendor,
                created=datetime.now().isoformat()
            )
            
            if not template.validate():
                raise RuntimeError("Invalid template created")
            
            return template


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Table Slicer - Extract tables from PDFs/images to Excel"
    )
    parser.add_argument('input_path', help='Path to PDF or image file')
    parser.add_argument('--output-dir', default='.', help='Output directory (default: current)')
    parser.add_argument('--vendor', help='Vendor name (auto-detect if not specified)')
    parser.add_argument('--force-new-template', action='store_true', 
                       help='Force creation of new template')
    parser.add_argument('--templates-file', default='vendor_templates.json',
                       help='Path to templates JSON file')
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        pipeline = TableSlicerPipeline(templates_file=args.templates_file)
        
        # Process file
        output = pipeline.process(
            args.input_path,
            args.output_dir,
            args.vendor,
            args.force_new_template
        )
        
        print(f"\n✅ Success! Table extracted to: {output}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())