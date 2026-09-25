"""Sayfa tuvali: render, yakinlastirma ve arac etkilesimleri."""

from __future__ import annotations

from enum import Enum

import pymupdf
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QImage, QPainterPath, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QGraphicsPathItem, QGraphicsPixmapItem,
                               QGraphicsRectItem, QGraphicsScene,
                               QGraphicsView)

from .i18n import tr


class Tool(Enum):
    SELECT = "select"
    TEXT_ADD = "text_add"
    TEXT_EDIT = "text_edit"
    TEXT_MOVE = "text_move"
    STYLE = "style"
    IMAGE_EDIT = "image_edit"
    HIGHLIGHT = "highlight"
    UNDERLINE = "underline"
    STRIKEOUT = "strikeout"
    DRAW = "draw"
    RECT = "rect"
    IMAGE = "image"
    REDACT = "redact"


#: Suruklenerek alan secen araclar.
DRAG_TOOLS = {Tool.TEXT_ADD, Tool.HIGHLIGHT, Tool.UNDERLINE, Tool.STRIKEOUT,
              Tool.RECT, Tool.IMAGE, Tool.REDACT}

#: Tek tiklamayla calisan araclar.
CLICK_TOOLS = {Tool.TEXT_EDIT, Tool.STYLE}

_HINT_SOURCE = {
    Tool.SELECT: "Seç: işaretlemeye çift tıkla → sil. Boşlukta sürükle → kaydır.",
    Tool.TEXT_ADD: "Metin ekle: yazının geleceği kutuyu sürükleyerek çiz.",
    Tool.TEXT_EDIT: "Metni düzenle: değiştirmek istediğin yazıya tıkla.",
    Tool.TEXT_MOVE: "Taşı: önce taşınacak alanı kutuyla seç (tek harf de olur), sonra seçimi sürükle.",
    Tool.STYLE: "Stil kopyala: önce kaynak yazıya, sonra uygulanacak yazıya tıkla.",
    Tool.IMAGE_EDIT: "Görsel ve simge: tıkla seç, içinden sürükle taşı, köşeden sürükle boyutlandır, Delete sil.",
    Tool.HIGHLIGHT: "Vurgula: metnin üzerinden sürükle.",
    Tool.UNDERLINE: "Altını çiz: metnin üzerinden sürükle.",
    Tool.STRIKEOUT: "Üstünü çiz: metnin üzerinden sürükle.",
    Tool.DRAW: "Serbest çizim: basılı tutup çiz.",
    Tool.RECT: "Dikdörtgen: çizmek istediğin alanı sürükle.",
    Tool.IMAGE: "Resim/İmza: yerleştireceğin alanı sürükle, sonra dosya seç.",
    Tool.REDACT: "Karart: alanı sürükle — içerik dosyadan kalıcı silinir.",
}


class _Hints(dict):
    """Arac ipucunu her okumada gecerli dile cevirir."""

    def __getitem__(self, key):
        return tr(_HINT_SOURCE[key])

    def get(self, key, default=None):
        if key in _HINT_SOURCE:
            return tr(_HINT_SOURCE[key])
        return default


TOOL_HINTS = _Hints()


def pixmap_from_pdf(pix) -> QPixmap:
    """PyMuPDF pixmap -> QPixmap."""
    image = QImage(pix.samples, pix.width, pix.height, pix.stride,
                   QImage.Format.Format_RGB888)
    # copy(): QImage ham tampona bakiyor, pix serbest kalinca cokmesin.
    return QPixmap.fromImage(image.copy())


