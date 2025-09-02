# ultimate_batch_processor.py - CLEAN VERSION
import glob
import pandas as pd
import datetime
from smart_extract import SmartExtractor
from slicer import TableSlicer
from template import TemplateManager

# Initialize smart extractor
extractor = SmartExtractor()

# Get vendor name ONCE
vendor = input("Enter vendor name (sysco/newark/etc): ").strip().lower()

# Process all pages
all_dfs = []
pdf_files = sorted(glob.glob("*_page*.pdf"))

print(f"🚜 SMART PROCESSING {len(pdf_files)} PAGES...")

# Get template ONCE before the loop
tm = TemplateManager()
template = tm.get_template(vendor)

if not template:
    print(f"❌ No template found for vendor: {vendor}")
    print(f"Available vendors: {tm.list_vendors()}")
    exit()

for i, pdf in enumerate(pdf_files, 1):
    try:
        print(f"[{i}/{len(pdf_files)}] Processing {pdf}...")
        
        # SMART extraction - auto-detects!
        extracted = extractor.extract(pdf)
        
        # Slice using the template we already loaded
        slicer = TableSlicer()
        df = slicer.slice_to_table(extracted, template.table_box, template.columns)
        
        all_dfs.append(df)
        print(f"   ✅ {len(df)} rows")
        
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        continue

# Merge and save
if all_dfs:
    mega_df = pd.concat(all_dfs, ignore_index=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{vendor.upper()}_SMART_{timestamp}.xlsx"
    mega_df.to_excel(output_file, index=False, header=False)
    
    print(f"✅ DONE! Output: {output_file}")
    print(f"📈 Total rows: {len(mega_df)}")
else:
    print("❌ No data processed - check errors above")