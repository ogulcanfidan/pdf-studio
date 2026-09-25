"""move_page'i her (src, dst) ikilisi icin dogrular."""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402

from pdfstudio.model import DocumentError, PdfDocument  # noqa: E402

fails = []


def build(n):
    doc = PdfDocument()
    doc.new()
    doc.doc.delete_page(0)
    for i in range(n):
        p = doc.doc.new_page()
        p.insert_text((72, 100), "P%d" % (i + 1), fontsize=20)
    doc._undo = []
    doc._redo = []
    return doc


def order(doc):
    return [doc.doc.load_page(i).get_text("text").strip()
            for i in range(doc.page_count)]


for n in (2, 3, 4, 6):
    for src in range(n):
        for dst in range(n):
            doc = build(n)
            start = order(doc)
            expected = start[:]
            page = expected.pop(src)
            expected.insert(dst, page)
            try:
                doc.move_page(src, dst)
                got = order(doc)
            except Exception as exc:
                fails.append((n, src, dst, "HATA: %r" % exc))
                doc.close()
                continue
            if got != expected:
                fails.append((n, src, dst, "beklenen %s, gelen %s"
                              % (expected, got)))
            # geri alma sirayi geri getirmeli
            if src != dst:
                doc.undo()
                if order(doc) != start:
                    fails.append((n, src, dst, "geri alma bozuk: %s" % order(doc)))
            doc.close()

print("Tum (n, src, dst) kombinasyonlari denendi.")

# sinir disi degerler
doc = build(3)
for bad in ((-1, 0), (0, 5), (3, 0), (0, -2)):
    try:
        doc.move_page(*bad)
        fails.append(("sinir", bad[0], bad[1], "hata vermedi"))
    except DocumentError:
        pass
    except Exception as exc:
        fails.append(("sinir", bad[0], bad[1], "yanlis hata turu: %r" % exc))
doc.close()

if fails:
    print("\nBASARISIZ (%d):" % len(fails))
    for n, src, dst, msg in fails[:25]:
        print("  n=%s src=%s dst=%s -> %s" % (n, src, dst, msg))
    sys.exit(1)
print("HEPSI DOGRU - sinir degerleri dahil.")
