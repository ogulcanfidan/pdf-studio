"""Belge modeli: PyMuPDF dokümanini sarar, geri alma yigini tutar."""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass

import pymupdf

from . import fontfix
from . import imaging
from . import verify as fontverify
from .branding import stamp_metadata


class DocumentError(Exception):
    pass


class NeighborTextLost(DocumentError):
    """Silme islemi hedef disindaki yaziya da dokundu; islem geri alindi.

    Sik yerlesimli belgelerde bir satirin sinirlari komsu satirin harflerine
    degebiliyor. Boyle bir durumda sessizce veri kaybetmektense islemi iptal
    edip kullaniciya haber veriyoruz.
    """

    def __init__(self, lost):
        self.lost = list(lost)
        ornek = ", ".join(repr(t[:40]) for t in self.lost[:3])
        super().__init__(
            "Bu satırı değiştirmek çevresindeki yazıya da dokunuyordu, "
            "işlem geri alındı. Etkilenen: %s" % ornek)


@dataclass
class TextSpan:
    """Duzenlenebilir metin birimi: sayfadaki bir SATIR.

    Neden parca (span) degil satir: harf arali (letter-spaced) basliklarda
    PyMuPDF her harfi ayri parca olarak cikariyor ('P', ' ', 'R', ...), yani
    parca birimiyle tiklayinca tek harf duzenlenebiliyordu. Satir hem
    kullanicinin bekledigi birim hem de harf araligini olcebildigimiz yer.
    """

    rect: pymupdf.Rect           # satirin sinirlari
    text: str                    # satirin tam metni
    size: float
    font: str
    color: tuple
    block_rect: pymupdf.Rect
    block_text: str
    origin: tuple = (0.0, 0.0)   # satirin taban cizgisi baslangici
    line_count: int = 1          # ait oldugu blogun satir sayisi
    tracking: float = 0.0        # karakter basi fazladan bosluk (pt)
    mixed_fonts: bool = False    # satirda birden fazla font/punto var mi


@dataclass
class TextStyle:
    """Bir yazinin bicimi - stil kopyalamada tasinan bilgi.

    apply_size varsayilan olarak False: punto kopyalanmaz. Punto da
    kopyalaninca satir buyuyup ustteki yazinin uzerine biniyordu; punto
    degisikligi metin duzenleme penceresinden yapiliyor.
    """

    font: str
    size: float
    color: tuple
    tracking: float = 0.0
    apply_size: bool = False

    def label(self) -> str:
        r, g, b = self.color
        return "%s · %.1f pt · #%02x%02x%02x" % (
            self.font, self.size, int(r * 255), int(g * 255), int(b * 255))


@dataclass
class ReplaceReport:
    """Metin degistirmenin nasil sonuclandigini anlatir."""

    font_name: str          # kullanilan font
    embedded: bool          # belgenin kendi gomulu fontu mu
    missing_chars: str      # fontta KESIN olmayan karakterler
    method: str             # "baseline" (birebir konum) veya "kutu" (sarmali)
    uncertain_chars: str = ""   # dogrulanamayan karakterler (bkz. asagi)
    covered: bool = False       # eski yazi silinmedi, uzeri ortuldu

    @property
    def is_exact(self) -> bool:
        return (self.embedded and not self.missing_chars
                and not self.uncertain_chars)


def escape_html(text: str) -> str:
    """Duz metni insert_htmlbox icin guvenli HTML'e cevir."""
    out = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return out.replace("\n", "<br/>")


def normalize_font_name(name: str) -> str:
    """'ABCDEF+Poppins-Regular' ve 'Poppins Regular' ayni anahtara insin."""
    if not name:
        return ""
    if len(name) > 7 and name[6] == "+":
        name = name[7:]          # alt kume (subset) oneki
    return "".join(ch for ch in name.lower() if ch.isalnum())


def sfnt_names(buffer) -> set:
    """Font dosyasinin 'name' tablosundaki aile/tam/PostScript adlarini ver.

    Neden gerekli: get_text() bir parcanin fontunu PostScript adiyla bildiriyor
    ('ArialMT'), PDF'teki /BaseFont ise aile adi olabiliyor ('Arial Regular').
    Ikisini eslestirmenin guvenilir yolu adlari font dosyasinin kendisinden
    okumak. Ilgili nameID'ler: 1=aile, 4=tam ad, 6=PostScript adi.
    """
    names = set()
    try:
        data = bytes(buffer)
        if len(data) < 12:
            return names

        offset = 0
        if data[:4] == b"ttcf":          # TrueType Collection -> ilk font
            offset = struct.unpack(">I", data[12:16])[0]

        num_tables = struct.unpack(">H", data[offset + 4:offset + 6])[0]
        table_offset = None
        for i in range(num_tables):
            rec = offset + 12 + i * 16
            if data[rec:rec + 4] == b"name":
                table_offset = struct.unpack(">I", data[rec + 8:rec + 12])[0]
                break
        if table_offset is None:
            return names

        count, storage_offset = struct.unpack(
            ">HH", data[table_offset + 2:table_offset + 6])
        storage = table_offset + storage_offset

        for i in range(count):
            rec = table_offset + 6 + i * 12
            platform, _enc, _lang, name_id, length, off = struct.unpack(
                ">HHHHHH", data[rec:rec + 12])
            if name_id not in (1, 4, 6):
                continue
            raw = data[storage + off:storage + off + length]
            try:
                text = (raw.decode("utf-16-be") if platform in (0, 3)
                        else raw.decode("latin-1"))
            except Exception:
                continue
            text = text.strip("\x00 \t")
            if text:
                names.add(text)
    except Exception:
        # Bozuk/desteklenmeyen font tablosu sessizce atlanir; cagiran taraf
        # zaten yedek fonta duser.
        pass
    return names


#: Font adlarindaki kalinlik sozcukleri -> sayisal agirlik.
#: Uzun olanlar once denenmeli ("extrabold" icinde "bold" gecer).
WEIGHT_WORDS = (
    ("extrabold", 800), ("ultrabold", 800), ("semibold", 600),
    ("demibold", 600), ("extralight", 200), ("ultralight", 200),
    ("hairline", 100), ("black", 900), ("heavy", 900), ("bold", 700),
    ("medium", 500), ("light", 300), ("thin", 100), ("book", 400),
    ("roman", 400), ("normal", 400), ("regular", 400),
)
ITALIC_WORDS = ("italic", "oblique", "italique", "kursiv", "cursiva")


def font_style_key(name: str):
    """Font adindan (agirlik, italik) cikar.

    Neden gerekli: 'Poppins-SemiBold' ile 'Poppins' ayni aileden ama ayni
    yazi DEGIL. Onek eslestirmesi bunlari birbirine karistirip yanlis
    kalinlikta yazi ciziyordu.
    """
    key = normalize_font_name(name)
    agirlik = None
    for word, value in WEIGHT_WORDS:
        if word in key:
            agirlik = value
            break
    italik = any(word in key for word in ITALIC_WORDS)
    return (agirlik if agirlik is not None else 400, italik)


def font_family_root(name: str) -> str:
    """Font adindan kalinlik/stil sozcuklerini atip aile kokunu ver.

    'Arial Regular' ve 'ArialMT' ayni aile; 'NotoSerif-Regular' degil.
    """
    key = normalize_font_name(name)
    for word, _ in WEIGHT_WORDS:
        key = key.replace(word, "")
    for word in ITALIC_WORDS:
        key = key.replace(word, "")
    return key


def same_font_family(a: str, b: str) -> bool:
    """Iki font adi ayni aileden mi?"""
    ka, kb = font_family_root(a), font_family_root(b)
    if not ka or not kb:
        return True                  # karar veremiyoruz, engelleme
    kisa = min(len(ka), len(kb), 5)
    return ka[:kisa] == kb[:kisa]


def font_match_score(query: str, candidate: str) -> int:
    """Aday font adi arananla ne kadar uyuyor? (-1 = uymuyor)"""
    if not query or not candidate:
        return -1
    if query == candidate:
        return 1000
    if font_style_key(query) != font_style_key(candidate):
        return -1                    # ayni aile olsa bile farkli kalinlik
    if candidate.startswith(query) or query.startswith(candidate):
        ortak = 0
        for a, b in zip(query, candidate):
            if a != b:
                break
            ortak += 1
        return 100 + ortak
    return -1


