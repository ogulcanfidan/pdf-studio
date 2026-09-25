"""Font teşhisi: belgenin İÇERİĞİNİ değil, yalnızca font bilgisini döker.

Kullanım:
    .venv\\Scripts\\python.exe teshis.py "C:\\yol\\cv.pdf"
    .venv\\Scripts\\python.exe teshis.py "C:\\yol\\cv.pdf" Fidan

İkinci argüman verilirse o kelimenin HER HARFİ için hangi fontun seçildiği
tek tek gösterilir — "Fidan'daki d" gibi sorunların kaynağı burada görünür.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import (PdfDocument, font_style_key,  # noqa: E402
                             normalize_font_name)

if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

yol = sys.argv[1]
aranan = sys.argv[2] if len(sys.argv) > 2 else None

doc = PdfDocument()
doc.open(yol)
print("dosya   : %s" % yol)
print("sayfa   : %d" % doc.page_count)

for sayfa_no in range(min(doc.page_count, 2)):
    page = doc.doc.load_page(sayfa_no)
    print()
    print("=== SAYFA %d: gömülü fontlar ===" % (sayfa_no + 1))
    for row in page.get_fonts(full=True):
        xref, ext, tur, basefont = row[0], row[1], row[2], row[3]
        try:
            buf = doc.doc.extract_font(xref)[3]
        except Exception as exc:
            print("  xref=%-4s %-30s ÇIKARILAMADI: %r" % (xref, basefont, exc))
            continue
        if not buf:
            print("  xref=%-4s %-30s (gömülü değil)" % (xref, basefont))
            continue
        try:
            ham = pymupdf.Font(fontbuffer=buf)
            ham_kod = len(ham.valid_codepoints())
        except Exception as exc:
            print("  xref=%-4s %-30s Font() HATA: %r" % (xref, basefont, exc))
            continue

        entry = doc._font_for_span_name(sayfa_no, basefont)
        onarilmis = len(entry[1].valid_codepoints()) if entry else 0
        print("  xref=%-4s %-30s tür=%-8s %6d bayt" % (xref, basefont, tur, len(buf)))
        print("        ham cmap=%-6d onarım sonrası=%-6d ağırlık=%d"
              % (ham_kod, onarilmis, font_style_key(basefont)[0]))

    print()
    print("=== SAYFA %d: metin parçalarının fontları ===" % (sayfa_no + 1))
    gorulen = {}
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                ad = sp["font"]
                gorulen.setdefault(ad, {"punto": set(), "harf": set()})
                gorulen[ad]["punto"].add(round(sp["size"], 1))
                gorulen[ad]["harf"].update(sp["text"])
    for ad, bilgi in sorted(gorulen.items()):
        eslesen = doc._font_for_span_name(sayfa_no, ad)
        print("  %-28r -> %-28r" % (ad, eslesen[1].name if eslesen else None))
        print("        anahtar=%-24s ağırlık=%d puntolar=%s"
              % (normalize_font_name(ad), font_style_key(ad)[0],
                 sorted(bilgi["punto"])[:6]))

    if aranan:
        print()
        print("=== SAYFA %d: %r kelimesinin harfleri ===" % (sayfa_no + 1, aranan))
        for rect in page.search_for(aranan):
            harfler = doc.chars_in(sayfa_no, rect)
            if not harfler:
                continue
            gruplar = {}
            for c in harfler:
                gruplar.setdefault(c["font"], []).append(c["char"])
            for c in harfler:
                font = doc._resolve_font(sayfa_no, c["font"],
                                         "".join(gruplar[c["font"]]))
                gomulu = doc._font_for_span_name(sayfa_no, c["font"])
                var = "?"
                if gomulu:
                    try:
                        var = str(gomulu[1].has_glyph(ord(c["char"])))
                    except Exception:
                        var = "hata"
                print("    %r kaynak=%-24r -> seçilen=%-24r has_glyph=%s"
                      % (c["char"], c["font"], font.name, var))
            break

# --- SIMULASYON: tasimayi kopya uzerinde gercekten yap ve olc ------------
if aranan:
    print()
    print("=== SIMULASYON: %r kelimesini taşı ve sonucu ölç ===" % aranan)
    import shutil
    import tempfile

    gecici = os.path.join(tempfile.mkdtemp(), "kopya.pdf")
    shutil.copyfile(yol, gecici)

    sim = PdfDocument()
    sim.open(gecici)
    bulundu = False
    for sayfa_no in range(sim.page_count):
        sayfa = sim.doc.load_page(sayfa_no)
        for rect in sayfa.search_for(aranan):
            harfler = sim.chars_in(sayfa_no, rect)
            if not harfler:
                continue
            bulundu = True
            kutu = pymupdf.Rect(harfler[0]["rect"])
            for c in harfler[1:]:
                kutu |= c["rect"]
            print("  taşınacak: %r (%d harf)"
                  % ("".join(c["char"] for c in harfler), len(harfler)))
            try:
                rapor = sim.move_region(sayfa_no, kutu, 40.0, 60.0)
                print("  rapor: yöntem=%s örtüldü=%s"
                      % (rapor.method, rapor.covered))
            except Exception as exc:
                print("  TAŞIMA HATASI: %r" % exc)
                break

            yeni = pymupdf.Rect(kutu) + (40, 60, 40, 60)
            sayfa2 = sim.doc.load_page(sayfa_no)
            print("  taşıma SONRASI harflerin fontları:")
            for b in sayfa2.get_text("rawdict").get("blocks", []):
                for ln in b.get("lines", []):
                    for sp in ln.get("spans", []):
                        for ch in sp.get("chars", []):
                            kb = pymupdf.Rect(ch["bbox"])
                            if (kb & yeni).is_empty:
                                continue
                            harf = ch.get("c", "")
                            if not harf.strip():
                                continue
                            print("     %r -> font=%-26r punto=%.1f"
                                  % (harf, sp["font"], sp["size"]))
            break
        if bulundu:
            break
    if not bulundu:
        print("  %r kelimesi bulunamadı." % aranan)
    sim.close()

doc.close()
print()
print("Bu çıktıda belge metni yok; yalnızca font adları ve sayılar var.")
