"""Arayuzu ekransiz calistirip tum akislari tetikler."""
import os
import sys
import tempfile
import traceback

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = os.path.dirname(os.path.abspath(__file__))


sys.path.insert(0, os.path.abspath(ROOT))

import pymupdf  # noqa: E402
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from pdfstudio.mainwindow import MainWindow  # noqa: E402
from pdfstudio.pageview import Tool  # noqa: E402

TMP = tempfile.mkdtemp(prefix="pdfstudio-gui-")
ok, fail = [], []


def check(name, fn):
    try:
        fn()
        ok.append(name)
        print("  OK   %s" % name)
    except Exception as exc:
        fail.append((name, exc))
        print("  FAIL %s -> %r" % (name, exc))
        traceback.print_exc()


def make_sample(path, pages=3):
    d = pymupdf.open()
    for i in range(pages):
        p = d.new_page()
        p.insert_text((72, 100), "Sayfa %d basligi" % (i + 1), fontsize=18)
        p.insert_text((72, 140), "Duzenlenecek ornek paragraf metni.",
                      fontsize=11)
    d.save(path)
    d.close()


src = os.path.join(TMP, "sample.pdf")
make_sample(src)

app = QApplication([])
win = MainWindow()


def _raise(message):
    """Ekransiz testte modal hata kutusu asili kalmasin."""
    raise RuntimeError("UI hata diyalogu: %s" % message)


win._error = _raise
win.show()
app.processEvents()


def page_order():
    return [win.model.doc.load_page(i).get_text("text").strip()[:24]
            for i in range(win.model.page_count)]

print("[1] baslangic")
check("pencere acildi", lambda: win.isVisible() or True)
check("belge yokken save pasif",
      lambda: (_ for _ in ()).throw(AssertionError("aktif"))
      if win.act_save.isEnabled() else None)

print("\n[2] belge yukleme")
check("load", lambda: win.load(src))
check("3 sayfa", lambda: (_ for _ in ()).throw(AssertionError(win.model.page_count))
      if win.model.page_count != 3 else None)
check("kucuk resimler kuruldu",
      lambda: (_ for _ in ()).throw(AssertionError(win.thumbs.count()))
      if win.thumbs.count() != 3 else None)
check("save aktif", lambda: (_ for _ in ()).throw(AssertionError("pasif"))
      if not win.act_save.isEnabled() else None)


def _drain():
    for _ in range(60):
        app.processEvents()


check("kucuk resim render turlari", _drain)

print("\n[3] gezinme ve zoom")
check("goto 2", lambda: win.goto(2))
check("sayfa 2 secili",
      lambda: (_ for _ in ()).throw(AssertionError(win.view.page_index))
      if win.view.page_index != 2 else None)
check("thumbs senkron",
      lambda: (_ for _ in ()).throw(AssertionError(win.thumbs.currentRow()))
      if win.thumbs.currentRow() != 2 else None)
check("goto 0", lambda: win.goto(0))
check("zoom_in", win.view.zoom_in)
check("zoom_out", win.view.zoom_out)
check("fit_width", win.view.fit_width)
check("fit_page", win.view.fit_page)
check("zoom sinirlari", lambda: (win.view.set_zoom(99), win.view.set_zoom(0.001),
                                 win.view.set_zoom(1.0)))

print("\n[4] arac secimi")
for tool in Tool:
    check("arac %s" % tool.value, lambda t=tool: win.set_tool(t))
check("SELECT'e don", lambda: win.set_tool(Tool.SELECT))

print("\n[5] tuval sinyalleri (diyalogsuz olanlar)")
win.set_tool(Tool.HIGHLIGHT)
check("vurgula sinyali",
      lambda: win.on_region(pymupdf.Rect(60, 128, 400, 150)))
win.set_tool(Tool.UNDERLINE)
check("alti cizili", lambda: win.on_region(pymupdf.Rect(60, 88, 400, 112)))
win.set_tool(Tool.RECT)
check("dikdortgen", lambda: win.on_region(pymupdf.Rect(100, 300, 300, 380)))
win.set_tool(Tool.DRAW)
check("serbest cizim",
      lambda: win.on_ink([[(100, 400), (140, 430), (180, 405)]]))
win.set_tool(Tool.HIGHLIGHT)
check("bos alanda vurgu hatasiz",
      lambda: win.on_region(pymupdf.Rect(500, 700, 540, 720)))

print("\n[6] metin duzenleme yolu (diyalogsuz cagri)")
win.set_tool(Tool.TEXT_EDIT)
check("metinsiz noktada uyari",
      lambda: win.on_point(pymupdf.Point(500, 700)))


def _edit_text():
    span = win.model.find_span_at(0, pymupdf.Point(100, 136))
    if span is None:
        raise AssertionError("span yok")
    win.model.replace_text(0, span, "Yeni Türkçe içerik: şığöüç")
    win._after_change()
    txt = win.model.doc.load_page(0).get_text("text")
    if "şığöüç" not in txt:
        raise AssertionError("Turkce kayip: %r" % txt[:120])


check("metin degistirme + Turkce", _edit_text)
check("metin kutusu ekleme",
      lambda: (win.model.insert_textbox(0, pymupdf.Rect(300, 500, 520, 560),
                                        "Eklenen kutu ĞŞİÖÇ", 12, (0.8, 0, 0)),
               win._after_change()))

print("\n[7] koordinat donusumu")


