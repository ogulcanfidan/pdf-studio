"""Tasima, stil kopyalama ve eklenen metnin duzenlenebilirligi."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument, TextStyle

TMP = tempfile.mkdtemp(prefix="pdfstudio-ms-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build(path):
    d = pymupdf.open(); page = d.new_page(width=430, height=300)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), "KAYNAK BASLIK", font=bold, fontsize=18)
    w.write_text(page, color=(0.8, 0.1, 0.1))
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 120), "hedef satir duz", font=reg, fontsize=10)
    w.write_text(page, color=(0.2, 0.2, 0.2))
    d.save(path, garbage=4, deflate=True); d.close()


def satirlar(doc):
    out = []
    for b in doc.doc.load_page(0).get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(s["text"] for s in ln.get("spans", []))
            if t.strip():
                sp = ln["spans"][0]
                out.append((t.replace("\xa0", " ").strip(),
                            round(ln["bbox"][0], 1), round(ln["bbox"][1], 1),
                            sp["font"], round(sp["size"], 1)))
    return out


print("=== 1. Eklenen metin sonradan secilip duzenlenebiliyor mu? ===")
p = os.path.join(TMP, "a.pdf")
build(p)
doc = PdfDocument(); doc.open(p)
doc.insert_textbox(0, pymupdf.Rect(40, 180, 320, 215), "Eklenen not", 13,
                   (0.1, 0.4, 0.8))

s = doc.find_span_at(0, pymupdf.Point(70, 193))
check("eklenen metin bulundu", s is not None and "Eklenen" in s.text,
      "-> %r" % (s.text if s else None))

# Biraz uzaktan tiklayinca da bulmali (tolerans)
s2 = doc.find_span_at(0, pymupdf.Point(70, 199))
check("birkac punto uzaktan da bulunuyor (tolerans)",
      s2 is not None and "Eklenen" in s2.text,
      "-> %r" % (s2.text if s2 else None))

doc.replace_text(0, s, "Degistirilmis not")
txt = doc.doc.load_page(0).get_text("text").replace("\xa0", " ")
check("eklenen metin DEGISTIRILEBILDI", "Degistirilmis not" in txt,
      "-> %r" % txt[:90])
doc.close()

print()
print("=== 2. Tasima ===")
p2 = os.path.join(TMP, "b.pdf")
build(p2)
doc = PdfDocument(); doc.open(p2)
doc.insert_textbox(0, pymupdf.Rect(40, 180, 320, 215), "Tasinacak", 13,
                   (0.1, 0.4, 0.8))
s = doc.find_span_at(0, pymupdf.Point(60, 193))
eski = (s.origin[0], s.origin[1])
doc.move_text(0, s, 120.0, 40.0)

yeni_s = doc.find_span_at(0, pymupdf.Point(60 + 120, 193 + 40))
check("tasinan metin yeni konumda bulundu",
      yeni_s is not None and "Tasinacak" in yeni_s.text,
      "-> %r" % (yeni_s.text if yeni_s else None))
if yeni_s:
    dx = yeni_s.origin[0] - eski[0]
    dy = yeni_s.origin[1] - eski[1]
    print("     kayma: dx=%.1f dy=%.1f (beklenen 120, 40)" % (dx, dy))
    check("dogru miktarda tasindi", abs(dx - 120) < 1 and abs(dy - 40) < 1,
          "-> dx=%.2f dy=%.2f" % (dx, dy))
eski_yerde = doc.find_span_at(0, pymupdf.Point(60, 193), tolerance=0.0)
check("eski konumda metin kalmadi",
      eski_yerde is None or "Tasinacak" not in eski_yerde.text,
      "-> %r" % (eski_yerde.text if eski_yerde else None))
check("diger satirlar yerinde",
      any("KAYNAK BASLIK" in t[0] for t in satirlar(doc))
      and any("hedef satir" in t[0] for t in satirlar(doc)),
      "-> %s" % satirlar(doc))
doc.close()

print()
print("=== 3. Stil kopyalama ===")
p3 = os.path.join(TMP, "c.pdf")
build(p3)
doc = PdfDocument(); doc.open(p3)

stil = doc.capture_style(0, pymupdf.Point(80, 55))
check("kaynak stil alindi", stil is not None)
if stil:
    print("     kaynak: %s" % stil.label())
    check("punto dogru alindi", abs(stil.size - 18) < 0.2, "-> %.1f" % stil.size)
    check("renk dogru alindi", stil.color[0] > 0.6 and stil.color[1] < 0.3,
          "-> %s" % (stil.color,))

hedef = doc.find_span_at(0, pymupdf.Point(70, 116))
check("hedef satir bulundu", hedef is not None and "hedef" in hedef.text,
      "-> %r" % (hedef.text if hedef else None))
onceki_punto = hedef.size
doc.restyle_text(0, hedef, stil)

yeni = doc.find_span_at(0, pymupdf.Point(70, 116))
if yeni is None:
    yeni = doc.find_span_at(0, pymupdf.Point(70, 118), tolerance=12)
check("stil uygulanan satir duruyor", yeni is not None,
      "-> %s" % satirlar(doc))
if yeni:
    print("     hedef: punto %.1f -> %.1f, font %r"
          % (onceki_punto, yeni.size, yeni.font))
    # Yeni davranis: stil kopyalama PUNTO TASIMAZ (satir yerinden oynamasin).
    # Punto degisikligi metin duzenleme penceresinden yapiliyor.
    check("punto KORUNDU (stil puntoyu tasimaz)",
          abs(yeni.size - onceki_punto) < 0.3,
          "-> %.1f vs %.1f" % (yeni.size, onceki_punto))
    # PDF metni bolunemez bosluk (NBSP) icerebiliyor; normalize et.
    duz = yeni.text.replace(" ", " ")
    check("metin korundu", "hedef satir" in duz, "-> %r" % duz)
check("kaynak satir bozulmadi",
      any("KAYNAK BASLIK" in t[0] for t in satirlar(doc)),
      "-> %s" % satirlar(doc))
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
