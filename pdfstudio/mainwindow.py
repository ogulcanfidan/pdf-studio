"""Ana pencere: menuler, arac cubugu, paneller ve tum eylem baglantilari."""

from __future__ import annotations

import os

import pymupdf
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QKeySequence
from PySide6.QtWidgets import (QApplication, QDockWidget, QFileDialog,
                               QMenu,
                               QHBoxLayout, QInputDialog, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QSpinBox, QToolBar,
                               QWidget)

from . import APP_NAME, VENDOR, __version__
from . import convert
from .branding import (about_html, app_icon, brand_pixmap,
                       set_taskbar_identity)
from .i18n import (apply_buttons, available_languages,
                   current_language, is_rtl, load_language,
                   set_language, tr)
from .dialogs import (ColorButton, EditTextDialog, ExportImagesDialog,
                      ImageAdjustDialog, TextDialog, WatermarkDialog)
from .model import DocumentError, NeighborTextLost, PdfDocument
from .pageview import TOOL_HINTS, PageView, Tool
from .panels import FormPanel, ThumbnailBar

def pdf_filter():
    """Dosya diyalogu filtresi - gecerli dile gore."""
    return tr("PDF dosyaları (*.pdf);;Tüm dosyalar (*)")


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.model = PdfDocument()
        self._style = None      # stil kopyalamada alinan bicim
        self._selected_image = None   # gorsel araciyla secilen gorsel
        self._selected_drawing = None # ... ya da secilen vektor cizim
        self.restart_language = None   # dil degisince yeniden ac
        self.reopen_path = None

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(1360, 900)
        self.setAcceptDrops(True)

        self.view = PageView(self)
        self.view.set_model(self.model)
        self.setCentralWidget(self.view)

        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbars()
        self._build_statusbar()
        self._connect()
        self._update_state()

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------

    def _build_docks(self) -> None:
        self.thumbs = ThumbnailBar(self)
        self.thumbs.set_model(self.model)
        dock = QDockWidget(tr("Sayfalar"), self)
        dock.setWidget(self.thumbs)
        dock.setMinimumWidth(190)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.thumb_dock = dock

        self.forms = FormPanel(self)
        self.forms.set_model(self.model)
        fdock = QDockWidget(tr("Form alanları"), self)
        fdock.setWidget(self.forms)
        fdock.setMinimumWidth(280)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, fdock)
        self.form_dock = fdock

    def _act(self, text, slot, shortcut=None, tip=None, checkable=False):
        action = QAction(text, self)
        action.triggered.connect(slot)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if tip:
            action.setStatusTip(tip)
        action.setCheckable(checkable)
        return action

    def _build_actions(self) -> None:
        a = self._act
        self.act_new = a(tr("&Yeni boş PDF"), self.on_new, "Ctrl+N")
        self.act_open = a(tr("&Aç…"), self.on_open, "Ctrl+O")
        self.act_save = a(tr("&Kaydet"), self.on_save, "Ctrl+S")
        self.act_save_as = a(tr("Farklı k&aydet…"), self.on_save_as, "Ctrl+Shift+S")
        self.act_compress = a(tr("Sıkıştırarak kaydet…"), self.on_save_compressed)
        self.act_export_text = a(tr("Metin (.txt)…"), self.on_export_text)
        self.act_export_img = a(tr("Resim (PNG / JPEG)…"), self.on_export_images)
        self.act_export_html = a(tr("Web sayfası (.html)…"), self.on_export_html)
        self.act_export_svg = a(tr("Vektör (.svg)…"), self.on_export_svg)
        self.act_export_docx = a(tr("Word belgesi (.docx)…"), self.on_export_docx)
        self.act_import = a(tr("PDF'e dönüştürerek aç…"), self.on_import,
                            "Ctrl+I",
                            "Resim, Word, metin, HTML, EPUB gibi dosyaları "
                            "PDF'e çevirip açar")
        self.act_quit = a(tr("Çı&kış"), self.close, "Ctrl+Q")

        self.act_undo = a(tr("&Geri al"), self.on_undo, "Ctrl+Z")
        self.act_redo = a(tr("&Yinele"), self.on_redo, "Ctrl+Y")
        self.act_find = a(tr("&Ara…"), self.on_find, "Ctrl+F")

        self.act_rot_left = a(tr("Sola döndür"), lambda: self.on_rotate(-90), "Ctrl+Left")
        self.act_rot_right = a(tr("Sağa döndür"), lambda: self.on_rotate(90), "Ctrl+Right")
        self.act_del_page = a(tr("Sayfayı sil"), self.on_delete_pages, "Ctrl+Delete")
        self.act_dup_page = a(tr("Sayfayı çoğalt"), self.on_duplicate_page)
        self.act_blank = a(tr("Boş sayfa ekle"), self.on_insert_blank)
        self.act_merge = a(tr("PDF ekle (birleştir)…"), self.on_merge)
        self.act_extract = a(tr("Seçili sayfaları çıkar…"), self.on_extract)

        self.act_watermark = a(tr("Filigran ekle…"), self.on_watermark)
        self.act_flatten = a(tr("Formu sabitle"), self.on_flatten)

        self.act_zoom_in = a(tr("Yakınlaştır"), self.view.zoom_in, "Ctrl++")
        self.act_zoom_out = a(tr("Uzaklaştır"), self.view.zoom_out, "Ctrl+-")
        self.act_fit_width = a(tr("Genişliğe sığdır"), self.view.fit_width, "Ctrl+1")
        self.act_fit_page = a(tr("Sayfaya sığdır"), self.view.fit_page, "Ctrl+0")
        self.act_prev = a(tr("Önceki sayfa"), lambda: self.goto(self.view.page_index - 1),
                          "PgUp")
        self.act_next = a(tr("Sonraki sayfa"), lambda: self.goto(self.view.page_index + 1),
                          "PgDown")

        self.act_about = a(tr("Hakkında"), self.on_about)
        self.act_shortcuts = a(tr("Klavye kısayolları"), self.on_shortcuts, "F1")

        # Araclar - tek secim
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_actions = {}
        tools = [
            (Tool.SELECT, tr("Seç / Kaydır"), "V"),
            (Tool.TEXT_EDIT, tr("Metni düzenle"), "E"),
            (Tool.TEXT_MOVE, tr("Taşı"), "M"),
            (Tool.STYLE, tr("Stil kopyala"), "P"),
            (Tool.IMAGE_EDIT, tr("Görsel düzenle"), "G"),
            (Tool.TEXT_ADD, tr("Metin ekle"), "T"),
            (Tool.HIGHLIGHT, tr("Vurgula"), "H"),
            (Tool.UNDERLINE, tr("Altını çiz"), "U"),
            (Tool.STRIKEOUT, tr("Üstünü çiz"), "S"),
            (Tool.DRAW, tr("Serbest çizim"), "D"),
            (Tool.RECT, tr("Dikdörtgen"), "R"),
            (Tool.IMAGE, tr("Resim / İmza"), "I"),
            (Tool.REDACT, tr("Karart"), "K"),
        ]
        for tool, label, key in tools:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setShortcut(QKeySequence(key))
            action.setStatusTip(TOOL_HINTS[tool])
            action.triggered.connect(lambda _c, t=tool: self.set_tool(t))
            self.tool_group.addAction(action)
            self.tool_actions[tool] = action
        self.tool_actions[Tool.SELECT].setChecked(True)

    def _build_menus(self) -> None:
        bar = self.menuBar()

        m = bar.addMenu(tr("&Dosya"))
        m.addActions([self.act_new, self.act_open, self.act_import])
        m.addSeparator()
        m.addActions([self.act_save, self.act_save_as, self.act_compress])
        m.addSeparator()
        export = m.addMenu(tr("PDF'i dönüştür"))
        export.addActions([self.act_export_img, self.act_export_docx,
                           self.act_export_html, self.act_export_svg,
                           self.act_export_text])
        m.addSeparator()
        m.addAction(self.act_quit)

        m = bar.addMenu(tr("Dü&zen"))
        m.addActions([self.act_undo, self.act_redo])
        m.addSeparator()
        m.addAction(self.act_find)

        m = bar.addMenu(tr("&Sayfa"))
        m.addActions([self.act_rot_left, self.act_rot_right])
        m.addSeparator()
        m.addActions([self.act_dup_page, self.act_blank, self.act_del_page])
        m.addSeparator()
        m.addActions([self.act_merge, self.act_extract])

        m = bar.addMenu(tr("&Araçlar"))
        for tool in self.tool_actions:
            m.addAction(self.tool_actions[tool])
        m.addSeparator()
        m.addActions([self.act_watermark, self.act_flatten])

        m = bar.addMenu(tr("&Görünüm"))
        m.addActions([self.act_zoom_in, self.act_zoom_out,
                      self.act_fit_width, self.act_fit_page])
        m.addSeparator()
        m.addActions([self.act_prev, self.act_next])
        m.addSeparator()
        m.addAction(self.thumb_dock.toggleViewAction())
        m.addAction(self.form_dock.toggleViewAction())

        m = bar.addMenu(tr("&Dil"))
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)
        for code, ad in available_languages():
            action = QAction(ad, self)
            action.setCheckable(True)
            action.setChecked(code == current_language())
            action.triggered.connect(lambda _c, k=code: self.on_language(k))
            self.lang_group.addAction(action)
            m.addAction(action)

        m = bar.addMenu(tr("&Yardım"))
        m.addActions([self.act_shortcuts, self.act_about])

    def _build_toolbars(self) -> None:
        tb = QToolBar(tr("Dosya"), self)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        tb.addActions([self.act_open, self.act_save])
        tb.addSeparator()
        tb.addActions([self.act_undo, self.act_redo])
        self.addToolBar(tb)

        tools = QToolBar(tr("Araçlar"), self)
        tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        for action in self.tool_actions.values():
            tools.addAction(action)
        tools.addSeparator()

        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(8, 0, 4, 0)
        row.addWidget(QLabel(tr("Renk:")))
        self.color_btn = ColorButton(QColor("#ffd400"))
        row.addWidget(self.color_btn)
        row.addWidget(QLabel(tr("Kalınlık:")))
        self.width_box = QSpinBox()
        self.width_box.setRange(1, 20)
        self.width_box.setValue(2)
        self.width_box.setSuffix(" pt")
        self.width_box.setMinimumWidth(78)  # deger + oklar sigsin
        row.addWidget(self.width_box)
        row.addSpacing(12)
        # Stil kopyalamada alinan bicim gorunur olsun - kullanici neyin
        # "elinde" oldugunu ve nasil birakacagini bilsin.
        self.style_label = QLabel("")
        self.style_label.setStyleSheet(
            "color:#4f46e5; font-weight:600; padding:0 6px;")
        row.addWidget(self.style_label)

        self.style_clear = QPushButton(tr("Stili bırak"))
        self.style_clear.setToolTip("Kopyalanan stili bırak (Esc)")
        self.style_clear.clicked.connect(self.clear_style)
        row.addWidget(self.style_clear)
        self._update_style_indicator()

        tools.addWidget(holder)

        # Uc arac cubugu tek satira sigmayip ">>" tasma menusune dusuyordu;
        # her birini kendi satirina aliyoruz.
        self.addToolBarBreak()
        self.addToolBar(tools)

        self.addToolBarBreak()
        view_bar = QToolBar(tr("Görünüm"), self)
        view_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        view_bar.addActions([self.act_zoom_out, self.act_zoom_in,
                             self.act_fit_width, self.act_fit_page])
        view_bar.addSeparator()
        view_bar.addActions([self.act_prev, self.act_next])
        self.addToolBar(view_bar)

    def _build_statusbar(self) -> None:
        self.page_label = QLabel("—")
        self.zoom_label = QLabel("—")
        self.hint_label = QLabel(TOOL_HINTS[Tool.SELECT])

        self.brand_label = QLabel(VENDOR)
        self.brand_label.setStyleSheet(
            "color:#6366f1; font-weight:600; padding:0 10px;")

        bar = self.statusBar()
        bar.addWidget(self.hint_label, 1)
        bar.addPermanentWidget(self.page_label)
        bar.addPermanentWidget(self.zoom_label)
        bar.addPermanentWidget(self.brand_label)

    def _connect(self) -> None:
        self.view.regionSelected.connect(self.on_region)
        self.view.pointClicked.connect(self.on_point)
        self.view.inkDrawn.connect(self.on_ink)
        self.view.annotDoubleClicked.connect(self.on_annot_click)
        self.view.regionMoved.connect(self.on_region_moved)
        self.view.imagePicked.connect(self.on_image_picked)
        self.view.imagePlaced.connect(self.on_image_placed)
        self.view.imageMenuRequested.connect(self.on_image_menu)
        self.view.cropSelected.connect(self.on_image_cropped)
        self.view.selectionChanged.connect(self.on_selection_changed)
        self.view.zoomChanged.connect(lambda _z: self._update_state())
        self.thumbs.pageSelected.connect(self.goto)
        self.thumbs.pageMoved.connect(self.on_page_moved)
        self.forms.fieldChanged.connect(self.on_field_changed)
        self.forms.flattenRequested.connect(self.on_flatten)

    # ------------------------------------------------------------------
    # yardimcilar
    # ------------------------------------------------------------------

    def clear_style(self) -> None:
        """Kopyalanan stili birak."""
        if self._style is None:
            return
        self._style = None
        self._update_style_indicator()
        self.statusBar().showMessage(tr("Stil bırakıldı."), 3000)

    def _update_style_indicator(self) -> None:
        etiket = getattr(self, "style_label", None)
        if etiket is None:
            return
        if self._style is None:
            etiket.setText("")
            self.style_clear.setVisible(False)
        else:
            etiket.setText("Stil: %s" % self._style.label())
            self.style_clear.setVisible(True)

    def set_tool(self, tool: Tool) -> None:
        # Stil aracindan cikinca alinan bicim unutulsun.
        if tool is not Tool.STYLE:
            self._style = None
            self._update_style_indicator()
        self.view.set_tool(tool)
        self.hint_label.setText(TOOL_HINTS[tool])

    def goto(self, index: int) -> None:
        if not self.model.is_open:
            return
        index = max(0, min(index, self.model.page_count - 1))
        self.view.set_page(index)
        if self.thumbs.currentRow() != index:
            self.thumbs.blockSignals(True)
            self.thumbs.setCurrentRow(index)
            self.thumbs.blockSignals(False)
        self._update_state()

    def _after_change(self, rebuild_thumbs: bool = False) -> None:
        """Belge degistikten sonra arayuzu tazele."""
        self.view.refresh()
        if rebuild_thumbs:
            self.thumbs.rebuild(self.view.page_index)
        else:
            self.thumbs.refresh_page(self.view.page_index)
        self.forms.reload()
        self._update_state()

    def _update_state(self) -> None:
        opened = self.model.is_open
        for action in (self.act_save, self.act_save_as, self.act_compress,
                       self.act_export_text, self.act_export_img,
                       self.act_export_html, self.act_export_svg,
                       self.act_export_docx,
                       self.act_rot_left, self.act_rot_right, self.act_del_page,
                       self.act_dup_page, self.act_blank, self.act_merge,
                       self.act_extract, self.act_watermark, self.act_find,
                       self.act_zoom_in, self.act_zoom_out, self.act_fit_width,
                       self.act_fit_page, self.act_prev, self.act_next):
            action.setEnabled(opened)
        for action in self.tool_actions.values():
            action.setEnabled(opened)

        self.act_undo.setEnabled(self.model.can_undo)
        self.act_redo.setEnabled(self.model.can_redo)
        self.act_flatten.setEnabled(opened and bool(self.model.form_fields())
                                    if opened else False)

        if opened:
            self.page_label.setText("Sayfa %d / %d"
                                    % (self.view.page_index + 1,
                                       self.model.page_count))
            self.zoom_label.setText("%%%d" % round(self.view.zoom * 100))
            name = os.path.basename(self.model.path) if self.model.path \
                else "Adsız.pdf"
            self.setWindowTitle("%s%s — %s"
                                % ("*" if self.model.dirty else "", name, APP_NAME))
        else:
            self.page_label.setText("—")
            self.zoom_label.setText("—")
            self.setWindowTitle(APP_NAME)

    def _error(self, message: str) -> None:
        box = QMessageBox(QMessageBox.Icon.Critical, APP_NAME, message,
                          QMessageBox.StandardButton.Ok, self)
        apply_buttons(box)
        box.exec()

    def _ask(self, message: str, buttons=None):
        """Evet/Hayir sorusu - dugmeleri cevrilmis olarak sor."""
        if buttons is None:
            buttons = (QMessageBox.StandardButton.Yes
                       | QMessageBox.StandardButton.No)
        box = QMessageBox(QMessageBox.Icon.Question, APP_NAME, message,
                          buttons, self)
        apply_buttons(box)
        box.exec()
        return box.standardButton(box.clickedButton())

    def _inform(self, message: str, icon=None) -> None:
        box = QMessageBox(icon or QMessageBox.Icon.Information, APP_NAME,
                          message, QMessageBox.StandardButton.Ok, self)
        box.setTextFormat(Qt.TextFormat.RichText)
        apply_buttons(box)
        box.exec()

    def _confirm_discard(self) -> bool:
        """Kaydedilmemis degisiklik varsa kullaniciya sor."""
        if not self.model.is_open or not self.model.dirty:
            return True
        choice = self._ask(
            tr("Kaydedilmemiş değişiklikler var. Kaydedilsin mi?"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if choice == QMessageBox.StandardButton.Cancel:
            return False
        if choice == QMessageBox.StandardButton.Save:
            return self.on_save()
        return True

    # ------------------------------------------------------------------
    # dosya
    # ------------------------------------------------------------------

    def on_new(self) -> None:
        if not self._confirm_discard():
            return
        self.model.new()
        self.view.set_page(0)
        self.view.fit_page()
        self._after_change(rebuild_thumbs=True)

    def on_open(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("PDF aç"), "", pdf_filter())
        if path:
            self.load(path)

    def load(self, path: str) -> None:
        try:
            self.model.open(path)
        except DocumentError:
            password, ok = QInputDialog.getText(
                self, APP_NAME, "Belge parola korumalı. Parolayı gir:")
            if not ok:
                return
            try:
                self.model.open(path, password)
            except Exception as exc:
                return self._error("Açılamadı: %s" % exc)
        except Exception as exc:
            return self._error("Açılamadı: %s" % exc)

        self.view.set_page(0)
        self.view.fit_width()
        self._after_change(rebuild_thumbs=True)
        self.statusBar().showMessage(
            "%s açıldı — %d sayfa" % (os.path.basename(path),
                                      self.model.page_count), 4000)

    def on_save(self) -> bool:
        if not self.model.is_open:
            return False
        if not self.model.path:
            return self.on_save_as()
        try:
            self.model.save()
        except Exception as exc:
            self._error("Kaydedilemedi: %s" % exc)
            return False
        self.view.refresh()
        self._update_state()
        self.statusBar().showMessage("Kaydedildi: %s" % self.model.path, 4000)
        return True

    def on_save_as(self) -> bool:
        if not self.model.is_open:
            return False
        suggested = self.model.path or "belge.pdf"
        path, _ = QFileDialog.getSaveFileName(self, tr("Farklı kaydet"), suggested,
                                              pdf_filter())
        if not path:
            return False
        try:
            self.model.save(path)
        except Exception as exc:
            self._error("Kaydedilemedi: %s" % exc)
            return False
        self.view.refresh()
        self._update_state()
        self.statusBar().showMessage("Kaydedildi: %s" % path, 4000)
        return True

    def on_save_compressed(self) -> None:
        if not self.model.is_open:
            return
        base = self.model.path or "belge.pdf"
        root, ext = os.path.splitext(base)
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Sıkıştırarak kaydet"), root + "-kucuk" + (ext or ".pdf"),
            pdf_filter())
        if not path:
            return
        before = os.path.getsize(self.model.path) if self.model.path \
            and os.path.exists(self.model.path) else None
        try:
            self.model.save(path, compress=True)
        except Exception as exc:
            return self._error("Kaydedilemedi: %s" % exc)
        after = os.path.getsize(path)
        if before:
            self.statusBar().showMessage(
                "Sıkıştırıldı: %.0f KB → %.0f KB (%%%.0f)"
                % (before / 1024, after / 1024,
                   100 - after * 100.0 / before), 6000)
        self.view.refresh()
        self._update_state()

    def on_export_text(self) -> None:
        if not self.model.is_open:
            return
        base = os.path.splitext(self.model.path or "belge")[0] + ".txt"
        path, _ = QFileDialog.getSaveFileName(self, "Metni kaydet", base,
                                              "Metin (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.model.extract_text())
        except Exception as exc:
            return self._error("Yazılamadı: %s" % exc)
        self.statusBar().showMessage("Metin kaydedildi: %s" % path, 4000)

    # --- bicim donusturme ------------------------------------------------

    def _suggest(self, ext: str) -> str:
        base = os.path.splitext(self.model.path or "belge")[0]
        return base + ext

    def _finish(self, result) -> None:
        """Donusum sonucunu kullaniciya bildir; sadakat kaybini gizleme."""
        if result.faithful:
            self.statusBar().showMessage("%s — %s"
                                         % (result.note, result.path), 7000)
        else:
            self._inform(
                
                "Dönüştürme tamamlandı.<br><br><b>%s</b><br><br>"
                "Kaydedildi: %s" % (result.note, result.path))

    def on_export_html(self) -> None:
        if not self.model.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "HTML olarak kaydet", self._suggest(".html"),
            "Web sayfası (*.html)")
        if not path:
            return
        try:
            self._finish(convert.to_html(self.model.doc, path))
        except Exception as exc:
            self._error("Dönüştürülemedi: %s" % exc)

    def on_export_svg(self) -> None:
        if not self.model.is_open:
            return
        folder = QFileDialog.getExistingDirectory(self, "SVG klasörü seç")
        if not folder:
            return
        stem = os.path.splitext(os.path.basename(self.model.path
                                                 or "sayfa"))[0]
        try:
            self._finish(convert.to_svg(self.model.doc, folder, stem=stem))
        except Exception as exc:
            self._error("Dönüştürülemedi: %s" % exc)

    def on_export_docx(self) -> None:
        if not self.model.is_open:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Word belgesi olarak kaydet", self._suggest(".docx"),
            "Word belgesi (*.docx)")
        if not path:
            return
        try:
            self._finish(convert.to_docx(self.model.doc, path))
        except convert.ConversionError as exc:
            self._error(str(exc))
        except Exception as exc:
            self._error("Dönüştürülemedi: %s" % exc)

    def on_import(self) -> None:
        """Baska bir bicimi PDF'e cevirip ac."""
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "PDF'e dönüştürülecek dosya", "", convert.import_filter())
        if not path:
            return

        target, _ = QFileDialog.getSaveFileName(
            self, "Oluşacak PDF nereye kaydedilsin?",
            os.path.splitext(path)[0] + ".pdf", pdf_filter())
        if not target:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = convert.any_to_pdf(path, target)
        except convert.ConversionError as exc:
            QApplication.restoreOverrideCursor()
            return self._error(str(exc))
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            return self._error("Dönüştürülemedi: %s" % exc)
        finally:
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

        self.load(target)
        self._finish(result)

    def on_export_images(self) -> None:
        if not self.model.is_open:
            return
        dialog = ExportImagesDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        opts = dialog.values()
        folder = QFileDialog.getExistingDirectory(self, tr("Kaydedilecek klasör"))
        if not folder:
            return

        zoom = opts["dpi"] / 72.0
        ext = "png" if opts["format"] == "png" else "jpg"
        pages = ([self.view.page_index] if opts["scope"] == "current"
                 else range(self.model.page_count))
        stem = os.path.splitext(os.path.basename(self.model.path or "sayfa"))[0]

        try:
            count = 0
            for index in pages:
                pix = self.model.render(index, zoom)
                pix.save(os.path.join(folder, "%s-%03d.%s"
                                      % (stem, index + 1, ext)))
                count += 1
        except Exception as exc:
            return self._error("Dışa aktarılamadı: %s" % exc)
        self.statusBar().showMessage("%d resim kaydedildi: %s" % (count, folder),
                                     5000)

    # ------------------------------------------------------------------
    # duzen
    # ------------------------------------------------------------------

    def on_undo(self) -> None:
        self.model.undo()
        self._after_change(rebuild_thumbs=True)

    def on_redo(self) -> None:
        self.model.redo()
        self._after_change(rebuild_thumbs=True)

    def on_find(self) -> None:
        if not self.model.is_open:
            return
        needle, ok = QInputDialog.getText(self, tr("Ara"), tr("Aranacak metin:"))
        if not ok or not needle.strip():
            return
        hits = self.model.search(needle.strip())
        if not hits:
            self.statusBar().showMessage("Bulunamadı: %s" % needle, 4000)
            return
        self.goto(hits[0][0])
        pages = sorted({p for p, _ in hits})
        self.statusBar().showMessage(
            "%d sonuç, %d sayfada. İlk sonuç: sayfa %d"
            % (len(hits), len(pages), hits[0][0] + 1), 6000)

    # ------------------------------------------------------------------
    # sayfa islemleri
    # ------------------------------------------------------------------

    def on_rotate(self, delta: int) -> None:
        rows = self.thumbs.selected_rows() or [self.view.page_index]
        for index in rows:
            self.model.rotate(index, delta)
        self._after_change(rebuild_thumbs=True)

    def on_delete_pages(self) -> None:
        rows = self.thumbs.selected_rows() or [self.view.page_index]
        if self._ask(
                "%d sayfa silinecek. Devam edilsin mi?" % len(rows)
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.model.delete_pages(rows)
        except DocumentError as exc:
            return self._error(str(exc))
        self.view.page_index = min(self.view.page_index,
                                   self.model.page_count - 1)
        self._after_change(rebuild_thumbs=True)

    def on_duplicate_page(self) -> None:
        self.model.duplicate_page(self.view.page_index)
        self._after_change(rebuild_thumbs=True)

    def on_insert_blank(self) -> None:
        self.model.insert_blank(self.view.page_index + 1)
        self._after_change(rebuild_thumbs=True)

    def on_merge(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Eklenecek PDF", "",
                                              pdf_filter())
        if not path:
            return
        try:
            added = self.model.append_pdf(path)
        except Exception as exc:
            return self._error("Eklenemedi: %s" % exc)
        self._after_change(rebuild_thumbs=True)
        self.statusBar().showMessage("%d sayfa eklendi" % added, 4000)

    def on_extract(self) -> None:
        rows = self.thumbs.selected_rows() or [self.view.page_index]
        path, _ = QFileDialog.getSaveFileName(self, "Seçili sayfaları kaydet",
                                              "secili-sayfalar.pdf", pdf_filter())
        if not path:
            return
        try:
            self.model.extract_pages(rows, path)
        except Exception as exc:
            return self._error("Çıkarılamadı: %s" % exc)
        self.statusBar().showMessage("%d sayfa kaydedildi: %s"
                                     % (len(rows), path), 5000)

    def on_page_moved(self, src: int, dst: int) -> None:
        try:
            self.model.move_page(src, dst)
        except Exception as exc:
            self._error("Taşınamadı: %s" % exc)
        self.view.set_page(dst)
        self._after_change(rebuild_thumbs=True)

    # ------------------------------------------------------------------
    # tuval etkilesimleri
    # ------------------------------------------------------------------

    def on_region(self, rect) -> None:
        tool = self.view.tool
        index = self.view.page_index
        color = self.color_btn.rgb()
        width = float(self.width_box.value())

        if tool is Tool.TEXT_ADD:
            dialog = TextDialog(self)
            if dialog.exec() != dialog.DialogCode.Accepted:
                return
            values = dialog.values()
            if not values["text"].strip():
                return
            self.model.insert_textbox(index, rect, values["text"],
                                      values["size"], values["color"],
                                      values["bold"])

        elif tool in (Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT):
            kind = {Tool.HIGHLIGHT: "highlight",
                    Tool.UNDERLINE: "underline",
                    Tool.STRIKEOUT: "strikeout"}[tool]
            if not self.model.markup(index, rect, kind, color):
                self.statusBar().showMessage(
                    tr("Seçilen alanda metin yok — işaretleme yapılmadı."), 4000)
                return

        elif tool is Tool.RECT:
            self.model.add_rect(index, rect, color, width)

        elif tool is Tool.IMAGE:
            path, _ = QFileDialog.getOpenFileName(
                self, tr("Resim seç"), "",
                "Resimler (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff)")
            if not path:
                return
            try:
                self.model.add_image(index, rect, path)
            except Exception as exc:
                return self._error("Resim eklenemedi: %s" % exc)

        elif tool is Tool.REDACT:
            if self._ask(
                    "Seçilen alandaki içerik dosyadan kalıcı olarak silinecek.\n"
                    "Devam edilsin mi?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) != QMessageBox.StandardButton.Yes:
                return
            self.model.redact(index, rect)
        else:
            return

        self._after_change()

    def on_point(self, point) -> None:
        if self.view.tool is Tool.STYLE:
            return self.on_style_click(point)
        if self.view.tool is not Tool.TEXT_EDIT:
            return
        index = self.view.page_index
        span = self.model.find_span_at(index, point)
        if span is None:
            self.statusBar().showMessage(
                tr("Burada düzenlenebilir metin yok. (Taranmış PDF olabilir.)"), 4000)
            return
        dialog = EditTextDialog(span, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        try:
            if values.get("size_changed") or values.get("color_changed"):
                report = self.model.resize_text(
                    index, span, values["text"],
                    values["size"] if values.get("size_changed") else None,
                    values["color"] if values.get("color_changed") else None,
                    values["whole_block"])
            else:
                report = self.model.replace_text(index, span, values["text"],
                                                 values["whole_block"])
        except NeighborTextLost as exc:
            self._after_change()
            return self._inform(
                
                "<b>Değişiklik yapılmadı.</b><br><br>"
                "Bu satırı değiştirmek çevresindeki yazıya da dokunuyordu, "
                "veri kaybetmemek için işlemi geri aldım.<br><br>"
                "Etkilenecek olan: %s<br><br>"
                "Satırlar çok sıkışıksa yakınlaştırıp tam hedefe tıklamayı "
                "ya da “Paragrafın tamamı” kapsamını denemeyi öner."
                % "<br>".join("• %s" % t[:60] for t in exc.lost[:4]))
        except Exception as exc:
            return self._error("Metin değiştirilemedi: %s" % exc)
        self._after_change()
        self._report_replace(report)

    def _report_replace(self, report) -> None:
        """Metin degistirmenin nasil sonuclandigini kullaniciya soyle."""
        if report.covered:
            # Satirlar cok sikisik oldugu icin eski yazi silinemedi, uzeri
            # ortuldu. Gizlilik acisindan onemli: metin dosyada duruyor.
            self.statusBar().showMessage(
                "Satırlar sıkışık olduğu için eski yazı silinmek yerine "
                "üzeri örtüldü — görünüm doğru, ama eski metin dosyada "
                "kalır. Tamamen silmek için “Karart” aracını kullan.", 11000)
            return

        if report.is_exact:
            self.statusBar().showMessage(
                "Belgenin kendi fontuyla yazıldı (%s) — görünüm korundu."
                % report.font_name, 6000)
            return

        if report.missing_chars:
            self._inform(
                
                "Belgedeki font <b>alt küme</b> olarak gömülmüş: yazdığın "
                "şu karakterleri içermiyor:<br><br>"
                "<b>%s</b><br><br>"
                "Bu yüzden satır <b>%s</b> fontuyla yazıldı ve görünüm "
                "özgün yazıdan farklı olacak. Bu karakterleri kullanmazsan "
                "belgenin kendi fontu korunur."
                % (report.missing_chars, report.font_name))
            return

        if report.uncertain_chars:
            # Font gomulu ve kullanildi; yalnizca bazi karakterlerin alt
            # kumede olup olmadigi dogrulanamiyor (cmap tablosu atilmis).
            self.statusBar().showMessage(
                "Belgenin kendi fontuyla yazıldı (%s). Şu karakterler "
                "belgede başka yerde geçmiyor, boş çıkarlarsa haber ver: %s"
                % (report.font_name, report.uncertain_chars), 9000)
            return

        self.statusBar().showMessage(
            "Belgenin fontu çıkarılamadı; %s ile yazıldı — görünüm "
            "farklı olabilir." % report.font_name, 7000)

    # --- tasima ve stil kopyalama ----------------------------------------

    def on_selection_changed(self, var: bool) -> None:
        """Tasima secimi olusunca/kalkinca ipucunu guncelle."""
        if var:
            self.hint_label.setText(
                tr("Seçim hazır — içine basıp sürükle. Vazgeçmek için Esc."))
        else:
            self.hint_label.setText(TOOL_HINTS[self.view.tool])

    def on_region_moved(self, rect, dx, dy) -> None:
        """Secili alani (tek harf de olabilir) yeni konuma tasi."""
        index = self.view.page_index
        try:
            report = self.model.move_region(index, rect, dx, dy)
        except NeighborTextLost as exc:
            self._after_change()
            return self._inform(
                
                "Taşıma yapılmadı: bu yazıyı kaldırmak çevresindeki yazıya "
                "da dokunuyordu.<br><br>%s"
                % "<br>".join("• %s" % t[:60] for t in exc.lost[:4]))
        except DocumentError as exc:
            return self.statusBar().showMessage(str(exc), 5000)
        except Exception as exc:
            return self._error("Taşınamadı: %s" % exc)
        self._after_change()
        notlar = []
        if report.covered:
            notlar.append(tr("eski yazının üzeri örtüldü"))
        if not report.embedded:
            notlar.append(tr("belgenin fontu bu harfleri çizemedi, tamamı "
                             "%s ile yazıldı") % report.font_name)
        ek = (" — " + " · ".join(notlar)) if notlar else ""
        self.statusBar().showMessage(
            tr("Taşındı") + " (%+.0f, %+.0f pt)%s" % (dx, dy, ek), 9000)

    def on_style_click(self, point) -> None:
        """İlk tıklama stili alır, ikincisi uygular."""
        index = self.view.page_index

        if self._style is None:
            style = self.model.capture_style(index, point)
            if style is None:
                self.statusBar().showMessage(
                    tr("Burada stil alınacak yazı yok."), 4000)
                return
            self._style = style
            self._update_style_indicator()
            self.statusBar().showMessage(
                "Stil alındı: %s — şimdi uygulanacak yazıya tıkla "
                "(iptal için Esc)." % style.label(), 12000)
            return

        span = self.model.find_span_at(index, point)
        if span is None:
            self.statusBar().showMessage(
                tr("Burada stil uygulanacak yazı yok."), 4000)
            return
        try:
            self.model.restyle_text(index, span, self._style)
        except NeighborTextLost as exc:
            self._after_change()
            return self._inform(
                
                "Stil uygulanmadı: bu yazıyı değiştirmek çevresindeki "
                "yazıya da dokunuyordu.<br><br>%s"
                % "<br>".join("• %s" % t[:60] for t in exc.lost[:4]))
        except Exception as exc:
            return self._error("Stil uygulanamadı: %s" % exc)
        self._after_change()
        self.statusBar().showMessage(
            "Stil uygulandı: %s (başka yazıya da tıklayabilirsin)"
            % self._style.label(), 8000)

    # --- gorsel duzenleme -------------------------------------------------

    def on_image_picked(self, point) -> None:
        """Tiklanan noktadaki EN KUCUK nesneyi sec: gorsel ya da vektor cizim.

        Sadece gorsele bakip cizime dusmek yetmiyordu: bircok sablonda sayfanin
        altinda tum yuzeyi kaplayan dev bir arka plan dokusu var. O dokuyu
        "noktadaki gorsel" sayinca, uzerindeki kucuk simgeye hic sira gelmiyor
        ve simge secilemiyordu. Bu yuzden ikisini de bulup kucuk
        olani seciyoruz.
        """
        gorsel = self.model.image_at(self.view.page_index, point)
        # CV'lerdeki telefon/zarf simgeleri cogunlukla gorsel degil,
        # kucuk vektor cizimlerdir; onlari da secilebilir yapiyoruz.
        cizim = self.model.drawing_at(self.view.page_index, point)
        if (gorsel is not None and cizim is not None
                and pymupdf.Rect(cizim["rect"]).get_area()
                < pymupdf.Rect(gorsel["rect"]).get_area()):
            gorsel = None

        self._selected_image = gorsel
        if gorsel is None:
            self._selected_drawing = cizim
            if cizim is None:
                self.view.clear_image_selection()
                self.statusBar().showMessage(
                    tr("Burada görsel ya da çizim yok."), 3000)
                return
            self.view.show_image_selection(cizim["rect"])
            return self.statusBar().showMessage(
                "%s  %.0f x %.0f pt — %s"
                % (tr("Çizim seçildi"), cizim["rect"].width,
                   cizim["rect"].height,
                   tr("taşımak için içinden, boyutlandırmak için köşeden "
                      "sürükle; silmek için Delete")), 9000)
        self._selected_drawing = None
        self.view.show_image_selection(gorsel["rect"])
        self.statusBar().showMessage(
            "%s  %.0f x %.0f pt (%d x %d px) — %s"
            % (tr("Görsel seçildi"), gorsel["rect"].width,
               gorsel["rect"].height, gorsel["width"], gorsel["height"],
               tr("taşımak için içinden, boyutlandırmak için köşeden "
                  "sürükle; silmek için Delete")), 9000)

    def on_image_placed(self, new_rect) -> None:
        """Surukleme bitti: gorseli/cizimi yeni yerine/boyutuna koy."""
        gorsel = getattr(self, "_selected_image", None)
        if gorsel is None:
            return self._place_drawing(new_rect)
        try:
            self.model.place_image(self.view.page_index, gorsel, new_rect)
        except DocumentError as exc:
            self.view.show_image_selection(gorsel["rect"])
            return self.statusBar().showMessage(str(exc), 5000)
        except Exception as exc:
            return self._error(tr("Görsel yerleştirilemedi: %s") % exc)

        self._after_change()
        orta = pymupdf.Point((new_rect.x0 + new_rect.x1) / 2,
                             (new_rect.y0 + new_rect.y1) / 2)
        yeni = self.model.image_at(self.view.page_index, orta)
        self._selected_image = yeni
        self.view.show_image_selection(yeni["rect"] if yeni else None)
        self.statusBar().showMessage(
            "%s  %.0f x %.0f pt" % (tr("Görsel güncellendi"),
                                    new_rect.width, new_rect.height), 5000)

    def _place_drawing(self, new_rect) -> None:
        """Secili vektor cizimi tasi / yeniden boyutlandir."""
        cizim = getattr(self, "_selected_drawing", None)
        if cizim is None:
            return
        try:
            self.model.place_drawing(self.view.page_index, cizim, new_rect)
        except DocumentError as exc:
            self.view.show_image_selection(cizim["rect"])
            return self.statusBar().showMessage(str(exc), 5000)
        except Exception as exc:
            return self._error(tr("Çizim taşınamadı: %s") % exc)

        self._after_change()
        orta = pymupdf.Point((new_rect.x0 + new_rect.x1) / 2,
                             (new_rect.y0 + new_rect.y1) / 2)
        yeni = self.model.drawing_at(self.view.page_index, orta)
        self._selected_drawing = yeni
        self.view.show_image_selection(yeni["rect"] if yeni else None)
        self.statusBar().showMessage(
            "%s  %.0f x %.0f pt" % (tr("Çizim güncellendi"),
                                    new_rect.width, new_rect.height), 5000)

    def delete_selected_drawing(self) -> None:
        """Secili vektor cizimi sil."""
        cizim = getattr(self, "_selected_drawing", None)
        if cizim is None:
            return
        try:
            self.model.delete_drawing(self.view.page_index, cizim)
        except Exception as exc:
            return self._error(tr("Çizim silinemedi: %s") % exc)
        self._selected_drawing = None
        self.view.clear_image_selection()
        self._after_change()
        self.statusBar().showMessage(tr("Çizim silindi."), 4000)

    def delete_selected_image(self) -> None:
        """Secili gorseli sil."""
        gorsel = getattr(self, "_selected_image", None)
        if gorsel is None:
            return self.delete_selected_drawing()
        try:
            self.model.delete_image(self.view.page_index, gorsel)
        except Exception as exc:
            return self._error(tr("Görsel silinemedi: %s") % exc)
        self._selected_image = None
        self.view.clear_image_selection()
        self._after_change()
        self.statusBar().showMessage(tr("Görsel silindi."), 4000)

    # --- gorsel icerigini duzenleme ---------------------------------------

    def on_image_menu(self, global_pos) -> None:
        """Secili gorsel icin sag tik menusu."""
        if getattr(self, "_selected_image", None) is None:
            # Vektor cizimde donus/kirpma gibi piksel islemleri anlamsiz;
            # yalnizca silme sunuluyor (tasima/boyutlandirma surukleyerek).
            if getattr(self, "_selected_drawing", None) is None:
                return
            menu = QMenu(self)
            menu.addAction(tr("Sil")).triggered.connect(
                self.delete_selected_drawing)
            return menu.exec(global_pos)
        menu = QMenu(self)
        ekle = menu.addAction
        ekle(tr("Sağa döndür")).triggered.connect(
            lambda: self._image_op("dondur", derece=90))
        ekle(tr("Sola döndür")).triggered.connect(
            lambda: self._image_op("dondur", derece=270))
        menu.addSeparator()
        ekle(tr("Yatay aynala")).triggered.connect(
            lambda: self._image_op("aynala", yatay=True))
        ekle(tr("Dikey aynala")).triggered.connect(
            lambda: self._image_op("aynala", yatay=False))
        menu.addSeparator()
        ekle(tr("Kırp…")).triggered.connect(self.start_image_crop)
        ekle(tr("Gri tonlama")).triggered.connect(
            lambda: self._image_op("gri"))
        ekle(tr("Parlaklık ve kontrast…")).triggered.connect(
            self.adjust_selected_image)
        menu.addSeparator()
        ekle(tr("Başka görselle değiştir…")).triggered.connect(
            self.replace_selected_image)
        ekle(tr("Görseli dışa aktar…")).triggered.connect(
            self.export_selected_image)
        menu.addSeparator()
        ekle(tr("Sil")).triggered.connect(self.delete_selected_image)
        menu.exec(global_pos)

    def _image_op(self, islem: str, **secenek) -> None:
        """Gorsel islemini uygula ve secimi tazele."""
        gorsel = getattr(self, "_selected_image", None)
        if gorsel is None:
            return
        try:
            boyut = self.model.edit_image(self.view.page_index, gorsel,
                                          islem, **secenek)
        except DocumentError as exc:
            return self.statusBar().showMessage(str(exc), 5000)
        except Exception as exc:
            return self._error(tr("Görsel düzenlenemedi: %s") % exc)

        self._after_change()
        self._reselect_image()
        self.statusBar().showMessage(
            "%s (%d x %d px)" % (tr("Görsel güncellendi"), boyut[0], boyut[1]),
            5000)

    def _reselect_image(self) -> None:
        """Islemden sonra ayni gorseli tekrar sec."""
        eski = getattr(self, "_selected_image", None)
        if eski is None:
            return
        rect = pymupdf.Rect(eski["rect"])
        orta = pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
        yeni = self.model.image_at(self.view.page_index, orta)
        if yeni is None:
            gorseller = self.model.images_on(self.view.page_index)
            yeni = gorseller[0] if gorseller else None
        self._selected_image = yeni
        self.view.show_image_selection(yeni["rect"] if yeni else None)

    def start_image_crop(self) -> None:
        if getattr(self, "_selected_image", None) is None:
            return
        self.view.start_crop()
        self.statusBar().showMessage(
            tr("Kırpmak istediğin alanı görselin içinde sürükleyerek seç."),
            8000)

    def on_image_cropped(self, rect) -> None:
        """Kullanici kirpma alanini sectі."""
        gorsel = getattr(self, "_selected_image", None)
        if gorsel is None:
            return
        kutu = pymupdf.Rect(gorsel["rect"])
        alan = pymupdf.Rect(rect) & kutu
        if alan.is_empty or alan.width < 3 or alan.height < 3:
            return self.statusBar().showMessage(
                tr("Kırpma alanı görselin dışında kaldı."), 5000)
        oran = ((alan.x0 - kutu.x0) / kutu.width,
                (alan.y0 - kutu.y0) / kutu.height,
                (alan.x1 - kutu.x0) / kutu.width,
                (alan.y1 - kutu.y0) / kutu.height)
        self._image_op("kirp", oran=oran)

    def adjust_selected_image(self) -> None:
        dialog = ImageAdjustDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self._image_op("ayarla", **dialog.values())

    def replace_selected_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Resim seç"), "",
            "Resimler (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)")
        if path:
            self._image_op("degistir", path=path)

    def export_selected_image(self) -> None:
        gorsel = getattr(self, "_selected_image", None)
        if gorsel is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Görseli dışa aktar…"), "gorsel.png",
            "PNG (*.png);;JPEG (*.jpg)")
        if not path:
            return
        try:
            self.model.export_image(gorsel, path)
        except Exception as exc:
            return self._error(tr("Kaydedilemedi: %s") % exc)
        self.statusBar().showMessage("%s: %s" % (tr("Kaydedildi"), path), 5000)

    def on_ink(self, strokes) -> None:
        self.model.add_ink(self.view.page_index, strokes,
                           self.color_btn.rgb(), float(self.width_box.value()))
        self._after_change()

    def on_annot_click(self, point) -> None:
        index = self.view.page_index
        annots = self.model.annots_at(index, point)
        if not annots:
            return
        if self._ask( "Bu işaretleme silinsin mi?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self.model.delete_annot(index, annots[0])
        self._after_change()

    # ------------------------------------------------------------------
    # araclar
    # ------------------------------------------------------------------

    def on_watermark(self) -> None:
        dialog = WatermarkDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        values = dialog.values()
        if not values["text"].strip():
            return
        try:
            self.model.watermark(values["text"], values["size"],
                                 values["opacity"], values["color"],
                                 values["rotate"])
        except Exception as exc:
            return self._error("Filigran eklenemedi: %s" % exc)
        self._after_change(rebuild_thumbs=True)

    def on_flatten(self) -> None:
        if self._ask(
                "Form alanları sabit içeriğe çevrilecek ve bir daha "
                "düzenlenemeyecek. Devam edilsin mi?"
        ) != QMessageBox.StandardButton.Yes:
            return
        try:
            self.model.flatten_form()
        except Exception as exc:
            return self._error("Sabitlenemedi: %s" % exc)
        self._after_change(rebuild_thumbs=True)

    def on_field_changed(self, page_index: int, name: str, value) -> None:
        try:
            self.model.set_field(page_index, name, value)
        except Exception as exc:
            return self._error("Alan yazılamadı: %s" % exc)
        self.view.refresh()
        self.thumbs.refresh_page(page_index)
        self._update_state()

    # ------------------------------------------------------------------
    # yardim
    # ------------------------------------------------------------------

    def on_language(self, code: str) -> None:
        """Dili degistir; pencereyi yeni dille yeniden kur."""
        if code == current_language():
            return
        if not self._confirm_discard():
            # Kullanici vazgecti; menudeki isareti geri al.
            for action in self.lang_group.actions():
                action.setChecked(False)
            return
        set_language(code)
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl()
                                   else Qt.LayoutDirection.LeftToRight)
        self.restart_language = code
        self.reopen_path = self.model.path
        self.close()

    def on_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(tr("Hakkında"))
        box.setIconPixmap(brand_pixmap(72))
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(about_html(__version__))
        apply_buttons(box)
        box.exec()

    def on_shortcuts(self) -> None:
        """Kisayollari cevrilmis arac adlariyla goster."""
        satirlar = ["<b>%s</b><br>" % tr("Dosya"),
                    "Ctrl+O · Ctrl+S · Ctrl+Shift+S · Ctrl+I<br><br>",
                    "<b>%s</b><br>" % tr("Dü&zen").replace("&", ""),
                    "Ctrl+Z · Ctrl+Y · Ctrl+F<br><br>",
                    "<b>%s</b><br>" % tr("Görünüm"),
                    "Ctrl++ / Ctrl+- · Ctrl+1 · Ctrl+0 · PgUp / PgDown<br><br>",
                    "<b>%s</b><br>" % tr("Araçlar")]
        for tool, action in self.tool_actions.items():
            kisayol = action.shortcut().toString()
            if kisayol:
                satirlar.append("%s — %s<br>" % (kisayol, action.text()))
        satirlar.append("<br><b>%s</b><br>" % tr("&Sayfa").replace("&", ""))
        satirlar.append("Ctrl+← / Ctrl+→ · Ctrl+Delete")
        self._inform("".join(satirlar))

    # ------------------------------------------------------------------
    # pencere olaylari
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        secili = (getattr(self, "_selected_image", None)
                  or getattr(self, "_selected_drawing", None))
        if (event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
                and self.view.tool is Tool.IMAGE_EDIT
                and secili is not None):
            self.delete_selected_image()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self.view.tool is Tool.IMAGE_EDIT and secili is not None:
                self._selected_image = None
                self._selected_drawing = None
                self.view.clear_image_selection()
                return
            if self.view._sel_rect is not None:
                self.view.clear_selection()
                self.statusBar().showMessage(tr("Taşıma seçimi bırakıldı."), 3000)
                return
            if self._style is not None:
                self.clear_style()
                return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith(".pdf"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path.lower().endswith(".pdf") and self._confirm_discard():
            self.load(path)

    def closeEvent(self, event):
        if self._confirm_discard():
            self.model.close()
            event.accept()
        else:
            event.ignore()


def run(argv=None) -> int:
    set_taskbar_identity()
    load_language()
    app = QApplication(argv or [])
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(VENDOR)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
    # Arapca gibi sagdan sola dillerde tum arayuz duzeni cevrilir.
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if is_rtl()
                           else Qt.LayoutDirection.LeftToRight)

    # Komut satirindan gelen dosya (PDF degilse once donusturulur).
    acilacak = None
    for arg in (argv or [])[1:]:
        if not os.path.exists(arg):
            continue
        if arg.lower().endswith(".pdf"):
            acilacak = arg
        else:
            try:
                target = os.path.splitext(arg)[0] + ".pdf"
                convert.any_to_pdf(arg, target)
                acilacak = target
            except Exception:
                acilacak = None
        break

    # Dil degisince pencereyi yeni dille yeniden kuruyoruz; acik dosya korunur.
    sonuc = 0
    while True:
        window = MainWindow()
        window.show()
        window.statusBar().showMessage(
            "%s %s — %s" % (APP_NAME, __version__, VENDOR), 5000)
        if acilacak:
            window.load(acilacak)

        sonuc = app.exec()
        if not getattr(window, "restart_language", None):
            break
        acilacak = getattr(window, "reopen_path", None)
    return sonuc
