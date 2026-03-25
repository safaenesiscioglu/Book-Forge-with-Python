"""
BookForge — Pure Python PDF converter
Modlar:
  1. preserve: Orijinal görünümü koru + OCR metin katmanı ekle + A5'e ölçekle
  2. reflow:   Metni yeniden düzenle → EPUB + A5 PDF (roman stili)
"""

import re
from pathlib import Path
from datetime import datetime

import fitz  # pymupdf
from PIL import Image
import pytesseract
from ebooklib import epub
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak

A5_W, A5_H = 419.53, 595.28  # A5 point cinsinden


# ── MOD 1: Orijinal görünüm koru + OCR + A5 ──────────────────────────────────

def preserve_convert(input_pdf: Path, output_path: Path, lang: str = "tur+eng", log=print) -> Path:
    """
    Orijinal sayfa görünümünü (kapak, resimler, stiller) koruyarak:
    - Görünmez OCR metin katmanı ekler (metin seçilebilir/aranabilir olur)
    - A5 boyutuna ölçekler
    """
    log("📄 Orijinal görünüm korunuyor + OCR metin katmanı ekleniyor...")

    src = fitz.open(str(input_pdf))
    out = fitz.open()
    total = len(src)

    for i, src_page in enumerate(src):
        log(f"   Sayfa {i+1}/{total} işleniyor...")
        orig = src_page.rect

        # A5'e ölçekle (en-boy oranı korunur, ortala)
        scale_x = A5_W / orig.width
        scale_y = A5_H / orig.height
        scale = min(scale_x, scale_y)
        new_w = orig.width * scale
        new_h = orig.height * scale
        x_off = (A5_W - new_w) / 2
        y_off = (A5_H - new_h) / 2

        # Yeni A5 sayfası — orijinal sayfayı görüntü olarak göm
        new_page = out.new_page(width=A5_W, height=A5_H)
        rect = fitz.Rect(x_off, y_off, x_off + new_w, y_off + new_h)
        new_page.show_pdf_page(rect, src, i)

        # OCR: sayfayı yüksek çözünürlükte render et
        zoom = 2.0
        pix = src_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Kelime bazında OCR verisi al
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

        # Her kelimeyi görünmez metin olarak A5 sayfasına göm
        for j in range(len(data["text"])):
            word = data["text"][j].strip()
            if not word or int(data["conf"][j]) < 30:
                continue
            x = data["left"][j] / zoom
            y = data["top"][j] / zoom
            h = data["height"][j] / zoom
            px0 = x_off + x * scale
            py1 = y_off + (y + h) * scale
            font_size = max(4, h * scale * 0.85)
            new_page.insert_text(
                fitz.Point(px0, py1),
                word + " ",
                fontsize=font_size,
                color=(1, 1, 1),   # beyaz = görünmez
                render_mode=3,     # invisible text (PDF standardı)
            )

    out.save(str(output_path), garbage=4, deflate=True)
    log("✅ A5 PDF oluşturuldu (orijinal görünüm + OCR)")
    src.close()
    out.close()
    return output_path


# ── MOD 2: Metin çıkar → EPUB + Roman stili A5 PDF ──────────────────────────

def extract_pages(pdf_path: Path, do_ocr: bool, lang: str, log=print) -> list:
    doc = fitz.open(str(pdf_path))
    pages_text = []
    total = len(doc)
    for i, page in enumerate(doc):
        log(f"   Sayfa {i+1}/{total} işleniyor...")
        text = page.get_text("text").strip()
        if text and len(text) > 50:
            pages_text.append(text)
        elif do_ocr:
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), colorspace=fitz.csRGB)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = pytesseract.image_to_string(img, lang=lang)
                pages_text.append(ocr_text.strip())
            except Exception as e:
                log(f"   ⚠️ Sayfa {i+1} OCR hatası: {e}")
                pages_text.append("")
        else:
            pages_text.append(text)
    doc.close()
    return pages_text


CHAPTER_RE = re.compile(
    r"^(BÖLÜM|CHAPTER|KISIM|PART|BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|"
    r"BEŞİNCİ|ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU|\d+[\.\-]\s)",
    re.IGNORECASE | re.UNICODE,
)

def pages_to_chapters(pages: list) -> list:
    chapters, current_title, current_paras = [], "Başlangıç", []
    for page_text in pages:
        for line in [l.strip() for l in page_text.splitlines() if l.strip()]:
            if len(line) < 60 and (
                (line.isupper() and len(line) > 2) or
                CHAPTER_RE.match(line) or
                (len(line) < 35 and line.istitle() and len(line.split()) <= 5)
            ):
                if current_paras:
                    chapters.append({"title": current_title, "paragraphs": current_paras})
                current_title, current_paras = line, []
            else:
                current_paras.append(line)
    if current_paras:
        chapters.append({"title": current_title, "paragraphs": current_paras})
    merged = []
    for ch in chapters:
        if merged and len(ch["paragraphs"]) < 3:
            merged[-1]["paragraphs"].extend(ch["paragraphs"])
        else:
            merged.append(ch)
    if not merged:
        all_lines = [l for p in pages for l in p.splitlines() if l.strip()]
        merged = [{"title": "İçerik", "paragraphs": all_lines}]
    return merged


EPUB_CSS = """
@charset "UTF-8";
body { font-family: Georgia, serif; font-size: 1em; line-height: 1.75;
       margin: 1.5em 2em; color: #1a1a1a; text-align: justify; hyphens: auto; }
h2   { font-family: Georgia, serif; font-weight: bold; font-size: 1.25em;
       text-align: center; margin: 2.5em auto 1.2em; page-break-after: avoid; }
p    { margin: 0; text-indent: 1.5em; }
p.first { text-indent: 0; }
.chapter { page-break-before: always; }
"""

