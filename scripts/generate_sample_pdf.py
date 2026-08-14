"""
Generate examples/sample_profile.pdf using pypdf's PdfWriter.

This synthetic profile is used for:
- testing PDFProfileAdapter
- demonstrating the PDF acquisition path in final_demo.py
- canonical equivalence tests (text vs PDF)

The profile uses a fictional person (Alex Rivera) — not a real individual.
Run this script once to regenerate the PDF if it gets deleted.
"""
import sys
from pathlib import Path

# Ensure we can import from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pypdf
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        StreamObject,
    )
except ImportError:
    print("pypdf is required. Run: pip install pypdf")
    sys.exit(1)

PROFILE_TEXT = """\
Alex Rivera
Head of Growth at TechScale \u2014 B2B SaaS | Revenue & Pipeline Strategy

About
I lead growth at TechScale, where I help B2B SaaS companies build scalable
outbound pipelines without burning out their SDR teams.
Previously scaled GTM at two Y Combinator companies from $0 to Series B.
Passionate about data-driven personalization and cutting through inbox noise.

Recent Activity
- Shared a post on why spray-and-pray cold outreach is dead in 2025
- Commented on a LinkedIn thread about AI-assisted SDR workflows
- Published an article: '5 outreach frameworks that actually get replies'
"""

PAGE_2_TEXT = """\
Experience
Head of Growth, TechScale (2023 \u2013 present)
  - Built outbound pipeline from scratch; 3x pipeline in 12 months
  - Integrated AI-assisted personalization for SDR workflows

VP Growth, Acme SaaS (2020 \u2013 2023)
  - Scaled ARR from $2M to $18M
  - Led team of 12 SDRs and 3 AEs

Education
B.S. Computer Science, Stanford University, 2016
"""

OUTPUT_PATH = Path(__file__).parent.parent / "examples" / "sample_profile.pdf"


def build_text_pdf(pages: list[str], output_path: Path) -> None:
    """
    Write a minimal but valid text-based PDF using pypdf's PdfWriter.
    Each string in `pages` becomes one PDF page.

    We use a simple content-stream approach that pypdf can read back cleanly.
    """
    writer = PdfWriter()

    # Standard PDF font reference (Helvetica is a built-in Type1 font)
    FONT_NAME = NameObject("/F1")
    FONT_SIZE = 11

    for page_text in pages:
        # Escape special PDF string characters
        safe = (
            page_text
            .replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("\r", "")
        )

        # Build BT ... ET content stream
        lines = safe.splitlines()
        stream_parts = ["BT", f"/F1 {FONT_SIZE} Tf", "50 750 Td", "14 TL"]
        for line in lines:
            stream_parts.append(f"({line}) Tj T*")
        stream_parts.append("ET")
        content_stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

        # Page dictionary
        page = writer.add_blank_page(width=612, height=792)  # US Letter

        # Attach font resource
        resources = DictionaryObject()
        font_dict = DictionaryObject()
        font_ref = DictionaryObject()
        font_ref[NameObject("/Type")] = NameObject("/Font")
        font_ref[NameObject("/Subtype")] = NameObject("/Type1")
        font_ref[NameObject("/BaseFont")] = NameObject("/Helvetica")
        font_dict[FONT_NAME] = font_ref
        resources[NameObject("/Font")] = font_dict
        page[NameObject("/Resources")] = resources

        # Attach content stream
        stream_obj = DecodedStreamObject()
        stream_obj.set_data(content_stream)
        stream_ref = writer._add_object(stream_obj)
        page[NameObject("/Contents")] = stream_ref

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"Written: {output_path} ({output_path.stat().st_size} bytes)")


if __name__ == "__main__":
    build_text_pdf([PROFILE_TEXT, PAGE_2_TEXT], OUTPUT_PATH)
