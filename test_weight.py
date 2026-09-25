"""Font kalinligi dogru secilip korunuyor mu?"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import (PdfDocument, font_match_score, font_style_key,
                             normalize_font_name)

TMP = tempfile.mkdtemp(prefix="pdfstudio-w-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


print("=== 1. Kalinlik ayrimi (birim testi) ===")
for ad, beklenen in (("Poppins-SemiBold", 600), ("Poppins", 400),
                     ("Poppins-Bold", 700), ("Arial Black", 900),
                     ("Roboto-Light", 300), ("Inter-Medium", 500),
                     ("Poppins-ExtraBold", 800), ("ArialMT", 400)):
    a = font_style_key(ad)[0]
    check("%-20s -> %d" % (ad, beklenen), a == beklenen, "-> %d" % a)

check("italik ayirt ediliyor", font_style_key("Poppins-BoldItalic")[1] is True)

print()
print("=== 2. Aile adi YANLIS kalinliga eslesmiyor ===")
ciftler = [
    ("poppinssemibold", "poppins", False),
    ("poppinsbold", "poppins", False),
    ("poppins", "poppinsbold", False),
    ("poppinsregular", "poppins", True),
    ("arialmt", "arial", True),
    ("poppinsbold", "poppinsbold", True),
    ("poppinsbolditalic", "poppinsbold", False),
]
for q, c, uymali in ciftler:
    puan = font_match_score(q, c)
    uyuyor = puan > 0
    check("%-20s vs %-16s -> %s" % (q, c, "uyar" if uymali else "UYMAZ"),
          uyuyor == uymali, "-> puan=%d" % puan)

print()
print("=== 3. Gercek belgede: her kalinlik kendi fontuna eslesiyor mu? ===")
p = os.path.join(TMP, "cv.pdf")
d = pymupdf.open(); page = d.new_page(width=460, height=240)
katman = [("Regular", "C:/Windows/Fonts/arial.ttf", 60),
          ("Bold", "C:/Windows/Fonts/arialbd.ttf", 110),
          ("Black", "C:/Windows/Fonts/ariblk.ttf", 160)]
for ad, yol, y in katman:
    if not os.path.exists(yol):
        continue
    f = pymupdf.Font(fontfile=yol)
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, y), "abcdefg %s" % ad, font=f, fontsize=16)
    w.write_text(page, color=(0, 0, 0))
d.save(p, garbage=4, deflate=True); d.close()
d = pymupdf.open(p); d.subset_fonts(); d.save(p+".s", garbage=4, deflate=True); d.close()
os.replace(p+".s", p)

doc = PdfDocument(); doc.open(p)
page = doc.doc.load_page(0)
for b in page.get_text("dict")["blocks"]:
    for ln in b.get("lines", []):
        t = "".join(s["text"] for s in ln.get("spans", []))
        sp = ln["spans"][0]
        bulunan = doc._font_for_span_name(0, sp["font"])
        if not bulunan:
            check("%r icin font bulundu" % t.strip()[:16], False)
            continue
        gercek = pymupdf.Rect(ln["bbox"]).width
        hesap = bulunan[1].text_length(t, fontsize=sp["size"])
        fark = abs(hesap - gercek) / max(1, gercek)
        check("%-18r dogru kalinlik (genislik %%%.1f)"
              % (t.replace("\xa0", " ").strip()[:16], fark * 100),
              fark < 0.03, "-> %%%.1f sapma" % (fark * 100))

print()
print("=== 4. Stil kopyalama: kalin -> ince satira, kalinlik gidiyor mu? ===")
stil = doc.capture_style(0, pymupdf.Point(70, 106))     # Bold satiri
hedef = doc.find_span_at(0, pymupdf.Point(70, 56))      # Regular satiri
check("kalin stil alindi", stil is not None and font_style_key(stil.font)[0] == 700,
      "-> %r" % (stil.font if stil else None))
if stil and hedef:
    onceki_genislik = hedef.rect.width
    doc.restyle_text(0, hedef, stil)
    yeni = doc.find_span_at(0, pymupdf.Point(70, 56))
    if yeni:
        print("     %r -> font %r, genislik %.1f -> %.1f"
              % (hedef.text.replace("\xa0", " ")[:18], yeni.font,
                 onceki_genislik, yeni.rect.width))
        check("uygulanan font KALIN", font_style_key(yeni.font)[0] == 700,
              "-> %r (agirlik %d)" % (yeni.font, font_style_key(yeni.font)[0]))
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
