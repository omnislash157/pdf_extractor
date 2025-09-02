# newark_batch_bulldozer.py - FINAL VERSION
import glob
import os
from table_slicer import TableSlicerPipeline
import pandas as pd
import datetime

# Initialize pipeline
pipeline = TableSlicerPipeline()

# Process all Newark pages
all_dfs = []
pdf_files = sorted(glob.glob("DRISCOLL CF ORDERS FOR THE WEEK OF SEPTEMBER 8, 2025_page*.pdf"))

print(f"🚜 PROCESSING {len(pdf_files)} PAGES...")

for i, pdf in enumerate(pdf_files, 1):
    try:
        print(f"[{i}/{len(pdf_files)}] Processing {pdf}...")
        
        # Extract to DataFrame (skip Excel for now)
        from extract import OCRExtractor
        from slicer import TableSlicer
        from template import TemplateManager
        
        # Get template
        tm = TemplateManager()
        template = tm.get_template("newark")
        
        # Extract and slice
        extractor = OCRExtractor()
        extracted = extractor.extract_from_pdf(pdf)
        slicer = TableSlicer()
        df = slicer.slice_to_table(extracted, template.table_box, template.columns)
        
        all_dfs.append(df)
        print(f"   ✅ {len(df)} rows extracted")  # Row count for sanity
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        continue

# MERGE ALL INTO ONE MEGA-EXCEL
print(f"📊 Merging {len(all_dfs)} tables...")
mega_df = pd.concat(all_dfs, ignore_index=True)

# Save with timestamp (no overwrites!)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"NEWARK_COMPLETE_{timestamp}.xlsx"
mega_df.to_excel(output_file, index=False, header=False)

print(f"✅ DONE! Output: {output_file}")
print(f"📈 Total rows: {len(mega_df)}")