"""Gorsel: secme, tasima, boyutlandirma, silme."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-img-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

def resim(path, renk):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 120, 80))
    pix.set_rect(pymupdf.IRect(0, 0, 120, 80), renk)
    pix.save(path)
    return path

A = resim(os.path.join(TMP, "a.png"), (30, 120, 200))
B = resim(os.path.join(TMP, "b.png"), (220, 90, 40))

def build(path):
    d = pymupdf.open(); page = d.new_page(width=420, height=320)
    page.insert_image(pymupdf.Rect(40, 40, 160, 120), filename=A)
    page.insert_image(pymupdf.Rect(230, 180, 350, 260), filename=B)
    f = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(40, 300), "Bu metin korunmali", font=f, fontsize=12)
    w.write_text(page)
    d.save(path, garbage=4, deflate=True); d.close()

print("=== 1. Gorseller bulunuyor mu? ===")
p = os.path.join(TMP, "1.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
gorseller = doc.images_on(0)
print("     bulunan: %d" % len(gorseller))
for g in gorseller:
    print("       bbox=%s %dx%d" % ([round(v,1) for v in g["rect"]], g["width"], g["height"]))
check("iki gorsel de bulundu", len(gorseller) == 2, "-> %d" % len(gorseller))

secilen = doc.image_at(0, pymupdf.Point(100, 80))
check("tiklanan gorsel secildi", secilen is not None
      and abs(secilen["rect"].x0 - 40) < 1, "-> %s" % (secilen["rect"] if secilen else None))
check("bos alanda secim yok", doc.image_at(0, pymupdf.Point(200, 300)) is None)
doc.close()

print()
print("=== 2. Tasima ===")
p = os.path.join(TMP, "2.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
g = doc.image_at(0, pymupdf.Point(100, 80))
eski = pymupdf.Rect(g["rect"])
doc.place_image(0, g, eski + (60, 120, 60, 120))
sonra = doc.images_on(0)
print("     sonra: %s" % [[round(v,1) for v in x["rect"]] for x in sonra])
check("gorsel sayisi korundu", len(sonra) == 2, "-> %d" % len(sonra))
check("yeni konumda", any(abs(x["rect"].x0 - 100) < 1 and abs(x["rect"].y0 - 160) < 1
                          for x in sonra), "-> %s" % [x["rect"] for x in sonra])
check("eski konumda yok", not any(abs(x["rect"].x0 - 40) < 1 and abs(x["rect"].y0 - 40) < 1
                                  for x in sonra))
check("diger gorsel yerinde", any(abs(x["rect"].x0 - 230) < 1 for x in sonra))
metin = doc.doc.load_page(0).get_text("text").replace("\xa0", " ")
check("metin korundu", "Bu metin korunmali" in metin, "-> %r" % metin[:50])
doc.close()

print()
print("=== 3. Boyutlandirma ===")
p = os.path.join(TMP, "3.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
g = doc.image_at(0, pymupdf.Point(100, 80))
buyuk = pymupdf.Rect(40, 40, 280, 200)
doc.place_image(0, g, buyuk)
sonra = doc.images_on(0)
hedef = [x for x in sonra if abs(x["rect"].x0 - 40) < 1]
check("boyut degisti", hedef and abs(hedef[0]["rect"].width - 240) < 2,
      "-> %s" % (hedef[0]["rect"] if hedef else None))
if hedef:
    print("     yeni boyut: %.0f x %.0f" % (hedef[0]["rect"].width, hedef[0]["rect"].height))
check("diger gorsel bozulmadi", any(abs(x["rect"].x0 - 230) < 1 for x in sonra))

# Kucultme
g2 = doc.image_at(0, pymupdf.Point(100, 80))
doc.place_image(0, g2, pymupdf.Rect(40, 40, 100, 80))
kucuk = [x for x in doc.images_on(0) if abs(x["rect"].x0 - 40) < 1]
check("kucultuldu", kucuk and abs(kucuk[0]["rect"].width - 60) < 2,
      "-> %s" % (kucuk[0]["rect"] if kucuk else None))
doc.close()

print()
print("=== 4. Silme ===")
p = os.path.join(TMP, "4.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
g = doc.image_at(0, pymupdf.Point(100, 80))
doc.delete_image(0, g)
sonra = doc.images_on(0)
check("bir gorsel silindi", len(sonra) == 1, "-> %d" % len(sonra))
check("dogru olan silindi", sonra and abs(sonra[0]["rect"].x0 - 230) < 1,
      "-> %s" % (sonra[0]["rect"] if sonra else None))
metin = doc.doc.load_page(0).get_text("text").replace("\xa0", " ")
check("metin korundu", "Bu metin korunmali" in metin, "-> %r" % metin[:50])
doc.close()

print()
print("=== 5. Geri alma tek adim ===")
p = os.path.join(TMP, "5.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
once = len(doc.images_on(0))
g = doc.image_at(0, pymupdf.Point(100, 80))
doc.delete_image(0, g)
doc.undo()
check("geri alma gorseli geri getirdi", len(doc.images_on(0)) == once,
      "-> %d vs %d" % (len(doc.images_on(0)), once))
doc.close()

print()
print("=== 6. Sayfa disina tasima engelleniyor mu? ===")
p = os.path.join(TMP, "6.pdf"); build(p)
doc = PdfDocument(); doc.open(p)
g = doc.image_at(0, pymupdf.Point(100, 80))
try:
    doc.place_image(0, g, pymupdf.Rect(900, 900, 1000, 1000))
    check("sayfa disi engellendi", False, "-> hata vermedi")
except Exception as exc:
    check("sayfa disi engellendi", True)
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")

print()
print("=== 7. ARAYUZ: secim, tasima, boyutlandirma, silme ===")
import os as _os
_os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from pdfstudio.mainwindow import MainWindow
from pdfstudio.pageview import Tool

app = QApplication.instance() or QApplication([])
p = os.path.join(TMP, "ui.pdf"); build(p)
win = MainWindow()
win._error = lambda m: (_ for _ in ()).throw(RuntimeError(m))
win.load(p)
win.set_tool(Tool.IMAGE_EDIT)
check("görsel aracı var", Tool.IMAGE_EDIT in win.tool_actions)

win.on_image_picked(pymupdf.Point(100, 80))
check("tıklayınca görsel seçildi", win._selected_image is not None,
      "-> %s" % win._selected_image)
check("tuvalde seçim çerçevesi var", win.view.image_rect is not None)
check("köşe tutamaçları çizildi", len(win.view._img_handles) == 4,
      "-> %d" % len(win.view._img_handles))

# Tasima
eski = pymupdf.Rect(win._selected_image["rect"])
win.on_image_placed(eski + (50, 70, 50, 70))
konumlar = [[round(v, 1) for v in g["rect"]] for g in win.model.images_on(0)]
print("     taşıma sonrası: %s" % konumlar)
check("taşındı", any(abs(g["rect"].x0 - 90) < 1.5 for g in win.model.images_on(0)),
      "-> %s" % konumlar)

# Boyutlandirma
g = win._selected_image
check("seçim taşımadan sonra korundu", g is not None)
if g:
    win.on_image_placed(pymupdf.Rect(g["rect"].x0, g["rect"].y0,
                                     g["rect"].x0 + 200, g["rect"].y0 + 140))
    buyuk = [x for x in win.model.images_on(0) if abs(x["rect"].width - 200) < 3]
    check("boyutlandırıldı", bool(buyuk),
          "-> %s" % [[round(v,1) for v in x["rect"]] for x in win.model.images_on(0)])

# Silme
adet = len(win.model.images_on(0))
win.delete_selected_image()
check("silindi", len(win.model.images_on(0)) == adet - 1,
      "-> %d vs %d" % (len(win.model.images_on(0)), adet))
check("seçim temizlendi", win._selected_image is None
      and win.view.image_rect is None)

# Bos alana tiklama
win.on_image_picked(pymupdf.Point(200, 300))
check("boş alanda seçim yok", win._selected_image is None)

# Metin hala duruyor
metin = win.model.doc.load_page(0).get_text("text").replace("\xa0", " ")
check("metin korundu", "Bu metin korunmali" in metin, "-> %r" % metin[:50])
win.model.dirty = False
win.close()

print()
print("=" * 62)
if fails:
    print("SON DURUM BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("GORSEL ARACI TAMAM")
