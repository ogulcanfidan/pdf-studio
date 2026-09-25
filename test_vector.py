"""Vektor simgeleri secme, tasima, boyutlandirma, silme.

CV'lerdeki telefon/zarf simgeleri gorsel DEGIL, kucuk dolu yollardan olusan
vektor cizimlerdir. Gorsel araci onlari goremedigi icin secilemiyorlardi.

Bir simge tek bir yol da degildir (telefon simgesi 5 ayri yol), bu yuzden
tiklanan noktadan baslayip komsu kucuk yollar kumeleniyor.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-vek-")
fails = []


def check(n, c, d=""):
    if c:
        print("  OK   %s" % n)
    else:
        print("  FAIL %s %s" % (n, d)); fails.append(n)


def kur():
    """Metin + iki kucuk vektor simge + buyuk zemin dolgusu."""
    yol = os.path.join(TMP, "s%d.pdf" % len(os.listdir(TMP)))
    d = pymupdf.open()
    p = d.new_page(width=400, height=300)
    p.draw_rect(p.rect, fill=(1, 1, 1), color=None)             # zemin
    p.draw_rect(pymupdf.Rect(10, 10, 180, 290), fill=(0.97, 0.97, 0.97),
                color=None)                                     # sol panel
    p.insert_text((60, 60), "0500 000 00 00", fontsize=11)
    p.insert_text((60, 110), "posta@ornek.com", fontsize=11)

    # "telefon" simgesi: govde + iki kucuk parca (30,48)-(45,63)
    p.draw_rect(pymupdf.Rect(30, 48, 45, 63), fill=(0.25, 0.25, 0.25),
                color=None)
    p.draw_circle(pymupdf.Point(34, 52), 2, fill=(1, 1, 1), color=None)
    p.draw_circle(pymupdf.Point(41, 59), 2, fill=(1, 1, 1), color=None)
    # "zarf" simgesi (30,98)-(45,111)
    p.draw_rect(pymupdf.Rect(30, 98, 45, 111), fill=(0.25, 0.25, 0.25),
                color=None)
    p.draw_line(pymupdf.Point(30, 98), pymupdf.Point(45, 111),
                color=(1, 1, 1), width=1)
    d.save(yol); d.close()
    doc = PdfDocument(); doc.open(yol)
    return doc


TEL = pymupdf.Point(37, 55)
ZARF = pymupdf.Point(37, 104)


def koyu(doc, kutu):
    pix = doc.doc.load_page(0).get_pixmap(dpi=200, clip=kutu)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    return int((a.mean(axis=2) < 170).sum())


print("=== 1. Simge secilebiliyor mu? ===")
doc = kur()
tel = doc.drawing_at(0, TEL)
check("telefon simgesi bulundu", tel is not None)
check("kutu simgenin kendisi kadar", tel is not None
      and abs(tel["rect"].width - 15) < 3 and abs(tel["rect"].height - 15) < 3,
      "-> %s" % (None if not tel else tuple(round(v, 1) for v in tel["rect"]),))
check("birden cok yol kumelendi", tel is not None and tel["count"] >= 2,
      "-> %s yol" % (None if not tel else tel["count"]))

zarf = doc.drawing_at(0, ZARF)
check("zarf simgesi ayri bulundu", zarf is not None
      and abs(zarf["rect"].y0 - 98) < 3,
      "-> %s" % (None if not zarf else tuple(round(v, 1) for v in zarf["rect"]),))

check("sayfa zemini secilmiyor",
      doc.drawing_at(0, pymupdf.Point(300, 250)) is None,
      "-> bos alanda buyuk dolgu secildi")

print()
print("=== 2. Tasima ===")
doc = kur()
tel = doc.drawing_at(0, TEL)
metin0 = doc.doc.load_page(0).get_text().strip()
eski = pymupdf.Rect(tel["rect"])
doc.place_drawing(0, tel, eski + (60, 0, 60, 0))

check("eski yerde iz kalmadi", koyu(doc, eski) == 0,
      "-> %d koyu piksel" % koyu(doc, eski))
yeni = doc.drawing_at(0, pymupdf.Point(TEL.x + 60, TEL.y))
check("yeni yerde simge var", yeni is not None)
check("boyut korundu", yeni is not None
      and abs(yeni["rect"].width - eski.width) < 2)
check("metin bozulmadi", doc.doc.load_page(0).get_text().strip() == metin0)
check("komsu simge yerinde", doc.drawing_at(0, ZARF) is not None)

print()
print("=== 3. Boyutlandirma ===")
doc = kur()
tel = doc.drawing_at(0, TEL)
eski = pymupdf.Rect(tel["rect"])
doc.place_drawing(0, tel, pymupdf.Rect(eski.x0, eski.y0,
                                       eski.x0 + eski.width * 2,
                                       eski.y0 + eski.height * 2))
buyuk = doc.drawing_at(0, pymupdf.Point(eski.x0 + 10, eski.y0 + 10))
check("iki katina cikti", buyuk is not None
      and abs(buyuk["rect"].width - eski.width * 2) < 3,
      "-> %s" % (None if not buyuk else round(buyuk["rect"].width, 1),))

print()
print("=== 4. Silme ve geri alma ===")
doc = kur()
tel = doc.drawing_at(0, TEL)
eski = pymupdf.Rect(tel["rect"])
metin0 = doc.doc.load_page(0).get_text().strip()
doc.delete_drawing(0, tel)
check("simge gitti", doc.drawing_at(0, TEL) is None)
check("silinen yerde iz yok", koyu(doc, eski) == 0)
check("komsu simge duruyor", doc.drawing_at(0, ZARF) is not None)
check("metin duruyor", doc.doc.load_page(0).get_text().strip() == metin0)
doc.undo()
check("geri alinca dondu", doc.drawing_at(0, TEL) is not None)

print()
print("=== 5. GERCEK DOSYALAR ===")
# Gercek PDF'ler depoya konmuyor (kisisel veri). Yollari yerel bir listeden
# ya da ortam degiskeninden okuyoruz; dosya yoksa bu bolum atlanir.
#   gercek-dosyalar.txt  -> her satirda bir PDF yolu  (.gitignore'da)
#   PDFSTUDIO_GERCEK_PDF -> ; ile ayrilmis yollar
import shutil

def gercek_listesi():
    yollar = []
    liste = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "gercek-dosyalar.txt")
    if os.path.exists(liste):
        with open(liste, encoding="utf-8") as fh:
            yollar += [s.strip() for s in fh
                       if s.strip() and not s.startswith("#")]
    yollar += [s.strip() for s in
               os.environ.get("PDFSTUDIO_GERCEK_PDF", "").split(";") if s.strip()]
    return yollar

GERCEKLER = gercek_listesi()
if not GERCEKLER:
    print("  ATLANDI: gercek dosya tanimlanmamis "
          "(gercek-dosyalar.txt ya da PDFSTUDIO_GERCEK_PDF)")

# Bu sablonlarda sayfanin altinda tum yuzeyi kaplayan dev bir arka plan
# dokusu var; secim "en kucuk nesne" kuralini uygulamazsa tiklama hep o
# dokuyu buluyor ve simgeye hic sira gelmiyor.
TEL_N = pymupdf.Point(54, 309)
ZARF_N = pymupdf.Point(54, 341)

for sira, GERCEK in enumerate(GERCEKLER):
    etiket = os.path.basename(GERCEK)[:20]
    if not os.path.exists(GERCEK):
        print("  ATLANDI (dosya yok): %s" % GERCEK)
        continue
    kopya = os.path.join(TMP, "gercek%d.pdf" % sira)
    shutil.copy(GERCEK, kopya)
    doc = PdfDocument(); doc.open(kopya)
    metin0 = doc.doc.load_page(0).get_text().strip()
    gorsel0 = len(doc.images_on(0))

    tel = doc.drawing_at(0, TEL_N)
    mail = doc.drawing_at(0, ZARF_N)
    check("%s: telefon simgesi secildi" % etiket,
          tel is not None and 10 < tel["rect"].width < 20,
          "-> %s" % (None if not tel
                     else tuple(round(v, 1) for v in tel["rect"]),))
    check("%s: zarf simgesi secildi" % etiket,
          mail is not None and 10 < mail["rect"].width < 20,
          "-> %s" % (None if not mail
                     else tuple(round(v, 1) for v in mail["rect"]),))
    check("%s: iki simge ayri nesne" % etiket,
          tel is not None and mail is not None
          and (pymupdf.Rect(tel["rect"]) & pymupdf.Rect(mail["rect"])).is_empty)

    eski = pymupdf.Rect(tel["rect"])
    doc.place_drawing(0, tel, eski + (25, 0, 25, 0))
    check("%s: eski yerde iz yok" % etiket, koyu(doc, eski) == 0,
          "-> %d koyu piksel" % koyu(doc, eski))
    check("%s: tasindiktan sonra metin ayni" % etiket,
          doc.doc.load_page(0).get_text().strip() == metin0)
    check("%s: fotograf ve zemin duruyor" % etiket,
          len(doc.images_on(0)) == gorsel0,
          "-> %d / %d" % (len(doc.images_on(0)), gorsel0))
    check("%s: zarf simgesi etkilenmedi" % etiket,
          doc.drawing_at(0, ZARF_N) is not None)
    doc.close()

print()
print("=== 6. ARAYUZ ===")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from pdfstudio.mainwindow import MainWindow
from pdfstudio.pageview import Tool

app = QApplication.instance() or QApplication([])
doc = kur(); yol = doc.path; doc.close()
win = MainWindow()
win._error = lambda m: (_ for _ in ()).throw(RuntimeError(m))
win.load(yol)
win.set_tool(Tool.IMAGE_EDIT)

win.on_image_picked(TEL)
check("arayuz: simge secildi", win._selected_drawing is not None)
check("arayuz: gorsel secimi bos", win._selected_image is None)
check("arayuz: cerceve cizildi", win.view.image_rect is not None)

kutu = pymupdf.Rect(win._selected_drawing["rect"])
win.on_image_placed(kutu + (40, 0, 40, 0))
check("arayuz: tasima calisti", win._selected_drawing is not None
      and abs(win._selected_drawing["rect"].x0 - (kutu.x0 + 40)) < 3,
      "-> %s" % (None if not win._selected_drawing else
                 tuple(round(v, 1) for v in win._selected_drawing["rect"]),))

win.delete_selected_image()          # gorsel yoksa cizime dusmeli
check("arayuz: Delete cizimi sildi", win._selected_drawing is None)
check("arayuz: sayfada simge kalmadi",
      win.model.drawing_at(0, pymupdf.Point(TEL.x + 40, TEL.y)) is None)

win.on_image_picked(pymupdf.Point(300, 250))
check("arayuz: bos alanda secim yok", win._selected_drawing is None
      and win._selected_image is None)

win.model.dirty = False
win.close()

print()
print("=== 7. ARAYUZ: gercek dosyada secim onceligi ===")
for sira, GERCEK in enumerate(GERCEKLER):
    etiket = os.path.basename(GERCEK)[:20]
    if not os.path.exists(GERCEK):
        print("  ATLANDI: %s" % etiket)
        continue
    kopya = os.path.join(TMP, "ui%d.pdf" % sira)
    shutil.copy(GERCEK, kopya)
    w2 = MainWindow()
    w2._error = lambda m: (_ for _ in ()).throw(RuntimeError(m))
    w2.load(kopya)
    w2.set_tool(Tool.IMAGE_EDIT)

    # Simge: dev arka plan dokusu degil, kucuk cizim secilmeli.
    w2.on_image_picked(TEL_N)
    check("%s: tiklayinca simge secildi" % etiket,
          w2._selected_drawing is not None and w2._selected_image is None,
          "-> gorsel: %s" % (None if not w2._selected_image else
                             tuple(round(v, 1)
                                   for v in w2._selected_image["rect"]),))

    # Fotograf hala GORSEL olarak secilmeli.
    w2.on_image_picked(pymupdf.Point(128, 135))
    check("%s: fotograf gorsel olarak secildi" % etiket,
          w2._selected_image is not None
          and 150 < w2._selected_image["rect"].width < 190,
          "-> %s" % (None if not w2._selected_image else
                     tuple(round(v, 1)
                           for v in w2._selected_image["rect"]),))

    # Simgeyi surukleyerek tasi.
    w2.on_image_picked(TEL_N)
    kutu = pymupdf.Rect(w2._selected_drawing["rect"])
    w2.on_image_placed(kutu + (25, 0, 25, 0))
    check("%s: simge surukleyerek tasindi" % etiket,
          w2._selected_drawing is not None
          and abs(w2._selected_drawing["rect"].x0 - (kutu.x0 + 25)) < 3,
          "-> %s" % (None if not w2._selected_drawing else
                     tuple(round(v, 1)
                           for v in w2._selected_drawing["rect"]),))
    check("%s: eski yerde iz yok (arayuz)" % etiket,
          koyu(w2.model, kutu) == 0,
          "-> %d koyu piksel" % koyu(w2.model, kutu))
    w2.model.dirty = False
    w2.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("VEKTOR SIMGE TAMAM")
