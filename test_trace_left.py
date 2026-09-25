"""Stil kopyalama sonrasi eski yazidan RENKLI IZ kaliyor mu?

Sorunlu yerlesim: ustte kalin bir baslik (g kuyrugu asagi sarkiyor),
hemen altinda teal renkli alt baslik. Kirpma satir bazinda yapilinca eski
yazinin ust kismi ortulmeden kaliyordu.
"""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument

TMP = tempfile.mkdtemp(prefix="pdfstudio-iz-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

TEAL = (0.03, 0.45, 0.45)

def build(path, aralik):
    d = pymupdf.open(); page = d.new_page(width=520, height=220)
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    # 'ğ' kuyrugu asagi sarkan baslik
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), "Oğulcan Fidan", font=bold, fontsize=24)
    w.write_text(page, color=(0.1, 0.15, 0.2))
    # Hemen altinda teal alt baslik - noktali harfler (i, İ) kritik
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60 + aralik),
             "Bilgi İşlem · Sistem Destek · Kullanıcı", font=reg, fontsize=11)
    w.write_text(page, color=TEAL)
    d.save(path, garbage=4, deflate=True); d.close()

def teal_piksel(path, clip):
    d = pymupdf.open(path)
    pix = d.load_page(0).get_pixmap(clip=clip, matrix=pymupdf.Matrix(4, 4), alpha=False)
    data = bytes(pix.samples); n = pix.n
    d.close()
    return sum(1 for i in range(0, len(data) - n, n)
               if data[i+1] - data[i] > 45 and data[i+2] - data[i] > 45
               and abs(data[i+1] - data[i+2]) < 45)

print("=== Stil uygulandiktan sonra teal iz kaliyor mu? ===")
for aralik in (16.0, 14.0, 12.0, 10.0):
    p = os.path.join(TMP, "a%.0f.pdf" % aralik)
    build(p, aralik)
    clip = pymupdf.Rect(25, 60 + aralik - 13, 510, 60 + aralik + 5)
    once = teal_piksel(p, clip)

    doc = PdfDocument(); doc.open(p)
    stil = doc.capture_style(0, pymupdf.Point(90, 52))
    hedef = doc.find_span_at(0, pymupdf.Point(90, 60 + aralik - 4))
    if stil is None or hedef is None:
        print("  aralik %4.1f -> secilemedi" % aralik); doc.close(); continue
    rapor = doc.restyle_text(0, hedef, stil)
    out = os.path.join(TMP, "s%.0f.pdf" % aralik)
    doc.save(out); doc.close()

    sonra = teal_piksel(out, clip)
    print("  aralik %4.1f -> yontem=%-8s teal piksel: %d -> %d"
          % (aralik, "ortuldu" if rapor.covered else "silindi", once, sonra))
    check("aralik %.1f: teal IZ KALMADI" % aralik, sonra < max(10, once * 0.03),
          "-> %d iz (basta %d)" % (sonra, once))

    d = pymupdf.open(out)
    metin = d.load_page(0).get_text("text").replace("\xa0", " ")
    d.close()
    check("aralik %.1f: ustteki baslik korundu" % aralik,
          "Oğulcan Fidan" in metin, "-> %r" % metin[:60])
    check("aralik %.1f: alt baslik metni tam" % aralik,
          "Kullanıcı" in metin, "-> %r" % metin[:80])

print()
print("=== Metin degistirmede iz kalmiyor mu? ===")
# DIKKAT: yeni metin de AYNI teal renkte yaziliyor; bu yuzden tum seridi
# saymak yaniltir. Yeni yazinin SAGINDA kalan teal = gercek iz.
p = os.path.join(TMP, "b.pdf"); build(p, 13.0)
doc = PdfDocument(); doc.open(p)
hedef = doc.find_span_at(0, pymupdf.Point(90, 60 + 13 - 4))
eski_sag = hedef.rect.x1
doc.replace_text(0, hedef, "Kisa metin")
out = os.path.join(TMP, "b2.pdf"); doc.save(out); doc.close()

d = pymupdf.open(out)
yeni_sag = 0.0
for b in d.load_page(0).get_text("dict")["blocks"]:
    for ln in b.get("lines", []):
        satir = "".join(sp["text"] for sp in ln.get("spans", [])).replace(" ", " ")
        if "Kisa metin" in satir:
            yeni_sag = max(yeni_sag, pymupdf.Rect(ln["bbox"]).x1)
d.close()
print("  eski sag kenar=%.1f  yeni sag kenar=%.1f" % (eski_sag, yeni_sag))
kuyruk = pymupdf.Rect(yeni_sag + 2, 60 + 13 - 13, eski_sag + 4, 60 + 13 + 5)
artik = teal_piksel(out, kuyruk) if kuyruk.width > 2 else 0
print("  eski yazinin kuyrugunda kalan teal: %d" % artik)
check("metin degistirmede iz yok", artik < 10, "-> %d" % artik)

d = pymupdf.open(out)
metin = d.load_page(0).get_text("text").replace(" ", " ")
d.close()
check("yeni metin yazildi", "Kisa metin" in metin, "-> %r" % metin[:70])
check("ustteki baslik korundu", "Oğulcan Fidan" in metin, "-> %r" % metin[:70])

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("HEPSI GECTI")
