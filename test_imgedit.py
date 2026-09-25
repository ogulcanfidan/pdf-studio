"""Gorsel icerigini duzenleme: dondur, aynala, kirp, gri, parlaklik, degistir."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pymupdf
from pdfstudio.model import PdfDocument
from pdfstudio import imaging

TMP = tempfile.mkdtemp(prefix="pdfstudio-ie-")
fails = []
def check(n, c, d=""):
    if c: print("  OK   %s" % n)
    else: print("  FAIL %s %s" % (n, d)); fails.append(n)

def resim(path, w=160, h=100):
    """Asimetrik gorsel: sol ust kose sari, gerisi mavi -> yon anlasilir."""
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h))
    pix.set_rect(pymupdf.IRect(0, 0, w, h), (40, 130, 210))
    pix.set_rect(pymupdf.IRect(0, 0, w // 4, h // 4), (240, 200, 60))
    pix.save(path)
    return path

KAYNAK = resim(os.path.join(TMP, "k.png"))
BASKA = resim(os.path.join(TMP, "b.png"), 80, 80)

def build(path):
    d = pymupdf.open(); page = d.new_page(width=420, height=320)
    page.insert_image(pymupdf.Rect(40, 40, 200, 140), filename=KAYNAK)
    f = pymupdf.Font(fontfile="C:/Windows/Fonts/arial.ttf")
    w = pymupdf.TextWriter(page.rect)
    w.append(pymupdf.Point(40, 300), "metin korunmali", font=f, fontsize=12)
    w.write_text(page)
    d.save(path, garbage=4, deflate=True); d.close()

def ac(ad):
    p = os.path.join(TMP, ad); build(p)
    doc = PdfDocument(); doc.open(p)
    return doc, doc.image_at(0, pymupdf.Point(100, 90))

def kose_rengi(doc, konum):
    """Gorselin belirtilen kosesindeki renk (sari mi mavi mi)."""
    page = doc.doc.load_page(0)
    pix = page.get_pixmap(clip=pymupdf.Rect(konum[0]-3, konum[1]-3,
                                            konum[0]+3, konum[1]+3))
    d = bytes(pix.samples)
    return (d[0], d[1], d[2])

def sari_mi(renk):
    return renk[0] > 150 and renk[1] > 130 and renk[2] < 120

print("=== 1. Dondurme (90 derece saat yonu) ===")
doc, g = ac("1.pdf")
onceki = pymupdf.Rect(g["rect"])
print("     once: sol ust %s" % (kose_rengi(doc, (48, 48)),))
check("once sol ust SARI", sari_mi(kose_rengi(doc, (48, 48))))
boyut = doc.edit_image(0, g, "dondur", derece=90)
yeni = doc.images_on(0)[0]
print("     sonra kutu: %s (piksel %s)" % ([round(v,1) for v in yeni["rect"]], boyut))
check("en-boy takla atti", abs(yeni["rect"].width - onceki.height) < 2
      and abs(yeni["rect"].height - onceki.width) < 2,
      "-> %s vs %s" % (yeni["rect"], onceki))
# 90 saat yonu: sol ust kose SAG UST'e gider
sag_ust = (yeni["rect"].x1 - 6, yeni["rect"].y0 + 6)
print("     sonra sag ust %s" % (kose_rengi(doc, sag_ust),))
check("sari kose SAG UST'e gitti (saat yonu)", sari_mi(kose_rengi(doc, sag_ust)),
      "-> %s" % (kose_rengi(doc, sag_ust),))
check("metin korundu", "metin korunmali" in doc.doc.load_page(0).get_text("text").replace("\xa0"," "))
doc.close()

print()
print("=== 2. Aynalama ===")
doc, g = ac("2.pdf")
doc.edit_image(0, g, "aynala", yatay=True)
y = doc.images_on(0)[0]["rect"]
check("yatay aynada sari SAG USTe gitti", sari_mi(kose_rengi(doc, (y.x1-6, y.y0+6))),
      "-> %s" % (kose_rengi(doc, (y.x1-6, y.y0+6)),))
doc.close()

doc, g = ac("2b.pdf")
doc.edit_image(0, g, "aynala", yatay=False)
y = doc.images_on(0)[0]["rect"]
check("dikey aynada sari SOL ALTa gitti", sari_mi(kose_rengi(doc, (y.x0+6, y.y1-6))),
      "-> %s" % (kose_rengi(doc, (y.x0+6, y.y1-6)),))
doc.close()

print()
print("=== 3. Kirpma ===")
doc, g = ac("3.pdf")
onceki = pymupdf.Rect(g["rect"])
boyut = doc.edit_image(0, g, "kirp", oran=(0.5, 0.0, 1.0, 0.5))
yeni = doc.images_on(0)[0]
print("     kutu: %s -> %s (piksel %s)"
      % ([round(v,1) for v in onceki], [round(v,1) for v in yeni["rect"]], boyut))
check("kutu da kirpildi", abs(yeni["rect"].width - onceki.width/2) < 2
      and abs(yeni["rect"].height - onceki.height/2) < 2,
      "-> %s" % (yeni["rect"],))
check("piksel boyutu yarilandi", abs(boyut[0] - 80) < 3 and abs(boyut[1] - 50) < 3,
      "-> %s" % (boyut,))
check("kirpilan bolgede sari YOK (sag ust alindi)",
      not sari_mi(kose_rengi(doc, (yeni["rect"].x0+6, yeni["rect"].y0+6))),
      "-> %s" % (kose_rengi(doc, (yeni["rect"].x0+6, yeni["rect"].y0+6)),))
doc.close()

print()
print("=== 4. Gri tonlama ===")
doc, g = ac("4.pdf")
doc.edit_image(0, g, "gri")
y = doc.images_on(0)[0]["rect"]
renk = kose_rengi(doc, (y.x0+6, y.y0+6))
print("     sari kose gri sonrasi: %s" % (renk,))
check("kanallar esitlendi (gri)", max(renk) - min(renk) < 25, "-> %s" % (renk,))
doc.close()

print()
print("=== 5. Parlaklik / kontrast ===")
doc, g = ac("5.pdf")
y0 = doc.images_on(0)[0]["rect"]
once = kose_rengi(doc, (y0.x1-6, y0.y1-6))
doc.edit_image(0, g, "ayarla", parlaklik=0.3)
y = doc.images_on(0)[0]["rect"]
sonra = kose_rengi(doc, (y.x1-6, y.y1-6))
print("     mavi alan: %s -> %s" % (once, sonra))
check("parlaklik artti", sum(sonra) > sum(once) + 60,
      "-> %s vs %s" % (sonra, once))
doc.close()

print()
print("=== 6. Baska dosyayla degistirme ===")
doc, g = ac("6.pdf")
kutu = pymupdf.Rect(g["rect"])
boyut = doc.edit_image(0, g, "degistir", path=BASKA)
yeni = doc.images_on(0)[0]
print("     yeni piksel boyutu: %s" % (boyut,))
check("icerik degisti (80x80)", boyut == (80, 80), "-> %s" % (boyut,))
check("konum korundu", abs(yeni["rect"].x0 - kutu.x0) < 1
      and abs(yeni["rect"].width - kutu.width) < 1, "-> %s" % (yeni["rect"],))
doc.close()

print()
print("=== 7. Disa aktarma ===")
doc, g = ac("7.pdf")
hedef = os.path.join(TMP, "cikti.png")
doc.export_image(g, hedef)
check("dosya olustu", os.path.exists(hedef) and os.path.getsize(hedef) > 50,
      "-> %s" % (os.path.getsize(hedef) if os.path.exists(hedef) else "yok"))
doc.close()

print()
print("=== 8. Geri alma tek adim ===")
doc, g = ac("8.pdf")
once_boyut = (g["rect"].width, g["rect"].height)
doc.edit_image(0, g, "dondur", derece=90)
doc.undo()
sonra = doc.images_on(0)[0]["rect"]
check("geri alma eski hale dondurdu",
      abs(sonra.width - once_boyut[0]) < 1 and abs(sonra.height - once_boyut[1]) < 1,
      "-> %s vs %s" % ((sonra.width, sonra.height), once_boyut))
doc.close()

print()
print("=== 9. Hatali girdiler ===")
doc, g = ac("9.pdf")
for islem, sec in (("dondur", {"derece": 45}), ("kirp", {"oran": (0.5,0.5,0.5,0.5)}),
                   ("bilinmeyen", {}), ("degistir", {"path": None})):
    try:
        doc.edit_image(0, g, islem, **sec)
        check("%s hatasi yakalandi" % islem, False, "-> hata vermedi")
    except Exception:
        check("%s hatasi yakalandi" % islem, True)
doc.close()

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("GORSEL DUZENLEME TAMAM")

print()
print("=== 10. ARAYUZ: sag tik menusu ve islemler ===")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PySide6.QtWidgets import QApplication
from pdfstudio.mainwindow import MainWindow
from pdfstudio.pageview import Tool

app = QApplication.instance() or QApplication([])
p = os.path.join(TMP, "ui.pdf"); build(p)
win = MainWindow()
win._error = lambda m: (_ for _ in ()).throw(RuntimeError(m))
win.load(p)
win.set_tool(Tool.IMAGE_EDIT)
win.on_image_picked(pymupdf.Point(100, 90))
check("görsel seçildi", win._selected_image is not None)

onceki = pymupdf.Rect(win._selected_image["rect"])
win._image_op("dondur", derece=90)
yeni = win.model.images_on(0)[0]["rect"]
check("menüden döndürme çalıştı",
      abs(yeni.width - onceki.height) < 2, "-> %s vs %s" % (yeni, onceki))
check("seçim korundu", win._selected_image is not None
      and win.view.image_rect is not None)

win._image_op("aynala", yatay=True)
check("aynalama çalıştı", win._selected_image is not None)

win._image_op("gri")
check("gri tonlama çalıştı", win._selected_image is not None)

win._image_op("ayarla", parlaklik=0.2, kontrast=0.1)
check("parlaklık ayarı çalıştı", win._selected_image is not None)

# Kirpma akisi: secim -> oran -> uygula
kutu = pymupdf.Rect(win._selected_image["rect"])
win.start_image_crop()
check("kırpma modu açıldı", win.view._crop_mode is True)
ic_alan = pymupdf.Rect(kutu.x0 + kutu.width * 0.25, kutu.y0 + kutu.height * 0.25,
                       kutu.x0 + kutu.width * 0.75, kutu.y0 + kutu.height * 0.75)
win.on_image_cropped(ic_alan)
sonra = win.model.images_on(0)[0]["rect"]
check("kırpma uygulandı", abs(sonra.width - kutu.width * 0.5) < 3,
      "-> %.1f vs %.1f" % (sonra.width, kutu.width * 0.5))

# Gorselin disinda kirpma reddedilmeli
adet_once = len(win.model.images_on(0))
win.on_image_cropped(pymupdf.Rect(5, 5, 20, 20))
check("görsel dışında kırpma reddedildi",
      len(win.model.images_on(0)) == adet_once)

# Degistirme ve disa aktarma
win._image_op("degistir", path=BASKA)
check("değiştirme çalıştı", win._selected_image is not None)
hedef = os.path.join(TMP, "ui-cikti.png")
win._selected_image = win.model.images_on(0)[0]
win.model.export_image(win._selected_image, hedef)
check("dışa aktarma çalıştı", os.path.exists(hedef))

metin = win.model.doc.load_page(0).get_text("text").replace("\xa0", " ")
check("metin tüm işlemler boyunca korundu", "metin korunmali" in metin,
      "-> %r" % metin[:40])
win.model.dirty = False
win.close()

print()
print("=== 11. ARAYUZ: kucuk gorsel secimi ve tutamaclar ===")
from PySide6.QtCore import QPointF

# Buyuk gorselin kosesinin HEMEN yanina kucuk bir ikon koyuyoruz:
# eskiden tutamacin gorunmez tiklama alani (cizilenin iki kati) bu ikonu
# yutuyordu ve ikon hic secilemiyordu.
kucuk_pdf = os.path.join(TMP, "kucuk.pdf")
d = pymupdf.open(); pg = d.new_page(width=420, height=320)
pg.insert_image(pymupdf.Rect(40, 40, 200, 140), filename=KAYNAK)
pg.insert_image(pymupdf.Rect(206, 146, 226, 166), filename=BASKA)   # 20x20 ikon
d.save(kucuk_pdf); d.close()

win2 = MainWindow()
win2._error = lambda m: (_ for _ in ()).throw(RuntimeError(m))
win2.load(kucuk_pdf)
win2.set_tool(Tool.IMAGE_EDIT)

win2.on_image_picked(pymupdf.Point(120, 90))          # once buyuk gorsel
check("büyük görsel seçildi", win2._selected_image is not None
      and win2._selected_image["rect"].width > 100)

# Buyuk gorselin sag-alt kosesinden 8 EKRAN pikseli oteye tikla. Eskiden
# tiklama alani her yone 9 piksel uzaniyordu (cizilen tutamacin iki kati),
# bu yuzden burasi tutamac sayilip yanindaki ikon secilemiyordu.
kose = win2.view._img_scene_rect().bottomRight()
nokta = QPointF(kose.x() + 8.0, kose.y() + 8.0)
bulunan = win2.view._handle_at(nokta)
check("köşenin 8 piksel yanı artık tutamaç sayılmıyor", bulunan is None,
      "-> %s" % (bulunan,))

# Tutamacin kendisi hala yakalanabiliyor olmali.
check("köşenin tam üstü hâlâ tutamaç",
      win2.view._handle_at(QPointF(kose.x(), kose.y())) == "sag_alt")

win2.on_image_picked(pymupdf.Point(216, 156))
secili = win2._selected_image
check("küçük ikon seçilebildi", secili is not None
      and abs(secili["rect"].width - 20) < 2,
      "-> %s" % (None if not secili else
                 tuple(round(v) for v in secili["rect"]),))

# Kucuk ikon secildiginde tutamaclar icini tamamen kaplamamali:
# aksi halde ikonu tasimak mumkun olmuyor.
r = win2.view._img_scene_rect()
boy = win2.view._handle_size(r)
check("küçük görselde tutamaç küçüldü", boy < win2.view.HANDLE,
      "-> %.1f (HANDLE=%.1f)" % (boy, win2.view.HANDLE))
merkez = QPointF(r.center().x(), r.center().y())
check("küçük görselin ortası taşımak için tıklanabilir",
      win2.view._handle_at(merkez) is None)

win2.model.dirty = False
win2.close()

print()
print("=" * 62)
if fails:
    print("SON DURUM BASARISIZ (%d): %s" % (len(fails), ", ".join(fails))); sys.exit(1)
print("GORSEL DUZENLEME ARAYUZU TAMAM")
