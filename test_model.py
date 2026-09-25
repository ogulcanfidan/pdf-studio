"""Model katmanini GUI olmadan bastan sona dener."""
import os
import sys
import tempfile
import traceback

import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pdfstudio.model import PdfDocument, DocumentError  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-test-")
ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
        print("  OK   %s" % name)
    except Exception as exc:
        fail.append((name, exc))
        print("  FAIL %s -> %r" % (name, exc))
        traceback.print_exc()


def make_sample(path, pages=3):
    d = pymupdf.open()
    for i in range(pages):
        p = d.new_page()
        p.insert_text((72, 100), "Sayfa %d basligi" % (i + 1), fontsize=18)
        p.insert_text((72, 140), "Bu bir ornek paragraftir ve duzenlenecektir.",
                      fontsize=11)
        p.draw_rect(pymupdf.Rect(60, 300, 300, 400), color=(0, 0, 1), width=2)
    d.save(path)
    d.close()


def make_form(path):
    d = pymupdf.open()
    p = d.new_page()
    p.insert_text((72, 80), "Basvuru Formu", fontsize=16)
    w = pymupdf.Widget()
    w.rect = pymupdf.Rect(72, 120, 300, 145)
    w.field_name = "ad_soyad"
    w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    w.field_value = ""
    p.add_widget(w)
    w2 = pymupdf.Widget()
    w2.rect = pymupdf.Rect(72, 160, 90, 178)
    w2.field_name = "onay"
    w2.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    w2.field_value = False
    p.add_widget(w2)
    d.save(path)
    d.close()


src = os.path.join(TMP, "sample.pdf")
form = os.path.join(TMP, "form.pdf")
make_sample(src)
make_form(form)
print("Test dizini:", TMP)

doc = PdfDocument()

print("\n[1] acma / render")
check("open", lambda: doc.open(src))
check("page_count==3", lambda: (_ for _ in ()).throw(AssertionError(doc.page_count))
      if doc.page_count != 3 else None)
check("render", lambda: doc.render(0, 1.5))
check("page_rect", lambda: doc.page_rect(0))

print("\n[2] sayfa islemleri")
check("rotate", lambda: doc.rotate(0, 90))
check("rotation uygulandi",
      lambda: (_ for _ in ()).throw(AssertionError("rot"))
      if doc.doc.load_page(0).rotation != 90 else None)
check("duplicate", lambda: doc.duplicate_page(0))
check("count==4", lambda: (_ for _ in ()).throw(AssertionError(doc.page_count))
      if doc.page_count != 4 else None)
check("insert_blank", lambda: doc.insert_blank(2))
check("move_page 0->3", lambda: doc.move_page(0, 3))
check("delete_pages", lambda: doc.delete_pages([4]))
check("append_pdf", lambda: doc.append_pdf(src))
check("extract_pages", lambda: doc.extract_pages([0, 1], os.path.join(TMP, "ex.pdf")))


def _delete_all():
    try:
        doc.delete_pages(list(range(doc.page_count)))
    except DocumentError:
        return
    raise AssertionError("tum sayfalar silinebildi")


check("tum sayfalari silme engellendi", _delete_all)

print("\n[3] geri al / yinele")
before = doc.page_count
check("undo", doc.undo)
check("undo sayfa sayisini degistirdi",
      lambda: (_ for _ in ()).throw(AssertionError("undo etkisiz"))
      if doc.page_count == before else None)
check("redo", doc.redo)
check("redo geri getirdi",
      lambda: (_ for _ in ()).throw(AssertionError("redo etkisiz"))
      if doc.page_count != before else None)

print("\n[4] metin")
doc.open(src)
span_holder = {}


def _find():
    s = doc.find_span_at(0, pymupdf.Point(100, 135))
    if s is None:
        raise AssertionError("span bulunamadi")
    span_holder["s"] = s


check("find_span_at", _find)
check("replace_text",
      lambda: doc.replace_text(0, span_holder["s"], "Degistirilmis Turkce metin: sisli gurultu"))


def _verify_replace():
    txt = doc.doc.load_page(0).get_text("text")
    if "Degistirilmis" not in txt:
        raise AssertionError("yeni metin yok: %r" % txt[:200])


