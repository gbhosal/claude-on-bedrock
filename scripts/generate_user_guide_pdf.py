"""Generate USER-GUIDE-bedrock-migration.pdf from the Markdown source."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "USER-GUIDE-bedrock-migration.md"
PDF_PATH = ROOT / "USER-GUIDE-bedrock-migration.pdf"

CSS = """
@page {
  size: letter;
  margin: 0.75in 0.85in;
  @bottom-center {
    content: "Anthropic to AWS Bedrock — LLM Application User Guide — May 2026";
    font-size: 8pt;
    color: #666;
  }
}
body {
  font-family: Helvetica, Arial, sans-serif;
  font-size: 10pt;
  line-height: 1.45;
  color: #1a1a1a;
}
h1 {
  font-size: 20pt;
  color: #111;
  border-bottom: 2px solid #232f3e;
  padding-bottom: 6px;
  margin-top: 0;
}
h2 {
  font-size: 14pt;
  color: #232f3e;
  margin-top: 22px;
  page-break-after: avoid;
}
h3 {
  font-size: 11pt;
  color: #333;
  margin-top: 16px;
  page-break-after: avoid;
}
p, li { margin: 0 0 8px 0; }
ul, ol { margin: 0 0 10px 18px; padding: 0; }
code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9pt;
  background: #f4f4f4;
  padding: 1px 4px;
  border-radius: 2px;
}
pre {
  font-family: Consolas, "Courier New", monospace;
  font-size: 8.5pt;
  background: #f6f8fa;
  border: 1px solid #ddd;
  padding: 10px 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
  page-break-inside: avoid;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
  font-size: 9pt;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #ccc;
  padding: 6px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #232f3e;
  color: #fff;
  font-weight: bold;
}
tr:nth-child(even) td { background: #fafafa; }
hr {
  border: none;
  border-top: 1px solid #ddd;
  margin: 18px 0;
}
strong { color: #111; }
em { color: #444; }
blockquote {
  border-left: 3px solid #ff9900;
  margin: 10px 0;
  padding: 4px 12px;
  color: #444;
  background: #fffbf0;
}
"""


def build_html(markdown_text: str) -> str:
    import markdown

    body = markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>AWS Bedrock LLM Application User Guide</title>
  <style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def write_pdf_weasyprint(html: str, output: Path) -> None:
    from weasyprint import HTML

    HTML(string=html, base_url=str(ROOT)).write_pdf(str(output))


def write_pdf_xhtml2pdf(html: str, output: Path) -> None:
    from xhtml2pdf import pisa

    with output.open("wb") as pdf_file:
        status = pisa.CreatePDF(html, dest=pdf_file, encoding="utf-8")
    if status.err:
        raise RuntimeError(f"xhtml2pdf failed with {status.err} error(s)")


def main() -> int:
    if not MD_PATH.exists():
        print(f"Missing source file: {MD_PATH}", file=sys.stderr)
        return 1

    markdown_text = MD_PATH.read_text(encoding="utf-8")
    # Strip HTML comments if any
    markdown_text = re.sub(r"<!--.*?-->", "", markdown_text, flags=re.DOTALL)
    html = build_html(markdown_text)

    try:
        import markdown  # noqa: F401
    except ImportError:
        print("Installing markdown...", file=sys.stderr)
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "markdown", "-q"]
        )
        html = build_html(markdown_text)

    errors: list[str] = []
    for name, writer in (
        ("weasyprint", write_pdf_weasyprint),
        ("xhtml2pdf", write_pdf_xhtml2pdf),
    ):
        try:
            if name == "weasyprint":
                import weasyprint  # noqa: F401
            if name == "xhtml2pdf":
                import xhtml2pdf  # noqa: F401
        except ImportError:
            continue
        try:
            writer(html, PDF_PATH)
            print(f"Wrote {PDF_PATH} ({PDF_PATH.stat().st_size:,} bytes) via {name}")
            return 0
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{name}: {exc}")

    print("Installing xhtml2pdf and retrying...", file=sys.stderr)
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "markdown", "xhtml2pdf", "-q"]
    )
    html = build_html(markdown_text)
    try:
        write_pdf_xhtml2pdf(html, PDF_PATH)
        print(f"Wrote {PDF_PATH} ({PDF_PATH.stat().st_size:,} bytes) via xhtml2pdf")
        return 0
    except Exception as exc:  # noqa: BLE001
        errors.append(f"xhtml2pdf (retry): {exc}")

    print("PDF generation failed:", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
