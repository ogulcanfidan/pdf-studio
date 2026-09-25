"""Komsu yazinin silinmesi: once daralt, sonra kaybi tespit edip geri al."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import NeighborTextLost, PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-neigh-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def yaz(page, font, nokta, metin, punto=10.0, renk=(0.1, 0.1, 0.1)):
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(*nokta), metin, font=font, fontsize=punto)
    w.write_text(page, color=renk)


def build(path, aralik):
    """Satir araligini parametreyle daralt; cok sikisirsa bbox'lar cakisir."""
    d = pymupdf.open()
    page = d.new_page(width=460, height=220)
    reg = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    y = 60.0
    for i, metin in enumerate(("UST SATIR korunmali",
                               "HEDEF satir degisecek",
                               "ALT SATIR korunmali")):
        yaz(page, reg, (30, y), metin, 10.0)
        y += aralik
    d.save(path, garbage=4, deflate=True)
    d.close()


def satirlar(doc):
    out = []
    for b in doc.doc.load_page(0).get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(s["text"] for s in ln.get("spans", [])).replace("\xa0", " ")
            if t.strip():
                out.append(t.strip())
    return out


print("=== Farkli satir araliklarinda davranis ===")
for aralik in (16.0, 12.0, 10.0, 9.0, 8.0):
    p = os.path.join(TMP, "a%.0f.pdf" % aralik)
    build(p, aralik)

    doc = PdfDocument()
    doc.open(p)
    once = satirlar(doc)
    span = doc.find_span_at(0, pymupdf.Point(80, 60 + aralik - 3))
    if span is None or "HEDEF" not in span.text:
        # Cok sikisik olunca satirlar tek blokta birlesebilir; atla.
        print("  aralik %4.1f -> hedef satir secilemedi (%r)"
              % (aralik, span.text[:30] if span else None))
        doc.close()
        continue

    durum = "yazildi"
    uygulandi = True
    try:
        rapor = doc.replace_text(0, span, "DEGISTI")
        durum = "ortuldu" if rapor.covered else "silindi"
    except NeighborTextLost as exc:
        durum = "GERI ALINDI (%d satir)" % len(exc.lost)
        uygulandi = False

    sonra = satirlar(doc)
    ust = any("UST SATIR" in t for t in sonra)
    alt = any("ALT SATIR" in t for t in sonra)
    yeni = any("DEGISTI" in t for t in sonra)
    print("  aralik %4.1f -> %-24s ust=%s alt=%s yeni=%s"
          % (aralik, durum, "VAR" if ust else "YOK",
             "VAR" if alt else "YOK", "VAR" if yeni else "YOK"))
    check("aralik %.1f: komsu satirlar korundu" % aralik, ust and alt,
          "-> once=%s sonra=%s" % (once, sonra))
    check("aralik %.1f: DEGISIKLIK UYGULANDI" % aralik, uygulandi and yeni,
          "-> durum=%s sonra=%s" % (durum, sonra))
    doc.close()

print()
print("=== Kasten cakisan kutular: kayip tespit ediliyor mu? ===")
p = os.path.join(TMP, "cakisan.pdf")
build(p, 16.0)
doc = PdfDocument()
doc.open(p)
span = doc.find_span_at(0, pymupdf.Point(80, 73))
check("hedef satir bulundu", span is not None and "HEDEF" in span.text,
      "-> %r" % (span.text if span else None))

# Hedefin sinirlarini kasten komsulari kapsayacak sekilde genislet.
span.rect = pymupdf.Rect(span.rect.x0, span.rect.y0 - 20,
                         span.rect.x1, span.rect.y1 + 20)
span.block_rect = span.rect

durum = None
try:
    rapor = doc.replace_text(0, span, "DEGISTI")
    durum = "ortuldu" if rapor.covered else "silindi"
except NeighborTextLost as exc:
    durum = "geri alindi"
    print("     yakalandi -> %s" % ", ".join(t[:30] for t in exc.lost))
print("     sonuc: %s" % durum)

# Degismez kural: ne olursa olsun komsu yazi KAYBOLMAZ. Program ya ortme
# yoluyla cozer ya da islemi geri alir; ikisi de kabul.
sonra = satirlar(doc)
check("ust satir geri geldi", any("UST SATIR" in t for t in sonra),
      "-> %s" % sonra)
check("alt satir geri geldi", any("ALT SATIR" in t for t in sonra),
      "-> %s" % sonra)
check("hedef satir da bozulmadan duruyor",
      any("HEDEF" in t for t in sonra), "-> %s" % sonra)
doc.close()

print()
print("=== Normal durumda hala calisiyor mu? ===")
p = os.path.join(TMP, "normal.pdf")
build(p, 18.0)
doc = PdfDocument()
doc.open(p)
span = doc.find_span_at(0, pymupdf.Point(80, 75))
doc.replace_text(0, span, "YENI METIN")
sonra = satirlar(doc)
check("degisiklik uygulandi", any("YENI METIN" in t for t in sonra),
      "-> %s" % sonra)
check("eski hedef gitti", not any("HEDEF" in t for t in sonra), "-> %s" % sonra)
check("komsular yerinde", any("UST" in t for t in sonra)
      and any("ALT" in t for t in sonra), "-> %s" % sonra)
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