class PageView(QGraphicsView):
    """Tek sayfayi gosteren tuval."""

    regionSelected = Signal(object)   # pymupdf.Rect (PDF koordinati)
    pointClicked = Signal(object)     # pymupdf.Point
    inkDrawn = Signal(list)           # [[(x, y), ...], ...]
    annotDoubleClicked = Signal(object)
    regionMoved = Signal(object, float, float)   # secili alan, dx, dy
    imagePicked = Signal(object)                 # tiklanan nokta (gorsel sec)
    imagePlaced = Signal(object)                 # gorselin yeni dikdortgeni
    imageMenuRequested = Signal(object)          # sag tik: ekran noktasi
    cropSelected = Signal(object)                # kirpma dikdortgeni
    selectionChanged = Signal(bool)              # tasima secimi var mi
    zoomChanged = Signal(float)

    MIN_ZOOM = 0.15
    MAX_ZOOM = 6.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self.setBackgroundBrush(QBrush(QColor("#4a4d52")))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

        self.model = None
        self.page_index = 0
        self.zoom = 1.0
        self.tool = Tool.SELECT
        self.accent = QColor("#2d7ff9")

        self._page_item: QGraphicsPixmapItem | None = None
        self._band: QGraphicsRectItem | None = None
        self._ink_item: QGraphicsPathItem | None = None
        self._origin: QPointF | None = None
        self._strokes: list[list[tuple[float, float]]] = []
        self._panning = False
        self._pan_from = None
        self._sel_rect = None      # tasima icin secili alan (PDF koordinati)
        self._sel_item = None      # secimi gosteren cerceve
        self._ghost = None         # suruklenirken imleci takip eden kopya
        self._ghost_from = None
        self.image_rect = None     # secili gorselin PDF koordinatindaki yeri
        self._img_item = None      # secim cercevesi
        self._img_handles = []     # kose tutamaclari
        self._img_mode = None      # "move" veya kose adi
        self._img_from = None
        self._img_start = None
        self._crop_mode = False    # gorsel kirpma bekleniyor mu

    # ------------------------------------------------------------------
    # kurulum
    # ------------------------------------------------------------------

    def set_model(self, model) -> None:
        self.model = model
        self.page_index = 0

    def set_tool(self, tool: Tool) -> None:
        if tool is not Tool.TEXT_MOVE:
            self.clear_selection()
        if tool is not Tool.IMAGE_EDIT:
            self.clear_image_selection()
        self.tool = tool
        if tool is Tool.SELECT:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        elif tool is Tool.TEXT_EDIT:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        elif tool is Tool.TEXT_MOVE:
            self.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
        elif tool is Tool.STYLE:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        elif tool is Tool.IMAGE_EDIT:
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def set_page(self, index: int) -> None:
        if not self.model or not self.model.is_open:
            return
        index = max(0, min(index, self.model.page_count - 1))
        self.page_index = index
        self.refresh()

    def refresh(self) -> None:
        self._scene.clear()
        self._page_item = None
        self._band = None
        self._ink_item = None
        # Sahne temizlendi; secim ogeleri artik gecersiz.
        self._sel_item = None
        self._ghost = None
        self._ghost_from = None
        self._img_item = None
        self._img_handles = []
        self._img_mode = None
        if self._sel_rect is not None:
            self._sel_rect = None
            self.selectionChanged.emit(False)
        if not self.model or not self.model.is_open:
            return
        if self.page_index >= self.model.page_count:
            self.page_index = max(0, self.model.page_count - 1)

        pix = self.model.render(self.page_index, self.zoom)
        item = QGraphicsPixmapItem(pixmap_from_pdf(pix))
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(item)
        self._page_item = item
        self._scene.setSceneRect(QRectF(item.pixmap().rect()))

    # ------------------------------------------------------------------
    # yakinlastirma
    # ------------------------------------------------------------------

    def set_zoom(self, zoom: float) -> None:
        zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, zoom))
        if abs(zoom - self.zoom) < 1e-6:
            return
        self.zoom = zoom
        self.refresh()
        self.zoomChanged.emit(zoom)

    def zoom_in(self) -> None:
        self.set_zoom(self.zoom * 1.25)

    def zoom_out(self) -> None:
        self.set_zoom(self.zoom / 1.25)

    def fit_width(self) -> None:
        if not self.model or not self.model.is_open:
            return
        rect = self.model.page_rect(self.page_index)
        if rect.width:
            margin = 36
            self.set_zoom((self.viewport().width() - margin) / rect.width)

    def fit_page(self) -> None:
        if not self.model or not self.model.is_open:
            return
        rect = self.model.page_rect(self.page_index)
        if rect.width and rect.height:
            margin = 36
            self.set_zoom(min((self.viewport().width() - margin) / rect.width,
                              (self.viewport().height() - margin) / rect.height))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self.set_zoom(self.zoom * (1.15 if delta > 0 else 1 / 1.15))
            event.accept()
        else:
            super().wheelEvent(event)

    # ------------------------------------------------------------------
    # koordinat donusumu
    # ------------------------------------------------------------------

    def _to_pdf_point(self, scene_pos: QPointF):
        return pymupdf.Point(scene_pos.x() / self.zoom, scene_pos.y() / self.zoom)

    def _to_pdf_rect(self, a: QPointF, b: QPointF):
        rect = pymupdf.Rect(min(a.x(), b.x()) / self.zoom,
                            min(a.y(), b.y()) / self.zoom,
                            max(a.x(), b.x()) / self.zoom,
                            max(a.y(), b.y()) / self.zoom)
        page = self.model.page_rect(self.page_index)
        return rect & page  # sayfa disina tasma

    # ------------------------------------------------------------------
    # fare
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if not self.model or not self.model.is_open or self._page_item is None:
            return super().mousePressEvent(event)
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)

        pos = self.mapToScene(event.position().toPoint())

        if self.tool is Tool.IMAGE_EDIT:
            if self._crop_mode:
                # Kirpma: serbest dikdortgen cizdir.
                self._origin = pos
                pen = QPen(self.accent, 1.4, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(45, 127, 249, 50))
                self._band = self._scene.addRect(QRectF(pos, pos),
                                                 pen, brush)
                return
            tutamac = self._handle_at(pos)
            if tutamac:
                self._img_mode = tutamac
                self._img_from = pos
                self._img_start = pymupdf.Rect(self.image_rect)
                return
            if (self.image_rect is not None
                    and self._img_scene_rect().contains(pos)):
                self._img_mode = "move"
                self._img_from = pos
                self._img_start = pymupdf.Rect(self.image_rect)
                return
            self.imagePicked.emit(self._to_pdf_point(pos))
            return

        if self.tool in CLICK_TOOLS:
            self.pointClicked.emit(self._to_pdf_point(pos))
            return

        if self.tool is Tool.TEXT_MOVE:
            # Iki asama: once tasinacak alani sec, sonra secimi surukle.
            if self._sel_rect is not None and self._scene_sel().contains(pos):
                self._start_ghost(pos)
            else:
                self.clear_selection()
                self._origin = pos
                pen = QPen(self.accent, 1, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(45, 127, 249, 40))
                self._band = self._scene.addRect(QRectF(pos, pos), pen, brush)
            return

        if self.tool is Tool.SELECT:
            self._panning = True
            self._pan_from = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if self.tool is Tool.DRAW:
            self._origin = pos
            self._strokes = [[(pos.x() / self.zoom, pos.y() / self.zoom)]]
            path = QPainterPath(pos)
            self._ink_item = self._scene.addPath(
                path, QPen(self.accent, 2, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            return

        if self.tool in DRAG_TOOLS:
            self._origin = pos
            pen = QPen(self.accent, 1, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(45, 127, 249, 40))
            self._band = self._scene.addRect(QRectF(pos, pos), pen, brush)
            return

        super().mousePressEvent(event)

    # --- tasima: secim ve onizleme ---------------------------------------

    def _scene_sel(self) -> QRectF:
        """Secimin sahne (ekran) koordinatlarindaki karsiligi."""
        r = self._sel_rect
        return QRectF(r.x0 * self.zoom, r.y0 * self.zoom,
                      r.width * self.zoom, r.height * self.zoom)

    def clear_selection(self) -> None:
        """Tasima secimini ve onizlemeyi kaldir."""
        for attr in ("_sel_item", "_ghost"):
            item = getattr(self, attr, None)
            if item is not None:
                try:
                    self._scene.removeItem(item)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._sel_rect = None
        self._ghost_from = None
        self.selectionChanged.emit(False)

    def _show_selection(self, pdf_rect) -> None:
        self._sel_rect = pdf_rect
        rect = self._scene_sel()
        pen = QPen(self.accent, 1.4, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(45, 127, 249, 28))
        self._sel_item = self._scene.addRect(rect, pen, brush)
        self.selectionChanged.emit(True)

    def _start_ghost(self, pos: QPointF) -> None:
        """Secili alanin yari saydam kopyasini olustur - imleci takip eder."""
        self._ghost_from = pos
        rect = self._scene_sel().toRect()
        if self._page_item is None or rect.isEmpty():
            return
        parca = self._page_item.pixmap().copy(rect)
        ghost = self._scene.addPixmap(parca)
        ghost.setOpacity(0.72)
        ghost.setPos(rect.x(), rect.y())
        ghost.setZValue(10)
        self._ghost = ghost

    # --- gorsel secimi ---------------------------------------------------

    HANDLE = 9.0              # tutamac boyu (ekran pikseli)
    MIN_HANDLE_RECT = 14.0    # bundan kucuk gorunen gorselde tutamac yok

    def show_image_selection(self, pdf_rect) -> None:
        """Secili gorselin cercevesini ve kose tutamaclarini ciz."""
        self.clear_image_selection()
        if pdf_rect is None:
            return
        self.image_rect = pymupdf.Rect(pdf_rect)
        r = self._img_scene_rect()
        pen = QPen(self.accent, 1.6, Qt.PenStyle.DashLine)
        self._img_item = self._scene.addRect(r, pen,
                                             QBrush(Qt.BrushStyle.NoBrush))
        self._img_item.setZValue(9)

        dolgu = QBrush(self.accent)
        kalem = QPen(QColor("#ffffff"), 1.2)
        h = self._handle_size(r)
        for ad, (x, y) in self._handle_points(r).items():
            item = self._scene.addRect(QRectF(x - h / 2, y - h / 2, h, h),
                                       kalem, dolgu)
            item.setZValue(10)
            item.setData(0, ad)
            self._img_handles.append(item)

    def start_crop(self) -> None:
        """Kirpma modunu ac: kullanici gorselin icinde alan secer."""
        self._crop_mode = True
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def cancel_crop(self) -> None:
        self._crop_mode = False
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def clear_image_selection(self) -> None:
        for item in list(self._img_handles):
            try:
                self._scene.removeItem(item)
            except Exception:
                pass
        self._img_handles = []
        if self._img_item is not None:
            try:
                self._scene.removeItem(self._img_item)
            except Exception:
                pass
            self._img_item = None
        self.image_rect = None
        self._img_mode = None

    def _img_scene_rect(self) -> QRectF:
        r = self.image_rect
        return QRectF(r.x0 * self.zoom, r.y0 * self.zoom,
                      r.width * self.zoom, r.height * self.zoom)

    @staticmethod
    def _handle_points(r: QRectF):
        return {"sol_ust": (r.left(), r.top()),
                "sag_ust": (r.right(), r.top()),
                "sol_alt": (r.left(), r.bottom()),
                "sag_alt": (r.right(), r.bottom())}

    def _handle_size(self, r: QRectF) -> float:
        """Tutamac boyu. Kucuk gorselde kuculur, yoksa gorseli tamamen kaplar.

        Dort kose tutamaci 9'ar piksel olunca 20 piksellik bir ikonun icinde
        tiklanacak yer kalmiyordu; tasimak da mumkun olmuyordu.
        """
        en_kucuk = min(r.width(), r.height())
        return max(5.0, min(self.HANDLE, en_kucuk / 2.2))

    def _handle_at(self, pos: QPointF):
        """Tiklama bir kose tutamacina mi denk geldi?

        Tiklama alani CIZILEN tutamaca uyar (+2 piksel tolerans). Eskiden
        alan cizimin iki kati genisti; yan taraftaki kucuk gorseller bu
        gorunmez bandin altinda kalip secilemiyordu.
        """
        if self.image_rect is None:
            return None
        r = self._img_scene_rect()
        if min(r.width(), r.height()) < self.MIN_HANDLE_RECT:
            # Ekranda cok kucuk goruneni koseden boyutlandirmak zaten
            # mumkun degil; tiklama tasima sayilsin. Boyutlandirmak
            # isteyen once yakinlastirir.
            return None
        yari = self._handle_size(r) / 2 + 2.0
        # Dort tutamac gorselin ortasinda bulusursa tasimak icin tiklanacak
        # yer kalmaz; alanlari her zaman merkezin disinda tutuyoruz.
        yari = max(2.0, min(yari, min(r.width(), r.height()) / 2 - 1.0))
        for ad, (x, y) in self._handle_points(r).items():
            if abs(pos.x() - x) <= yari and abs(pos.y() - y) <= yari:
                return ad
        return None

    def _apply_image_drag(self, pos: QPointF) -> None:
        """Surukleme sirasinda cerceveyi guncelle."""
        if self._img_start is None or self._img_from is None:
            return
        dx = (pos.x() - self._img_from.x()) / self.zoom
        dy = (pos.y() - self._img_from.y()) / self.zoom
        r = pymupdf.Rect(self._img_start)

        if self._img_mode == "move":
            yeni = pymupdf.Rect(r.x0 + dx, r.y0 + dy, r.x1 + dx, r.y1 + dy)
        else:
            x0, y0, x1, y1 = r.x0, r.y0, r.x1, r.y1
            if "sol" in self._img_mode:
                x0 += dx
            else:
                x1 += dx
            if "ust" in self._img_mode:
                y0 += dy
            else:
                y1 += dy
            # En az 6pt kalsin, ters cevrilmesin.
            if x1 - x0 < 6 or y1 - y0 < 6:
                return
            yeni = pymupdf.Rect(x0, y0, x1, y1)

        self.image_rect = yeni
        if self._img_item is not None:
            self._img_item.setRect(self._img_scene_rect())
        h = self._handle_size(self._img_scene_rect())
        noktalar = self._handle_points(self._img_scene_rect())
        for item in self._img_handles:
            ad = item.data(0)
            if ad in noktalar:
                x, y = noktalar[ad]
                item.setRect(QRectF(x - h / 2, y - h / 2, h, h))

    def mouseMoveEvent(self, event):
        if self._img_mode is not None:
            self._apply_image_drag(self.mapToScene(event.position().toPoint()))
            return

        if self.tool is Tool.IMAGE_EDIT and self.image_rect is not None:
            ad = self._handle_at(self.mapToScene(event.position().toPoint()))
            if ad in ("sol_ust", "sag_alt"):
                self.viewport().setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif ad in ("sag_ust", "sol_alt"):
                self.viewport().setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        if self._ghost is not None and self._ghost_from is not None:
            pos = self.mapToScene(event.position().toPoint())
            base = self._scene_sel()
            self._ghost.setPos(base.x() + (pos.x() - self._ghost_from.x()),
                               base.y() + (pos.y() - self._ghost_from.y()))
            return

        if self._panning and self._pan_from is not None:
            delta = event.position().toPoint() - self._pan_from
            self._pan_from = event.position().toPoint()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y())
            return

        if self._origin is None:
            return super().mouseMoveEvent(event)

        pos = self.mapToScene(event.position().toPoint())

        if self.tool is Tool.DRAW and self._ink_item is not None:
            self._strokes[-1].append((pos.x() / self.zoom, pos.y() / self.zoom))
            path = self._ink_item.path()
            path.lineTo(pos)
            self._ink_item.setPath(path)
            return

        if self._band is not None:
            self._band.setRect(QRectF(self._origin, pos).normalized())

    def mouseReleaseEvent(self, event):
        if self._img_mode is not None:
            mod, self._img_mode = self._img_mode, None
            baslangic, self._img_start = self._img_start, None
            self._img_from = None
            if (self.image_rect is not None and baslangic is not None
                    and pymupdf.Rect(self.image_rect) != baslangic):
                self.imagePlaced.emit(pymupdf.Rect(self.image_rect))
            return

        # Onizlemeyi birak -> tasimayi uygula.
        if self._ghost is not None and self._ghost_from is not None:
            pos = self.mapToScene(event.position().toPoint())
            dx = (pos.x() - self._ghost_from.x()) / self.zoom
            dy = (pos.y() - self._ghost_from.y()) / self.zoom
            kaynak = self._sel_rect
            self.clear_selection()
            if kaynak is not None and (abs(dx) > 0.4 or abs(dy) > 0.4):
                self.regionMoved.emit(kaynak, dx, dy)
            return

        if self._panning:
            self._panning = False
            self._pan_from = None
            self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self._origin is None:
            return super().mouseReleaseEvent(event)

        pos = self.mapToScene(event.position().toPoint())
        origin, self._origin = self._origin, None

        if self.tool is Tool.DRAW:
            if self._ink_item is not None:
                self._scene.removeItem(self._ink_item)
                self._ink_item = None
            strokes = [s for s in self._strokes if len(s) > 1]
            self._strokes = []
            if strokes:
                self.inkDrawn.emit(strokes)
            return

        if self._band is not None:
            self._scene.removeItem(self._band)
            self._band = None

        if self.tool is Tool.IMAGE_EDIT and self._crop_mode:
            alan = self._to_pdf_rect(origin, pos)
            self.cancel_crop()
            if not alan.is_empty and alan.width > 3 and alan.height > 3:
                self.cropSelected.emit(alan)
            return

        if self.tool is Tool.TEXT_MOVE:
            secim = self._to_pdf_rect(origin, pos)
            if secim.is_empty or secim.width < 1.5 or secim.height < 1.5:
                return
            self._show_selection(secim)
            return

        rect = self._to_pdf_rect(origin, pos)
        if rect.is_empty or rect.width < 3 or rect.height < 3:
            return
        self.regionSelected.emit(rect)

    def contextMenuEvent(self, event):
        """Gorsel aracindayken sag tik: duzenleme menusu."""
        if (self.tool is Tool.IMAGE_EDIT and self.image_rect is not None
                and self.model and self.model.is_open):
            self.imageMenuRequested.emit(event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)

    def mouseDoubleClickEvent(self, event):
        if (self.tool is Tool.SELECT and self.model and self.model.is_open
                and event.button() == Qt.MouseButton.LeftButton):
            pos = self.mapToScene(event.position().toPoint())
            self.annotDoubleClicked.emit(self._to_pdf_point(pos))
            return
        super().mouseDoubleClickEvent(event)
