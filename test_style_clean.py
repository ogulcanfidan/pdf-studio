"""Stil kopyalama arkada iz birakiyor mu? Piksel sayarak olc."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-sc-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build(path, aralik):
    """Sikisik CV yerlesimi: buyuk ad + hemen altinda kucuk teal satir."""
    d = pymupdf.open(); page = d.new_page(width=470, height=200)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), "OGULCAN FIDAN", font=bold, fontsize=22)
    w.write_text(page, color=(0.1, 0.15, 0.2))
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60 + aralik),
             "Bilgi Islem . Sistem Destek", font=reg, fontsize=10.5)
    w.write_text(page, color=(0.03, 0.45, 0.45))
    d.save(path, garbage=4, deflate=True); d.close()


def teal_piksel(path, clip):
    """Eski teal yazidan kalan iz var mi? Yesilimsi pikselleri say."""
    d = pymupdf.open(path)
    pix = d.load_page(0).get_pixmap(clip=clip, matrix=pymupdf.Matrix(4, 4),
                                    alpha=False)
    data = bytes(pix.samples); n = pix.n
    d.close()
    sayac = 0
    for i in range(0, len(data) - n, n):
        r, g, b = data[i], data[i+1], data[i+2]
        # Gercek teal: yesil ve mavi, kirmiziya gore BELIRGIN yuksek.
        # (Koyu gri yazinin kenar yumusatmasi bu esigi gecemez: orada
        #  g - r farki ~10 iken teal'de ~107.)
        if g - r > 45 and b - r > 45 and abs(g - b) < 45:
            sayac += 1
    return sayac


print("=== Alt satira BUYUK stil uygulayinca eski teal yazidan iz kaliyor mu? ===")
for aralik in (16.0, 14.0, 12.0):
    p = os.path.join(TMP, "a%.0f.pdf" % aralik)
    build(p, aralik)

    doc = PdfDocument(); doc.open(p)
    clip = pymupdf.Rect(25, 60 + aralik - 12, 460, 60 + aralik + 5)
    once = teal_piksel(p, clip)

    stil = doc.capture_style(0, pymupdf.Point(90, 52))     # buyuk koyu baslik
    hedef = doc.find_span_at(0, pymupdf.Point(90, 60 + aralik - 4))
    if stil is None or hedef is None:
        print("  aralik %4.1f -> secilemedi" % aralik)
        doc.close(); continue

    doc.restyle_text(0, hedef, stil)
    out = os.path.join(TMP, "s%.0f.pdf" % aralik)
    doc.save(out); doc.close()

    sonra = teal_piksel(out, clip)
    print("  aralik %4.1f -> teal piksel: %d -> %d" % (aralik, once, sonra))
    check("aralik %.1f: eski teal yazidan iz kalmadi" % aralik,
          sonra < max(8, once * 0.03),
          "-> %d piksel iz kaldi (basta %d)" % (sonra, once))

    d = pymupdf.open(out)
    metin = d.load_page(0).get_text("text").replace("\xa0", " ")
    d.close()
    check("aralik %.1f: metin korundu" % aralik, "Sistem Destek" in metin,
          "-> %r" % metin[:80])
    check("aralik %.1f: baslik bozulmadi" % aralik, "OGULCAN" in metin,
          "-> %r" % metin[:80])

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
