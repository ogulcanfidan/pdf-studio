"""Alt kume gomulu fontlarin eksik 'cmap' tablosunu onarir.

Sorun: PDF alt kume araclari Identity-H fontlardan unicode tablosunu (cmap)
atiyor - PDF karakterleri glif numarasiyla cizdigi icin buna ihtiyaci yok.
Fontu disari cikarip yeniden yazmak istedigimizde ise unicode -> glif
eslemesi olmadan font kullanilamiyor: PyMuPDF sessizce baska bir font koyuyor.

Cozum ve neden bu sirayla:
  1. get_texttrace() her karakterin GERCEK glif numarasini veriyor. Bu
     tartismasiz dogru kaynak - sayfada o glifle cizilmis.
  2. ToUnicode haritasi daha genis (sayfada gecmeyen harfleri de kapsar) ama
     ayristirmasi bicime gore degisiyor. Bu yuzden once (1) ile CAPRAZ
     DOGRULANIR; celisiyorsa tamamen atilir.
  3. Sonuc font, yazmadan once gorsel olarak dogrulanir (verify.py tarafinda).
"""

from __future__ import annotations

import re
import struct

import pymupdf

_BFCHAR = re.compile(rb"beginbfchar(.*?)endbfchar", re.S)
_BFRANGE = re.compile(rb"beginbfrange(.*?)endbfrange", re.S)
_HEX = re.compile(rb"<([0-9A-Fa-f]*)>")
_RANGE_ENTRY = re.compile(
    rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(\[[^\]]*\]|<[0-9A-Fa-f]*>)", re.S)


def _norm(name: str) -> str:
    if not name:
        return ""
    if len(name) > 7 and name[6] == "+":
        name = name[7:]
    return "".join(c for c in name.lower() if c.isalnum())


def _first_codepoint(hex_text: bytes):
    try:
        raw = hex_text.decode("ascii")
    except Exception:
        return None
    if len(raw) % 2:
        raw = "0" + raw
    if not raw:
        return None
    try:
        blob = bytes.fromhex(raw)
    except ValueError:
        return None
    if len(blob) < 2:
        return blob[0] if blob else None
    try:
        text = blob.decode("utf-16-be", errors="ignore")
    except Exception:
        return None
    return ord(text[0]) if text else None


def trace_map(page, font_name: str):
    """{unicode: glif} - sayfada o fontla CIZILMIS karakterlerden.

    Bu harita tartismasiz dogrudur: her kayit, sayfada gercekten o glifle
    cizilmis bir karakterden geliyor.
    """
    hedef = _norm(font_name)
    mapping = {}
    try:
        items = page.get_texttrace()
    except Exception:
        return mapping

    for item in items:
        if _norm(item.get("font", "")) != hedef:
            continue
        for ch in item.get("chars", []):
            try:
                ucs, gid = int(ch[0]), int(ch[1])
            except (TypeError, ValueError, IndexError):
                continue
            if 0 < ucs <= 0xFFFF and 0 < gid <= 0xFFFF:
                mapping.setdefault(ucs, gid)
    return mapping


def tounicode_map(doc, font_xref: int):
    """{unicode: glif} - PDF'in ToUnicode haritasindan (daha genis, daha riskli)."""
    try:
        kind, value = doc.xref_get_key(font_xref, "ToUnicode")
    except Exception:
        return {}
    if kind != "xref":
        return {}
    try:
        data = doc.xref_stream(int(value.split()[0]))
    except Exception:
        return {}
    if not data:
        return {}

    mapping = {}
    for blok in _BFCHAR.findall(data):
        parts = _HEX.findall(blok)
        for i in range(0, len(parts) - 1, 2):
            try:
                gid = int(parts[i], 16)
            except ValueError:
                continue
            code = _first_codepoint(parts[i + 1])
            if code:
                mapping.setdefault(code, gid)

    for blok in _BFRANGE.findall(data):
        for lo_hex, hi_hex, hedef in _RANGE_ENTRY.findall(blok):
            try:
                lo, hi = int(lo_hex, 16), int(hi_hex, 16)
            except ValueError:
                continue
            if hi < lo or hi - lo > 65535:
                continue
            if hedef.startswith(b"["):
                for offset, parca in enumerate(_HEX.findall(hedef)):
                    if lo + offset > hi:
                        break
                    code = _first_codepoint(parca)
                    if code:
                        mapping.setdefault(code, lo + offset)
            else:
                base = _first_codepoint(hedef.strip(b"<>"))
                if base is None:
                    continue
                for offset in range(hi - lo + 1):
                    mapping.setdefault(base + offset, lo + offset)
    return mapping


