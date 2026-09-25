"""Ortulen eski yazi yerine ustteki yeni yazi seciliyor mu?"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-ov-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

p = os.path.join(TMP, "a.pdf")
d = pymupdf.open(); page = d.new_page(width=460, height=200)
reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
# Cok sikisik iki satir -> ortme yoluna zorlar
w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 60), "ESKI SATIR METNI", font=reg, fontsize=11)
w.write_text(page, color=(0.1,0.1,0.1))
w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 71), "ALT SATIR", font=reg, fontsize=11)
w.write_text(page, color=(0.1,0.1,0.1))
d.save(p, garbage=4, deflate=True); d.close()

doc = PdfDocument(); doc.open(p)
span = doc.find_span_at(0, pymupdf.Point(70, 56))
check("eski satir bulundu", span is not None and "ESKI" in span.text,
      "-> %r" % (span.text if span else None))

rapor = doc.replace_text(0, span, "YENI SATIR METNI")
print("     yontem=%s ortuldu=%s" % (rapor.method, rapor.covered))

# Ayni noktaya tekrar tikla: YENI yazi secilmeli
tekrar = doc.find_span_at(0, pymupdf.Point(70, 56))
print("     tekrar tiklaninca: %r" % (tekrar.text.replace("\xa0"," ") if tekrar else None))
check("USTTEKI yeni yazi secildi",
      tekrar is not None and "YENI" in tekrar.text,
      "-> %r" % (tekrar.text if tekrar else None))

# Ikinci kez duzenle: anlamli olmali
if tekrar:
    doc.replace_text(0, tekrar, "UCUNCU METIN")
    metin = doc.doc.load_page(0).get_text("text").replace("\xa0"," ")
    print("     sayfa: %r" % metin.strip()[:80])
    check("ikinci duzenleme dogru satiri degistirdi", "UCUNCU METIN" in metin,
          "-> %r" % metin[:80])
    check("alt satir hala duruyor", "ALT SATIR" in metin, "-> %r" % metin[:80])
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")
