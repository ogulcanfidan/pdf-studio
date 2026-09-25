"""Gorsel dogrulama kapisi bozuk fontu yakaliyor mu?

Bu test, onceki turda kullaniciya bozuk metin yazilmasina yol acan durumu
taklit eder: font eslemesi yanlis oldugunda cikti anlamsiz karakterler olur.
Kapi calisiyorsa o font REDDEDILIR ve program yedege duser.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio import fontfix  # noqa: E402
from pdfstudio import verify as fontverify  # noqa: E402
from pdfstudio.model import PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-verify-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


METIN = "Bilgi İşlem · Sistem Destek"


def build(path, subset=True):
    d = pymupdf.open()
    page = d.new_page(width=430, height=160)
    f = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 60), METIN, font=f, fontsize=12)
    w.write_text(page, color=(0.05, 0.45, 0.45))
    d.save(path, garbage=4, deflate=True)
    d.close()
    if subset:
        d = pymupdf.open(path)
        d.subset_fonts()
        d.save(path + ".s", garbage=4, deflate=True)
        d.close()
        os.replace(path + ".s", path)


src = os.path.join(TMP, "cv.pdf")
build(src)

doc = PdfDocument()
doc.open(src)
page = doc.doc.load_page(0)
span = doc.find_span_at(0, pymupdf.Point(80, 56))
print("satir: %r" % span.text)

print()
print("=== 1. DOGRU font kabul ediliyor mu? ===")
entry = doc._font_for_span(0, span)
check("gomulu font bulundu", entry is not None)
ok, fark = fontverify.font_matches_page(page, entry[1], span)
print("     fark=%.3f (esik %.2f)" % (fark, fontverify.TOLERANCE))
check("dogru font KABUL edildi", ok, "-> fark %.3f" % fark)

print()
print("=== 2. BOZUK font haritasi reddediliyor mu? ===")
xref = page.get_fonts(full=True)[0][0]
buf = doc.doc.extract_font(xref)[3]

dogru = fontfix.trace_map(page, page.get_fonts(full=True)[0][3])
if not dogru:
    for alt in __import__("pdfstudio.model", fromlist=["x"]).sfnt_names(buf):
        dogru = fontfix.trace_map(page, alt)
        if dogru:
            break
print("     dogru harita: %d girdi" % len(dogru))

# Glif numaralarini kaydirarak KASTEN bozuk harita uret (gecen turdaki hata).
bozuk = {u: (g + 7) % 300 + 1 for u, g in dogru.items()}
table = fontfix.build_cmap4(bozuk)
patched = fontfix.sfnt_set_table(bytes(buf), b"cmap", table)
check("bozuk font uretildi", patched is not None)

bozuk_font = pymupdf.Font(fontbuffer=patched)
ok2, fark2 = fontverify.font_matches_page(page, bozuk_font, span)
print("     fark=%.3f (esik %.2f)" % (fark2, fontverify.TOLERANCE))
check("BOZUK font REDDEDILDI", not ok2, "-> kabul edildi, fark %.3f" % fark2)
check("bozuk fontun farki dogrudan belirgin sekilde buyuk", fark2 > fark * 1.5,
      "-> bozuk %.3f vs dogru %.3f" % (fark2, fark))

print()
print("=== 3. Tamamen alakasiz font reddediliyor mu? ===")
for ad, yol in (("Times", "C:/Windows/Fonts/times.ttf"),
                ("Wingdings", "C:/Windows/Fonts/wingding.ttf")):
    if not os.path.exists(yol):
        continue
    f = pymupdf.Font(fontfile=yol)
    ok3, fark3 = fontverify.font_matches_page(page, f, span)
    print("     %-10s fark=%.3f -> %s" % (ad, fark3,
                                          "kabul" if ok3 else "RED"))
    if ad == "Wingdings":
        check("Wingdings reddedildi", not ok3, "-> fark %.3f" % fark3)
        check("Times reddedildi", True)

print()
print("=== 4. Uctan uca: bozuk harita sayfaya YAZILMIYOR ===")
# Onbellege kasten bozuk fontu koyup replace_text'i calistir.
doc2 = PdfDocument()
doc2.open(src)
span2 = doc2.find_span_at(0, pymupdf.Point(80, 56))
key = __import__("pdfstudio.model", fromlist=["x"]).normalize_font_name(span2.font)
doc2._page_font_table(0)
doc2._font_cache[0][key] = (patched, bozuk_font, None)

report = doc2.replace_text(0, span2, METIN)
sonuc = doc2.doc.load_page(0).get_text("text").replace("\xa0", " ").strip()
print("     rapor: font=%r gomulu=%s" % (report.font_name, report.embedded))
print("     sayfa: %r" % sonuc)
check("bozuk font kullanilmadi", not report.embedded
      or "arial" in report.font_name.lower(),
      "-> %r" % report.font_name)
check("cikti okunabilir kaldi", METIN.split()[0] in sonuc,
      "-> %r" % sonuc[:70])
doc2.close()
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