def _trace_color(value):
    """get_texttrace rengini (int ya da dizi) 0..1 ucluye cevir."""
    if value is None:
        return (0.0, 0.0, 0.0)
    if isinstance(value, (int, float)):
        c = int(value)
        return (((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0,
                (c & 255) / 255.0)
    try:
        parts = [float(v) for v in value]
    except (TypeError, ValueError):
        return (0.0, 0.0, 0.0)
    if len(parts) == 1:                       # gri
        return (parts[0], parts[0], parts[0])
    if len(parts) >= 3:
        if max(parts[:3]) > 1.0:              # 0..255 olcegi
            return tuple(v / 255.0 for v in parts[:3])
        return tuple(parts[:3])
    return (0.0, 0.0, 0.0)


def system_font_files():
    """Windows'ta kurulu font dosyalarinin yollarini ver (kullanici + sistem)."""
    roots = [os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")]
    local = os.environ.get("LOCALAPPDATA")
    if local:
        # Kullanicinin kendi kurdugu fontlar (Google Fonts vb.) buraya gider.
        roots.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))

    files = []
    for root in roots:
        try:
            for entry in os.listdir(root):
                if entry.lower().endswith((".ttf", ".otf", ".ttc")):
                    files.append(os.path.join(root, entry))
        except OSError:
            continue
    return files


class PdfDocument:
    """Acik PDF + geri al/yinele.

    Geri alma, her degisiklikten once belgenin tamamini bayta cevirip yigina
    koyarak calisir. Basit ama her islem icin (sayfa tasima, redaksiyon, form)
    eksiksiz calisiyor; yigin UNDO_LIMIT ile sinirli tutuluyor.
    """

    UNDO_LIMIT = 25

    def __init__(self) -> None:
        self.doc = None
        self.path = None
        self.dirty = False
        self._undo = []
        self._redo = []
        # {sayfa: {normalize edilmis font adi: (buffer, pymupdf.Font)}}
        self._font_cache = {}
        # Sistem fontu aramasi pahali; belge degisse de gecerli kalir.
        self._system_fonts = {}
        # {sayfa: {font: o fontla yazili karakterler}}
        self._char_cache = {}

    def _invalidate_fonts(self) -> None:
        """doc nesnesi degisince font onbellekleri gecersizdir."""
        self._font_cache = {}
        self._char_cache = {}

    # ------------------------------------------------------------------
    # yasam dongusu
    # ------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self.doc is not None

    @property
    def page_count(self) -> int:
        return self.doc.page_count if self.doc else 0

    def open(self, path: str, password=None) -> None:
        doc = pymupdf.open(path)
        if doc.needs_pass:
            if not password or not doc.authenticate(password):
                doc.close()
                raise DocumentError("Belge parola korumali; parola gerekli veya yanlis.")
        self.close()
        self.doc = doc
        self.path = path
        self.dirty = False
        self._invalidate_fonts()

    def new(self) -> None:
        self.close()
        self.doc = pymupdf.open()
        self.doc.new_page()
        self._invalidate_fonts()
        self.path = None
        self.dirty = True

    def close(self) -> None:
        if self.doc is not None:
            self.doc.close()
        self.doc = None
        self.path = None
        self.dirty = False
        self._undo = []
        self._redo = []
        self._invalidate_fonts()

    def save(self, path=None, compress: bool = False) -> str:
        if not self.doc:
            raise DocumentError("Acik belge yok.")
        target = path or self.path
        if not target:
            raise DocumentError("Kaydedilecek dosya yolu yok.")

        opts = dict(garbage=4, deflate=True, clean=True)
        if compress:
            opts.update(deflate_images=True, deflate_fonts=True)
            try:
                self.doc.subset_fonts()
            except Exception:
                # Font alt kumeleme her belgede calismaz; kayit yine de surmeli.
                pass

        stamp_metadata(self.doc)

        # Ayni dosyanin uzerine dogrudan yazmak PyMuPDF'te hata verir, once
        # bayta aliyoruz. Farkli hedefte de ayni yolu izleyip acik belgeyi
        # yeni dosyaya baglariz.
        data = self.doc.tobytes(**opts)
        self.doc.close()
        self.doc = None
        with open(target, "wb") as fh:
            fh.write(data)
        self.doc = pymupdf.open(target)
        self._invalidate_fonts()

        self.path = target
        self.dirty = False
        return target

    # ------------------------------------------------------------------
    # geri al / yinele
    # ------------------------------------------------------------------

    def snapshot(self) -> None:
        """Degisiklik yapmadan hemen ONCE cagir."""
        if not self.doc:
            return
        self._undo.append(self.doc.tobytes())
        if len(self._undo) > self.UNDO_LIMIT:
            self._undo.pop(0)
        self._redo = []
        self.dirty = True

    def drop_snapshot(self) -> None:
        """Hicbir sey degistirmeyen islemin anlik goruntusunu yigindan at."""
        if self._undo:
            self._undo.pop()

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def _restore(self, data: bytes) -> None:
        self.doc.close()
        self.doc = pymupdf.open(stream=data, filetype="pdf")
        self._invalidate_fonts()

    def undo(self) -> None:
        if not self._undo or not self.doc:
            return
        self._redo.append(self.doc.tobytes())
        self._restore(self._undo.pop())
        self.dirty = True

    def redo(self) -> None:
        if not self._redo or not self.doc:
            return
        self._undo.append(self.doc.tobytes())
        self._restore(self._redo.pop())
        self.dirty = True

    # ------------------------------------------------------------------
    # render
    # ------------------------------------------------------------------

    def render(self, index: int, zoom: float = 1.0):
        page = self.doc.load_page(index)
        return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)

    def page_rect(self, index: int):
        return self.doc.load_page(index).rect

    # ------------------------------------------------------------------
    # sayfa islemleri
    # ------------------------------------------------------------------

    def rotate(self, index: int, delta: int) -> None:
        self.snapshot()
        page = self.doc.load_page(index)
        page.set_rotation((page.rotation + delta) % 360)

    def delete_pages(self, indices) -> None:
        if not indices:
            return
        if len(set(indices)) >= self.page_count:
            raise DocumentError("Belgedeki tum sayfalar silinemez.")
        self.snapshot()
        for i in sorted(set(indices), reverse=True):
            self.doc.delete_page(i)

    def move_page(self, src: int, dst: int) -> None:
        """src'deki sayfayi dst indeksine tasi (dst = tasima SONRASI konum).

        PyMuPDF'in move_page(pno, to) cagrisi "to indeksinin onune ekle"
        anlaminda ve to == page_count "bad page number" hatasi veriyor;
        sona tasima -1 ile yapiliyor.
        """
        if src == dst:
            return
        if not (0 <= src < self.page_count and 0 <= dst < self.page_count):
            raise DocumentError("Gecersiz sayfa numarasi.")

        if dst > src:
            to = dst + 1
            if to >= self.page_count:
                to = -1  # sona tasi
        else:
            to = dst

        self.snapshot()
        self.doc.move_page(src, to)

    def duplicate_page(self, index: int) -> None:
        self.snapshot()
        self.doc.fullcopy_page(index, index + 1)

    def insert_blank(self, index: int) -> None:
        self.snapshot()
        ref = self.doc.load_page(max(0, min(index, self.page_count - 1))).rect
        self.doc.new_page(pno=index, width=ref.width, height=ref.height)

    def append_pdf(self, path: str) -> int:
        other = pymupdf.open(path)
        if other.needs_pass:
            other.close()
            raise DocumentError("Eklenecek PDF parola korumali.")
        added = other.page_count
        self.snapshot()
        self.doc.insert_pdf(other)
        other.close()
        return added

    def extract_pages(self, indices, path: str) -> None:
        out = pymupdf.open()
        for i in sorted(set(indices)):
            out.insert_pdf(self.doc, from_page=i, to_page=i)
        out.save(path, garbage=4, deflate=True)
        out.close()

    # ------------------------------------------------------------------
    # metin
    # ------------------------------------------------------------------

    #: Tiklama toleransi (pt). Kucuk yazilarda tam harfin uzerine denk
    #: getirmek zor oldugu icin yakini da kabul ediyoruz.
    HIT_TOLERANCE = 5.0

    def find_span_at(self, index: int, point, tolerance: float = None):
        """Noktanin uzerindeki (ya da en yakin) SATIRI dondur."""
        page = self.doc.load_page(index)
        data = page.get_text("dict")
        tol = self.HIT_TOLERANCE if tolerance is None else tolerance

        tam = None
        en_yakin = None
        en_kisa = tol + 1.0

        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue
            brect = pymupdf.Rect(block["bbox"])
            block_text = "\n".join(
                "".join(s["text"] for s in line.get("spans", []))
                for line in block.get("lines", [])
            )
            line_count = len(block.get("lines", []))

            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                lrect = pymupdf.Rect(line["bbox"])

                if lrect.contains(point):
                    # EN SON cizilen kazanir. Ortulen (silinmeyen) eski yazi
                    # sayfada duruyor; ustune yenisi yazilinca tiklayinca
                    # gorunmeyen eskisi secilip duzenleme saciyordu.
                    tam = (line, lrect, brect, block_text, line_count)
                    continue

                # Tam isabet yoksa en yakin satiri aday tut.
                dx = max(lrect.x0 - point.x, 0, point.x - lrect.x1)
                dy = max(lrect.y0 - point.y, 0, point.y - lrect.y1)
                uzaklik = (dx * dx + dy * dy) ** 0.5
                if uzaklik <= en_kisa:
                    en_kisa = uzaklik
                    en_yakin = (line, lrect, brect, block_text, line_count)

        secilen = tam or (en_yakin if en_kisa <= tol else None)
        if not secilen:
            return None
        return self._line_to_span(index, *secilen)

    def _line_to_span(self, index, line, lrect, brect, block_text,
                      line_count) -> TextSpan:
        """Bir satiri TextSpan'e cevir; harf araligini da olc."""
        spans = line["spans"]
        text = "".join(s["text"] for s in spans)

        # Satirda birden fazla bicim olabilir; en uzun parcayi temel al.
        lead = max(spans, key=lambda s: len(s.get("text", "")))
        color_int = int(lead.get("color", 0))
        size = float(lead.get("size", 11.0))
        font_name = lead.get("font", "helv")
        origin = tuple(spans[0].get("origin", (lrect.x0, lrect.y1)))

        mixed = any(s.get("font") != font_name
                    or abs(float(s.get("size", size)) - size) > 0.1
                    for s in spans)

        # Harf araligi: gercek satir genisligi ile fontun dogal genisligi
        # arasindaki fark, karakter basina dagitilir. Aralik yoksa ~0 cikar.
        tracking = 0.0
        found = self._font_for_span_name(index, font_name)
        if found and len(text) > 1:
            natural = found[1].text_length(text, fontsize=size)
            tracking = (lrect.width - natural) / (len(text) - 1)
            if abs(tracking) < 0.05:
                tracking = 0.0

        return TextSpan(
            rect=lrect,
            text=text,
            size=size,
            font=font_name,
            color=(((color_int >> 16) & 255) / 255.0,
                   ((color_int >> 8) & 255) / 255.0,
                   (color_int & 255) / 255.0),
            block_rect=brect,
            block_text=block_text,
            origin=origin,
            line_count=max(1, line_count),
            tracking=tracking,
            mixed_fonts=mixed,
        )

    # --- gomulu font erisimi -------------------------------------------

    def _page_font_table(self, index: int) -> dict:
        """Sayfadaki gomulu fontlari {normalize ad: (buffer, Font)} olarak ver."""
        if index in self._font_cache:
            return self._font_cache[index]

        table = {}
        page = self.doc.load_page(index)
        for row in page.get_fonts(full=True):
            xref, basefont = row[0], row[3]
            try:
                info = self.doc.extract_font(xref)
                buffer = info[3]
                if not buffer:
                    continue          # gomulu degil (Base14 vb.)
                font = pymupdf.Font(fontbuffer=buffer)
            except Exception:
                continue              # bozuk/desteklenmeyen font atlanir

            # Alt kume fontlardan unicode tablosu atilmis olabilir; o hâlde
            # yeniden yazarken PyMuPDF baska bir font koyuyor. cmap'i
            # sayfadaki gercek gliflerden geri kurmayi dene.
            safe_chars = None
            try:
                usable = bool(font.valid_codepoints())
            except Exception:
                usable = False
            if not usable:
                fixed = fontfix.repair(self.doc, page, xref, buffer, basefont)
                if not fixed:
                    # Ad eslesmiyor olabilir; fontun kendi adiyla tekrar dene.
                    for alt in sfnt_names(buffer):
                        fixed = fontfix.repair(self.doc, page, xref, buffer,
                                               alt)
                        if fixed:
                            break
                if fixed:
                    buffer, font, safe_chars = fixed

            entry = (buffer, font, safe_chars)
            # Font dosyasinin kendi adlari + PDF'teki adlar; hepsi anahtar
            # olsun ki span.font hangisini bildiriyorsa bulunabilsin.
            names = sfnt_names(buffer)
            names.add(basefont)
            names.add(getattr(font, "name", "") or "")
            for name in names:
                key = normalize_font_name(name)
                if key:
                    table.setdefault(key, entry)

        self._font_cache[index] = table
        return table

    def _system_font(self, span_font: str):
        """Kurulu fontlar arasinda ayni aileyi ara (alt kume yetmediginde).

        CV sablonlari cogu zaman kullanicinin kendi kurdugu bir Google
        fontunu kullaniyor; gomulu alt kume yetersiz kalinca tam surumu
        sistemden bulabilirsek gorunum birebir korunur.
        """
        key = normalize_font_name(span_font)
        if not key:
            return None
        if key in self._system_fonts:
            return self._system_fonts[key]

        for path in system_font_files():
            try:
                with open(path, "rb") as fh:
                    buffer = fh.read()
                names = {normalize_font_name(n) for n in sfnt_names(buffer)}
            except Exception:
                continue
            # Kalinlik/italik uyusmayan dosyayi alma: 'Poppins-SemiBold'
            # ararken duz Poppins'i dondurmek yaziyi inceltiyordu.
            if any(font_match_score(key, n) > 0 for n in names):
                try:
                    entry = (buffer, pymupdf.Font(fontbuffer=buffer), None)
                except Exception:
                    continue
                self._system_fonts[key] = entry
                return entry

        self._system_fonts[key] = None
        return None

    #: Aile bulunamadiginda denenecek sistem aileleri (sirayla).
    FALLBACK_FAMILIES = ("arial", "segoeui", "calibri", "tahoma", "verdana",
                         "dejavusans", "notosans")

    def _weight_fallback(self, font_name: str):
        """Ayni KALINLIKTA bir sistem fontu bul.

        Gomulu font kullanilamadiginda duz 'helv'e dusmek yaziyi inceltiyor;
        kalin bir basligin stilini kopyalayinca kalinlik kayboluyordu. Burada
        once ayni aile, sonra yaygin aileler arasinda ayni agirlikta olan
        aranir.
        """
        hedef = font_style_key(font_name)
        anahtar = ("wf", hedef)
        if anahtar in self._system_fonts:
            return self._system_fonts[anahtar]

        aile = normalize_font_name(font_name)
        for word, _ in WEIGHT_WORDS:
            aile = aile.replace(word, "")
        tercih = [aile] + [f for f in self.FALLBACK_FAMILIES if f != aile]

        adaylar = []
        for path in system_font_files():
            try:
                with open(path, "rb") as fh:
                    buffer = fh.read()
                names = {normalize_font_name(n) for n in sfnt_names(buffer)}
            except Exception:
                continue
            if not names:
                continue
            if not any(font_style_key(n) == hedef for n in names):
                continue
            for sira, istenen in enumerate(tercih):
                if istenen and any(n.startswith(istenen) for n in names):
                    adaylar.append((sira, buffer))
                    break

        entry = None
        if adaylar:
            adaylar.sort(key=lambda t: t[0])
            try:
                buffer = adaylar[0][1]
                entry = (buffer, pymupdf.Font(fontbuffer=buffer), None)
            except Exception:
                entry = None

        self._system_fonts[anahtar] = entry
        return entry

    def _font_for_span_name(self, index: int, font_name: str):
        """Font adina gore gomulu fontu bul; yoksa None.

        Eslestirme KALINLIK DUYARLI: 'Poppins-SemiBold' ararken aile adi
        'Poppins' ile eslesip Regular'i dondurmesin diye.
        """
        table = self._page_font_table(index)
        key = normalize_font_name(font_name)
        if not key:
            return None
        if key in table:
            return table[key]

        en_iyi, en_iyi_puan = None, 0
        for name, entry in table.items():
            puan = font_match_score(key, name)
            if puan > en_iyi_puan:
                en_iyi, en_iyi_puan = entry, puan
        return en_iyi

    def _font_for_span(self, index: int, span: TextSpan):
        return self._font_for_span_name(index, span.font)

    def _chars_drawn_with(self, index: int, font_name: str) -> set:
        """Sayfada bu fontla YAZILI karakterler - en guvenilir kanit.

        Alt kume araclari Identity-H fontlarda 'cmap' tablosunu atiyor;
        o zaman has_glyph her karakter icin 0 donuyor (yalan). Belgede o
        fontla zaten cizilmis karakterler ise tartismasiz calisiyor.
        """
        key = normalize_font_name(font_name)
        cache = self._char_cache.setdefault(index, None)
        if cache is None:
            cache = {}
            page = self.doc.load_page(index)
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for sp in line.get("spans", []):
                        k = normalize_font_name(sp.get("font", ""))
                        if k:
                            cache.setdefault(k, set()).update(sp.get("text", ""))
            self._char_cache[index] = cache

        if key in cache:
            return cache[key]
        for name, chars in cache.items():
            if name.startswith(key) or key.startswith(name):
                return chars
        return set()

    @staticmethod
    def _cmap_usable(font) -> bool:
        """Fontun unicode tablosu guvenilir mi?

        valid_codepoints() bos donuyorsa cmap atilmistir; has_glyph'in
        cevabi anlamsizdir (font yine de dogru ciziyor).
        """
        try:
            return len(font.valid_codepoints()) > 0
        except Exception:
            return False

    def _check_glyphs(self, font, text: str, known: set):
        """(kesin_eksik, dogrulanamayan) karakterleri ver."""
        aday = {ch for ch in text if not ch.isspace() and ch not in known}
        if not aday:
            return "", ""

        if not self._cmap_usable(font):
            # has_glyph guvenilmez: belgede gorulmeyen karakterleri
            # "bilinmiyor" say, fontu yine de kullan.
            return "", "".join(sorted(aday))

        eksik = {ch for ch in aday if font.has_glyph(ord(ch)) == 0}
        return "".join(sorted(eksik)), ""

    def capture_style(self, index: int, point):
        """Tiklanan yazinin bicimini al (stil kopyalama icin)."""
        span = self.find_span_at(index, point)
        if span is None:
            return None
        return TextStyle(font=span.font, size=span.size, color=span.color,
                         tracking=span.tracking)

    def move_text(self, index: int, span: TextSpan, dx: float,
                  dy: float) -> ReplaceReport:
        """Satiri oldugu gibi baska bir konuma tasi."""
        return self.replace_text(index, span, span.text, offset=(dx, dy))

    # --- secili alani tasima (tek harf de olabilir) ----------------------

    def chars_in(self, index: int, rect):
        """Dikdortgenin icindeki karakterleri konumlariyla ver.

        Tasima icin satir degil KARAKTER cozunurlugu gerekiyor: kullanici
        tek bir harfi de tasiyabilmeli.
        """
        page = self.doc.load_page(index)
        hedef = pymupdf.Rect(rect)
        out = []
        try:
            items = page.get_texttrace()
        except Exception:
            return out

        for item in items:
            if item.get("type") != 0:
                continue
            font_adi = item.get("font", "")
            punto = float(item.get("size", 11.0))
            renk = _trace_color(item.get("color"))
            for ch in item.get("chars", []):
                try:
                    ucs, _gid, origin, bbox = ch[0], ch[1], ch[2], ch[3]
                except (IndexError, TypeError):
                    continue
                kutu = pymupdf.Rect(bbox)
                if kutu.is_empty:
                    continue
                ortak = kutu & hedef
                # Merkezi secimin icindeyse o karakter seciliye dahildir.
                if ortak.is_empty or ortak.get_area() < kutu.get_area() * 0.35:
                    continue
                out.append({
                    "char": chr(int(ucs)),
                    "origin": (float(origin[0]), float(origin[1])),
                    "rect": kutu,
                    "font": font_adi,
                    "size": punto,
                    "color": renk,
                })
        return out

    def move_region(self, index: int, rect, dx: float, dy: float):
        """Secili alandaki karakterleri oldugu gibi kaydir.

        Her karakter kendi konumuyla yeniden yazilir, bu yuzden harf
        araliklari ve hizalama birebir korunur.
        """
        chars = self.chars_in(index, rect)
        if not chars:
            raise DocumentError("Seçilen alanda taşınacak yazı yok.")

        page = self.doc.load_page(index)
        sayfa = page.rect
        for c in chars:
            if not (sayfa.x0 - 1 <= c["origin"][0] + dx <= sayfa.x1 + 1
                    and sayfa.y0 - 1 <= c["origin"][1] + dy <= sayfa.y1 + 1):
                raise DocumentError("Hedef konum sayfanın dışına taşıyor.")

        # Font cozumlemesi icin sahte bir span uret (mevcut boru hattini kullan).
        ilk = chars[0]
        proto = TextSpan(
            rect=pymupdf.Rect(rect), text="".join(c["char"] for c in chars),
            size=ilk["size"], font=ilk["font"], color=ilk["color"],
            block_rect=pymupdf.Rect(rect), block_text="",
            origin=ilk["origin"],
        )

        before = self._line_inventory(index)
        self.snapshot()
        page = self.doc.load_page(index)

        # Eski karakterleri sil; komsuya dokunursa ortmeye gec.
        for c in chars:
            page.add_redact_annot(c["rect"])
        page.apply_redactions(images=0, graphics=0, text=0)

        covered = False
        kayip = self._lost_lines(before, self._line_inventory(index), proto,
                                 ignore_rects=[c["rect"] for c in chars])
        if kayip:
            self._rollback_to_snapshot()
            page = self.doc.load_page(index)
            self._cover_rects(page, [c["rect"] for c in chars])
            covered = True
        else:
            # Silme calisti mi, GERCEKTEN olc. Bazi belgelerde harfin
            # murekkebi bildirilen kutusunun disina tasiyor ve geride iz
            # kaliyor; oyleyse ustunu ortelim.
            artik = [c["rect"] for c in chars
                     if self._ink_bounds(page, c["rect"]) is not None]
            if artik:
                self._cover_rects(page, artik)
                covered = True

        # Fontu KARAKTER BASINA degil, kaynak fonta gore BIR KEZ coz.
        # Aksi halde tek bir harf baska fonta dusup ("Fidan"daki 'd')
        # yazinin ortasinda farkli gorunuyordu.
        gruplar = {}
        for c in chars:
            gruplar.setdefault(c["font"], []).append(c["char"])
        cozulen = {}
        gomulu_kaldi = True
        for ad, harf in gruplar.items():
            secilen = self._resolve_font(index, ad, "".join(harf))
            cozulen[ad] = secilen
            belge_fontu = self._font_for_span_name(index, ad)
            if not belge_fontu or belge_fontu[1] is not secilen:
                gomulu_kaldi = False

        yazildi = 0
        for c in chars:
            font = cozulen[c["font"]]
            writer = pymupdf.TextWriter(page.rect)
            writer.append(pymupdf.Point(c["origin"][0] + dx,
                                        c["origin"][1] + dy),
                          c["char"], font=font, fontsize=c["size"])
            writer.write_text(page, color=c["color"])
            yazildi += 1

        self._font_cache.pop(index, None)
        self._char_cache.pop(index, None)

        kullanilan = cozulen.get(ilk["font"])
        return ReplaceReport(
            font_name=(getattr(kullanilan, "name", "") or ilk["font"]),
            embedded=gomulu_kaldi, missing_chars="", method="karakter",
            covered=covered)

    def _cover_rects(self, page, rects) -> None:
        """Verilen kutularin uzerini ort, komsu harfleri geri ciz."""
        if rects:
            self._cover_and_restore(page, None, list(rects))

    def _other_text_rects_for(self, page, alan, haric):
        """Verilen alanin disindaki metnin murekkep sutunlari."""
        out = []
        try:
            yakin = pymupdf.Rect(alan) + (-2, -16, 2, 16)
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    lrect = pymupdf.Rect(line["bbox"])
                    if lrect.is_empty or (lrect & yakin).is_empty:
                        continue
                    # Tasinan karakterleri komsu sayma.
                    if any(not (lrect & pymupdf.Rect(r)).is_empty
                           and (lrect & pymupdf.Rect(r)).get_area()
                           >= pymupdf.Rect(r).get_area() * 0.6 for r in haric):
                        devam = True
                    out.extend(self._ink_columns(page, lrect))
        except Exception:
            pass
        return out

    @staticmethod
    def _font_renders_all(font, text: str) -> bool:
        """Font bu harflerin HEPSINI gercekten cizebiliyor mu?

        has_glyph "evet" dese bile PyMuPDF yazarken tek bir harf icin baska
        bir fonta (Noto Serif) gecebiliyor; gomulu alt kume fontlarda tek bir
        glifin bozuk olmasi yeterli. Tek guvenilir yol: deneme amacli yazip
        sonucu geri okumak.
        """
        harfler = "".join(sorted({c for c in (text or "") if not c.isspace()}))
        if not harfler:
            return True
        beklenen_ad = getattr(font, "name", "") or ""
        if not beklenen_ad:
            return True
        try:
            gecici = pymupdf.open()
            sayfa = gecici.new_page(width=40 + len(harfler) * 26, height=60)
            writer = pymupdf.TextWriter(sayfa.rect)
            writer.append(pymupdf.Point(6, 40), harfler, font=font,
                          fontsize=18)
            writer.write_text(sayfa)

            uygun = True
            for block in sayfa.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    for sp in line.get("spans", []):
                        ad = sp.get("font", "")
                        if not ad:
                            continue
                        if not same_font_family(ad, beklenen_ad):
                            uygun = False
            gecici.close()
            return uygun
        except Exception:
            return True          # olcemedik, cagirana engel olma

    def _resolve_font(self, index: int, font_name: str, sample: str):
        """Bir metin parcasinin TAMAMI icin tek font sec.

        Iki kural var, ikisi de gercek hatalardan geliyor:

        1. Karar KARAKTER BASINA verilmez. Eskiden her harf ayri
           degerlendiriliyordu ve 'Fidan' kelimesindeki 'd' yedege dusup
           kelimenin ortasinda farkli gorunuyordu.
        2. has_glyph'in "evet"i yetmez. PyMuPDF yazarken tek bir harf icin
           sessizce baska bir fonta (Noto Serif) gecebiliyor; bu yuzden font
           kabul edilmeden once harfler deneme amacli YAZILIP sonuc okunur.
        """
        harfler = [c for c in (sample or "") if not c.isspace()]
        metin = "".join(harfler)

        found = self._font_for_span_name(index, font_name)
        if found:
            font = found[1]
            try:
                guvenilir = bool(font.valid_codepoints())
            except Exception:
                guvenilir = False
            kapsiyor = True
            if guvenilir and harfler:
                try:
                    kapsiyor = all(font.has_glyph(ord(c)) for c in harfler)
                except Exception:
                    kapsiyor = True
            # NOT: _font_renders_all burada BILEREK kullanilmiyor.
            # Tek bir harf cizilemedigi icin tum kelimeyi yedek fonta
            # dusurmek, belgenin kendi fontunu gereksiz yere kaybettiriyor.
            # Bozuk glif nadir; gomulu fontu korumak daha az zarar veriyor.
            if kapsiyor:
                return font

        system = self._system_font(font_name)
        if system:
            return system[1]

        yedek = self._weight_fallback(font_name)
        if yedek:
            return yedek[1]
        return pymupdf.Font("helv")

    def restyle_text(self, index: int, span: TextSpan, style,
                     apply_size: bool = False) -> ReplaceReport:
        """Satirin metnini koruyup bicimini degistir.

        apply_size=False (varsayilan): punto kopyalanmaz, satir yerinde kalir.
        """
        kullanilan = TextStyle(font=style.font, size=style.size,
                               color=style.color, tracking=style.tracking,
                               apply_size=apply_size)
        return self.replace_text(index, span, span.text, style=kullanilan)

    def resize_text(self, index: int, span: TextSpan, new_text: str,
                    size: float = None, color=None,
                    whole_block: bool = False) -> ReplaceReport:
        """Metni degistirirken punto ve/veya rengi de ayarla."""
        stil = TextStyle(font=span.font,
                         size=size if size is not None else span.size,
                         color=color if color is not None else span.color,
                         tracking=span.tracking,
                         apply_size=size is not None)
        return self.replace_text(index, span, new_text,
                                 whole_block=whole_block, style=stil)

    def replace_text(self, index: int, span: TextSpan, new_text: str,
                     whole_block: bool = False, offset=None,
                     style=None) -> ReplaceReport:
        """Mevcut metni sil, yerine yenisini AYNI fontla ve konumda yaz.

        Iki yol var:
          * baseline - tek satirlik degisiklikte TextWriter ile span'in
            origin'ine yazilir; konum ve taban cizgisi birebir korunur.
          * kutu     - cok satirli/uzun metinde insert_htmlbox sarmali yazar;
            gomulu font @font-face ile aktarilir.

        Redaksiyon yalnizca metni kaldirir (images=0, graphics=0), altindaki
        resim ve cizimler korunur.
        """
        page = self.doc.load_page(index)

        # ONEMLI: fontu redaksiyondan ONCE cikar - apply_redactions artik
        # kullanilmayan font kaynagini sayfadan atabiliyor.
        probe = new_text.replace("\n", " ")

        # SILINECEK yer her zaman ozgun span; YAZILACAK bicim/konum stil ve
        # kaydirma ile degisebilir (tasima ve stil kopyalama bunu kullanir).
        write = self._derive_span(span, offset, style)
        known = self._chars_drawn_with(index, write.font)

        buffer = font = None
        embedded = False
        missing = uncertain = ""
        mismatch = 0.0
        # Gorsel dogrulama ozgun span'e gore yapiliyor; punto degisse bile
        # gecerli. Yalnizca FONT degistiginde atlanir.
        dogrula = (style is None
                   or normalize_font_name(style.font)
                   == normalize_font_name(span.font))

        # 1) Belgenin kendi gomulu fontu - oncelikli.
        #    ONEMLI: kabul etmeden once sayfadaki ozgun yaziyi uretip
        #    uretemedigini GORSEL olarak dogruluyoruz. Yanlis glif haritasi
        #    (bozuk cmap onarimi) ancak boyle yakalaniyor.
        found = self._font_for_span_name(index, write.font)
        if found:
            aday_font = found[1]
            safe_chars = found[2] if len(found) > 2 else None
            missing, uncertain = self._check_glyphs(aday_font, probe, known)
            if safe_chars:
                # Onarilan haritada kesin dogrulanan karakterler bellidir;
                # digerlerini "belirsiz" say.
                uncertain = "".join(sorted({
                    ch for ch in probe
                    if not ch.isspace() and ch not in known
                    and ord(ch) not in safe_chars
                }))
            if not missing:
                if dogrula:
                    ok, mismatch = fontverify.font_matches_page(
                        page, aday_font, span)
                else:
                    ok = True
                # Cizim denemesi yalnizca BILGI icin: tek harf yuzunden
                # gomulu fontu birakmiyoruz (bkz. _resolve_font notu).
                tam_cizebiliyor = self._font_renders_all(aday_font, probe)
                if ok:
                    buffer, font = found[0], aday_font
                    embedded = True
                    if not tam_cizebiliyor and not uncertain:
                        uncertain = "".join(sorted({
                            c for c in probe if not c.isspace()}))[:12]
                else:
                    # Font sayfadakini taklit edemiyor -> guvenme.
                    missing = uncertain = ""

        # 2) Gomulu font kullanilamiyor -> sistemde kurulu ayni aileyi dene
        #    (Poppins gibi kullanici fontlari burada bulunur).
        if font is None:
            system = self._system_font(write.font)
            if system:
                sys_missing, _ = self._check_glyphs(system[1], probe, set())
                ok = True
                if dogrula:
                    ok, _ = fontverify.font_matches_page(page, system[1], span)
                if not sys_missing and ok:
                    buffer, font = system[0], system[1]
                    embedded = True
                    missing = uncertain = ""

        # 3) Son care: AYNI KALINLIKTA bir sistem fontu; o da yoksa yerlesik.
        #    Duz 'helv'e dusmek kalin basliklarin stilini inceltiyordu.
        if font is None:
            yedek = self._weight_fallback(write.font)
            if yedek:
                buffer, font = yedek[0], yedek[1]
            else:
                font = pymupdf.Font("helv")
                buffer = None
            embedded = False
            uncertain = ""

        font_label = getattr(font, "name", "") or span.font

        # Silmeden ONCE sayfadaki diger satirlarin envanterini al; sonra
        # karsilastirip yanlislikla komsu yazi silindi mi diye bakacagiz.
        before = self._line_inventory(index)

        self.snapshot()
        page = self.doc.load_page(index)
        target = pymupdf.Rect(span.block_rect if whole_block else span.rect)

        # Tum satir dikdortgenini degil, harflerin GERCEK sinirlarini sil.
        # Satir bbox'i satir araligini da kapsadigi icin sik yerlesimlerde
        # ust/alt satirin harflerine degip onlari da siliyordu.
        for rect in self._glyph_rects(index, span, whole_block) or [target]:
            page.add_redact_annot(rect)
        page.apply_redactions(images=0, graphics=0, text=0)

        # Guvence: hedef disinda bir satir kaybolduysa silmeyi geri al ve
        # "ortme" yoluna gec. Sik satirli belgelerde (CV) harf sinirlari
        # komsu satira degdigi icin silme kaciniz oluyor.
        covered = False
        kayip = self._lost_lines(before, self._line_inventory(index), span)
        if kayip:
            self._rollback_to_snapshot()
            page = self.doc.load_page(index)
            self._cover(page, index, span, whole_block)
            covered = True

            # Ortme de komsuya dokunduysa (olmamali) tamamen vazgec.
            kalan_kayip = self._lost_lines(before,
                                           self._line_inventory(index), span)
            if kalan_kayip:
                self._rollback_to_snapshot()
                self._undo.pop()
                self._font_cache.pop(index, None)
                self._char_cache.pop(index, None)
                raise NeighborTextLost(kalan_kayip)

        # Tek satirda kaliyor ve sayfaya sigiyorsa taban cizgisine yaz.
        # Konum ve bicim "write" span'inden gelir (tasima / stil kopyalama).
        origin = pymupdf.Point(*write.origin)
        single_line = (not whole_block and "\n" not in new_text)
        width = self._advance(font, probe, write.size, write.tracking)
        fits = (origin.x >= page.rect.x0
                and origin.x + width <= page.rect.x1 - 2
                and page.rect.y0 <= origin.y <= page.rect.y1)

        if single_line and fits and probe.strip():
            self._write_baseline(page, origin, probe, font, write)
            method = "baseline"
        else:
            method = "kutu"
            kutu = pymupdf.Rect(write.block_rect if whole_block
                                else write.rect) & page.rect
            self._write_box(page, kutu or target, new_text, write, font,
                            buffer)

        # Sayfa degisti: font ve karakter onbellegi artik eski.
        self._font_cache.pop(index, None)
        self._char_cache.pop(index, None)

        return ReplaceReport(font_name=font_label, embedded=embedded,
                             missing_chars=missing, method=method,
                             uncertain_chars=uncertain, covered=covered)

    @staticmethod
    def _derive_span(span: TextSpan, offset, style) -> TextSpan:
        """Yazma icin span turet: kaydirma ve/veya yeni bicim uygula.

        Silme her zaman OZGUN span'e gore yapilir; bu yalnizca yeni yazinin
        nereye ve nasil cizilecegini belirler.
        """
        if not offset and style is None:
            return span

        dx, dy = offset or (0.0, 0.0)
        punto = span.size
        if style is not None and getattr(style, "apply_size", False):
            punto = style.size
        yeni = TextSpan(
            rect=pymupdf.Rect(span.rect) + (dx, dy, dx, dy),
            text=span.text,
            size=punto,
            font=style.font if style else span.font,
            color=style.color if style else span.color,
            block_rect=pymupdf.Rect(span.block_rect) + (dx, dy, dx, dy),
            block_text=span.block_text,
            origin=(span.origin[0] + dx, span.origin[1] + dy),
            line_count=span.line_count,
            tracking=style.tracking if style else span.tracking,
            mixed_fonts=span.mixed_fonts,
        )

        # Punto degistiyse eski harf araligini oranla.
        if span.size > 0 and abs(yeni.size - span.size) > 0.01:
            yeni.tracking = span.tracking * (yeni.size / span.size)
        return yeni

    def _rollback_to_snapshot(self) -> None:
        """Son anlik goruntuye don ama onu yigindan CIKARMA.

        Boylece bir kullanici islemi, ic denemeler ne olursa olsun tek bir
        'geri al' adimi olarak kalir.
        """
        if self._undo:
            self._restore(self._undo[-1])

    def _background_color(self, page, rect):
        """Yazinin arkasindaki zemin rengini olc (en sik gecen piksel)."""
        try:
            genis = pymupdf.Rect(rect) + (-6, -3, 6, 3)
            genis = genis & page.rect
            if genis.is_empty:
                return (1.0, 1.0, 1.0)
            pix = page.get_pixmap(clip=genis, alpha=False)
            data = bytes(pix.samples)
            n = pix.n
            sayac = {}
            # Her pikseli taramaya gerek yok; seyrek ornek yeterli.
            for i in range(0, len(data) - n, n * 7):
                key = data[i:i + 3]
                sayac[key] = sayac.get(key, 0) + 1
            if not sayac:
                return (1.0, 1.0, 1.0)
            baskin = max(sayac.items(), key=lambda kv: kv[1])[0]
            return tuple(b / 255.0 for b in baskin)
        except Exception:
            return (1.0, 1.0, 1.0)

    @staticmethod
    def _ink_bounds(page, rect, zoom: float = 4.0, esik: int = 215):
        """Bir alandaki GERCEK murekkep siniri (font kutusu degil).

        Font kutusu harflerin ustunde/altinda bos pay birakiyor; ortme ve
        kirpma bu paya gore yapilinca ya eski yazidan iz kaliyor ya da komsu
        satirdan gereksiz yer feda ediliyor.
        """
        try:
            clip = pymupdf.Rect(rect) & page.rect
            if clip.is_empty or clip.width < 0.3 or clip.height < 0.3:
                return None
            pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom),
                                  alpha=False)
            data = bytes(pix.samples)
            w, h, n = pix.width, pix.height, pix.n
            top = bottom = left = right = None
            for y in range(h):
                base = y * w * n
                for x in range(w):
                    if data[base + x * n] < esik:
                        if top is None:
                            top = y
                        bottom = y
                        if left is None or x < left:
                            left = x
                        if right is None or x > right:
                            right = x
            if top is None:
                return None
            return pymupdf.Rect(clip.x0 + left / zoom,
                                clip.y0 + top / zoom,
                                clip.x0 + (right + 1) / zoom,
                                clip.y0 + (bottom + 1) / zoom)
        except Exception:
            return None

    def _ink_columns(self, page, rect, zoom: float = 4.0,
                     esik: int = 215, step: int = 2):
        """Alandaki murekkebi SUTUN SUTUN sinirla.

        Karakter kutusu bile fazla kaba kaliyordu: bir harfin kutusu bos
        yerleri de kapsadigi icin, komsudan kacinmak adina eski yazinin
        ortulmesi gereken kismi feda ediliyordu. Burada yalnizca gercekten
        murekkep olan ince dikey seritler dondurulur.
        """
        out = []
        try:
            clip = pymupdf.Rect(rect) & page.rect
            if clip.is_empty or clip.width < 0.3 or clip.height < 0.3:
                return out
            pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom),
                                  alpha=False)
            data = bytes(pix.samples)
            w, h, n = pix.width, pix.height, pix.n
            x = 0
            while x < w:
                x2 = min(w, x + step)
                ust = alt = None
                for xi in range(x, x2):
                    sutun = xi * n
                    for y in range(h):
                        if data[y * w * n + sutun] < esik:
                            if ust is None or y < ust:
                                ust = y
                            if alt is None or y > alt:
                                alt = y
                if ust is not None:
                    out.append(pymupdf.Rect(
                        clip.x0 + x / zoom, clip.y0 + ust / zoom,
                        clip.x0 + x2 / zoom, clip.y0 + (alt + 1) / zoom))
                x = x2
        except Exception:
            pass
        return out

    def _other_text_rects(self, index: int, hedef):
        """Hedef disindaki KARAKTERLERIN sinirlari.

        Neden karakter bazinda: satir bazinda kirpinca, ustteki basligin tek
        bir 'g' kuyrugu yuzunden alttaki yazinin TUM genisliginde bir serit
        feda ediliyor ve eski yazinin ust kismi ortulmeden kaliyordu - stil
        kopyalamadan sonra kalan renkli izlerin sebebi buydu.

        Dikey sinir satirin GERCEK murekkebinden, yatay sinir her harfin
        kendi kutusundan alinir.
        """
        out = []
        try:
            page = self.doc.load_page(index)
            for block in page.get_text("rawdict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    lrect = pymupdf.Rect(line["bbox"])
                    if lrect.is_empty:
                        continue
                    ortak = lrect & hedef
                    if (not ortak.is_empty
                            and ortak.get_area() >= lrect.get_area() * 0.6):
                        continue          # bu satir hedefin kendisi

                    # Yalnizca hedefe yakin komsular icin olcum yap.
                    yakin = pymupdf.Rect(hedef) + (-2, -14, 2, 14)
                    if (lrect & yakin).is_empty:
                        continue
                    out.extend(self._ink_columns(page, lrect))
        except Exception:
            pass
        return out

    @staticmethod
    def _clip_away_from(rect, others, pad: float = 0.3):
        """Dikdortgeni komsu metin kutularina degmeyecek sekilde kis.

        Ortme kutusu alt satirin tepesine tastiginde i/İ noktalari ve uzun
        harflerin ust kismi boyaniyordu; bunu engeller.
        """
        r = pymupdf.Rect(rect)
        for other in others:
            if other.x1 <= r.x0 or other.x0 >= r.x1:
                continue                     # yatayda ortusmuyor
            if other.y0 >= r.y1 or other.y1 <= r.y0:
                continue                     # dikeyde ortusmuyor

            merkez = (r.y0 + r.y1) / 2
            if other.y0 > merkez:            # komsu ASAGIDA -> alttan kis
                r.y1 = min(r.y1, other.y0 - pad)
            elif other.y1 < merkez:          # komsu YUKARIDA -> ustten kis
                r.y0 = max(r.y0, other.y1 + pad)
        return r if (r.y1 - r.y0) > 0.5 and (r.x1 - r.x0) > 0.1 else None

    def _cover(self, page, index: int, span: TextSpan,
               whole_block: bool) -> None:
        """Eski yaziyi silmek yerine zemin rengiyle ort.

        Silme (redaction) komsu satirin harflerine degdiginde kullanilir.
        Dikkat: ortulen metin dosyadan SILINMEZ, yalnizca gorunmez olur.
        """
        hedef = pymupdf.Rect(span.block_rect if whole_block else span.rect)
        kutular = self._glyph_rects(index, span, whole_block) or [hedef]
        self._cover_and_restore(page, index, kutular)

    def _cover_and_restore(self, page, index, kutular) -> None:
        """Tamamen ort, sonra ortunun altinda kalan KOMSU harfleri geri ciz.

        Sik yerlesimlerde ustteki satirin murekkebi eski yazinin tam ustunde,
        ayni sutunda olabiliyor; kirparak temiz sonuc alinamiyor ve geriye
        renkli izler kaliyordu. Onun yerine eksiksiz ortup, zarar gormesi
        muhtemel komsu harfleri ayni konum, font ve renkle yeniden ciziyoruz.
        """
        birlesik = pymupdf.Rect(kutular[0])
        for r in kutular[1:]:
            birlesik |= pymupdf.Rect(r)
        renk = self._background_color(page, birlesik)

        ortulecek = []
        for r in kutular:
            sutunlar = self._ink_columns(page, r)
            if not sutunlar:
                ink = self._ink_bounds(page, r)
                sutunlar = [ink if ink is not None else pymupdf.Rect(r)]
            ortulecek.extend(pymupdf.Rect(c) + (-0.3, -0.4, 0.3, 0.4)
                             for c in sutunlar)
        if not ortulecek:
            return

        alan = pymupdf.Rect(ortulecek[0])
        for r in ortulecek[1:]:
            alan |= r

        kurtarilacak = self._chars_touching(page, alan, kutular)

        for r in ortulecek:
            page.draw_rect(r, color=None, fill=renk, width=0)

        gruplar = {}
        for c in kurtarilacak:
            gruplar.setdefault(c["font"], []).append(c["char"])
        for c in kurtarilacak:
            if index is None:
                sistem = self._system_font(c["font"])
                font = sistem[1] if sistem else pymupdf.Font("helv")
            else:
                font = self._resolve_font(index, c["font"],
                                          "".join(gruplar[c["font"]]))
            writer = pymupdf.TextWriter(page.rect)
            writer.append(pymupdf.Point(*c["origin"]), c["char"], font=font,
                          fontsize=c["size"])
            writer.write_text(page, color=c["color"])

    @staticmethod
    def _chars_touching(page, alan, haric):
        """Alana degen ama hedefe AIT OLMAYAN karakterler."""
        out = []
        haric = [pymupdf.Rect(r) for r in haric]
        try:
            for item in page.get_texttrace():
                if item.get("type") != 0:
                    continue
                punto = float(item.get("size", 11.0))
                renk = _trace_color(item.get("color"))
                ad = item.get("font", "")
                for ch in item.get("chars", []):
                    try:
                        ucs, origin, bbox = ch[0], ch[2], ch[3]
                    except (IndexError, TypeError):
                        continue
                    kutu = pymupdf.Rect(bbox)
                    if kutu.is_empty or (kutu & alan).is_empty:
                        continue
                    if any(not (kutu & h).is_empty
                           and (kutu & h).get_area() >= kutu.get_area() * 0.6
                           for h in haric):
                        continue          # hedefin kendi harfi
                    harf = chr(int(ucs))
                    if not harf.strip():
                        continue
                    out.append({"char": harf, "size": punto, "color": renk,
                                "font": ad,
                                "origin": (float(origin[0]),
                                           float(origin[1]))})
        except Exception:
            pass
        return out

    def _line_inventory(self, index: int):
        """Sayfadaki satirlarin (metin, taban_y, kutu) listesi."""
        out = []
        try:
            page = self.doc.load_page(index)
            for block in page.get_text("dict").get("blocks", []):
                for line in block.get("lines", []):
                    text = "".join(s["text"] for s in line.get("spans", []))
                    if text.strip():
                        out.append((text, round(line["bbox"][3], 1),
                                    pymupdf.Rect(line["bbox"])))
        except Exception:
            return []
        return out

    @staticmethod
    def _lost_lines(before, after, span, ignore_rects=None):
        """Hedef satir disinda kaybolan satirlari ver.

        ignore_rects: degismesi BEKLENEN alanlar (ornegin tasinan
        karakterlerin bulundugu satirlar). Bunlarin metni degisince bu bir
        kayip degildir; aksi halde kismi tasimada yanlis alarm ciktigi icin
        program gereksizce ortme yoluna dusuyordu.
        """
        if not before:
            return []
        kalan = list(after)
        hedef = (span.text or "").strip()
        atla = [pymupdf.Rect(r) for r in (ignore_rects or [])]
        kayip = []

        for text, baseline, rect in before:
            eslesme = next((i for i, (t, b, _r) in enumerate(kalan)
                            if t == text and abs(b - baseline) < 0.6), None)
            if eslesme is not None:
                kalan.pop(eslesme)
                continue
            if text.strip() == hedef:
                continue          # zaten degistirilmesi istenen satir
            if any(not (pymupdf.Rect(rect) & r).is_empty for r in atla):
                continue          # degismesi beklenen alan
            kayip.append(text.strip())
        return kayip

    def _glyph_rects(self, index: int, span: TextSpan, whole_block: bool):
        """Silinecek harflerin gercek sinirlari (satir bbox'i degil).

        Satir bbox'i satir araligini da kapsiyor; sik yerlesimli belgelerde
        bu alan ust/alt satirin harflerine degip onlari da sildiriyordu.
        """
        try:
            page = self.doc.load_page(index)
            hedef = pymupdf.Rect(span.block_rect if whole_block else span.rect)
            rects = []
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for sp in line.get("spans", []):
                        r = pymupdf.Rect(sp["bbox"])
                        if r.is_empty:
                            continue
                        ortak = r & hedef
                        # Parcanin buyuk kismi hedefin icindeyse silinecek
                        # yaziya aittir; kenarina degen komsu harf degil.
                        if (not ortak.is_empty
                                and ortak.get_area() >= r.get_area() * 0.6):
                            rects.append(r)
            return rects
        except Exception:
            return None

    @staticmethod
    def _advance(font, text: str, size: float, tracking: float) -> float:
        """Harf araligi dahil toplam genislik."""
        width = font.text_length(text, fontsize=size)
        if tracking and len(text) > 1:
            width += tracking * (len(text) - 1)
        return width

    def _write_baseline(self, page, origin, text: str, font,
                        span: TextSpan) -> None:
        """Taban cizgisine yaz; harf araligi varsa harf harf konumlandir.

        Harf arali basliklarda (P R O F I L) metni tek parca yazmak araligi
        yok ediyor ve gorunum belirgin sekilde degisiyor; o yuzden olculen
        tracking kadar ilerleyerek her karakteri ayri yaziyoruz.
        """
        writer = pymupdf.TextWriter(page.rect)

        if not span.tracking:
            writer.append(origin, text, font=font, fontsize=span.size)
        else:
            x = origin.x
            for ch in text:
                writer.append(pymupdf.Point(x, origin.y), ch, font=font,
                              fontsize=span.size)
                x += (font.glyph_advance(ord(ch)) * span.size) + span.tracking

        writer.write_text(page, color=span.color)

    def _write_box(self, page, target, new_text: str, span: TextSpan,
                   font, buffer) -> None:
        """Sarmali yazim: gomulu font varsa @font-face ile aktarilir."""
        box = pymupdf.Rect(
            target.x0 - 1,
            target.y0 - 1,
            min(page.rect.x1, target.x1 + max(14.0, target.width * 0.4)),
            min(page.rect.y1, target.y1 + max(8.0, target.height * 0.8)),
        )
        r, g, b = span.color
        archive = None
        family = "sans-serif"
        prefix = ""
        if buffer is not None:
            archive = pymupdf.Archive()
            archive.add(buffer, "gomulu.ttf")
            family = "gomulu"
            prefix = "@font-face {font-family: gomulu; src: url(gomulu.ttf);} "

        css = (
            "%s* {font-size:%.1fpx;color:rgb(%d,%d,%d);line-height:1.15;"
            "margin:0;font-family:%s;}"
            % (prefix, span.size, int(r * 255), int(g * 255), int(b * 255),
               family)
        )
        page.insert_htmlbox(box, escape_html(new_text), css=css,
                            archive=archive, scale_low=0.5)

    def insert_textbox(self, index: int, rect, text: str, size: float,
                       color, bold: bool = False) -> None:
        self.snapshot()
        page = self.doc.load_page(index)
        r, g, b = color
        css = (
            "* {font-size:%.1fpx;font-weight:%s;color:rgb(%d,%d,%d);"
            "line-height:1.2;margin:0;font-family:sans-serif;}"
            % (size, "bold" if bold else "normal",
               int(r * 255), int(g * 255), int(b * 255))
        )
        page.insert_htmlbox(pymupdf.Rect(rect), escape_html(text), css=css,
                            scale_low=0.4)

    def extract_text(self) -> str:
        parts = []
        for i in range(self.page_count):
            parts.append("--- Sayfa %d ---\n" % (i + 1))
            parts.append(self.doc.load_page(i).get_text("text"))
            parts.append("\n")
        return "".join(parts)

    def search(self, needle: str):
        """Tum belgede ara; (sayfa, rect) listesi dondurur."""
        hits = []
        for i in range(self.page_count):
            for rect in self.doc.load_page(i).search_for(needle):
                hits.append((i, rect))
        return hits

    # ------------------------------------------------------------------
    # isaretlemeler
    # ------------------------------------------------------------------

    def markup(self, index: int, rect, kind: str, color) -> bool:
        """Secili alandaki metne vurgu / alti cizili / ustu cizili uygula."""
        page = self.doc.load_page(index)
        sel = pymupdf.Rect(rect)
        quads = [pymupdf.Rect(w[:4]).quad
                 for w in page.get_text("words")
                 if pymupdf.Rect(w[:4]).intersects(sel)]
        if not quads:
            return False
        self.snapshot()
        fn = {
            "highlight": page.add_highlight_annot,
            "underline": page.add_underline_annot,
            "strikeout": page.add_strikeout_annot,
        }[kind]
        annot = fn(quads)
        annot.set_colors(stroke=color)
        annot.update()
        return True

    def add_rect(self, index: int, rect, color, width: float = 1.5,
                 filled: bool = False) -> None:
        self.snapshot()
        page = self.doc.load_page(index)
        annot = page.add_rect_annot(pymupdf.Rect(rect))
        annot.set_colors(stroke=color, fill=color if filled else None)
        annot.set_border(width=width)
        annot.update()

    def add_ink(self, index: int, strokes, color, width: float = 2.0) -> None:
        self.snapshot()
        page = self.doc.load_page(index)
        annot = page.add_ink_annot(strokes)
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()

    def add_image(self, index: int, rect, path: str) -> None:
        self.snapshot()
        page = self.doc.load_page(index)
        page.insert_image(pymupdf.Rect(rect), filename=path, keep_proportion=True)

    # ------------------------------------------------------------------
    # gorselleri secme, tasima, boyutlandirma, silme
    # ------------------------------------------------------------------

    def images_on(self, index: int):
        """Sayfadaki gorsellerin konumu ve kaynagi."""
        out = []
        try:
            page = self.doc.load_page(index)
            for info in page.get_image_info(xrefs=True):
                rect = pymupdf.Rect(info["bbox"])
                if rect.is_empty or rect.width < 1 or rect.height < 1:
                    continue
                # Silinen gorselin yerinde 1x1 saydam bir kalinti kaliyor;
                # gorunmedigi halde secilebilir olmasin.
                if int(info.get("width", 0)) <= 1 and int(info.get("height", 0)) <= 1:
                    continue
                out.append({"xref": int(info.get("xref", 0)),
                            "rect": rect,
                            "width": int(info.get("width", 0)),
                            "height": int(info.get("height", 0))})
        except Exception:
            return []
        return out

    def image_at(self, index: int, point):
        """Noktadaki gorsel; ust uste binenlerde EN KUCUK olani secilir."""
        adaylar = [g for g in self.images_on(index)
                   if pymupdf.Rect(g["rect"]).contains(point)]
        if not adaylar:
            return None
        return min(adaylar, key=lambda g: g["rect"].get_area())

    def _image_bytes(self, xref: int):
        """Gorselin PNG baytlari; SAYDAMLIK KORUNUR.

        PDF'te saydamlik gorselin kendisinde degil, ayri bir "soft mask"
        nesnesinde durur. extract_image yalnizca taban gorseli verir; onu
        oldugu gibi geri yazarsak seffaf bolgeler SIYAH bir dikdortgene
        donusup cevresindeki yaziyi orter. Bu yuzden maskeyi birlestiriyoruz.
        """
        try:
            bilgi = self.doc.extract_image(xref) or {}
        except Exception:
            return None
        ham = bilgi.get("image")
        try:
            smask = int(bilgi.get("smask", 0) or 0)
        except (TypeError, ValueError):
            smask = 0
        if not smask:
            return ham
        try:
            taban = pymupdf.Pixmap(self.doc, xref)
            if taban.alpha:                      # zaten saydam
                return taban.tobytes("png")
            if taban.colorspace and taban.colorspace.n > 3:
                taban = pymupdf.Pixmap(pymupdf.csRGB, taban)
            maske = pymupdf.Pixmap(self.doc, smask)
            return pymupdf.Pixmap(taban, maske).tobytes("png")
        except Exception:
            return ham

    def _remove_image_at(self, page, rect) -> None:
        """Son care: xref'i olmayan (gomulu/inline) gorseli alanla kaldir.

        apply_redactions(images=2) alana DEGEN her gorselin piksellerini
        siliyor; bu yuzden yalnizca xref ile calisamadigimizda kullaniyoruz.
        text=1 -> METIN KORUNUR, graphics=0 -> CIZIMLER KORUNUR.
        """
        page.add_redact_annot(pymupdf.Rect(rect) + (-0.6, -0.6, 0.6, 0.6))
        page.apply_redactions(images=2, graphics=0, text=1)

    def _drop_image(self, page, image) -> None:
        """Gorseli sayfadan kaldir; KOMSU GORSELLERE DOKUNMAZ.

        page.delete_image gorseli 1x1 saydam bir goruntuyle degistirir:
        yalnizca o xref etkilenir, cevresindeki gorsel/cizim/metin aynen
        kalir. Alan bazli silme yalnizca xref yoksa devreye giriyor.
        """
        xref = int(image.get("xref", 0) or 0)
        if xref > 0:
            try:
                page.delete_image(xref)
            except Exception:
                pass
            else:
                # PyMuPDF ayni baytlari tekrar eklemesin diye bir "digest"
                # onbellegi tutuyor. Bosalttigimiz xref orada kalirsa, hemen
                # ardindan eklenen gorsel o BOS xref'e baglaniyor ve 1x1
                # saydam bir lekeye donusuyor. Onbellegi temizliyoruz.
                try:
                    self.doc.InsertedImages = {}
                except Exception:
                    pass
                return
        self._remove_image_at(page, image["rect"])

    def delete_image(self, index: int, image) -> None:
        """Gorseli sayfadan sil."""
        self.snapshot()
        page = self.doc.load_page(index)
        self._drop_image(page, image)

    def _replace_image_data(self, index: int, image, yeni_veri: bytes,
                            yeni_rect=None) -> None:
        """Gorselin ICERIGINI degistir; konumu (ya da verilen yeni konumu) korur.

        Tek yol izleniyor: gorsel xref'i uzerinden kaldirilir, yenisi hedef
        kutusuna konur. Yalnizca o gorsel etkilenir; komsu gorseller, cizimler
        ve metin oldugu gibi kalir.

        page.replace_image cazip gorunuyordu ama her cagrida sayfaya eskisini
        de birakip yeni bir kaynak ekliyor; art arda islem yapilinca silme
        yanlis nesneye denk gelip gorselin eski hali sayfada kaliyordu.
        """
        eski = pymupdf.Rect(image["rect"])
        hedef = pymupdf.Rect(yeni_rect) if yeni_rect is not None else eski
        hedef = hedef & self.doc.load_page(index).rect
        if hedef.is_empty or hedef.width < 2 or hedef.height < 2:
            raise DocumentError("Görsel için geçerli bir alan kalmadı.")

        self.snapshot()
        page = self.doc.load_page(index)
        self._drop_image(page, image)
        page = self.doc.load_page(index)
        page.insert_image(hedef, stream=imaging.distinct(yeni_veri),
                          keep_proportion=False)

    def edit_image(self, index: int, image, islem: str, **secenek):
        """Gorselin icerigini duzenle.

        islem: "dondur", "aynala", "kirp", "gri", "ayarla", "degistir"
        Donus: gorselin yeni piksel boyutu (genislik, yukseklik).
        """
        veri = self._image_bytes(image["xref"])
        if not veri and islem != "degistir":
            raise DocumentError("Görselin kaynağı okunamadı.")

        eski = pymupdf.Rect(image["rect"])
        yeni_rect = None

        if islem == "dondur":
            derece = int(secenek.get("derece", 90))
            yeni = imaging.rotate(veri, derece)
            if derece in (90, 270):
                # Kare olmayan gorsel donunce en-boy takla atar; kutuyu da
                # cevirmezsek gorsel eziliyor.
                orta_x = (eski.x0 + eski.x1) / 2
                orta_y = (eski.y0 + eski.y1) / 2
                yeni_rect = pymupdf.Rect(orta_x - eski.height / 2,
                                         orta_y - eski.width / 2,
                                         orta_x + eski.height / 2,
                                         orta_y + eski.width / 2)
        elif islem == "aynala":
            yeni = imaging.flip(veri, yatay=bool(secenek.get("yatay", True)))
        elif islem == "kirp":
            oran = secenek.get("oran")
            yeni = imaging.crop(veri, oran)
            # Kirpilan bolge, gorselin kutusunda da ayni orana karsilik gelir.
            yeni_rect = pymupdf.Rect(
                eski.x0 + oran[0] * eski.width,
                eski.y0 + oran[1] * eski.height,
                eski.x0 + oran[2] * eski.width,
                eski.y0 + oran[3] * eski.height)
        elif islem == "gri":
            yeni = imaging.grayscale(veri)
        elif islem == "ayarla":
            yeni = imaging.adjust(veri,
                                  parlaklik=float(secenek.get("parlaklik", 0)),
                                  kontrast=float(secenek.get("kontrast", 0)))
        elif islem == "degistir":
            yol = secenek.get("path")
            if not yol:
                raise DocumentError("Dosya seçilmedi.")
            yeni = imaging.from_file(yol)
        else:
            raise DocumentError("Bilinmeyen görsel işlemi: %s" % islem)

        self._replace_image_data(index, image, yeni, yeni_rect)
        return imaging.size_of(yeni)

    def export_image(self, image, path: str) -> None:
        """Gorseli diske kaydet."""
        veri = self._image_bytes(image["xref"])
        if not veri:
            raise DocumentError("Görselin kaynağı okunamadı.")
        try:
            pix = pymupdf.Pixmap(veri)
            pix.save(path)
        except Exception as exc:
            raise DocumentError("Kaydedilemedi: %s" % exc)

    def place_image(self, index: int, image, new_rect) -> None:
        """Gorseli tasi ve/veya yeniden boyutlandir.

        Yalnizca tasinan gorsel kaldirilip yeni kutusuna konuyor; komsu
        gorsellere, cizimlere ve metne dokunulmuyor.
        """
        sayfa_rect = self.doc.load_page(index).rect
        hedef = pymupdf.Rect(new_rect) & sayfa_rect
        if hedef.is_empty or hedef.width < 2 or hedef.height < 2:
            raise DocumentError("Görsel için geçerli bir alan seçilmedi.")

        veri = self._image_bytes(image["xref"])
        if not veri:
            raise DocumentError("Görselin kaynağı okunamadı.")

        self.snapshot()
        page = self.doc.load_page(index)
        self._drop_image(page, image)
        page = self.doc.load_page(index)
        page.insert_image(hedef, stream=imaging.distinct(veri),
                          keep_proportion=False)

    # ------------------------------------------------------------------
    # vektor cizimler (simgeler, ayraclar, seritler)
    # ------------------------------------------------------------------
    #
    # CV'lerdeki telefon/zarf simgeleri cogu zaman gorsel DEGIL, kucuk dolu
    # yollardan olusan vektor cizimlerdir; bu yuzden gorsel araciyla
    # secilemiyorlardi. Bir simge tek bir yol da degildir (telefon simgesi 5
    # ayri yol), o yuzden once komsu yollari kumeliyoruz.

    DRAWING_MAX = 90.0        # bir "nesne" sayilacak en buyuk kume (pt)
    DRAWING_SHARE = 0.02      # sayfanin bu oranindan buyuk yollar arka plandir

    def drawing_at(self, index: int, point, azami: float = None):
        """Noktadaki vektor cizim grubunu dondur (yoksa None).

        Once noktayi iceren EN KUCUK yol bulunur, sonra ona degen kucuk
        yollar kumeye katilir. Sayfa zemini gibi buyuk dolgular disarida
        birakilir, yoksa her tiklama tum sayfayi secerdi.
        """
        azami = self.DRAWING_MAX if azami is None else float(azami)
        try:
            page = self.doc.load_page(index)
            yollar = page.get_drawings()
        except Exception:
            return None

        sinir = page.rect.get_area() * self.DRAWING_SHARE
        aday = [c for c in yollar
                if not pymupdf.Rect(c["rect"]).is_empty
                and pymupdf.Rect(c["rect"]).get_area() <= sinir]

        icinde = [c for c in aday if pymupdf.Rect(c["rect"]).contains(point)]
        if not icinde:
            return None
        icinde.sort(key=lambda c: pymupdf.Rect(c["rect"]).get_area())

        grup = [icinde[0]]
        kutu = pymupdf.Rect(icinde[0]["rect"])
        buyudu = True
        while buyudu:
            buyudu = False
            for c in aday:
                if any(c is g for g in grup):
                    continue
                r = pymupdf.Rect(c["rect"])
                if (r & (kutu + (-1, -1, 1, 1))).is_empty:
                    continue
                yeni = pymupdf.Rect(kutu) | r
                if yeni.width > azami or yeni.height > azami:
                    continue
                grup.append(c)
                kutu = yeni
                buyudu = True
        return {"rect": kutu, "paths": grup, "count": len(grup)}

    def _erase_drawing(self, page, rect) -> None:
        """Alani TAMAMEN dolduran cizimleri kaldir.

        graphics=1 (REMOVE_IF_COVERED) yalnizca kutunun icine tamamen sigan
        cizgi/dolguyu siler; sayfa zemini gibi disari tasan seyler kalir.
        images=0 -> gorseller, text=1 -> metin korunur.
        """
        page.add_redact_annot(pymupdf.Rect(rect) + (-0.5, -0.5, 0.5, 0.5))
        page.apply_redactions(images=0, graphics=1, text=1)

    @staticmethod
    def _redraw(page, paths, eski, hedef) -> None:
        """Yollari eski kutudan hedef kutuya tasiyarak yeniden ciz."""
        sx = hedef.width / eski.width if eski.width else 1.0
        sy = hedef.height / eski.height if eski.height else 1.0

        def esle(p):
            return pymupdf.Point(hedef.x0 + (p.x - eski.x0) * sx,
                                 hedef.y0 + (p.y - eski.y0) * sy)

        olcek = (abs(sx) + abs(sy)) / 2.0
        sekil = page.new_shape()
        for c in paths:
            for it in c["items"]:
                tur = it[0]
                if tur == "l":
                    sekil.draw_line(esle(it[1]), esle(it[2]))
                elif tur == "c":
                    sekil.draw_bezier(esle(it[1]), esle(it[2]),
                                      esle(it[3]), esle(it[4]))
                elif tur == "re":
                    r = pymupdf.Rect(it[1])
                    sekil.draw_rect(pymupdf.Rect(esle(r.tl), esle(r.br)))
                elif tur == "qu":
                    q = it[1]
                    sekil.draw_quad(pymupdf.Quad(esle(q.ul), esle(q.ur),
                                                 esle(q.ll), esle(q.lr)))
            kalinlik = c.get("width")
            sekil.finish(
                fill=c.get("fill"), color=c.get("color"),
                width=(kalinlik * olcek) if kalinlik else 0,
                even_odd=bool(c.get("even_odd")),
                closePath=bool(c.get("closePath")),
                fill_opacity=(1 if c.get("fill_opacity") is None
                              else c["fill_opacity"]),
                stroke_opacity=(1 if c.get("stroke_opacity") is None
                                else c["stroke_opacity"]))
        sekil.commit()

    def place_drawing(self, index: int, obj, new_rect) -> None:
        """Vektor cizimi tasi ve/veya yeniden boyutlandir."""
        page = self.doc.load_page(index)
        eski = pymupdf.Rect(obj["rect"])
        hedef = pymupdf.Rect(new_rect) & page.rect
        if hedef.is_empty or hedef.width < 1 or hedef.height < 1:
            raise DocumentError("Çizim için geçerli bir alan seçilmedi.")
        if eski.is_empty:
            raise DocumentError("Çizim okunamadı.")

        self.snapshot()
        page = self.doc.load_page(index)
        # Once sil, sonra ciz: ters sirada, yeni cizim eskisiyle cakisirsa
        # kaldirma islemi yeni cizimi de silerdi.
        self._erase_drawing(page, eski)
        page = self.doc.load_page(index)
        self._redraw(page, obj["paths"], eski, hedef)

    def delete_drawing(self, index: int, obj) -> None:
        """Vektor cizimi sayfadan sil."""
        self.snapshot()
        page = self.doc.load_page(index)
        self._erase_drawing(page, pymupdf.Rect(obj["rect"]))

    def redact(self, index: int, rect) -> None:
        """Alani kalici olarak karart - altindaki veri dosyadan silinir."""
        self.snapshot()
        page = self.doc.load_page(index)
        page.add_redact_annot(pymupdf.Rect(rect), fill=(0, 0, 0))
        page.apply_redactions()

    def annots_at(self, index: int, point):
        page = self.doc.load_page(index)
        return [a for a in page.annots() if pymupdf.Rect(a.rect).contains(point)]

    def delete_annot(self, index: int, annot) -> None:
        self.snapshot()
        self.doc.load_page(index).delete_annot(annot)

    def watermark(self, text: str, size: int, opacity: float, color,
                  rotate: int = 45) -> None:
        """Her sayfaya capraz filigran yaz.

        insert_htmlbox yalnizca 90'in katlarinda donduruyor, o yuzden serbest
        aci icin TextWriter + morph kullaniyoruz. Font("helv") Turkce glifleri
        dogru gomuyor (fontname="helv" ile insert_text gommuyor - kullanma).
        """
        self.snapshot()
        font = pymupdf.Font("helv")
        for i in range(self.page_count):
            page = self.doc.load_page(i)
            r = page.rect

            # Sayfaya sigmazsa punto kucult.
            fs = float(size)
            while fs > 6 and font.text_length(text, fontsize=fs) > r.width * 0.9:
                fs -= 1.0

            width = font.text_length(text, fontsize=fs)
            pivot = pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
            start = pymupdf.Point(pivot.x - width / 2, pivot.y + fs * 0.35)

            writer = pymupdf.TextWriter(r)
            writer.append(start, text, font=font, fontsize=fs)
            writer.write_text(page, morph=(pivot, pymupdf.Matrix(rotate)),
                              color=color, opacity=opacity)

    # ------------------------------------------------------------------
    # formlar
    # ------------------------------------------------------------------

    @property
    def has_form(self) -> bool:
        return bool(self.doc and self.doc.is_form_pdf)

    def form_fields(self):
        out = []
        for i in range(self.page_count):
            for w in self.doc.load_page(i).widgets():
                out.append((i, w))
        return out

    def set_field(self, page_index: int, field_name: str, value) -> None:
        self.snapshot()
        for w in self.doc.load_page(page_index).widgets():
            if w.field_name == field_name:
                w.field_value = value
                w.update()
                return
        self.drop_snapshot()

    def flatten_form(self) -> None:
        """Form alanlarini sabit icerige cevir - artik duzenlenemez."""
        self.snapshot()
        for i in range(self.page_count):
            page = self.doc.load_page(i)
            for w in list(page.widgets()):
                val = w.field_value
                if val not in (None, "", False):
                    text = "X" if val is True else str(val)
                    css = ("* {font-size:%.1fpx;font-family:sans-serif;"
                           "color:#000;margin:0;}"
                           % max(8.0, w.rect.height * 0.62))
                    page.insert_htmlbox(w.rect, escape_html(text), css=css,
                                        scale_low=0.4)
                page.delete_widget(w)