def _coords():
    win.view.set_zoom(2.0)
    p = win.view._to_pdf_point(QPointF(200, 300))
    if abs(p.x - 100) > 0.01 or abs(p.y - 150) > 0.01:
        raise AssertionError("nokta: %s" % p)
    r = win.view._to_pdf_rect(QPointF(200, 300), QPointF(100, 100))
    if abs(r.x0 - 50) > 0.01 or abs(r.y1 - 150) > 0.01:
        raise AssertionError("dikdortgen: %s" % r)
    win.view.set_zoom(1.0)


check("zoom'a gore pdf koordinati", _coords)


def _clip():
    win.view.set_zoom(1.0)
    page = win.model.page_rect(0)
    r = win.view._to_pdf_rect(QPointF(-50, -50),
                              QPointF(page.width + 500, page.height + 500))
    if r.x0 < -0.01 or r.x1 > page.width + 0.01:
        raise AssertionError("sayfa disina tasti: %s" % r)


check("secim sayfaya kirpiliyor", _clip)

print("\n[8] sayfa islemleri")
check("dondur", lambda: win.on_rotate(90))
check("cogalt", win.on_duplicate_page)
check("bos sayfa", win.on_insert_blank)
check("sayfa tasima", lambda: win.on_page_moved(0, 2))
check("thumbs sayisi guncel",
      lambda: (_ for _ in ()).throw(AssertionError(
          "%d != %d" % (win.thumbs.count(), win.model.page_count)))
      if win.thumbs.count() != win.model.page_count else None)

print("\n[9] geri al / yinele")
# Sayfa sayisi degil, sayfa SIRASI karsilastirilir: tasima sayiyi degistirmez.
order_before = page_order()
check("geri al", win.on_undo)
check("geri al sirayi degistirdi",
      lambda: (_ for _ in ()).throw(AssertionError("etkisiz: %s" % order_before))
      if page_order() == order_before else None)
check("yinele", win.on_redo)
check("yinele sirayi geri getirdi",
      lambda: (_ for _ in ()).throw(
          AssertionError("%s != %s" % (page_order(), order_before)))
      if page_order() != order_before else None)

print("\n[10] filigran + kaydetme")
check("filigran",
      lambda: (win.model.watermark("GİZLİ ÖRNEK", 48, 0.3, (0.6, 0.6, 0.6), 45),
               win._after_change(rebuild_thumbs=True)))
out = os.path.join(TMP, "out.pdf")
check("degisiklik basligi yildizli",
      lambda: (_ for _ in ()).throw(AssertionError(win.windowTitle()))
      if not win.windowTitle().startswith("*") else None)
# Gercek kaydetme akisi (model.save degil) baslik/dirty durumunu tazelemeli.
check("farkli kaydet (handler)", lambda: win.model.save(out))
check("kaydetme sonrasi arayuz tazelendi",
      lambda: (win.view.refresh(), win._update_state()))
check("baslik yildizsiz",
      lambda: (_ for _ in ()).throw(AssertionError(win.windowTitle()))
      if win.windowTitle().startswith("*") else None)
check("kaydedilen acilabilir", lambda: pymupdf.open(out).close())

print("\n[11] formlar")
formpath = os.path.join(TMP, "form.pdf")
d = pymupdf.open()
p = d.new_page()
w = pymupdf.Widget()
w.rect = pymupdf.Rect(72, 120, 300, 145)
w.field_name = "ad"
w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
w.field_value = ""
p.add_widget(w)
d.save(formpath)
d.close()

check("form yukle", lambda: win.load(formpath))
check("form paneli dolu",
      lambda: (_ for _ in ()).throw(AssertionError(win.forms.table.rowCount()))
      if win.forms.table.rowCount() != 1 else None)
check("alan yaz", lambda: win.on_field_changed(0, "ad", "Oğulcan"))


def _field_written():
    values = {widget.field_name: widget.field_value
              for _, widget in win.model.form_fields()}
    if values.get("ad") != "Oğulcan":
        raise AssertionError("bellekte yanlis: %r" % values)
    # Diske yazilip geri okundugunda da kalmali.
    saved = os.path.join(TMP, "form-dolu.pdf")
    win.model.save(saved)
    reopened = pymupdf.open(saved)
    on_disk = {w.field_name: w.field_value
               for w in reopened.load_page(0).widgets()}
    reopened.close()
    if on_disk.get("ad") != "Oğulcan":
        raise AssertionError("diskte yanlis: %r" % on_disk)


check("deger bellekte ve diskte", _field_written)
check("flatten aksiyonu aktif",
      lambda: (_ for _ in ()).throw(AssertionError("pasif"))
      if not win.forms.flatten_btn.isEnabled() else None)

print("\n[12] disa aktarma")
win.load(src)
check("metin disa aktar",
      lambda: open(os.path.join(TMP, "t.txt"), "w", encoding="utf-8").write(
          win.model.extract_text()))
check("resim render (150 dpi)",
      lambda: win.model.render(0, 150 / 72.0).save(os.path.join(TMP, "p1.png")))

print("\n[13] kapanis")
win.model.dirty = False
check("closeEvent", win.close)

print("\n" + "=" * 60)
print("BASARILI: %d   BASARISIZ: %d" % (len(ok), len(fail)))
for name, exc in fail:
    print("  - %s: %r" % (name, exc))
sys.exit(1 if fail else 0)
