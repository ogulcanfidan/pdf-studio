"""Alt kume (subset) gomulu fontlarda dogru davranis.

Gercek CV'lerde font alt kume olarak gomuluyor ve unicode tablosu (cmap)
kullanilamaz hale geliyor: has_glyph her karakter icin 0 donuyor ama font
mukemmel calisiyor. Program bu tuzaga dusup Helvetica'ya kacmamali.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import PdfDocument  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-subset-")
fails = []


def check(name, cond, detail=""):
    if cond:
        print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        fails.append(name)


def build_cv(path, subset=True):
    """Harf arali PROFIL basligi + normal paragraf; sonra fontu alt kumele."""
    doc = pymupdf.open()
    page = doc.new_page(width=430, height=240)
    font = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")

    x = 30.0
    for ch in "PROFİL":
        w = pymupdf.TextWriter(page.rect)
        w.append(pymupdf.Point(x, 60), ch, font=font, fontsize=12)
        w.write_text(page, color=(0.03, 0.47, 0.47))
        x += font.glyph_advance(ord(ch)) * 12 + 6.0

    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(30, 95),
             "Üç yıl bilgi işlem ve son kullanıcı desteği alanında çalıştım.",
             font=font, fontsize=9.5)
    w.write_text(page, color=(0.15, 0.15, 0.15))

    doc.save(path, garbage=4, deflate=True)
    doc.close()

    if subset:
        d = pymupdf.open(path)
        d.subset_fonts()
        d.save(path + ".s", garbage=4, deflate=True)
        d.close()
        os.replace(path + ".s", path)


def cmap_durumu(path):
    """Gomulu fontun unicode tablosu kullanilabilir mi?"""
    d = pymupdf.open(path)
    page = d.load_page(0)
    row = page.get_fonts(full=True)[0]
    buf = d.extract_font(row[0])[3]
    f = pymupdf.Font(fontbuffer=buf)
    n = len(f.valid_codepoints())
    eksik = [c for c in "PROFİL" if f.has_glyph(ord(c)) == 0]
    d.close()
    return n, "".join(eksik)


print("=== 0. On kosul: alt kume font gercekten cmap'siz mi? ===")
cv = os.path.join(TMP, "cv.pdf")
build_cv(cv, subset=True)
n, eksik = cmap_durumu(cv)
print("     valid_codepoints=%d, has_glyph'e gore eksik=%r" % (n, eksik))
check("cmap kullanilamaz durumda (gercek CV kosulu)", n == 0,
      "-> %d kod noktasi" % n)
check("has_glyph yaniltiyor (hepsini eksik saniyor)", eksik == "PROFİL",
      "-> %r" % eksik)

print()
print("=== 1. Bu kosulda yanlis uyari cikiyor mu? ===")
doc = PdfDocument()
doc.open(cv)
span = doc.find_span_at(0, pymupdf.Point(60, 56))
check("baslik satiri bulundu", span is not None)
print("     text=%r font=%r tracking=%.2f"
      % (span.text, span.font, span.tracking))

report = doc.replace_text(0, span, span.text)
print("     rapor: font=%r gomulu=%s eksik=%r belirsiz=%r"
      % (report.font_name, report.embedded, report.missing_chars,
         report.uncertain_chars))

check("YANLIS 'eksik harf' uyarisi YOK", report.missing_chars == "",
      "-> hatali eksik: %r" % report.missing_chars)
check("belgede zaten yazili harfler belirsiz sayilmadi",
      report.uncertain_chars == "", "-> %r" % report.uncertain_chars)
check("belgenin kendi fontu kullanildi", report.embedded,
      "-> %r" % report.font_name)
check("Helvetica'ya DUSMEDI",
      "helvetica" not in report.font_name.lower()
      and "nimbus" not in report.font_name.lower(),
      "-> %r" % report.font_name)

yeni = doc.find_span_at(0, pymupdf.Point(60, 56))
if yeni:
    fark = abs(yeni.rect.width - span.rect.width)
    print("     genislik once=%.2f sonra=%.2f fark=%.2f"
          % (span.rect.width, yeni.rect.width, fark))
    check("harf araligi korundu", fark < 1.5, "-> %.2f pt" % fark)
    # Onarilan font kendi gercek PostScript adini bildirir ('ArialMT'),
    # PDF'in uydurdugu ad ('Arial Regular') degil; aile ayni olmali.
    from pdfstudio.model import normalize_font_name as _n
    a, b = _n(yeni.font), _n(span.font)
    check("ayni font ailesi", a.startswith(b[:5]) or b.startswith(a[:5]),
          "-> %r vs %r" % (yeni.font, span.font))

sonra_path = os.path.join(TMP, "sonra.pdf")
doc.save(sonra_path)
doc.close()

print()
print("=== 2. Gercekten cizildi mi? (piksel karsilastirmasi) ===")
ref = os.path.join(TMP, "ref.pdf")
build_cv(ref, subset=True)


def koyu_piksel(path, clip):
    d = pymupdf.open(path)
    pix = d.load_page(0).get_pixmap(clip=clip, matrix=pymupdf.Matrix(2, 2))
    d.close()
    return sum(1 for b in bytes(pix.samples)[::3] if b < 200)


clip = pymupdf.Rect(25, 45, 200, 70)
once = koyu_piksel(ref, clip)
sonra = koyu_piksel(sonra_path, clip)
print("     koyu piksel: once=%d sonra=%d" % (once, sonra))
check("yazi bos cikmadi", sonra > once * 0.5, "-> %d vs %d" % (sonra, once))
oran = abs(sonra - once) / max(1, once)
check("gorunum neredeyse ayni (%20 icinde)", oran < 0.20,
      "-> fark %%%.0f" % (oran * 100))

print()
print("=== 3. Karar mantigi (taklit fontlarla, birim testi) ===")
# subset_fonts() glifleri gercekte silmedigi icin karar fonksiyonunu
# dogrudan sinamak daha kesin.


class SahteFont:
    """valid_codepoints ve has_glyph davranisini taklit eder."""

    def __init__(self, codepoints, glyphs):
        self._cp = list(codepoints)
        self._glyphs = set(glyphs)

    def valid_codepoints(self):
        return self._cp

    def has_glyph(self, code):
        return 1 if chr(code) in self._glyphs else 0


doc = PdfDocument()

# a) cmap kullanilamaz -> asla "kesin eksik" deme
cmapsiz = SahteFont([], "")
eksik, belirsiz = doc._check_glyphs(cmapsiz, "PROFİL QWX", set("PROFİL"))
print("     cmap yok      -> eksik=%r belirsiz=%r" % (eksik, belirsiz))
check("cmap yokken 'kesin eksik' demiyor", eksik == "")
check("cmap yokken bilinmeyenler 'belirsiz'", set("QWX") <= set(belirsiz),
      "-> %r" % belirsiz)
check("belgede yazili harfler belirsiz sayilmiyor",
      not (set("PROFİL") & set(belirsiz)), "-> %r" % belirsiz)

# b) cmap saglam, glifler gercekten yok -> "kesin eksik"
saglam = SahteFont([ord(c) for c in "PROFİL"], "PROFİL")
eksik, belirsiz = doc._check_glyphs(saglam, "PROFİL QWX", set("PROFİL"))
print("     cmap saglam   -> eksik=%r belirsiz=%r" % (eksik, belirsiz))
check("saglam cmap'te eksik harfler bildiriliyor",
      set("QWX") <= set(eksik), "-> %r" % eksik)
check("saglam cmap'te belirsizlik yok", belirsiz == "", "-> %r" % belirsiz)

# c) glifler var -> hicbir uyari yok
tam = SahteFont([ord(c) for c in "PROFİLQWX"], "PROFİLQWX")
eksik, belirsiz = doc._check_glyphs(tam, "PROFİL QWX", set("PROFİL"))
print("     glifler var   -> eksik=%r belirsiz=%r" % (eksik, belirsiz))
check("glifler varken uyari yok", eksik == "" and belirsiz == "")

# d) bosluklar hicbir zaman uyari uretmez
eksik, belirsiz = doc._check_glyphs(cmapsiz, "   \n\t ", set())
check("bosluklar uyari uretmiyor", eksik == "" and belirsiz == "")

print()
print("=== 4. Alt kume OLMAYAN belgede karar netligi ===")
cv4 = os.path.join(TMP, "cv4.pdf")
build_cv(cv4, subset=False)
n4, _ = cmap_durumu(cv4)
print("     valid_codepoints=%d (tam font)" % n4)
doc = PdfDocument()
doc.open(cv4)
span = doc.find_span_at(0, pymupdf.Point(60, 56))
report = doc.replace_text(0, span, "PROFİL QWX")
print("     rapor: gomulu=%s eksik=%r belirsiz=%r"
      % (report.embedded, report.missing_chars, report.uncertain_chars))
check("tam fontta belirsizlik yok",
      report.uncertain_chars == "" and report.missing_chars == "",
      "-> eksik=%r belirsiz=%r" % (report.missing_chars,
                                   report.uncertain_chars))
check("tam fontta da gomulu font kullanildi", report.embedded)
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
