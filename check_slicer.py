# check_slicer.py - Save and run this
from slicer import TableSlicer
import inspect

slicer = TableSlicer()
methods = [m for m in dir(slicer) if not m.startswith('__')]
print("Methods found in TableSlicer:")
for m in methods:
    print(f"  - {m}")

if '_bin_into_columns' not in methods:
    print("\n❌ MISSING: _bin_into_columns method!")
else:
    print("\n✅ _bin_into_columns exists")