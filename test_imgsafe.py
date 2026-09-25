"""Gorsel duzenleme sayfaya zarar vermemeli.

Olculen dort sey:
  1. Saydam (alfa kanalli) gorsel duzenlenince saydamligini korumali;
     eskiden seffaf bolgeler SIYAH dikdortgene donup cevreyi orturdu.
  2. Islem, komsu gorsele dokunmamali.
  3. Silinen gorselin 1x1 kalintisi bir daha secilememeli.
  4. Metin ve cizimler her islemden sonra yerinde kalmali.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-is-")
fails = []


def check(n, c, d=""):
    if c:
        print("  OK   %s" % n)
    else:
        print("  FAIL %s %s" % (n, d)); fails.append(n)


def saydam_png(path, w=120, h=120):
    """Ortasi dolu daire, kenarlari TAMAMEN seffaf."""
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:h, 0:w]
    ic = (xx - w / 2) ** 2 + (yy - h / 2) ** 2 < (w / 2 - 8) ** 2
    rgba[..., 0][ic] = 230
    rgba[..., 3][ic] = 255
    pix = pymupdf.Pixmap(pymupdf.csRGB, w, h,
                         np.ascontiguousarray(rgba).tobytes(), 1)
    pix.save(path)
    return path


def duz_png(path, renk, w=40, h=40):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h))
    pix.set_rect(pix.irect, renk)
    pix.save(path)
    return path


SAYDAM = saydam_png(os.path.join(TMP, "saydam.png"))
KOMSU = duz_png(os.path.join(TMP, "komsu.png"), (40, 170, 70))


def kur():
    """Metin + cizim + saydam gorsel + hemen yaninda kucuk komsu gorsel."""
    yol = os.path.join(TMP, "s%d.pdf" % len(os.listdir(TMP)))
    d = pymupdf.open()
    p = d.new_page(width=400, height=300)
    p.insert_text((30, 40), "ust metin", fontsize=12)
    p.insert_text((30, 280), "alt metin", fontsize=12)
    p.draw_rect(pymupdf.Rect(25, 55, 260, 200), color=(0, 0.4, 0.9), width=1.5)
    p.insert_image(pymupdf.Rect(40, 70, 160, 190), filename=SAYDAM)
    p.insert_image(pymupdf.Rect(190, 70, 220, 100), filename=KOMSU)
    d.save(yol); d.close()
    doc = PdfDocument(); doc.open(yol)
    return doc


def piksel(doc, kutu=None):
    pg = doc.doc.load_page(0)
    pix = pg.get_pixmap(dpi=100, clip=kutu)
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n).astype(int)


def durum(doc):
    pg = doc.doc.load_page(0)
    return pg.get_text().strip(), len(pg.get_drawings())


KOMSU_KUTU = pymupdf.Rect(190, 70, 220, 100)
# Gorselin kutusu icinde, dairenin DISINDA kalan kose: burasi sayfa
# arkaplani (beyaz) olarak kalmali.
KOSE = pymupdf.Rect(42, 72, 52, 82)

print("saydamlik korunuyor mu")
for islem, kw in [("dondur", {"derece": 90}), ("aynala", {"yatay": True}),
                  ("gri", {}), ("ayarla", {"parlaklik": 0.2, "kontrast": 0.0})]:
    doc = kur()
    metin0, cizim0 = durum(doc)
    komsu0 = piksel(doc, KOMSU_KUTU)
    g = doc.image_at(0, pymupdf.Point(100, 130))
    doc.edit_image(0, g, islem, **kw)

    kose = piksel(doc, KOSE)
    check("%s: seffaf kose beyaz kaldi" % islem, kose.mean() > 240,
          "ortalama parlaklik %.0f (siyah kutu olusmus)" % kose.mean())

    komsu1 = piksel(doc, KOMSU_KUTU)
    ayni = komsu0.shape == komsu1.shape and int(
        (np.abs(komsu0 - komsu1) > 12).sum()) == 0
    check("%s: komsu gorsel bozulmadi" % islem, ayni)

    metin1, cizim1 = durum(doc)
    check("%s: metin ve cizim yerinde" % islem,
          metin1 == metin0 and cizim1 == cizim0,
          "metin %r cizim %d->%d" % (metin1, cizim0, cizim1))

print("tasima komsuya dokunmuyor")
doc = kur()
komsu0 = piksel(doc, KOMSU_KUTU)
metin0, cizim0 = durum(doc)
g = doc.image_at(0, pymupdf.Point(100, 130))
doc.place_image(0, g, pymupdf.Rect(60, 90, 180, 210))
komsu1 = piksel(doc, KOMSU_KUTU)
check("tasima: komsu gorsel bozulmadi",
      int((np.abs(komsu0 - komsu1) > 12).sum()) == 0)
check("tasima: metin ve cizim yerinde", durum(doc) == (metin0, cizim0))
kose = piksel(doc, pymupdf.Rect(62, 92, 72, 102))
check("tasima: saydamlik korundu", kose.mean() > 240,
      "ortalama %.0f" % kose.mean())

print("silinen gorsel bir daha secilemiyor")
doc = kur()
metin0, cizim0 = durum(doc)
g = doc.image_at(0, pymupdf.Point(100, 130))
doc.delete_image(0, g)
check("silme: ayni noktada artik gorsel yok",
      doc.image_at(0, pymupdf.Point(100, 130)) is None)
check("silme: komsu gorsel duruyor",
      doc.image_at(0, pymupdf.Point(205, 85)) is not None)
check("silme: metin ve cizim yerinde", durum(doc) == (metin0, cizim0))
doc.undo()
check("silme: geri alinca gorsel dondu",
      doc.image_at(0, pymupdf.Point(100, 130)) is not None)

print("kutu degismeyen islem gorseli YERINDE degistiriyor")
doc = kur()
g = doc.image_at(0, pymupdf.Point(100, 130))
onceki = pymupdf.Rect(g["rect"])
doc.edit_image(0, g, "gri")
y = doc.image_at(0, pymupdf.Point(100, 130))
check("gri: kutu ayni kaldi",
      y is not None and abs(y["rect"].x0 - onceki.x0) < 0.01
      and abs(y["rect"].x1 - onceki.x1) < 0.01,
      "%s -> %s" % (tuple(round(v) for v in onceki),
                    None if not y else tuple(round(v) for v in y["rect"])))

print()
if fails:
    print("BASARISIZ: %d -> %s" % (len(fails), fails)); sys.exit(1)
print("GORSEL GUVENLIGI TAMAM")
