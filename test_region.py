"""Kismi secimle tasima: tek harf dahil, konum ve renk korunarak."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-reg-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build(path):
    d = pymupdf.open(); page = d.new_page(width=430, height=220)
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), "ABCDEF GHIJ", font=reg, fontsize=16)
    w.write_text(page, color=(0.85, 0.1, 0.1))
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 120), "ikinci satir korunmali", font=reg,
             fontsize=11)
    w.write_text(page, color=(0.1, 0.1, 0.1))
    d.save(path, garbage=4, deflate=True); d.close()


def metin(doc):
    return doc.doc.load_page(0).get_text("text").replace("\xa0", " ")


print("=== 1. Secili alandaki karakterler dogru bulunuyor mu? ===")
p = os.path.join(TMP, "a.pdf"); build(p)
doc = PdfDocument(); doc.open(p)

hepsi = doc.chars_in(0, pymupdf.Rect(25, 44, 400, 64))
print("     tum satir: %r" % "".join(c["char"] for c in hepsi))
check("tum satir secildi", "ABCDEF" in "".join(c["char"] for c in hepsi))

# Ilk harfin kutusunu bul, yalnizca onu sec
ilk = hepsi[0]
tek = doc.chars_in(0, ilk["rect"])
print("     tek harf : %r" % "".join(c["char"] for c in tek))
check("TEK HARF secilebiliyor", len(tek) == 1 and tek[0]["char"] == "A",
      "-> %r" % [c["char"] for c in tek])
check("karakter rengi alindi", ilk["color"][0] > 0.6 and ilk["color"][1] < 0.3,
      "-> %s" % (ilk["color"],))
doc.close()

print()
print("=== 2. Tek harf tasima ===")
p2 = os.path.join(TMP, "b.pdf"); build(p2)
doc = PdfDocument(); doc.open(p2)
ilk = doc.chars_in(0, pymupdf.Rect(25, 44, 400, 64))[0]
rapor = doc.move_region(0, ilk["rect"], 0.0, 60.0)
txt = metin(doc)
print("     yontem=%s ortuldu=%s" % (rapor.method, rapor.covered))
print("     sayfa: %r" % txt.strip()[:60])

yeni = doc.chars_in(0, pymupdf.Rect(ilk["rect"].x0 - 2, ilk["rect"].y0 + 58,
                                    ilk["rect"].x1 + 2, ilk["rect"].y1 + 62))
check("harf yeni konumda", any(c["char"] == "A" for c in yeni),
      "-> %r" % [c["char"] for c in yeni])
eski = doc.chars_in(0, ilk["rect"])
check("eski konumda harf kalmadi", not any(c["char"] == "A" for c in eski),
      "-> %r" % [c["char"] for c in eski])
check("satirin geri kalani duruyor", "BCDEF" in txt, "-> %r" % txt[:60])
check("ikinci satir duruyor", "ikinci satir" in txt, "-> %r" % txt[:80])
doc.close()

print()
print("=== 3. Bir kelime tasima, renk ve punto korunuyor mu? ===")
p3 = os.path.join(TMP, "c.pdf"); build(p3)
doc = PdfDocument(); doc.open(p3)
hepsi = doc.chars_in(0, pymupdf.Rect(25, 44, 400, 64))
gh = [c for c in hepsi if c["char"] in "GHIJ"]
kutu = pymupdf.Rect(gh[0]["rect"])
for c in gh[1:]:
    kutu |= c["rect"]
print("     secilen: %r" % "".join(c["char"] for c in gh))
doc.move_region(0, kutu, 40.0, 50.0)
txt = metin(doc)
check("kelime tasindi ve metin korundu", "GHIJ" in txt.replace(" ", ""),
      "-> %r" % txt.strip()[:70])
check("onceki kisim yerinde", "ABCDEF" in txt, "-> %r" % txt[:60])

tasinan = doc.chars_in(0, pymupdf.Rect(kutu.x0 + 38, kutu.y0 + 48,
                                       kutu.x1 + 42, kutu.y1 + 52))
if tasinan:
    print("     tasinan punto=%.1f renk=%s"
          % (tasinan[0]["size"], tuple(round(v, 2) for v in tasinan[0]["color"])))
    check("punto korundu", abs(tasinan[0]["size"] - 16) < 0.3,
          "-> %.1f" % tasinan[0]["size"])
    check("renk korundu", tasinan[0]["color"][0] > 0.6
          and tasinan[0]["color"][1] < 0.3, "-> %s" % (tasinan[0]["color"],))
doc.close()

print()
print("=== 4. Geri alma tek adim mi? ===")
p4 = os.path.join(TMP, "d.pdf"); build(p4)
doc = PdfDocument(); doc.open(p4)
once = metin(doc)
ilk = doc.chars_in(0, pymupdf.Rect(25, 44, 400, 64))[0]
doc.move_region(0, ilk["rect"], 0.0, 60.0)
doc.undo()
check("tek geri alma eski hale dondurdu",
      metin(doc).strip() == once.strip(),
      "-> %r vs %r" % (metin(doc).strip()[:40], once.strip()[:40]))
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
