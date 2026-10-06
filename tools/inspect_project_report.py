"""Extract reviewable text and structural metadata without executing document content."""
from pathlib import Path
import json
import zipfile
from lxml import etree
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_work_extract" / "report_review_20261005"
DEST.mkdir(parents=True, exist_ok=True)
SOURCE = Path(r"C:\Users\P1 Gen 5\Downloads\Copy of Bao_cao_blockchain.docx")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
with zipfile.ZipFile(SOURCE) as z:
    xml = etree.fromstring(z.read("word/document.xml"))
    paras = xml.xpath("//w:body//w:p", namespaces=NS)
    records = []
    for index, p in enumerate(paras):
        text = "".join(p.xpath(".//w:t/text()", namespaces=NS))
        style = p.xpath("./w:pPr/w:pStyle/@w:val", namespaces=NS)
        records.append({"id": index, "style": style[0] if style else "", "text": text,
                        "drawings": len(p.xpath(".//w:drawing", namespaces=NS)),
                        "equations": len(p.xpath(".//*[local-name()='oMath']")),
                        "in_table": bool(p.xpath("ancestor::w:tc", namespaces=NS))})
    (DEST / "report_paragraphs.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (DEST / "report_full.txt").write_text("\n".join(f"[{r['id']:04d}] ({r['style']}) {'[TABLE] ' if r['in_table'] else ''}{r['text']}" for r in records), encoding="utf-8")
    print(json.dumps({"paragraphs": len(records), "tables": len(xml.xpath("//w:tbl", namespaces=NS)),
                      "images": len([n for n in z.namelist() if n.startswith('word/media/')]),
                      "chapters": [{"id": r['id'], "text": r['text']} for r in records if r['text'].strip().upper().startswith(('CHƯƠNG', 'TÀI LIỆU THAM KHẢO', 'KẾT LUẬN'))]}, ensure_ascii=True, indent=2))
for pdf in sorted((ROOT / "baocao").glob("*.pdf")):
    with pymupdf.open(pdf) as doc:
        text = "\n\n".join(f"[PAGE {i+1}]\n" + page.get_text() for i, page in enumerate(doc))
        (DEST / (pdf.stem + ".txt")).write_text(text, encoding="utf-8")
        print(json.dumps({"reference": pdf.name, "pages": len(doc), "characters": len(text)}, ensure_ascii=True))
