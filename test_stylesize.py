"""Stil kopyalama punto tasimiyor; punto duzenleme penceresinden ayarlaniyor."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument, font_style_key

TMP = tempfile.mkdtemp(prefix="pdfstudio-ss-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

def build(path):
    d = pymupdf.open(); page = d.new_page(width=470, height=220)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 60), "Oğulcan Fidan", font=bold, fontsize=22)
    w.write_text(page, color=(0.1,0.15,0.2))
    w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 85), "Bilgi İşlem · Sistem", font=reg, fontsize=10.5)
    w.write_text(page, color=(0.03,0.45,0.45))
    d.save(path, garbage=4, deflate=True); d.close()

print("=== 1. Stil kopyalama puntoyu TASIMIYOR ===")
p = os.path.join(TMP, "a.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
stil = doc.capture_style(0, pymupdf.Point(80, 52))
hedef = doc.find_span_at(0, pymupdf.Point(70, 81))
onceki_punto = hedef.size
onceki_ust = hedef.rect.y0
print("     kaynak punto=%.1f, hedef punto=%.1f" % (stil.size, onceki_punto))
doc.restyle_text(0, hedef, stil)
yeni = doc.find_span_at(0, pymupdf.Point(70, 81))
check("hedef satir duruyor", yeni is not None)
if yeni:
    print("     sonra: punto=%.1f font=%r" % (yeni.size, yeni.font))
    check("PUNTO KORUNDU (buyumedi)", abs(yeni.size - onceki_punto) < 0.2,
          "-> %.1f vs %.1f" % (yeni.size, onceki_punto))
    check("KALINLIK aktarildi", font_style_key(yeni.font)[0] >= 600,
          "-> %r" % yeni.font)
    check("satir yukari tasmadi (bindirme yok)",
          yeni.rect.y0 >= onceki_ust - 1.0,
          "-> %.1f vs %.1f" % (yeni.rect.y0, onceki_ust))

# Ust satir bozulmadi mi?
metin = doc.doc.load_page(0).get_text("text").replace("\xa0"," ")
check("ustteki baslik korundu", "Oğulcan Fidan" in metin, "-> %r" % metin[:60])
doc.close()

print()
print("=== 2. Duzenlerken punto ayarlanabiliyor ===")
p2 = os.path.join(TMP, "b.pdf"); build(p2)
doc = PdfDocument(); doc.open(p2)
hedef = doc.find_span_at(0, pymupdf.Point(70, 81))
print("     baslangic punto=%.1f" % hedef.size)
doc.resize_text(0, hedef, "Yeni içerik", 16.0)
yeni = doc.find_span_at(0, pymupdf.Point(70, 81))
if yeni is None:
    yeni = doc.find_span_at(0, pymupdf.Point(70, 78), tolerance=12)
check("metin degisti", yeni is not None and "Yeni içerik" in yeni.text.replace("\xa0"," "),
      "-> %r" % (yeni.text if yeni else None))
if yeni:
    print("     sonra punto=%.1f" % yeni.size)
    check("PUNTO 16'ya ayarlandi", abs(yeni.size - 16.0) < 0.3, "-> %.1f" % yeni.size)
doc.close()

print()
print("=== 3. Punto degismediginde eski yol (dogrulama acik) ===")
p3 = os.path.join(TMP, "c.pdf"); build(p3)
doc = PdfDocument(); doc.open(p3)
hedef = doc.find_span_at(0, pymupdf.Point(70, 81))
rapor = doc.replace_text(0, hedef, "Sadece metin")
check("gomulu font kullanildi", rapor.embedded, "-> %r" % rapor.font_name)
metin = doc.doc.load_page(0).get_text("text").replace("\xa0"," ")
check("yeni metin yazildi", "Sadece metin" in metin, "-> %r" % metin[:60])
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")

print()
print("=== 4. Duzenlerken RENK ayarlanabiliyor ===")
p4 = os.path.join(TMP, "d.pdf"); build(p4)
doc = PdfDocument(); doc.open(p4)
hedef = doc.find_span_at(0, pymupdf.Point(70, 81))
print("     baslangic renk=%s" % (tuple(round(v,2) for v in hedef.color),))
doc.resize_text(0, hedef, "Renkli metin", color=(0.85, 0.1, 0.1))
yeni = doc.find_span_at(0, pymupdf.Point(70, 81))
if yeni is None:
    yeni = doc.find_span_at(0, pymupdf.Point(70, 78), tolerance=12)
check("metin degisti", yeni is not None and "Renkli" in yeni.text.replace("\xa0"," "),
      "-> %r" % (yeni.text if yeni else None))
if yeni:
    print("     sonra renk=%s punto=%.1f"
          % (tuple(round(v,2) for v in yeni.color), yeni.size))
    check("RENK kirmiziya dondu", yeni.color[0] > 0.6 and yeni.color[1] < 0.3,
          "-> %s" % (yeni.color,))
    check("punto degismedi", abs(yeni.size - 10.5) < 0.3, "-> %.1f" % yeni.size)
doc.close()

print()
print("=== 5. Punto ve renk BIRLIKTE ===")
p5 = os.path.join(TMP, "e.pdf"); build(p5)
doc = PdfDocument(); doc.open(p5)
hedef = doc.find_span_at(0, pymupdf.Point(70, 81))
doc.resize_text(0, hedef, "Ikisi birden", size=15.0, color=(0.1, 0.2, 0.8))
yeni = doc.find_span_at(0, pymupdf.Point(70, 80), tolerance=14)
if yeni:
    print("     punto=%.1f renk=%s" % (yeni.size, tuple(round(v,2) for v in yeni.color)))
    check("punto 15", abs(yeni.size - 15.0) < 0.3, "-> %.1f" % yeni.size)
    check("renk mavi", yeni.color[2] > 0.6, "-> %s" % (yeni.color,))
doc.close()

print()
print("=" * 62)
if fails:
    print("SON DURUM BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("RENK VE PUNTO TAMAM")
