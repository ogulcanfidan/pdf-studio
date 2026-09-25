"""Yan paneller: sayfa kucuk resimleri ve form alanlari."""

from __future__ import annotations

import pymupdf
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHeaderView,
                               QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from .i18n import tr
from .pageview import pixmap_from_pdf

THUMB_WIDTH = 132


class ThumbnailBar(QListWidget):
    """Sayfa kucuk resimleri; surukleyerek sira degistirilebilir."""

    pageSelected = Signal(int)
    pageMoved = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_ref = None
        self._pending = []
        self._suppress = False

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_WIDTH, int(THUMB_WIDTH * 1.5)))
        self.setGridSize(QSize(THUMB_WIDTH + 22, int(THUMB_WIDTH * 1.5) + 34))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSpacing(6)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setUniformItemSizes(True)

        self.currentRowChanged.connect(self._on_row_changed)
        self.model().rowsMoved.connect(self._on_rows_moved)

        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._render_next)

    # ------------------------------------------------------------------

    def set_model(self, model) -> None:
        self.model_ref = model

    def rebuild(self, current: int = 0) -> None:
        """Listeyi sifirdan kur; goruntuler arka planda doldurulur."""
        self._suppress = True
        self.clear()
        self._pending = []
        self._timer.stop()

        if not self.model_ref or not self.model_ref.is_open:
            self._suppress = False
            return

        placeholder = QPixmap(THUMB_WIDTH, int(THUMB_WIDTH * 1.4))
        placeholder.fill(QColor("#ffffff"))

        for i in range(self.model_ref.page_count):
            item = QListWidgetItem(QIcon(placeholder), str(i + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            self.addItem(item)
            self._pending.append(i)

        self.setCurrentRow(max(0, min(current, self.count() - 1)))
        self._suppress = False
        self._timer.start()

    def _render_next(self) -> None:
        """Her turda birkac kucuk resim uret - arayuz donmasin."""
        if not self._pending or not self.model_ref or not self.model_ref.is_open:
            self._timer.stop()
            return
        for _ in range(3):
            if not self._pending:
                self._timer.stop()
                return
            index = self._pending.pop(0)
            if index >= self.count() or index >= self.model_ref.page_count:
                continue
            try:
                rect = self.model_ref.page_rect(index)
                zoom = THUMB_WIDTH / rect.width if rect.width else 0.2
                pix = self.model_ref.render(index, zoom)
                self.item(index).setIcon(QIcon(pixmap_from_pdf(pix)))
            except Exception:
                # Bozuk tek sayfa tum paneli durdurmasin.
                continue

    def refresh_page(self, index: int) -> None:
        if not self.model_ref or index >= self.count():
            return
        if index not in self._pending:
            self._pending.append(index)
        self._timer.start()

    def selected_rows(self) -> list[int]:
        return sorted(i.row() for i in self.selectedIndexes())

    # ------------------------------------------------------------------

    def _on_row_changed(self, row: int) -> None:
        if not self._suppress and row >= 0:
            self.pageSelected.emit(row)

    def _on_rows_moved(self, parent, start, end, dest, row) -> None:
        if self._suppress:
            return
        dst = row if row < start else row - 1
        if dst != start:
            self.pageMoved.emit(start, dst)


class FormPanel(QWidget):
    """PDF form alanlarini listeler ve duzenletir."""

    fieldChanged = Signal(int, str, object)
    flattenRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model_ref = None
        self._rows = []
        self._loading = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.info = QLabel(tr("Belge açılmadı."))
        self.info.setWordWrap(True)
        layout.addWidget(self.info)

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels([tr("Alan"), tr("Sayfa"), tr("Değer")])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.table, 1)

        self.flatten_btn = QPushButton(tr("Formu sabitle (düzenlenemez yap)"))
        self.flatten_btn.clicked.connect(self.flattenRequested.emit)
        self.flatten_btn.setEnabled(False)
        layout.addWidget(self.flatten_btn)

    def set_model(self, model) -> None:
        self.model_ref = model

    def reload(self) -> None:
        self._loading = True
        self.table.setRowCount(0)
        self._rows = []

        if not self.model_ref or not self.model_ref.is_open:
            self.info.setText(tr("Belge açılmadı."))
            self.flatten_btn.setEnabled(False)
            self._loading = False
            return

        fields = self.model_ref.form_fields()
        if not fields:
            self.info.setText(tr("Bu belgede doldurulabilir form alanı yok."))
            self.flatten_btn.setEnabled(False)
            self._loading = False
            return

        self.info.setText(tr("%d form alanı bulundu. Değer sütununu düzenleyebilirsin.")
                          % len(fields))
        self.flatten_btn.setEnabled(True)
        self.table.setRowCount(len(fields))

        for row, (page_index, widget) in enumerate(fields):
            name = widget.field_name or "(isimsiz)"
            self._rows.append((page_index, name, widget.field_type))

            name_item = QTableWidgetItem(name)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled
                               | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 0, name_item)

            page_item = QTableWidgetItem(str(page_index + 1))
            page_item.setFlags(Qt.ItemFlag.ItemIsEnabled
                               | Qt.ItemFlag.ItemIsSelectable)
            self.table.setItem(row, 1, page_item)

            if widget.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                combo = QComboBox()
                combo.addItems([tr("İşaretsiz"), tr("İşaretli")])
                combo.setCurrentIndex(1 if widget.field_value else 0)
                combo.currentIndexChanged.connect(
                    lambda idx, r=row: self._emit(r, bool(idx)))
                self.table.setCellWidget(row, 2, combo)
            else:
                value = widget.field_value
                self.table.setItem(row, 2, QTableWidgetItem(
                    "" if value is None else str(value)))

        self._loading = False

    def _emit(self, row: int, value) -> None:
        if self._loading or row >= len(self._rows):
            return
        page_index, name, _ = self._rows[row]
        self.fieldChanged.emit(page_index, name, value)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 2:
            return
        self._emit(item.row(), item.text())
