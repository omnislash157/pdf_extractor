#!/usr/bin/env python3
"""
launch_gui.py - Standalone DrawSnap GUI Launcher
Simple launcher for creating table extraction templates visually.
Run: python launch_gui.py
"""

import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from drawsnap_gui import create_template_gui
except ImportError:
    print("❌ ERROR: drawsnap_gui.py not found in current directory!")
    print("   Make sure this launcher is in the same folder as drawsnap_gui.py")
    sys.exit(1)

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 DrawSnap Template Creator - Standalone Launcher")
    print("   Draw table regions visually on PDF documents")
    print("=" * 60)
    
    # Create hidden root for dialogs
    root = tk.Tk()
    root.withdraw()
    
    # Select PDF with helpful prompt
    print("\n📂 Opening file selector...")
    pdf_path = filedialog.askopenfilename(
        title="Select PDF to Create Template",
        filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
        initialdir=os.getcwd()
    )
    
    if not pdf_path:
        messagebox.showinfo(
            "DrawSnap Launcher", 
            "No PDF selected.\nTemplate creation cancelled."
        )
        root.destroy()
        print("⚠️  No PDF selected - exiting.")
        sys.exit(0)
    
    print(f"✓  Selected: {os.path.basename(pdf_path)}")
    
    # Get vendor with clear instructions
    print("\n🏢 Vendor identification...")
    vendor = simpledialog.askstring(
        "Vendor Identification", 
        "Enter the vendor name for this template:\n\n" +
        "Examples: amazon, walmart, invoicesrus\n" +
        "(Leave blank to use 'test' for testing)"
    )
    
    vendor = vendor.strip().lower() if vendor else 'test'
    print(f"✓  Vendor set to: '{vendor}'")
    
    # Clean up dialog root before launching main GUI
    root.destroy()
    
    # Launch DrawSnap
    print("\n📐 Launching DrawSnap GUI...")
    print("   Instructions:")
    print("   1. Click 'Draw Table Box' and drag a rectangle around the table")
    print("   2. Click 'Draw Columns' and click to add column separators")
    print("   3. Click 'Save Template' when done")
    print("-" * 60)
    
    try:
        success = create_template_gui(pdf_path, vendor)
    except Exception as e:
        print(f"\n❌ ERROR: GUI failed - {e}")
        sys.exit(1)
    
    # Report results
    print("-" * 60)
    if success:
        print("✅ SUCCESS! Template saved to vendor_templates.json")
        print(f"   Vendor: {vendor}")
        print(f"   Ready for: python table_slicer.py <pdf> --vendor {vendor}")
    else:
        print("❌ Template creation cancelled.")
        print("   No changes were saved.")
    print("=" * 60)