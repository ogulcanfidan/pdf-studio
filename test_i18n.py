"""Dil destegi: ceviri butunlugu ve Ingilizce kalinti kontrolu."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import (QApplication, QDialogButtonBox, QMessageBox)
app = QApplication([])

from pdfstudio import i18n
from pdfstudio.mainwindow import MainWindow
from pdfstudio.pageview import TOOL_HINTS, Tool

fails = []
def check(name, cond, detail=""):
    if cond: print("  OK   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail)); fails.append(name)

print("=== 1. Yedi dil de var mi? ===")
diller = i18n.available_languages()
check("8 dil tanimli (tr + 7)", len(diller) == 8, "-> %d" % len(diller))
kodlar = [k for k, _ in diller]
check("Italyanca cikarildi", "it" not in kodlar, "-> %s" % kodlar)
check("Cince eklendi", "zh" in kodlar, "-> %s" % kodlar)
check("Arapca eklendi", "ar" in kodlar, "-> %s" % kodlar)
check("Arapca sagdan sola", i18n.is_rtl("ar") and not i18n.is_rtl("zh"))
print("     %s" % ", ".join("%s(%s)" % (a, k) for k, a in diller))

print()
print("=== 2. Her dil icin arayuz kuruluyor ve ceviriyor mu? ===")
for kod, ad in diller:
    i18n._current = kod
    w = MainWindow()
    basliklar = [a.text() for a in w.tool_actions.values()]
    ceviri_var = i18n.tr("Kaydet") != "Kaydet" or kod == "tr"
    check("%-3s pencere kuruldu ve cevrildi" % kod,
          len(basliklar) == len(w.tool_actions) and ceviri_var,
          "-> %d arac" % len(basliklar))
    w.close()

print()
print("=== 3. Turkcede Ingilizce kalinti var mi? ===")
i18n._current = "tr"
kutu = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                        | QDialogButtonBox.StandardButton.Cancel)
i18n.apply_buttons(kutu)
metinler = [b.text() for b in kutu.buttons()]
print("     diyalog dugmeleri: %s" % metinler)
check("OK -> Tamam", "Tamam" in metinler, "-> %s" % metinler)
check("Cancel -> İptal", "İptal" in metinler, "-> %s" % metinler)

mb = QMessageBox()
mb.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                      | QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard)
i18n.apply_buttons(mb)
mt = [b.text().replace("&", "") for b in mb.buttons()]
print("     mesaj dugmeleri  : %s" % mt)
for beklenen in ("Evet", "Hayır", "Kaydet", "Kaydetme"):
    check("%s cevrildi" % beklenen, beklenen in mt, "-> %s" % mt)

print()
print("=== 4. Arac ipuclari cevriliyor mu? ===")
i18n._current = "en"
ing = TOOL_HINTS[Tool.REDACT]
i18n._current = "tr"
turk = TOOL_HINTS[Tool.REDACT]
check("ipucu dile gore degisiyor", ing != turk, "-> %r" % ing[:40])
check("Ingilizce ipucu Ingilizce", "Redact" in ing, "-> %r" % ing[:40])

print()
print("=== 5. Katalog butunlugu: her satirda 6 ceviri ===")
eksik = [k for k, v in i18n._ROWS.items() if len(v) != 5]
check("tum satirlar 5 Latin/Kiril dilli", not eksik, "-> eksik: %s" % eksik[:3])
bos = [k for k, v in i18n._ROWS.items() if any(not str(x).strip() for x in v)]
check("bos ceviri yok", not bos, "-> %s" % bos[:3])
for kod, sozluk in i18n.EXTRA.items():
    kayip = [k for k in i18n._ROWS if k not in sozluk]
    check("%s tam (eksik yok)" % kod, not kayip, "-> %d eksik" % len(kayip))
    bosluk = [k for k, v in sozluk.items() if not str(v).strip()]
    check("%s bos ceviri yok" % kod, not bosluk, "-> %s" % bosluk[:3])
toplam = len(i18n._ROWS) * (len(i18n.ORDER) + len(i18n.EXTRA))
print("     toplam %d metin x 7 dil = %d ceviri" % (len(i18n._ROWS), toplam))

print()
print("=== 6. Dil tercihi kaydediliyor mu? ===")
i18n.set_language("de")
check("set_language calisti", i18n.current_language() == "de")
i18n._current = "tr"
i18n.load_language()
check("kayitli tercih geri yuklendi", i18n.current_language() == "de",
      "-> %s" % i18n.current_language())
i18n.set_language("tr")

print()
print("=" * 62)
if fails:
    print("BASARISIZ (%d): %s" % (len(fails), ", ".join(fails)))
    sys.exit(1)
print("HEPSI GECTI")
