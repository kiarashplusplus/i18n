# Texas Driver Handbook (DL-7) — English → Farsi Translation

Side-by-side page-by-page translation of the Texas Driver Handbook from English to Farsi (Persian).

## Files

| File | Description |
|------|-------------|
| `dl-7.pdf` | Original English PDF (89 pages) |
| `output/handbook_en_fa.pdf` | Side-by-side English/Farsi PDF |
| `output/handbook_en_fa.html` | HTML version (viewable in browser) |
| `extracted_pages.json` | Extracted English text per page |
| `translated_pages.json` | Farsi translations per page |
| `translate.py` | Translation pipeline script |

## How It Works

1. **Text extraction** — PyPDF2 extracts text from each of the 89 PDF pages
2. **Translation** — OpenAI GPT-5.2 translates each page to formal Farsi with 6 parallel workers
3. **PDF generation** — WeasyPrint renders a side-by-side A3 landscape PDF with:
   - English (LTR) on the left column
   - Farsi (RTL) on the right column
   - Page numbers matching the original document

## Re-running

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Full run (translate + generate PDF) — supports checkpoint resume
python3 translate.py

# Regenerate PDF only (from existing translations)
python3 translate.py --pdf-only
```

## Dependencies

```bash
pip install openai PyPDF2 weasyprint arabic-reshaper python-bidi
sudo apt-get install fonts-noto-core  # Noto Naskh Arabic font for Farsi
```

## Translation Quality

- Model: GPT-5.2 (state-of-the-art, Feb 2026)
- Proper nouns (Texas, DPS) preserved in English with Farsi transliteration
- Formal register appropriate for government documents
- Numbers and legal references preserved exactly