def merged_map(doc, page, font_xref: int, font_name: str):
    """Kesin haritayi kur; ToUnicode'u ancak CELISMIYORSA ekle."""
    kesin = trace_map(page, font_name)
    if not kesin:
        return {}, False

    genis = tounicode_map(doc, font_xref)
    if not genis:
        return kesin, False

    ortak = [u for u in kesin if u in genis]
    celiskili = [u for u in ortak if genis[u] != kesin[u]]

    # Ortak alanda tek bir uyusmazlik bile varsa ToUnicode ayristirmasina
    # guvenilmez; yalnizca kesin haritayla devam et.
    if celiskili or len(ortak) < min(3, len(kesin)):
        return kesin, False

    birlesik = dict(genis)
    birlesik.update(kesin)          # celiski yok ama kesin olan onceliklidir
    return birlesik, True


def build_cmap4(mapping) -> bytes:
    """unicode -> glif tablosundan format 4 cmap alt tablosu uret."""
    items = sorted((u, g) for u, g in mapping.items()
                   if 0 < u <= 0xFFFF and 0 < g <= 0xFFFF)
    if not items:
        return b""

    segments = []
    start_u, start_g = items[0]
    prev_u, prev_g = items[0]
    for u, g in items[1:]:
        if u == prev_u + 1 and g == prev_g + 1:
            prev_u, prev_g = u, g
            continue
        segments.append((start_u, prev_u, start_g))
        start_u, start_g = u, g
        prev_u, prev_g = u, g
    segments.append((start_u, prev_u, start_g))
    segments.append((0xFFFF, 0xFFFF, 0))

    seg_count = len(segments)
    ends, starts, deltas, offsets = [], [], [], []
    for start, end, gid in segments:
        starts.append(start)
        ends.append(end)
        deltas.append(1 if start == 0xFFFF else (gid - start) & 0xFFFF)
        offsets.append(0)

    search_range, entry_selector = 2, 0
    while search_range * 2 <= seg_count * 2:
        search_range *= 2
        entry_selector += 1
    range_shift = seg_count * 2 - search_range

    body = b"".join([
        struct.pack(">%dH" % seg_count, *ends),
        struct.pack(">H", 0),
        struct.pack(">%dH" % seg_count, *starts),
        struct.pack(">%dH" % seg_count, *deltas),
        struct.pack(">%dH" % seg_count, *offsets),
    ])
    subtable = struct.pack(">HHHHHHH", 4, 14 + len(body), 0, seg_count * 2,
                           search_range, entry_selector, range_shift) + body
    return struct.pack(">HHHHI", 0, 1, 3, 1, 12) + subtable


def sfnt_set_table(data: bytes, tag: bytes, table: bytes):
    """sfnt font dosyasina tablo ekle/degistir."""
    if len(data) < 12 or data[:4] == b"ttcf":
        return None
    try:
        num = struct.unpack(">H", data[4:6])[0]
        records = []
        for i in range(num):
            rec = 12 + i * 16
            t = data[rec:rec + 4]
            offset, length = struct.unpack(">II", data[rec + 8:rec + 16])
            if t == tag:
                continue
            blob = data[offset:offset + length]
            if len(blob) != length:
                return None
            records.append((t, data[rec + 4:rec + 8], blob))

        records.append((tag, b"\0\0\0\0", table))
        records.sort(key=lambda r: r[0])

        count = len(records)
        out = bytearray(data[:4]) + struct.pack(">HHHH", count, 0, 0, 0)
        offset = 12 + count * 16
        body = bytearray()
        for t, checksum, blob in records:
            out += t + checksum + struct.pack(">II", offset + len(body),
                                              len(blob))
            body += blob
            while len(body) % 4:
                body += b"\0"
        return bytes(out) + bytes(body)
    except Exception:
        return None


def repair(doc, page, font_xref: int, buffer, font_name: str):
    """Fontun cmap tablosunu sayfadaki gercek gliflerden kur.

    Basarili olursa (yeni_buffer, Font, guvenli_karakterler) dondurur.
    guvenli_karakterler: dogrulugu kesin olan kod noktalari kumesi.
    """
    mapping, genisletildi = merged_map(doc, page, font_xref, font_name)
    if not mapping:
        return None

    table = build_cmap4(mapping)
    if not table:
        return None

    patched = sfnt_set_table(bytes(buffer), b"cmap", table)
    if not patched:
        return None

    try:
        font = pymupdf.Font(fontbuffer=patched)
        if not font.valid_codepoints():
            return None
    except Exception:
        return None

    kesin = set(trace_map(page, font_name))
    return patched, font, kesin