def safe_xml(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

def build_epub(chapters: list, title: str, output_path: Path, log=print) -> Path:
    log("📖 EPUB oluşturuluyor...")
    book = epub.EpubBook()
    book.set_identifier(f"bf-{datetime.now().timestamp():.0f}")
    book.set_title(title)
    book.set_language("tr")
    style = epub.EpubItem(uid="css", file_name="style.css", media_type="text/css", content=EPUB_CSS)
    book.add_item(style)
    spine, toc = ["nav"], []
    added = 0
    for idx, ch in enumerate(chapters):
        non_empty = [p for p in ch["paragraphs"] if p.strip()]
        if not non_empty:
            continue
        cid = f"c{idx:03d}"
        heading = safe_xml(ch["title"])
        paras_html = "".join(
            f'<p{"" if pi else " class=\"first\""}>{safe_xml(p)}</p>\n'
            for pi, p in enumerate(non_empty)
        )
        content = (
            "<?xml version='1.0' encoding='utf-8'?>\n<!DOCTYPE html>\n"
            '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="tr">\n'
            f"<head><meta charset='utf-8'/><title>{heading}</title>"
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
            f'<body><div class="chapter"><h2>{heading}</h2>{paras_html}</div></body>\n</html>'
        )
        chap = epub.EpubHtml(title=ch["title"][:100], file_name=f"{cid}.xhtml", lang="tr")
        chap.content = content.encode("utf-8")
        chap.add_item(style)
        book.add_item(chap)
        spine.append(chap)
        toc.append(epub.Link(f"{cid}.xhtml", ch["title"][:100], cid))
        added += 1
    if added == 0:
        raise ValueError("Hiç içerik bulunamadı.")
    book.toc, book.spine = toc, spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(output_path), book)
    log(f"✅ EPUB oluşturuldu ({added} bölüm)")
    return output_path


def build_a5_pdf_reflow(chapters: list, title: str, output_path: Path, log=print) -> Path:
    log("📄 Roman stili A5 PDF oluşturuluyor...")
    doc = SimpleDocTemplate(str(output_path), pagesize=A5,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=20*mm, bottomMargin=20*mm, title=title)
    body    = ParagraphStyle("Body",    fontName="Times-Roman", fontSize=10.5,
                             leading=16, alignment=TA_JUSTIFY, firstLineIndent=14)
    first   = ParagraphStyle("First",   parent=body, firstLineIndent=0, spaceBefore=4)
    heading = ParagraphStyle("Heading", fontName="Times-Bold",  fontSize=13,
                             leading=18, alignment=1, spaceBefore=24, spaceAfter=14)
    title_s = ParagraphStyle("Title",   fontName="Times-Bold",  fontSize=18,
                             leading=24, alignment=1, spaceBefore=60, spaceAfter=8)
    story = [Spacer(1, 30*mm), Paragraph(safe_xml(title), title_s), PageBreak()]
    for idx, ch in enumerate(chapters):
        non_empty = [p for p in ch["paragraphs"] if p.strip()]
        if not non_empty:
            continue
        if idx > 0:
            story.append(PageBreak())
        story.append(Paragraph(safe_xml(ch["title"]), heading))
        for pi, para in enumerate(non_empty):
            story.append(Paragraph(safe_xml(para), first if pi == 0 else body))
    doc.build(story)
    log("✅ Roman stili A5 PDF oluşturuldu")
    return output_path


# ── Ana pipeline ──────────────────────────────────────────────────────────────

def convert(
    input_pdf: Path,
    output_dir: Path,
    title: str = None,
    mode: str = "preserve",   # "preserve" veya "reflow"
    do_ocr: bool = True,
    lang: str = "tur+eng",
    make_epub: bool = True,
    make_pdf: bool = True,
    log=print,
) -> list:
    """
    mode="preserve": Orijinal görünüm + OCR metin katmanı + A5
    mode="reflow":   OCR metin çıkar → EPUB + Roman stili A5 PDF
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_pdf.stem
    if not title:
        title = stem.replace("_", " ").replace("-", " ").title()

    log(f"📚 '{title}' işleniyor... (mod: {mode})")
    outputs = []

    if mode == "preserve":
        pdf_path = output_dir / f"{stem}_A5.pdf"
        preserve_convert(input_pdf, pdf_path, lang=lang, log=log)
        outputs.append({"name": pdf_path.name, "path": str(pdf_path), "type": "pdf"})

    else:  # reflow
        if do_ocr:
            log("🔍 OCR başlıyor...")
        else:
            log("📑 Metin çıkarılıyor...")
        pages = extract_pages(input_pdf, do_ocr=do_ocr, lang=lang, log=log)
        log(f"✅ {len(pages)} sayfa işlendi")
        chapters = pages_to_chapters(pages)
        log(f"📂 {len(chapters)} bölüm tespit edildi")

        if make_epub:
            epub_path = output_dir / f"{stem}.epub"
            build_epub(chapters, title, epub_path, log=log)
            outputs.append({"name": epub_path.name, "path": str(epub_path), "type": "epub"})

        if make_pdf:
            pdf_path = output_dir / f"{stem}_A5.pdf"
            build_a5_pdf_reflow(chapters, title, pdf_path, log=log)
            outputs.append({"name": pdf_path.name, "path": str(pdf_path), "type": "pdf"})

    log(f"🎉 Tamamlandı! {len(outputs)} dosya hazır.")
    return outputs
