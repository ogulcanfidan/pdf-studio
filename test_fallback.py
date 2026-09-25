"""Yedege dusulse bile KALINLIK korunuyor mu? Tek harf farkli fonta duser mi?"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument, font_style_key

TMP = tempfile.mkdtemp(prefix="pdfstudio-fb-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

doc = PdfDocument()

print("=== 1. Kalinlik koruyan yedek bulunuyor mu? ===")
for ad, beklenen in (("Poppins-Bold", 700), ("Poppins-SemiBold", 600),
                     ("Poppins-Light", 300), ("Poppins", 400),
                     ("Montserrat-Black", 900)):
    yedek = doc._weight_fallback(ad)
    if yedek is None:
        check("%-20s yedek bulundu" % ad, False, "-> yok")
        continue
    bulunan = yedek[1].name
    agirlik = font_style_key(bulunan)[0]
    print("     %-20s -> %-28r (agirlik %d, beklenen %d)"
          % (ad, bulunan, agirlik, beklenen))
    check("%-20s kalinligi korundu" % ad, agirlik == beklenen,
          "-> %d" % agirlik)

print()
print("=== 2. Yedek gercekten daha kalin mi ciziyor? ===")
hafif = doc._weight_fallback("Poppins")
kalin = doc._weight_fallback("Poppins-Bold")
if hafif and kalin:
    metin = "Oğulcan Fidan"
    w1 = hafif[1].text_length(metin, fontsize=20)
    w2 = kalin[1].text_length(metin, fontsize=20)
    print("     normal genislik=%.1f  kalin genislik=%.1f" % (w1, w2))
    check("kalin yedek daha genis (gercekten kalin)", w2 > w1 * 1.02,
          "-> %.1f vs %.1f" % (w2, w1))

print()
print("=== 3. Tek harf farkli fonta dusuyor mu? (Fidan'daki d) ===")
p = os.path.join(TMP, "a.pdf")
d = pymupdf.open(); page = d.new_page(width=420, height=180)
f = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
w = pymupdf.TextWriter(page.rect)
w.append(pymupdf.Point(30, 60), "Oğulcan Fidan", font=f, fontsize=22)
w.write_text(page, color=(0.1, 0.15, 0.2))
d.save(p, garbage=4, deflate=True); d.close()
d = pymupdf.open(p); d.subset_fonts(); d.save(p+".s", garbage=4, deflate=True); d.close()
os.replace(p+".s", p)

doc2 = PdfDocument(); doc2.open(p)
hepsi = doc2.chars_in(0, pymupdf.Rect(25, 40, 400, 70))
fidan = [c for c in hepsi if c["char"] in "Fidan"]
kutu = pymupdf.Rect(fidan[0]["rect"])
for c in fidan[1:]:
    kutu |= c["rect"]

# Tum karakterler icin TEK font cozulmeli
gruplar = {}
for c in hepsi:
    gruplar.setdefault(c["font"], []).append(c["char"])
cozulen = {ad: doc2._resolve_font(0, ad, "".join(h)) for ad, h in gruplar.items()}
print("     kaynak font sayisi: %d -> cozulen font sayisi: %d"
      % (len(gruplar), len(set(id(f) for f in cozulen.values()))))
check("tum satir TEK fontla cozuldu", len(set(id(f) for f in cozulen.values())) == 1)

doc2.move_region(0, kutu, 60.0, 50.0)
out = os.path.join(TMP, "sonra.pdf")
doc2.save(out); doc2.close()

d = pymupdf.open(out)
fontlar = set()
for b in d.load_page(0).get_text("dict")["blocks"]:
    for ln in b.get("lines", []):
        for sp in ln.get("spans", []):
            if any(ch in sp["text"] for ch in "Fidan"):
                fontlar.add(sp["font"])
metin = d.load_page(0).get_text("text").replace("\xa0", " ")
d.close()
print("     tasinan yazidaki font sayisi: %d %s" % (len(fontlar), sorted(fontlar)))
check("tasinan yazi TEK fontta", len(fontlar) == 1, "-> %s" % sorted(fontlar))
check("harfler eksiksiz", "Fidan" in metin.replace(" ", ""), "-> %r" % metin[:50])

print()
print("=== 4. Stil kopyalama: yedege dusse bile kalin kaliyor mu? ===")
p2 = os.path.join(TMP, "b.pdf")
d = pymupdf.open(); page = d.new_page(width=460, height=200)
bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 60), "Oğulcan Fidan", font=bold, fontsize=22)
w.write_text(page, color=(0.1,0.15,0.2))
w = pymupdf.TextWriter(page.rect); w.append(pymupdf.Point(30, 110), "0500 000 00 00", font=reg, fontsize=10.5)
w.write_text(page, color=(0.45,0.45,0.45))
d.save(p2, garbage=4, deflate=True); d.close()

doc3 = PdfDocument(); doc3.open(p2)
stil = doc3.capture_style(0, pymupdf.Point(80, 52))
hedef = doc3.find_span_at(0, pymupdf.Point(70, 106))
onceki = hedef.rect.width
rapor = doc3.restyle_text(0, hedef, stil)
yeni = doc3.find_span_at(0, pymupdf.Point(70, 106))
print("     rapor: font=%r gomulu=%s" % (rapor.font_name, rapor.embedded))
if yeni:
    print("     hedef font: %r (agirlik %d)" % (yeni.font, font_style_key(yeni.font)[0]))
    check("uygulanan yazi KALIN", font_style_key(yeni.font)[0] >= 600,
          "-> %r agirlik %d" % (yeni.font, font_style_key(yeni.font)[0]))
doc3.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")
