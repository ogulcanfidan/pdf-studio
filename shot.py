"""Arayuzu ekransiz calistirip PNG'ye cekerek gorsel dogrulama yapar."""
import os
import sys
import tempfile

# PDFSTUDIO_REAL=1 ile gercek Windows platformunda calistir (fontlar gorunsun).
if not os.environ.get("PDFSTUDIO_REAL"):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pdfstudio.mainwindow import MainWindow  # noqa: E402
from pdfstudio.pageview import Tool  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-shot-")
src = os.path.join(TMP, "ornek.pdf")

# Gercekci bir ornek belge: baslik, paragraflar, tablo cizgileri, form alani.
doc = pymupdf.open()
for n in range(4):
    page = doc.new_page()
    page.insert_htmlbox(
        pymupdf.Rect(60, 60, 540, 120),
        "Yıllık Faaliyet Raporu %d. Bölüm" % (n + 1),
        css="* {font-size:22px;font-family:sans-serif;font-weight:bold;"
            "color:#1a3a6b;}")
    page.insert_htmlbox(
        pymupdf.Rect(60, 130, 540, 300),
        "Bu belge PDF Studio'nun düzenleme yeteneklerini göstermek için "
        "hazırlanmıştır. Türkçe karakterler: ğ ü ş i ö ç Ğ Ü Ş İ Ö Ç. "
        "Metni düzenle aracıyla bu paragrafın üzerine tıklayıp içeriği "
        "değiştirebilir, vurgulama aracıyla satırları işaretleyebilirsin.",
        css="* {font-size:12px;font-family:sans-serif;line-height:1.6;"
            "color:#222;}")
    page.draw_rect(pymupdf.Rect(60, 330, 540, 430), color=(0.72, 0.75, 0.8),
                   width=1)
    for i in range(1, 4):
        y = 330 + i * 25
        page.draw_line(pymupdf.Point(60, y), pymupdf.Point(540, y),
                       color=(0.85, 0.87, 0.9), width=0.7)
    page.insert_htmlbox(
        pymupdf.Rect(70, 335, 530, 355), "Kalem · Tutar · Oran",
        css="* {font-size:11px;font-family:sans-serif;color:#444;}")

widget = pymupdf.Widget()
widget.rect = pymupdf.Rect(60, 470, 320, 495)
widget.field_name = "onaylayan"
widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
widget.field_value = ""
doc.load_page(0).add_widget(widget)

widget2 = pymupdf.Widget()
widget2.rect = pymupdf.Rect(60, 510, 80, 530)
widget2.field_name = "kontrol_edildi"
widget2.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
widget2.field_value = False
doc.load_page(0).add_widget(widget2)

doc.save(src)
doc.close()

app = QApplication([])
win = MainWindow()
win.resize(1400, 900)
win.show()
win.load(src)

# Kucuk resimlerin uretilmesi icin olay dongusunu birkac tur cevir.
for _ in range(200):
    app.processEvents()

# Birkac duzenleme uygula ki ekranda gorunsun.
win.model.markup(0, pymupdf.Rect(60, 150, 540, 175), "highlight", (1, 0.85, 0.2))
win.model.add_rect(0, pymupdf.Rect(60, 330, 540, 430), (0.1, 0.5, 0.9), 2.0)
win.model.insert_textbox(0, pymupdf.Rect(350, 460, 540, 500),
                         "Onaylandı ✓", 14, (0.1, 0.55, 0.2), bold=True)
win.model.watermark("TASLAK", 60, 0.13, (0.35, 0.45, 0.7), 45)
win.set_tool(Tool.TEXT_EDIT)
win._after_change(rebuild_thumbs=True)

for _ in range(200):
    app.processEvents()

from pdfstudio.branding import brand_pixmap
brand_pixmap(256).save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fmj-simge.png"))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arayuz-gercek.png" if os.environ.get("PDFSTUDIO_REAL") else "arayuz.png")
win.grab().save(out)
print("ekran goruntusu:", out)
print("sayfa sayisi   :", win.model.page_count)
print("form alanlari  :", win.forms.table.rowCount())
print("kucuk resimler :", win.thumbs.count())
print("baslik         :", win.windowTitle())
