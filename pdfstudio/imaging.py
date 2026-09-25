"""Gorsel icerigini duzenleme: dondur, aynala, kirp, renk, parlaklik.

Tasarim: her islem PNG baytlari alir, PNG baytlari dondurur. Boylece model
katmani yalnizca "eski bayt -> yeni bayt" bilir; PDF tarafinda gorsel ayni
sekilde yeniden yerlestirilir.

numpy kullaniliyor: saf Python'da her piksel uzerinde donmek buyuk gorsellerde
saniyeler suruyordu.
"""

from __future__ import annotations

import os
import struct
import zlib

import numpy as np
import pymupdf


class ImageError(Exception):
    pass


def _pixmap(data: bytes):
    try:
        return pymupdf.Pixmap(data)
    except Exception as exc:
        raise ImageError("Görsel okunamadı: %s" % exc)


def _array(pix):
    """Pixmap -> (yukseklik, genislik, kanal) dizisi."""
    return np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)


def _to_png(pix_like, colorspace, alpha: int) -> bytes:
    """Dizi -> PNG baytlari."""
    dizi = np.ascontiguousarray(pix_like)
    yeni = pymupdf.Pixmap(colorspace, dizi.shape[1], dizi.shape[0],
                          dizi.tobytes(), alpha)
    return yeni.tobytes("png")


def _rebuild(data: bytes, donustur) -> bytes:
    pix = _pixmap(data)
    dizi = _array(pix)
    return _to_png(donustur(dizi), pix.colorspace, pix.alpha)


# ---------------------------------------------------------------- islemler

def rotate(data: bytes, derece: int) -> bytes:
    """Saat yonunde 90 / 180 / 270 derece dondur."""
    derece = int(derece) % 360
    if derece == 0:
        return data
    if derece not in (90, 180, 270):
        raise ImageError("Döndürme yalnızca 90, 180 veya 270 derece olabilir.")
    # np.rot90 saat yonunun TERSINE doner; saat yonu icin 4-k aliyoruz.
    k = {90: 3, 180: 2, 270: 1}[derece]
    return _rebuild(data, lambda a: np.rot90(a, k))


def flip(data: bytes, yatay: bool = True) -> bytes:
    """Yatay (sol-sag) veya dikey (ust-alt) aynala."""
    if yatay:
        return _rebuild(data, lambda a: a[:, ::-1])
    return _rebuild(data, lambda a: a[::-1, :])


def crop(data: bytes, oran) -> bytes:
    """Orana gore kirp.

    oran: (x0, y0, x1, y1) - her biri 0..1 arasinda, gorselin kendi
    kutusuna gore. Boylece ekrandaki secim, gorselin gercek cozunurlugunden
    bagimsiz calisir.
    """
    pix = _pixmap(data)
    dizi = _array(pix)
    h, w = dizi.shape[0], dizi.shape[1]

    x0 = int(round(max(0.0, min(1.0, oran[0])) * w))
    y0 = int(round(max(0.0, min(1.0, oran[1])) * h))
    x1 = int(round(max(0.0, min(1.0, oran[2])) * w))
    y1 = int(round(max(0.0, min(1.0, oran[3])) * h))
    if x1 - x0 < 2 or y1 - y0 < 2:
        raise ImageError("Kırpma alanı çok küçük.")

    return _to_png(dizi[y0:y1, x0:x1], pix.colorspace, pix.alpha)


def grayscale(data: bytes) -> bytes:
    """Gri tonlamaya cevir (renk kanallari korunur, gorunum gri)."""
    pix = _pixmap(data)
    dizi = _array(pix).astype(np.float32)
    kanal = dizi.shape[2]
    if kanal < 3:
        return data                      # zaten gri
    # Insan gozunun duyarliligina gore agirlikli ortalama.
    gri = (dizi[:, :, 0] * 0.299 + dizi[:, :, 1] * 0.587
           + dizi[:, :, 2] * 0.114)
    sonuc = dizi.copy()
    for i in range(3):
        sonuc[:, :, i] = gri
    return _to_png(np.clip(sonuc, 0, 255).astype(np.uint8),
                   pix.colorspace, pix.alpha)


def adjust(data: bytes, parlaklik: float = 0.0, kontrast: float = 0.0) -> bytes:
    """Parlaklik ve kontrast ayarla.

    Ikisi de -1..+1 arasinda; 0 degisiklik yok demektir.
    """
    if abs(parlaklik) < 0.001 and abs(kontrast) < 0.001:
        return data

    pix = _pixmap(data)
    dizi = _array(pix).astype(np.float32)
    kanal = dizi.shape[2]
    # Alfa kanali varsa ona dokunma.
    renkli = dizi[:, :, :3] if kanal >= 3 else dizi

    if kontrast:
        k = 1.0 + float(kontrast)
        renkli = (renkli - 128.0) * k + 128.0
    if parlaklik:
        renkli = renkli + float(parlaklik) * 255.0

    sonuc = dizi.copy()
    if kanal >= 3:
        sonuc[:, :, :3] = renkli
    else:
        sonuc = renkli
    return _to_png(np.clip(sonuc, 0, 255).astype(np.uint8),
                   pix.colorspace, pix.alpha)


def distinct(data: bytes) -> bytes:
    """Ayni goruntuyu, baytlari FARKLI olacak sekilde dondur.

    Neden gerekli: bir gorseli sayfadan kaldirip yeni yerine koyarken
    baytlar birebir ayni kalirsa, PyMuPDF onu "zaten var" sayip yeni
    eklemeyi az once bosalttigimiz nesneye bagliyor; gorsel 1x1 saydam bir
    lekeye donusuyor. Goruntuye dokunmadan, yok sayilan bir yorum alani
    ekleyerek baytlari ayirt edilebilir yapiyoruz.
    """
    im = os.urandom(6).hex().encode("ascii")

    if data[:8] == b"\x89PNG\r\n\x1a\n":
        # IEND'den hemen once bir tEXt parcasi: her okuyucu yok sayar.
        son = data.rfind(b"IEND")
        if son > 4:
            govde = b"tEXt" + b"pdfstudio\x00" + im
            parca = (struct.pack(">I", len(govde) - 4) + govde
                     + struct.pack(">I", zlib.crc32(govde) & 0xFFFFFFFF))
            return data[:son - 4] + parca + data[son - 4:]

    if data[:2] == b"\xff\xd8":
        # JPEG: SOI'den hemen sonra bir COM (yorum) bolumu.
        govde = b"pdfstudio " + im
        return (data[:2] + b"\xff\xfe" + struct.pack(">H", len(govde) + 2)
                + govde + data[2:])

    # Taninmayan bicim: PNG'ye cevirip ayni islemi uygula.
    return distinct(_pixmap(data).tobytes("png"))


def size_of(data: bytes):
    """Gorselin piksel boyutu."""
    pix = _pixmap(data)
    return pix.width, pix.height


def from_file(path: str) -> bytes:
    """Diskteki gorseli PNG baytlarina cevir (her bicim kabul edilir)."""
    try:
        pix = pymupdf.Pixmap(path)
    except Exception as exc:
        raise ImageError("Dosya okunamadı: %s" % exc)
    return pix.tobytes("png")
