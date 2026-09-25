"""FMJ Software marka kimligi: simge, imza, belge damgasi."""

from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap)

VENDOR = "FMJ Software"
BRAND = "FMJ"
APP_NAME = "PDF Studio"
TAGLINE = "PDF düzenleme ve dönüştürme"

# Marka renkleri (logodan alindi)
INK = "#4f46e5"        # ana ton (indigo)
INK_DARK = "#4338ca"
ACCENT = "#a5b4fc"     # vurgu (acik indigo)
ACCENT_PEN = "#f4b942" # uygulama simgesindeki kalem (amber)
PAPER = "#ffffff"

# Gercek marka logosu; yoksa asagidaki cizim yedek olarak kullanilir.
LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "assets", "fmj-logo.png")


def brand_pixmap(size: int = 256) -> QPixmap:
    """FMJ Software KURUM logosu - Hakkinda kutusunda kullanilir.

    Uygulamanin kendi simgesi icin app_pixmap()/app_icon() var; pencere ve
    gorev cubugunda o gorunur.
    """
    if os.path.exists(LOGO_PATH):
        pixmap = QPixmap(LOGO_PATH)
        if not pixmap.isNull():
            return pixmap.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
    return _drawn_pixmap(size)


def app_pixmap(size: int = 256) -> QPixmap:
    """PDF Studio'nun KENDI simgesi: belge + duzenleme kalemi.

    Kurum logosundan ayri tutuluyor - gorev cubugunda hangi uygulamanin
    calistigi anlasilsin diye.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256.0

    # Marka renginde yuvarlak kose zemin
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor(INK))
    gradient.setColorAt(1.0, QColor(INK_DARK))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(10 * s, 10 * s, 236 * s, 236 * s),
                            54 * s, 54 * s)

    # Belge sayfasi (kivrik koseli)
    page = QPainterPath()
    page.moveTo(66 * s, 48 * s)
    page.lineTo(142 * s, 48 * s)
    page.lineTo(182 * s, 88 * s)
    page.lineTo(182 * s, 190 * s)
    page.quadTo(182 * s, 206 * s, 166 * s, 206 * s)
    page.lineTo(82 * s, 206 * s)
    page.quadTo(66 * s, 206 * s, 66 * s, 190 * s)
    page.closeSubpath()
    painter.setBrush(QBrush(QColor(PAPER)))
    painter.drawPath(page)

    # Kivrilan kose
    fold = QPainterPath()
    fold.moveTo(142 * s, 48 * s)
    fold.lineTo(142 * s, 88 * s)
    fold.lineTo(182 * s, 88 * s)
    fold.closeSubpath()
    painter.setBrush(QBrush(QColor("#c7d2fe")))
    painter.drawPath(fold)

    # Metin satirlari
    painter.setBrush(QBrush(QColor("#94a3b8")))
    for i, (x, w) in enumerate(((84, 78), (84, 62), (84, 70))):
        painter.drawRoundedRect(
            QRectF(x * s, (108 + i * 20) * s, w * s, 8 * s), 4 * s, 4 * s)

    # Duzenleme kalemi (capraz), uygulamayi "duzenleyici" yapan isaret
    painter.save()
    painter.translate(150 * s, 150 * s)
    painter.rotate(45)
    painter.setBrush(QBrush(QColor(ACCENT_PEN)))
    painter.drawRoundedRect(QRectF(-11 * s, -54 * s, 22 * s, 82 * s),
                            6 * s, 6 * s)
    ucu = QPainterPath()
    ucu.moveTo(-11 * s, 28 * s)
    ucu.lineTo(11 * s, 28 * s)
    ucu.lineTo(0, 52 * s)
    ucu.closeSubpath()
    painter.setBrush(QBrush(QColor("#f8fafc")))
    painter.drawPath(ucu)
    painter.restore()

    painter.end()
    return pixmap


def app_icon() -> QIcon:
    """Pencere ve gorev cubugu simgesi."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_pixmap(size))
    return icon


def set_taskbar_identity() -> None:
    """Windows gorev cubugunda Python yerine uygulamanin simgesi gorunsun.

    Kendi AppUserModelID'mizi ilan etmezsek Windows uygulamayi python
    yorumlayicisiyla gruplar ve onun simgesini gosterir.
    """
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "FMJSoftware.PDFStudio.1")
    except Exception:
        # Windows disi ya da erisim yoksa sessizce gec; simge yine atanir.
        pass


def _drawn_pixmap(size: int = 256) -> QPixmap:
    """Logo dosyasi yoksa kullanilan yedek cizim."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    s = size / 256.0
    # Yuvarlak kosel zemin
    gradient = QLinearGradient(0, 0, 0, size)
    gradient.setColorAt(0.0, QColor(INK))
    gradient.setColorAt(1.0, QColor(INK_DARK))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s),
                            52 * s, 52 * s)

    # Sayfa silueti (kivrik kose)
    page = QPainterPath()
    page.moveTo(78 * s, 54 * s)
    page.lineTo(150 * s, 54 * s)
    page.lineTo(186 * s, 90 * s)
    page.lineTo(186 * s, 202 * s)
    page.lineTo(78 * s, 202 * s)
    page.closeSubpath()
    painter.setBrush(QBrush(QColor(PAPER)))
    painter.drawPath(page)

    # Kivrilan kose
    fold = QPainterPath()
    fold.moveTo(150 * s, 54 * s)
    fold.lineTo(150 * s, 90 * s)
    fold.lineTo(186 * s, 90 * s)
    fold.closeSubpath()
    painter.setBrush(QBrush(QColor("#cbd5d1")))
    painter.drawPath(fold)

    # Vurgu serit
    painter.setBrush(QBrush(QColor(ACCENT)))
    painter.drawRoundedRect(QRectF(96 * s, 108 * s, 72 * s, 9 * s),
                            4 * s, 4 * s)

    # FMJ harfleri
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(44 * s))
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2 * s)
    painter.setFont(font)
    painter.setPen(QPen(QColor(INK_DARK)))
    painter.drawText(QRectF(78 * s, 128 * s, 108 * s, 60 * s),
                     Qt.AlignmentFlag.AlignCenter, BRAND)

    painter.end()
    return pixmap


def about_html(version: str) -> str:
    return (
        "<div style='min-width:360px'>"
        "<h2 style='margin:0;color:%s'>%s</h2>"
        "<p style='margin:2px 0 10px;color:#666'>%s &middot; sürüm %s</p>"
        "<p style='margin:0 0 10px'><b>%s</b> tarafından geliştirildi.</p>"
        "<p style='margin:0;color:#444'>Sayfa işlemleri, üzerine ekleme, "
        "metin düzenleme, form doldurma ve biçim dönüştürme.</p>"
        "<p style='margin:10px 0 0;color:#888;font-size:11px'>"
        "Python &middot; PySide6 (Qt) &middot; PyMuPDF</p>"
        "</div>" % (INK, APP_NAME, TAGLINE, version, VENDOR)
    )


def stamp_metadata(doc) -> None:
    """Uretilen PDF'e FMJ Software imzasini isle.

    Var olan baslik/yazar gibi alanlari bozmadan yalnizca uretici
    bilgilerini gunceller.
    """
    try:
        meta = dict(doc.metadata or {})
    except Exception:
        meta = {}
    meta["producer"] = "%s — %s" % (APP_NAME, VENDOR)
    if not meta.get("creator"):
        meta["creator"] = "%s (%s)" % (APP_NAME, VENDOR)
    try:
        doc.set_metadata(meta)
    except Exception:
        # Metadata yazilamamasi kaydetmeyi engellemesin.
        pass
