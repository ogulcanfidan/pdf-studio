"""Ortme kutusu komsu satirin tepesini boyuyor mu? Piksel piksel olc.

Belirti: ustteki satir duzenlenince alttaki satirin
i/İ noktalari ve uzun harflerinin ust kismi kayboluyor.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-clip-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


# Noktali ve uzun harfli metin - en hassas durum
ALT_METIN = "Bilgi İşlem · Sistem Destek · Kullanıcı Eğitimi"


def build(path, aralik):
    d = pymupdf.open()
    page = d.new_page(width=470, height=200)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")

    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), "OGULCAN FIDAN", font=bold, fontsize=22)
    w.write_text(page, color=(0.1, 0.15, 0.2))

    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60 + aralik), ALT_METIN, font=reg, fontsize=10.5)
    w.write_text(page, color=(0.03, 0.45, 0.45))

    d.save(path, garbage=4, deflate=True)
    d.close()


def alt_satir_pikselleri(path, aralik):
    """Alt satirin bulundugu seridi yuksek cozunurlukte tara."""
    d = pymupdf.open(path)
    page = d.load_page(0)
    clip = pymupdf.Rect(25, 60 + aralik - 12, 460, 60 + aralik + 4)
    pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(4, 4), alpha=False)
    data = bytes(pix.samples)
    d.close()
    # Koyu piksel sayisi = o seritteki mürekkep miktari
    return sum(1 for i in range(0, len(data), pix.n) if data[i] < 180)


print("=== Ust satiri degistirince alt satirin muürekkebi degisiyor mu? ===")
for aralik in (30.0, 24.0, 20.0, 17.0, 15.0):
    src = os.path.join(TMP, "a%.0f.pdf" % aralik)
    build(src, aralik)
    once = alt_satir_pikselleri(src, aralik)

    doc = PdfDocument()
    doc.open(src)
    span = doc.find_span_at(0, pymupdf.Point(90, 52))
    if span is None or "FIDAN" not in span.text:
        print("  aralik %4.1f -> ust satir secilemedi" % aralik)
        doc.close()
        continue

    rapor = doc.replace_text(0, span, "OGULCAN FIDANDASDADSADA")
    out = os.path.join(TMP, "s%.0f.pdf" % aralik)
    doc.save(out)
    doc.close()

    sonra = alt_satir_pikselleri(out, aralik)
    kayip = (once - sonra) / max(1, once)
    print("  aralik %4.1f -> yontem=%-8s alt satir mürekkep: %d -> %d (%%%.1f kayip)"
          % (aralik, "ortuldu" if rapor.covered else "silindi",
             once, sonra, kayip * 100))
    check("aralik %.1f: alt satir bozulmadi (<%%2 kayip)" % aralik,
          kayip < 0.02, "-> %%%.1f kayboldu" % (kayip * 100))

    # Metin olarak da duruyor mu?
    d = pymupdf.open(out)
    metin = d.load_page(0).get_text("text").replace("\xa0", " ")
    d.close()
    check("aralik %.1f: alt satir metni tam" % aralik,
          "Kullanıcı Eğitimi" in metin, "-> %r" % metin[:90])
    check("aralik %.1f: yeni metin yazildi" % aralik,
          "FIDANDASDADSADA" in metin, "-> %r" % metin[:90])

print()
print("=== Cok sikisik: ortme kutusu tamamen kirpilsa bile calisiyor mu? ===")
src = os.path.join(TMP, "sik.pdf")
build(src, 13.0)
once = alt_satir_pikselleri(src, 13.0)
doc = PdfDocument()
doc.open(src)
span = doc.find_span_at(0, pymupdf.Point(90, 52))
if span:
    rapor = doc.replace_text(0, span, "KISA")
    out = os.path.join(TMP, "sik-son.pdf")
    doc.save(out)
    doc.close()
    sonra = alt_satir_pikselleri(out, 13.0)
    kayip = (once - sonra) / max(1, once)
    print("  mürekkep: %d -> %d (%%%.1f)" % (once, sonra, kayip * 100))
    check("cok sikisikta da alt satir korundu", kayip < 0.02,
          "-> %%%.1f" % (kayip * 100))
    d = pymupdf.open(out)
    metin = d.load_page(0).get_text("text").replace("\xa0", " ")
    d.close()
    check("cok sikisikta alt satir metni tam", "Kullanıcı Eğitimi" in metin,
          "-> %r" % metin[:90])

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")

print()
print("=== ORTME yolunu zorla: kutu komsu harflere degiyor mu? ===")
src = os.path.join(TMP, "ortme.pdf")
build(src, 14.0)
once = alt_satir_pikselleri(src, 14.0)

doc = PdfDocument()
doc.open(src)
span = doc.find_span_at(0, pymupdf.Point(90, 52))
page = doc.doc.load_page(0)

# Silmeyi atlayip dogrudan ortme yolunu calistir (sorunlu senaryo).
doc.snapshot()
doc._cover(page, 0, span, False)
out = os.path.join(TMP, "ortme-son.pdf")
doc.save(out)
doc.close()

sonra = alt_satir_pikselleri(out, 14.0)
kayip = (once - sonra) / max(1, once)
print("  alt satir mürekkep: %d -> %d (%%%.1f)" % (once, sonra, kayip * 100))
check("ORTME alt satiri bozmuyor", kayip < 0.02, "-> %%%.1f" % (kayip * 100))

d = pymupdf.open(out)
metin = d.load_page(0).get_text("text").replace("\xa0", " ")
d.close()
check("ortme sonrasi alt satir metni tam", "Kullanıcı Eğitimi" in metin,
      "-> %r" % metin[:90])

# Ust satir gercekten gorunmez oldu mu?
d = pymupdf.open(out)
p0 = d.load_page(0)
ust = p0.get_pixmap(clip=pymupdf.Rect(25, 38, 460, 62),
                    matrix=pymupdf.Matrix(4, 4), alpha=False)
koyu = sum(1 for i in range(0, len(bytes(ust.samples)), ust.n)
           if bytes(ust.samples)[i] < 180)
d.close()
print("  ust satir kalan mürekkep: %d" % koyu)
check("ust satir gercekten ortuldu", koyu < 200, "-> %d piksel kaldi" % koyu)

print()
print("=" * 62)
if fails:
    print("SON DURUM BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("ORTME YOLU DA TEMIZ")
