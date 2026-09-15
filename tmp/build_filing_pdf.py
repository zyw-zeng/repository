"""从已精简的 Word 方案书生成可提交的中文 PDF。"""

from html import escape
from io import BytesIO
from pathlib import Path
import shutil

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(r"E:\AI\repository")
SOURCE_DOCX = ROOT / "output" / "备案资料" / "网站建设方案书-曾有为.docx"
TARGET_PDF = ROOT / "output" / "备案资料" / "曾有为.pdf"
BACKUP_DIR = ROOT / "tmp" / "filing_backup"
FONT_PATH = Path(r"C:\Windows\Fonts\msyh.ttc")


def register_fonts() -> None:
    """注册支持中文的微软雅黑字体，避免 PDF 出现缺字方框。"""
    if not FONT_PATH.exists():
        raise FileNotFoundError(f"未找到中文字体：{FONT_PATH}")
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei", str(FONT_PATH), subfontIndex=0))


def paragraph_style(text: str, styles: dict[str, ParagraphStyle]) -> ParagraphStyle:
    """根据方案书层级选择正文、标题或项目符号样式。"""
    if text.startswith(tuple("一二三四五六七八九十")) and "、" in text[:4]:
        return styles["heading"]
    if text.startswith("•"):
        return styles["bullet"]
    if text.startswith("图 "):
        return styles["caption"]
    if text.startswith("网站主办者签名：") or text.startswith("日期："):
        return styles["signature"]
    return styles["body"]


def build_styles() -> dict[str, ParagraphStyle]:
    """建立适合备案方案书的克制排版体系。"""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleChinese",
            parent=base["Title"],
            fontName="MicrosoftYaHei",
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=18,
        ),
        "heading": ParagraphStyle(
            "HeadingChinese",
            parent=base["Heading2"],
            fontName="MicrosoftYaHei",
            fontSize=14,
            leading=22,
            textColor=colors.black,
            spaceBefore=12,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei",
            fontSize=10.5,
            leading=19,
            alignment=TA_LEFT,
            textColor=colors.black,
            firstLineIndent=2 * 10.5,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "BulletChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei",
            fontSize=10.5,
            leading=18,
            alignment=TA_LEFT,
            leftIndent=0.65 * cm,
            firstLineIndent=-0.35 * cm,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "CaptionChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei",
            fontSize=9,
            leading=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
            spaceAfter=9,
        ),
        "signature": ParagraphStyle(
            "SignatureChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei",
            fontSize=11,
            leading=22,
            alignment=TA_LEFT,
            leftIndent=9.2 * cm,
            spaceBefore=10,
        ),
        "table": ParagraphStyle(
            "TableChinese",
            parent=base["BodyText"],
            fontName="MicrosoftYaHei",
            fontSize=10.5,
            leading=17,
            textColor=colors.black,
        ),
    }


def image_from_paragraph(document: Document, paragraph: DocxParagraph) -> Image | None:
    """提取段落中的第一张图片并按页面宽度等比缩放。"""
    blip = paragraph._element.find(".//" + qn("a:blip"))
    if blip is None:
        return None
    relation_id = blip.get(qn("r:embed"))
    if not relation_id:
        return None
    part = document.part.related_parts[relation_id]
    image = Image(BytesIO(part.blob))
    max_width = 15.8 * cm
    max_height = 9.5 * cm
    scale = min(max_width / image.imageWidth, max_height / image.imageHeight, 1)
    image.drawWidth = image.imageWidth * scale
    image.drawHeight = image.imageHeight * scale
    image.hAlign = "CENTER"
    return image


def signature_story(image: Image, style: ParagraphStyle) -> Table:
    """把真实签名与字段名称排在同一行，并靠右放置。"""
    target_width = 3.6 * cm
    image.drawHeight = image.drawHeight * target_width / image.drawWidth
    image.drawWidth = target_width
    result = Table(
        [[Paragraph("网站主办者签名：", style), image]],
        colWidths=[3.7 * cm, 3.8 * cm],
        hAlign="RIGHT",
    )
    result.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return result


def table_story(table: DocxTable, style: ParagraphStyle) -> Table:
    """将备案基本信息表转换成三行简洁表格。"""
    data = [
        [Paragraph(escape(cell.text.strip()), style) for cell in row.cells]
        for row in table.rows
    ]
    result = Table(data, colWidths=[4.1 * cm, 11.4 * cm], hAlign="CENTER")
    result.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "MicrosoftYaHei"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F3F5")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#C8CDD3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return result


def main() -> None:
    """按 Word 正文顺序生成 PDF，并保留真实签名空位。"""
    register_fonts()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET_PDF.exists():
        shutil.copy2(TARGET_PDF, BACKUP_DIR / TARGET_PDF.name)

    document = Document(SOURCE_DOCX)
    styles = build_styles()
    story = []
    for element in document.element.body.iterchildren():
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "tbl":
            story.extend([table_story(DocxTable(element, document), styles["table"]), Spacer(1, 14)])
            continue
        if tag != "p":
            continue
        paragraph = DocxParagraph(element, document)
        image = image_from_paragraph(document, paragraph)
        if image is not None:
            if paragraph.text.strip().startswith("网站主办者签名："):
                story.append(signature_story(image, styles["table"]))
                continue
            story.extend([Spacer(1, 5), image, Spacer(1, 5)])
            continue
        text = paragraph.text.strip()
        if not text:
            continue
        if text == "网站建设方案":
            story.append(Paragraph(text, styles["title"]))
            continue
        story.append(Paragraph(escape(text), paragraph_style(text, styles)))

    temporary = TARGET_PDF.with_suffix(".updated.pdf")
    pdf = SimpleDocTemplate(
        str(temporary),
        pagesize=A4,
        rightMargin=2.25 * cm,
        leftMargin=2.25 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title="网站建设方案",
        author="曾有为",
    )
    pdf.build(story)
    temporary.replace(TARGET_PDF)


if __name__ == "__main__":
    main()
