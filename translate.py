#!/usr/bin/env python3
"""
Texas Driver Handbook (DL-7) — English → Farsi Translation Pipeline
Uses OpenAI GPT-5.2 for translation and WeasyPrint for side-by-side PDF generation.
"""

import json
import os
import sys
import time
import concurrent.futures
from pathlib import Path

from openai import OpenAI

# ── Configuration ──────────────────────────────────────────────────────────────
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-5.2"
MAX_WORKERS = 6  # parallel translation threads
INPUT_JSON = Path(__file__).parent / "extracted_pages.json"
OUTPUT_JSON = Path(__file__).parent / "translated_pages.json"
OUTPUT_HTML = Path(__file__).parent / "output" / "handbook_en_fa.html"
OUTPUT_PDF = Path(__file__).parent / "output" / "handbook_en_fa.pdf"

SYSTEM_PROMPT = """\
You are an expert English-to-Farsi (Persian) translator specializing in official \
government documents, legal texts, and driver licensing materials. Translate the \
following English text into fluent, natural Farsi.

Rules:
1. Preserve the original meaning precisely — do not omit or add information.
2. Keep proper nouns (e.g., "Texas", "DPS") in their original English form, \
   optionally followed by a Farsi transliteration in parentheses the first time.
3. Preserve numerical values, measurements, and legal references exactly.
4. Use formal Farsi register appropriate for an official handbook.
5. Maintain paragraph structure and bullet/list formatting from the source.
6. For headings and chapter titles, provide a clear Farsi translation.
7. Return ONLY the Farsi translation — no commentary, no English text, no notes.
"""

client = OpenAI(api_key=API_KEY)


def translate_page(page_num: int, english_text: str) -> tuple[int, str]:
    """Translate a single page's English text to Farsi via GPT-5.2."""
    if not english_text.strip():
        return page_num, ""

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Translate the following text from page {page_num} "
                        f"of the Texas Driver Handbook to Farsi:\n\n{english_text}",
                    },
                ],
                temperature=0.3,
                max_completion_tokens=8192,
            )
            farsi = resp.choices[0].message.content.strip()
            print(f"  ✓ Page {page_num:>2d} translated ({len(farsi)} chars)")
            return page_num, farsi
        except Exception as e:
            wait = 2 ** (attempt + 1)
            print(f"  ✗ Page {page_num} attempt {attempt+1} failed: {e}. Retrying in {wait}s…")
            time.sleep(wait)

    print(f"  ✗ Page {page_num} FAILED after 3 attempts")
    return page_num, f"[Translation failed for page {page_num}]"


