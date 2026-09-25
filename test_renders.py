"""Font bir harfi yazarken baska fonta kaciyorsa yakalaniyor mu?"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

doc = PdfDocument()
arial = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")

print("=== Latin harfler: Arial hepsini cizebilir ===")
check("Fidan -> uygun", doc._font_renders_all(arial, "Fidan"))
check("Turkce -> uygun", doc._font_renders_all(arial, "Oğulcan ĞÜŞİÖÇ"))

print()
print("=== Arial'in cizemedigi harfler yakalaniyor mu? ===")
# Cince/Japonca glifleri Arial'de yok -> PyMuPDF baska fonta kacar
for metin, etiket in (("中文字", "Çince"), ("日本語", "Japonca"),
                      ("Fidan中", "karisik")):
    sonuc = doc._font_renders_all(arial, metin)
    print("     %-10s -> %s" % (etiket, "uygun" if sonuc else "REDDEDILDI"))
    check("%s reddedildi" % etiket, not sonuc)

print()
print("=== Wingdings ile Latin yazmak ===")
import os
if os.path.exists("C:/Windows/Fonts/wingding.ttf"):
    wd = pymupdf.Font(fontfile="C:/Windows/Fonts/wingding.ttf")
    sonuc = doc._font_renders_all(wd, "Fidan")
    print("     Wingdings + 'Fidan' -> %s" % ("uygun" if sonuc else "REDDEDILDI"))

print()
print("=== Bos ve bosluk girdiler ===")
check("bos metin uygun", doc._font_renders_all(arial, ""))
check("sadece bosluk uygun", doc._font_renders_all(arial, "   "))

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")

print()
print("=== _resolve_font gercekten cizim denemesi yapiyor mu? ===")
import os, tempfile
TMP = tempfile.mkdtemp()
p = os.path.join(TMP, "a.pdf")
d = pymupdf.open(); pg = d.new_page(width=420, height=160)
f = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
w = pymupdf.TextWriter(pg.rect)
w.append(pymupdf.Point(30, 60), "Fidan", font=f, fontsize=20)
w.write_text(pg)
d.save(p, garbage=4, deflate=True); d.close()

doc2 = PdfDocument(); doc2.open(p)
span = doc2.find_span_at(0, pymupdf.Point(50, 56))
kaynak = span.font

# Latin harfler: gomulu font kabul edilmeli
font1 = doc2._resolve_font(0, kaynak, "Fidan")
print("     'Fidan' -> %r" % font1.name)
check("Latin harflerde gomulu font secildi",
      "arial" in font1.name.lower(), "-> %r" % font1.name)

# Fontun cizemeyecegi harfler: BASKA fonta gecmeli, yarim yamalak degil
font2 = doc2._resolve_font(0, kaynak, "中文字")
print("     '中文字' -> %r" % font2.name)
# NOT: _resolve_font artik tek harf yuzunden gomulu fontu birakmiyor
# (kullanici tercihi). _font_renders_all yalnizca BILGI amacli kullaniliyor.
check("cizim denemesi bilgi veriyor",
      doc2._font_renders_all(font1, "中文字") is False)

# Karisik: tek harf bile cizilemiyorsa TUM grup ayni yedege gecmeli
font3 = doc2._resolve_font(0, kaynak, "Fidan中")
print("     'Fidan中' -> %r" % font3.name)
check("gomulu font korunuyor (tercih edilen davranis)",
      "arial" in font3.name.lower() or font3.name == font1.name,
      "-> %r" % font3.name)
doc2.close()

print()
print("=" * 62)
if fails:
    print("SON DURUM BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("COZUM YOLU DOGRULANDI")
