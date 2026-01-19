# Test Data Directory

Place test PDFs here for integration testing.

## Required Test Files

For the E2E integration test (`test_ingestion_e2e.ps1`), you need:

**Default test file:**
- `test_pathfinder_rulebook.pdf` - Small excerpt from Pathfinder 1e Core Rulebook (5-10 pages recommended)

## Recommended Test PDFs

Use small excerpts (5-20 pages) for faster testing:

### Pathfinder 1e
- Core Rulebook excerpt (character creation chapter)
- Bestiary excerpt (5-10 creatures)
- Adventure Path excerpt

### Cyberpunk RED
- Quick Start Guide
- Core Rulebook excerpt (lifepath chapter)

### D&D 5e
- Basic Rules excerpt
- Player's Handbook character creation

### Other TTRPGs
- Any TTRPG rulebook excerpt with mixed content:
  - Rules text
  - Tables (stat blocks, equipment)
  - Images/illustrations
  - Sidebars

## Creating Test Excerpts

To create a small test PDF from a larger rulebook:

**Using Adobe Acrobat:**
1. Open the full rulebook
2. Select "Organize Pages"
3. Select pages 10-20 (or any 10-page range)
4. Click "Extract"
5. Save as `test_pathfinder_rulebook.pdf`

**Using PowerShell + PDFtk:**
```powershell
# Extract pages 10-20
pdftk "Pathfinder_Core_Rulebook.pdf" cat 10-20 output "test_pathfinder_rulebook.pdf"
```

**Using Python + PyPDF2:**
```python
from PyPDF2 import PdfReader, PdfWriter

reader = PdfReader("Pathfinder_Core_Rulebook.pdf")
writer = PdfWriter()

for page_num in range(10, 20):  # Pages 10-20
    writer.add_page(reader.pages[page_num])

with open("test_pathfinder_rulebook.pdf", "wb") as output_file:
    writer.write(output_file)
```

## File Naming Convention

Test files should follow this pattern:
- `test_<system>_<book>.pdf`
- Examples:
  - `test_pathfinder_rulebook.pdf`
  - `test_cyberpunk_quickstart.pdf`
  - `test_dnd5e_basic_rules.pdf`

## Copyright Notice

⚠️ **IMPORTANT:** Only use PDFs you have legal rights to test with.

- Use publicly available Quick Start Guides / Basic Rules
- Use excerpts from books you own (for personal testing only)
- Never distribute copyrighted content
- Test data is for development/testing purposes only

## File Characteristics for Good Testing

Ideal test PDFs should include:

### Content Diversity
- ✅ Rules text (paragraphs)
- ✅ Tables (stat blocks, equipment lists)
- ✅ Images/illustrations
- ✅ Sidebars/callouts
- ✅ Headings/sections
- ✅ Lists (numbered, bulleted)

### Technical Characteristics
- ✅ Text-based (not scanned images)
- ✅ Well-formatted (proper fonts, structure)
- ✅ 5-20 pages (faster testing)
- ✅ ~1-5 MB file size

### Avoid
- ❌ Scanned image PDFs (OCR quality varies)
- ❌ Full core books (too large for quick testing)
- ❌ Corrupted/malformed PDFs
- ❌ Password-protected PDFs

## Current Test Files

(List your test files here as you add them)

- [ ] `test_pathfinder_rulebook.pdf` - Pathfinder 1e excerpt
- [ ] `test_cyberpunk_quickstart.pdf` - Cyberpunk RED Quick Start
- [ ] (Add more as needed)