def run_translations():
    """Translate all pages, with checkpoint support (skips already-translated pages)."""
    with open(INPUT_JSON) as f:
        english_pages: dict[str, str] = json.load(f)

    # Load checkpoint if exists
    if OUTPUT_JSON.exists():
        with open(OUTPUT_JSON) as f:
            farsi_pages: dict[str, str] = json.load(f)
        print(f"Resuming from checkpoint — {len(farsi_pages)} pages already translated.")
    else:
        farsi_pages = {}

    # Determine which pages still need translation
    todo = {
        int(k): v
        for k, v in english_pages.items()
        if k not in farsi_pages and v.strip()
    }

    if not todo:
        print("All pages already translated!")
        return farsi_pages

    print(f"Translating {len(todo)} pages using {MODEL} with {MAX_WORKERS} workers…\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(translate_page, pnum, text): pnum
            for pnum, text in sorted(todo.items())
        }
        for future in concurrent.futures.as_completed(futures):
            pnum, farsi_text = future.result()
            farsi_pages[str(pnum)] = farsi_text
            # Checkpoint after every page
            with open(OUTPUT_JSON, "w") as f:
                json.dump(farsi_pages, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Translation complete — {len(farsi_pages)} pages saved to {OUTPUT_JSON}")
    return farsi_pages


def generate_html(english_pages: dict, farsi_pages: dict) -> str:
    """Build a side-by-side HTML document: English (LTR) | Farsi (RTL)."""
    pages_html = []
    for page_num in sorted(int(k) for k in english_pages.keys()):
        en = english_pages[str(page_num)].strip()
        fa = farsi_pages.get(str(page_num), "").strip()
        if not en and not fa:
            continue

        # Convert newlines to <br> for simple formatting preservation
        en_html = en.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>\n")
        fa_html = fa.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>\n")

        pages_html.append(f"""
    <div class="page-pair">
      <div class="page-header">Page {page_num} / صفحه {page_num}</div>
      <div class="columns">
        <div class="col col-en" dir="ltr" lang="en">
          {en_html}
        </div>
        <div class="col col-fa" dir="rtl" lang="fa">
          {fa_html}
        </div>
      </div>
    </div>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Texas Driver Handbook — English / Farsi (فارسی)</title>
<style>
  @page {{
    size: A3 landscape;
    margin: 12mm;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Noto Sans', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 10pt;
    line-height: 1.55;
    color: #1a1a1a;
    background: #fff;
  }}

  .cover {{
    page-break-after: always;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    text-align: center;
  }}
  .cover h1 {{ font-size: 28pt; margin-bottom: 8pt; color: #002868; }}
  .cover h2 {{ font-size: 20pt; font-family: 'Noto Naskh Arabic', 'Noto Sans Arabic', 'Tahoma', sans-serif; color: #BF0A30; direction: rtl; }}
  .cover p {{ font-size: 12pt; margin-top: 20pt; color: #555; }}

  .page-pair {{
    page-break-after: always;
    padding: 0;
  }}

  .page-header {{
    background: linear-gradient(135deg, #002868, #BF0A30);
    color: #fff;
    padding: 6pt 14pt;
    font-size: 11pt;
    font-weight: bold;
    border-radius: 4pt 4pt 0 0;
    font-family: 'Noto Sans', 'Noto Naskh Arabic', sans-serif;
  }}

  .columns {{
    display: flex;
    gap: 0;
    border: 1px solid #ccc;
    border-top: none;
    min-height: 80vh;
  }}

  .col {{
    flex: 1;
    padding: 12pt 16pt;
    overflow-wrap: break-word;
  }}

  .col-en {{
    background: #fafcff;
    border-right: 2px solid #002868;
    font-family: 'Noto Sans', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  }}

  .col-fa {{
    background: #fffaf5;
    font-family: 'Noto Naskh Arabic', 'Noto Sans Arabic', 'Tahoma', sans-serif;
    font-size: 10.5pt;
    line-height: 1.8;
  }}
</style>
</head>
<body>

<div class="cover">
  <h1>Texas Driver Handbook</h1>
  <h2>کتابچه راهنمای رانندگی تگزاس</h2>
  <p>English / Farsi Side-by-Side Translation — DL-7</p>
  <p>Translated using GPT-5.2 · {time.strftime("%B %Y")}</p>
</div>

{"".join(pages_html)}

</body>
</html>"""
    return html


def generate_pdf():
    """Generate the final side-by-side PDF from translated pages."""
    from weasyprint import HTML

    with open(INPUT_JSON) as f:
        english_pages = json.load(f)
    with open(OUTPUT_JSON) as f:
        farsi_pages = json.load(f)

    print("Generating HTML…")
    html_content = generate_html(english_pages, farsi_pages)

    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  ✓ HTML saved to {OUTPUT_HTML}")

    print("Generating PDF (this may take a minute)…")
    HTML(string=html_content, base_url=str(OUTPUT_HTML.parent)).write_pdf(str(OUTPUT_PDF))
    pdf_size = OUTPUT_PDF.stat().st_size / (1024 * 1024)
    print(f"  ✓ PDF saved to {OUTPUT_PDF} ({pdf_size:.1f} MB)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--pdf-only":
        generate_pdf()
        return

    # Phase 1: Translate
    run_translations()

    # Phase 2: Generate PDF
    generate_pdf()

    print("\n🎉 Done! Files produced:")
    print(f"   • {OUTPUT_JSON}")
    print(f"   • {OUTPUT_HTML}")
    print(f"   • {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