check("yeni metin sayfada", _verify_replace)
check("insert_textbox",
      lambda: doc.insert_textbox(0, pymupdf.Rect(300, 500, 520, 560),
                                 "Eklenen kutu\nikinci satir", 12, (0.8, 0, 0)))
check("extract_text", lambda: doc.extract_text())
check("search", lambda: doc.search("Sayfa"))

print("\n[5] isaretlemeler")
doc.open(src)
check("highlight",
      lambda: (_ for _ in ()).throw(AssertionError("quad yok"))
      if not doc.markup(0, pymupdf.Rect(60, 125, 400, 150), "highlight", (1, 1, 0))
      else None)
check("underline",
      lambda: doc.markup(0, pymupdf.Rect(60, 90, 400, 110), "underline", (0, 0, 1)))
check("strikeout",
      lambda: doc.markup(0, pymupdf.Rect(60, 90, 400, 110), "strikeout", (1, 0, 0)))
check("markup bos alan False dondurur",
      lambda: (_ for _ in ()).throw(AssertionError("True dondu"))
      if doc.markup(0, pymupdf.Rect(500, 700, 520, 720), "highlight", (1, 1, 0))
      else None)
check("add_rect",
      lambda: doc.add_rect(0, pymupdf.Rect(100, 400, 300, 480), (0, 0.6, 0)))
check("add_ink",
      lambda: doc.add_ink(0, [[(100, 500), (150, 520), (200, 505)]], (0, 0, 0)))
check("annots_at",
      lambda: doc.annots_at(0, pymupdf.Point(150, 440)))

png = os.path.join(TMP, "sig.png")
pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 60)).save(png)
check("add_image", lambda: doc.add_image(0, pymupdf.Rect(350, 600, 470, 660), png))
check("redact", lambda: doc.redact(0, pymupdf.Rect(60, 90, 300, 115)))


def _verify_redact():
    if "basligi" in doc.doc.load_page(0).get_text("text"):
        raise AssertionError("redaksiyon metni silmedi")


check("redaksiyon metni sildi", _verify_redact)
check("watermark", lambda: doc.watermark("TASLAK", 48, 0.25, (0.6, 0.6, 0.6)))

print("\n[6] formlar")
doc.open(form)
check("has_form", lambda: (_ for _ in ()).throw(AssertionError("form degil"))
      if not doc.has_form else None)
check("form_fields", lambda: (_ for _ in ()).throw(AssertionError("alan yok"))
      if len(doc.form_fields()) != 2 else None)
check("set_field text", lambda: doc.set_field(0, "ad_soyad", "Ogulcan Fidan"))
check("set_field checkbox", lambda: doc.set_field(0, "onay", True))


def _verify_field():
    vals = {w.field_name: w.field_value for _, w in doc.form_fields()}
    if vals.get("ad_soyad") != "Ogulcan Fidan":
        raise AssertionError(vals)


check("form degeri yazildi", _verify_field)
check("flatten_form", lambda: doc.flatten_form())
check("flatten sonrasi widget yok",
      lambda: (_ for _ in ()).throw(AssertionError("widget kaldi"))
      if doc.form_fields() else None)
check("flatten sonrasi metin var",
      lambda: (_ for _ in ()).throw(AssertionError("metin yok"))
      if "Ogulcan" not in doc.doc.load_page(0).get_text("text") else None)

print("\n[7] kaydetme")
doc.open(src)
doc.rotate(0, 180)
out = os.path.join(TMP, "out.pdf")
check("save farkli dosyaya", lambda: doc.save(out))
check("dirty temizlendi", lambda: (_ for _ in ()).throw(AssertionError("dirty"))
      if doc.dirty else None)
check("ayni dosyaya tekrar kaydet", lambda: doc.save())
check("kaydedilen dosya acilabiliyor", lambda: pymupdf.open(out).close())
check("rotasyon kalici",
      lambda: (_ for _ in ()).throw(AssertionError("rot kaybi"))
      if pymupdf.open(out).load_page(0).rotation != 180 else None)
check("compress save",
      lambda: doc.save(os.path.join(TMP, "small.pdf"), compress=True))
check("new bos belge", lambda: doc.new())
check("close", lambda: doc.close())

print("\n" + "=" * 60)
print("BASARILI: %d   BASARISIZ: %d" % (len(ok), len(fail)))
for name, exc in fail:
    print("  - %s: %r" % (name, exc))
sys.exit(1 if fail else 0)
