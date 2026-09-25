"""Harf arali (letter-spaced) basliklar: birim satir mi, aralik korunuyor mu?"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-track-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build(path, spacing):
    """CV basligi gibi harf arali metin uret."""
    doc = pymupdf.open()
    page = doc.new_page(width=420, height=200)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")

    x = 30.0
    for ch in "PROFİL":
        w = pymupdf.TextWriter(page.rect)
        w.append(pymupdf.Point(x, 60), ch, font=bold, fontsize=13)
        w.write_text(page, color=(0.05, 0.45, 0.45))
        x += bold.glyph_advance(ord(ch)) * 13 + spacing

    # Aralıksız normal satir (karsilastirma icin)
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 110), "Normal satir metni", font=bold,
             fontsize=13)
    w.write_text(page, color=(0.1, 0.1, 0.1))

    doc.save(path, garbage=4, deflate=True)
    doc.close()


print("=== 1. Harf arali basliga tiklayinca ne geliyor? ===")
p = os.path.join(TMP, "a.pdf")
build(p, spacing=5.0)

doc = PdfDocument()
doc.open(p)
span = doc.find_span_at(0, pymupdf.Point(60, 56))
check("satir bulundu", span is not None)
print("     text=%r" % span.text)
print("     rect genislik=%.2f tracking=%.2f pt"
      % (span.rect.width, span.tracking))

check("TEK HARF DEGIL, tum satir geldi", len(span.text.strip()) > 3,
      "-> %r" % span.text)
check("harf araligi olculdu", abs(span.tracking) > 0.01
      or " " in span.text,
      "-> tracking=%.3f text=%r" % (span.tracking, span.text))

genislik_once = span.rect.width
report = doc.replace_text(0, span, span.text)   # ayni metni geri yaz
after = doc.doc.load_page(0)
yeni = doc.find_span_at(0, pymupdf.Point(60, 56))
check("yeniden yazildiktan sonra satir duruyor", yeni is not None)
if yeni:
    fark = abs(yeni.rect.width - genislik_once)
    print("     genislik once=%.2f sonra=%.2f fark=%.2f"
          % (genislik_once, yeni.rect.width, fark))
    check("GENISLIK KORUNDU (<1.5pt fark)", fark < 1.5,
          "-> %.2f pt kaydi" % fark)
    dx = abs(yeni.origin[0] - span.origin[0])
    check("baslangic konumu korundu", dx < 0.5, "-> dx=%.3f" % dx)
doc.close()

print()
print("=== 2. Farkli araliklarla genislik sapmasi ===")
for spacing in (0.0, 2.0, 5.0, 9.0):
    p = os.path.join(TMP, "s%.0f.pdf" % spacing)
    build(p, spacing=spacing)
    d = PdfDocument()
    d.open(p)
    s = d.find_span_at(0, pymupdf.Point(60, 56))
    if s is None:
        print("  aralik %.1f -> satir bulunamadi" % spacing)
        fails.append("aralik %.1f" % spacing)
        d.close()
        continue
    w0 = s.rect.width
    d.replace_text(0, s, s.text)
    s2 = d.find_span_at(0, pymupdf.Point(60, 56))
    w1 = s2.rect.width if s2 else -1
    fark = abs(w1 - w0)
    print("  aralik %4.1f pt -> once %.2f, sonra %.2f, fark %.2f"
          % (spacing, w0, w1, fark))
    check("aralik %.1f korundu" % spacing, fark < 1.5, "-> %.2f" % fark)
    d.close()

print()
print("=== 3. Normal (araliksiz) satir bozulmuyor mu? ===")
p = os.path.join(TMP, "n.pdf")
build(p, spacing=5.0)
d = PdfDocument()
d.open(p)
s = d.find_span_at(0, pymupdf.Point(80, 106))
check("normal satir bulundu", s is not None)
if s:
    print("     text=%r tracking=%.3f" % (s.text, s.tracking))
    check("normal satirda aralik ~0", abs(s.tracking) < 0.3,
          "-> %.3f" % s.tracking)
    w0 = s.rect.width
    d.replace_text(0, s, "Degistirilmis satir metni")
    txt = d.doc.load_page(0).get_text("text").replace("\xa0", " ")
    check("yeni metin yazildi", "Degistirilmis" in txt, "-> %r" % txt[:90])
    check("baslik bozulmadi", "P" in txt)
d.close()

print()
print("=== 4. Satirda birden fazla font varsa bildiriliyor mu? ===")
p2 = os.path.join(TMP, "m.pdf")
doc = pymupdf.open()
page = doc.new_page(width=420, height=150)
bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
ilk = "Kalin kisim "
w = pymupdf.TextWriter(page.rect)
w.append(pymupdf.Point(30, 60), ilk, font=bold, fontsize=12)
w.write_text(page)
# Ayni satir sayilmasi icin tam bitisik devam et.
w = pymupdf.TextWriter(page.rect)
w.append(pymupdf.Point(30 + bold.text_length(ilk, fontsize=12), 60),
         "normal kisim", font=reg, fontsize=12)
w.write_text(page)
doc.save(p2)
doc.close()

d = PdfDocument()
d.open(p2)
s = d.find_span_at(0, pymupdf.Point(70, 56))
check("karisik satir bulundu", s is not None)
if s:
    print("     text=%r mixed_fonts=%s" % (s.text, s.mixed_fonts))
    check("karisik bicim bayragi kalkti", s.mixed_fonts is True)
d.close()

print()
print("=" * 60)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
