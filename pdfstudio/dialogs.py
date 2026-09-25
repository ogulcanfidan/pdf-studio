"""Diyaloglar: metin girisi, metin duzenleme, filigran, resim disa aktarma."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from .i18n import apply_buttons, tr
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                               QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QSlider, QSpinBox, QVBoxLayout)


class ColorButton(QPushButton):
    """Tiklayinca renk secici acan dugme."""

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedWidth(64)
        self._apply()
        self.clicked.connect(self._pick)

    def _apply(self) -> None:
        self.setStyleSheet(
            "background:%s; border:1px solid #888; border-radius:3px;"
            % self._color.name())

    def _pick(self) -> None:
        color = QColorDialog.getColor(self._color, self, tr("Renk seç"))
        if color.isValid():
            self._color = color
            self._apply()

    def rgb(self) -> tuple:
        return (self._color.redF(), self._color.greenF(), self._color.blueF())


class TextDialog(QDialog):
    """Yeni metin kutusu ekleme."""

    def __init__(self, parent=None, title=None, text="",
                 size=12.0, color=QColor("#000000")):
        super().__init__(parent)
        self.setWindowTitle(title or tr("Metin ekle"))
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit(text)
        self.editor.setPlaceholderText(tr("Yazıyı buraya gir…"))
        layout.addWidget(self.editor, 1)

        form = QFormLayout()
        self.size_box = QDoubleSpinBox()
        self.size_box.setRange(4.0, 200.0)
        self.size_box.setValue(size)
        self.size_box.setSuffix(" pt")
        form.addRow(tr("Punto:"), self.size_box)

        self.color_btn = ColorButton(color)
        form.addRow(tr("Renk:"), self.color_btn)

        self.bold = QCheckBox(tr("Kalın"))
        form.addRow("", self.bold)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        apply_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.editor.setFocus()

    def values(self) -> dict:
        return {
            "text": self.editor.toPlainText(),
            "size": self.size_box.value(),
            "color": self.color_btn.rgb(),
            "bold": self.bold.isChecked(),
        }


class EditTextDialog(QDialog):
    """Sayfadaki mevcut metni degistirme."""

    def __init__(self, span, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Metni düzenle"))
        self.setMinimumWidth(480)
        self.span = span

        layout = QVBoxLayout(self)

        note = QLabel(tr(
            "Yazı silinip aynı taban çizgisine yeniden yazılır; belgenin "
            "kendi fontu, punto ve harf aralığı korunur."))
        note.setWordWrap(True)
        note.setStyleSheet("color:#8a6d1a; background:#fff8e1; padding:7px;"
                           "border:1px solid #f0d48a; border-radius:4px;")
        layout.addWidget(note)

        self.scope = QComboBox()
        self.scope.addItem(tr("Yalnızca bu satır"), False)
        self.scope.addItem(tr("Paragrafın tamamı"), True)
        self.scope.currentIndexChanged.connect(self._scope_changed)
        form = QFormLayout()
        form.addRow(tr("Kapsam:"), self.scope)
        layout.addLayout(form)

        self.editor = QPlainTextEdit(span.text)
        layout.addWidget(self.editor, 1)

        # Punto burada ayarlanabilir; stil kopyalama puntoyu tasimaz.
        punto_satiri = QHBoxLayout()
        punto_satiri.addWidget(QLabel(tr("Punto:")))
        self.size_box = QDoubleSpinBox()
        self.size_box.setRange(4.0, 200.0)
        self.size_box.setDecimals(1)
        self.size_box.setSingleStep(0.5)
        self.size_box.setValue(float(span.size))
        self.size_box.setSuffix(" pt")
        self.size_box.setMinimumWidth(96)
        punto_satiri.addWidget(self.size_box)

        self.reset_size = QPushButton(tr("Özgün punto"))
        self.reset_size.setToolTip("%.1f pt" % span.size)
        self.reset_size.clicked.connect(
            lambda: self.size_box.setValue(float(span.size)))
        punto_satiri.addWidget(self.reset_size)

        # Renk de buradan degistirilebilir; varsayilan yazinin kendi rengi.
        punto_satiri.addSpacing(14)
        punto_satiri.addWidget(QLabel(tr("Renk:")))
        r, g, b = span.color
        self._ozgun_renk = QColor(int(r * 255), int(g * 255), int(b * 255))
        self.color_btn = ColorButton(self._ozgun_renk)
        punto_satiri.addWidget(self.color_btn)

        self.reset_color = QPushButton(tr("Özgün renk"))
        self.reset_color.clicked.connect(self._renk_sifirla)
        punto_satiri.addWidget(self.reset_color)
        punto_satiri.addStretch(1)
        layout.addLayout(punto_satiri)

        detay = ["%s %s" % (tr("Font:"), span.font)]
        if abs(getattr(span, "tracking", 0.0)) > 0.05:
            detay.append("%s %+.2f pt" % (tr("Harf aralığı:"), span.tracking))
        info = QLabel(" · ".join(detay))
        info.setStyleSheet("color:#666;")
        layout.addWidget(info)

        if getattr(span, "mixed_fonts", False):
            warn = QLabel(tr(
                "Bu satırda birden fazla yazı tipi var; tamamı tek bir "
                "yazı tipiyle yeniden yazılacak.") + " (%s)" % span.font)
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#8a1a1a; background:#fdecec; padding:6px;"
                               "border:1px solid #f0a8a8; border-radius:4px;")
            layout.addWidget(warn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        apply_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.editor.setFocus()
        self.editor.selectAll()

    def _renk_sifirla(self) -> None:
        self.color_btn._color = QColor(self._ozgun_renk)
        self.color_btn._apply()

    def _scope_changed(self, _index: int) -> None:
        whole = self.scope.currentData()
        self.editor.setPlainText(self.span.block_text if whole else self.span.text)

    def values(self) -> dict:
        return {
            "text": self.editor.toPlainText(),
            "whole_block": bool(self.scope.currentData()),
            "size": self.size_box.value(),
            "size_changed": abs(self.size_box.value() - self.span.size) > 0.05,
            "color": self.color_btn.rgb(),
            "color_changed": self.color_btn._color.name()
            != self._ozgun_renk.name(),
        }


class WatermarkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Filigran ekle"))
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.text = QLineEdit("TASLAK")
        form.addRow(tr("Metin:"), self.text)

        self.size = QSpinBox()
        self.size.setRange(8, 200)
        self.size.setValue(54)
        self.size.setSuffix(" pt")
        form.addRow(tr("Punto:"), self.size)

        self.angle = QSpinBox()
        self.angle.setRange(-180, 180)
        self.angle.setValue(45)
        self.angle.setSuffix("°")
        form.addRow(tr("Açı:"), self.angle)

        self.color_btn = ColorButton(QColor("#9aa0a6"))
        form.addRow(tr("Renk:"), self.color_btn)

        opacity_row = QHBoxLayout()
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(5, 100)
        self.opacity.setValue(25)
        self.opacity_label = QLabel("%25")
        self.opacity.valueChanged.connect(
            lambda v: self.opacity_label.setText("%%%d" % v))
        opacity_row.addWidget(self.opacity, 1)
        opacity_row.addWidget(self.opacity_label)
        form.addRow(tr("Saydamlık:"), opacity_row)

        layout.addLayout(form)
        layout.addWidget(QLabel(tr("Filigran belgedeki tüm sayfalara eklenir.")))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        apply_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "text": self.text.text(),
            "size": self.size.value(),
            "rotate": self.angle.value(),
            "color": self.color_btn.rgb(),
            "opacity": self.opacity.value() / 100.0,
        }


class ImageAdjustDialog(QDialog):
    """Gorselin parlaklik ve kontrastini ayarlar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Parlaklık ve kontrast"))
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.brightness = QSlider(Qt.Orientation.Horizontal)
        self.brightness.setRange(-100, 100)
        self.brightness.setValue(0)
        self.b_label = QLabel("0")
        self.brightness.valueChanged.connect(
            lambda v: self.b_label.setText("%+d" % v))
        b_row = QHBoxLayout()
        b_row.addWidget(self.brightness, 1)
        b_row.addWidget(self.b_label)
        form.addRow(tr("Parlaklık:"), b_row)

        self.contrast = QSlider(Qt.Orientation.Horizontal)
        self.contrast.setRange(-100, 100)
        self.contrast.setValue(0)
        self.c_label = QLabel("0")
        self.contrast.valueChanged.connect(
            lambda v: self.c_label.setText("%+d" % v))
        c_row = QHBoxLayout()
        c_row.addWidget(self.contrast, 1)
        c_row.addWidget(self.c_label)
        form.addRow(tr("Kontrast:"), c_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        apply_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {"parlaklik": self.brightness.value() / 100.0,
                "kontrast": self.contrast.value() / 100.0}


class ExportImagesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Resim olarak dışa aktar"))
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.dpi = QSpinBox()
        self.dpi.setRange(48, 600)
        self.dpi.setValue(150)
        self.dpi.setSingleStep(25)
        self.dpi.setSuffix(" DPI")
        form.addRow(tr("Çözünürlük:"), self.dpi)

        self.fmt = QComboBox()
        self.fmt.addItems(["PNG", "JPEG"])
        form.addRow(tr("Biçim:"), self.fmt)

        self.scope = QComboBox()
        self.scope.addItem(tr("Tüm sayfalar"), "all")
        self.scope.addItem(tr("Yalnızca geçerli sayfa"), "current")
        form.addRow(tr("Kapsam:"), self.scope)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        apply_buttons(buttons)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "dpi": self.dpi.value(),
            "format": self.fmt.currentText().lower(),
            "scope": self.scope.currentData(),
        }
