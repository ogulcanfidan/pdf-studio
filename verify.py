"""Supheli uc davranisi dogrudan olcer: geri alma, baslik/dirty, form degeri."""
import faulthandler
import os
import sys
import tempfile

# Takilma olursa 25 saniye sonra yigini bas ve cik.
faulthandler.dump_traceback_later(25, exit=True)

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pymupdf  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pdfstudio.mainwindow import MainWindow  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-verify-")
src = os.path.join(TMP, "s.pdf")
d = pymupdf.open()
for i in range(3):
    p = d.new_page()
    p.insert_text((72, 100), "SAYFA-%d" % (i + 1), fontsize=20)
d.save(src)
d.close()

app = QApplication([])
win = MainWindow()


def _raise(message):
    """Ekransiz testte modal hata kutusu asili kalmasin - istisnaya cevir."""
    raise RuntimeError("UI hata diyalogu: %s" % message)


win._error = _raise
win.load(src)


def order():
    return [win.model.doc.load_page(i).get_text("text").strip()
            for i in range(win.model.page_count)]


print("--- 1. geri alma sayfa sirasini geri getiriyor mu ---")
start = order()
print("baslangic      :", start)
win.on_page_moved(0, 2)
moved = order()
print("tasima sonrasi :", moved)
win.on_undo()
undone = order()
print("geri al sonrasi:", undone)
win.on_redo()
redone = order()
print("yinele sonrasi :", redone)
print("SONUC: geri alma %s | yineleme %s"
      % ("DOGRU" if undone == start else "HATALI",
         "DOGRU" if redone == moved else "HATALI"))

print()
print("--- 2. baslik / dirty akisi (gercek save handler) ---")
win.load(src)
print("yukleme sonrasi:", win.windowTitle())
win.on_rotate(90)
after_edit = win.windowTitle()
print("degisiklik sonr:", after_edit)
win.on_save()
after_save = win.windowTitle()
print("on_save() sonra:", after_save)
print("SONUC: %s" % ("DOGRU" if after_edit.startswith("*")
                     and not after_save.startswith("*") else "HATALI"))

print()
print("--- 3. form degeri diske yaziliyor mu ---")
fp = os.path.join(TMP, "f.pdf")
d = pymupdf.open()
p = d.new_page()
w = pymupdf.Widget()
w.rect = pymupdf.Rect(72, 120, 300, 145)
w.field_name = "ad"
w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
w.field_value = ""
p.add_widget(w)
d.save(fp)
d.close()

win.load(fp)
win.on_field_changed(0, "ad", "Oğulcan Fidan")
in_memory = {wid.field_name: wid.field_value for _, wid in win.model.form_fields()}
print("bellekte       :", in_memory)

saved = os.path.join(TMP, "f-dolu.pdf")
win.model.save(saved)
reopened = pymupdf.open(saved)
on_disk = {wid.field_name: wid.field_value
           for wid in reopened.load_page(0).widgets()}
reopened.close()
print("diskten okunan :", on_disk)
print("SONUC: %s" % ("DOGRU" if on_disk.get("ad") == "Oğulcan Fidan"
                     else "HATALI"))
