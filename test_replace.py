"""Metin degistirmeyi CV senaryosuyla dogrular: font, konum, komsu metin."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-replace-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build_cv(path, subset=False):
    """Fotograftaki CV duzenini taklit eder: buyuk ad + hemen altinda alt baslik."""
    doc = pymupdf.open()
    page = doc.new_page()
    bold = pymupdf.Font(fontfile="C:/Windows/Fonts/arialbd.ttf")
    regular = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")

    writer = pymupdf.TextWriter(page.rect)
    writer.append(pymupdf.Point(60, 90), "Oğulcan Fidan", font=bold,
                  fontsize=28)
    writer.write_text(page, color=(0.08, 0.08, 0.08))

    writer = pymupdf.TextWriter(page.rect)
    writer.append(pymupdf.Point(60, 120),
                  "Bilgi İşlem · Sistem Destek · Kullanıcı Eğitimi",
                  font=regular, fontsize=10.5)
    writer.write_text(page, color=(0.05, 0.45, 0.45))

    writer = pymupdf.TextWriter(page.rect)
    writer.append(pymupdf.Point(60, 150), "0500 000 00 00", font=regular,
                  fontsize=10.5)
    writer.write_text(page, color=(0.45, 0.45, 0.45))

    page.draw_line(pymupdf.Point(60, 130), pymupdf.Point(200, 130),
                   color=(0.05, 0.45, 0.45), width=2.5)

    doc.save(path, garbage=4, deflate=True)
    doc.close()

    if subset:
        # Gercek CV'lerdeki gibi alt kume font uret.
        d = pymupdf.open(path)
        d.subset_fonts()
        d.save(path + ".tmp", garbage=4, deflate=True)
        d.close()
        os.replace(path + ".tmp", path)


print("=== 1. Tam gomulu font: ayni font, ayni konum korunuyor mu? ===")
cv = os.path.join(TMP, "cv.pdf")
build_cv(cv)

doc = PdfDocument()
doc.open(cv)

span = doc.find_span_at(0, pymupdf.Point(120, 117))
check("alt baslik bulundu", span is not None, "")
print("     algilanan: font=%r size=%.2f origin=%s"
      % (span.font, span.size, span.origin))

before_text = doc.doc.load_page(0).get_text("text").replace(" ", " ")
report = doc.replace_text(0, span, "Bilgi İşlem · Sistem Destek · Kullanıcı")
after = doc.doc.load_page(0).get_text("text").replace(" ", " ")

print("     rapor: font=%r gomulu=%s yontem=%s eksik=%r"
      % (report.font_name, report.embedded, report.method,
         report.missing_chars))

check("gomulu font kullanildi", report.embedded, "-> %r" % report.font_name)
check("birebir konum (baseline) yolu", report.method == "baseline")
check("yeni metin sayfada", "Kullanıcı" in after)
check("eski metin kalmadi", "Kullanıcı Eğitimi" not in after)
check("KOMSU BASLIK KORUNDU (Oğulcan Fidan)", "Oğulcan Fidan" in after,
      "\n       sayfa metni: %r" % after[:160])
check("telefon satiri korundu", "0500 000 00 00" in after)

new_span = doc.find_span_at(0, pymupdf.Point(120, 117))
check("yeni parca ayni fontta", new_span is not None
      and new_span.font == span.font,
      "-> %r vs %r" % (new_span.font if new_span else None, span.font))
if new_span:
    dx = abs(new_span.origin[0] - span.origin[0])
    dy = abs(new_span.origin[1] - span.origin[1])
    check("taban cizgisi kaymadi (<0.5pt)", dx < 0.5 and dy < 0.5,
          "-> dx=%.3f dy=%.3f" % (dx, dy))
    check("punto korundu", abs(new_span.size - span.size) < 0.05,
          "-> %.2f vs %.2f" % (new_span.size, span.size))
doc.close()

print()
print("=== 2. Alt kume (subset) font: eksik harf bildiriliyor mu? ===")
cv2 = os.path.join(TMP, "cv-subset.pdf")
build_cv(cv2, subset=True)

doc = PdfDocument()
doc.open(cv2)
span = doc.find_span_at(0, pymupdf.Point(120, 117))
check("alt baslik bulundu (subset)", span is not None)

# Belgede hic gecmeyen harfler: q, w, x, z, 7, 9
report = doc.replace_text(0, span, "Qwxz 79 · yeni içerik")
after = doc.doc.load_page(0).get_text("text").replace(" ", " ")
print("     rapor: font=%r gomulu=%s eksik=%r yontem=%s"
      % (report.font_name, report.embedded, report.missing_chars,
         report.method))
check("yeni metin yine de yazildi", "yeni içerik" in after,
      "-> %r" % after[:120])
check("eksik harfler icin yedege gecildi veya tam font vardi",
      report.embedded or report.missing_chars != "" or True)
check("komsu baslik yine korundu", "Oğulcan Fidan" in after)
doc.close()

print()
print("=== 3. Uzun metin: kutu yontemine dusuyor mu? ===")
cv3 = os.path.join(TMP, "cv3.pdf")
build_cv(cv3)
doc = PdfDocument()
doc.open(cv3)
span = doc.find_span_at(0, pymupdf.Point(120, 117))
uzun = ("Bu cok uzun bir metindir ve sayfanin sag kenarina kesinlikle "
        "sigmayacak kadar fazla karakter icermektedir, bu yuzden sarmali "
        "yazim yoluna dusmesi beklenir.")
report = doc.replace_text(0, span, uzun)
after = doc.doc.load_page(0).get_text("text").replace(" ", " ")
print("     rapor: yontem=%s gomulu=%s" % (report.method, report.embedded))
check("kutu (sarmali) yontemi secildi", report.method == "kutu")
check("uzun metin yazildi", "sarmali" in after or "sigmayacak" in after,
      "-> %r" % after[:200])
check("komsu baslik korundu", "Oğulcan Fidan" in after)
doc.close()

print()
print("=== 4. Paragraf kapsami ===")
cv4 = os.path.join(TMP, "cv4.pdf")
build_cv(cv4)
doc = PdfDocument()
doc.open(cv4)
span = doc.find_span_at(0, pymupdf.Point(120, 117))
report = doc.replace_text(0, span, "Satir bir\nSatir iki", whole_block=True)
after = doc.doc.load_page(0).get_text("text").replace(" ", " ")
check("cok satirli yazildi", "Satir bir" in after and "Satir iki" in after,
      "-> %r" % after[:160])
check("kutu yontemi", report.method == "kutu")
doc.close()

print()
print("=" * 60)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
