"""Fix seed function calls to include client parameter."""
import re
from pathlib import Path

test_file = Path(__file__).parent / "backend" / "tests" / "test_matter_resolution.py"
content = test_file.read_text()

# Update all seed calls to include client parameter
patterns = [
    (r'_seed_matter\((db_session)(,|\))', r'_seed_matter(\1, client\2'),
    (r'_seed_matter\((db_session, "[^"]+")(\))', r'_seed_matter(\1, client\2'),
    (r'_seed_email\((db_session)(,|\))', r'_seed_email(\1, client\2'),
    (r'_seed_email\((db_session,\s*client=None)(,|\))', r'_seed_email(\1, client\2'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

# Write back
test_file.write_text(content)
print("Updated seed function calls")