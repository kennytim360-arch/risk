"""Quick fix for indentation issues"""

import sys
from pathlib import Path

# Fix correlation analyzer
analyzer_file = Path(__file__).parent.parent / "src" / "correlation" / "analyzer.py"

print(f"Fixing {analyzer_file}...")

with open(analyzer_file, 'r') as f:
    content = f.read()

# Replace any problematic sections
content = content.replace('\t', '    ')  # Replace tabs with spaces

with open(analyzer_file, 'w') as f:
    f.write(content)

print("✓ Fixed indentation issues")
print("\nNow try: python scripts\\live_analysis.py")
