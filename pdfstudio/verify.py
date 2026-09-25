"""Yazmadan ONCE gorsel dogrulama.

Bu modulun tek isi var: bir aday fontun, sayfadaki mevcut yaziyi taklit edip
edemedigini olcmek. Font eslemesi yanlissa (bozuk glifler, kayik cmap) ortaya
anlamsiz karakterler cikar; bunu kullaniciya yazmadan yakalamak icin adayla
ayni metni ayri bir sayfaya cizip ozgun bolgeyle karsilastiriyoruz.

Neden gerekli: cmap onarimi dogru gorunse bile yanlis glif haritasi
uretebiliyor ve sonuc ancak ekranda fark ediliyor. Burasi o riski kapatir.
"""

from __future__ import annotations

import pymupdf

# Karsilastirma cozunurlugu (yuksek olmasi gerekmiyor, sekil yeter).
ZOOM = 2.0
# Sutun mürekkep profili farki bu esigin altindaysa font kabul edilir.
# Olculen ayrim cok net: dogru font ~0.002, bozuk glif haritasi ~0.20,
# alakasiz font (Wingdings) ~0.21. Esik ikisinin arasinda, dogruya yakin.
TOLERANCE = 0.08


def _ink_profile(pixmap):
    """Kirpilmis goruntunun sutun basina koyu piksel orani."""
    data = bytes(pixmap.samples)
    width, height, n = pixmap.width, pixmap.height, pixmap.n
    if width == 0 or height == 0:
        return []
    columns = []
    for x in range(width):
        dark = 0
        base = x * n
        for y in range(height):
            if data[y * width * n + base] < 170:
                dark += 1
        columns.append(dark / height)
    return columns


def _compare(a, b) -> float:
    """Iki profil arasindaki ortalama mutlak fark (0 = ayni)."""
    if not a or not b:
        return 1.0
    n = min(len(a), len(b))
    if n == 0:
        return 1.0
    return sum(abs(a[i] - b[i]) for i in range(n)) / n


def render_like(font, span, page_rect, tracking: float):
    """Aday fontla, span'in metnini ayni konuma ve AYNI RENKTE cizip dondur.

    Renk onemli: acik gri bir yaziyi siyah cizip karsilastirirsak dogru font
    bile reddedilir.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=page_rect.width, height=page_rect.height)
    origin = pymupdf.Point(*span.origin)

    writer = pymupdf.TextWriter(page.rect)
    if tracking:
        x = origin.x
        for ch in span.text:
            writer.append(pymupdf.Point(x, origin.y), ch, font=font,
                          fontsize=span.size)
            x += font.glyph_advance(ord(ch)) * span.size + tracking
    else:
        writer.append(origin, span.text, font=font, fontsize=span.size)
    writer.write_text(page, color=span.color)

    clip = pymupdf.Rect(span.rect) & page.rect
    pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(ZOOM, ZOOM))
    doc.close()
    return pix


def font_matches_page(page, font, span) -> tuple:
    """Aday font, sayfadaki ozgun yaziyi uretebiliyor mu?

    (kabul_edildi, fark) dondurur. Fark buyukse font yanlis glif ciziyordur.
    """
    text = (span.text or "").strip()
    if len(text) < 2:
        return True, 0.0           # olcemeyecek kadar kisa, riske girme

    clip = pymupdf.Rect(span.rect) & page.rect
    if clip.is_empty or clip.width < 2 or clip.height < 2:
        return True, 0.0

    try:
        original = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(ZOOM, ZOOM))
        candidate = render_like(font, span, page.rect, span.tracking)
    except Exception:
        # Olcemedik; karar verme, cagiran taraf kendi yedegine dussun.
        return True, 0.0

    fark = _compare(_ink_profile(original), _ink_profile(candidate))
    return fark <= TOLERANCE, fark
