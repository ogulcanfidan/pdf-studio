# PDF Studio — FMJ Software

Windows için masaüstü PDF düzenleyici ve biçim dönüştürücü.
Python + PySide6 (Qt) + PyMuPDF.

## Çalıştırma

`calistir.bat` dosyasına çift tıkla. İlk açılışta sanal ortamı kurup
bağımlılıkları indirir, sonraki açılışlar anında olur.

Elle:

```bat
.venv\Scripts\python.exe main.py [belge.pdf]
```

## Neler yapabilir

- **Sayfa işlemleri** — döndürme, silme, çoğaltma, yeniden sıralama,
  birleştirme, seçili sayfaları ayırma
- **Metin düzenleme** — sayfadaki yazıya tıklayıp değiştirme; belgenin kendi
  fontu, punto, renk ve harf aralığı korunur
- **Taşıma ve stil kopyalama** — seçtiğin alanı (tek harf bile) sürükleyerek
  taşıma, bir yazının biçimini başka yazıya aktarma
- **Görsel düzenleme** — ekleme, taşıma, boyutlandırma, döndürme, aynalama,
  kırpma, gri tonlama, parlaklık/kontrast, değiştirme, dışa aktarma
- **Vektör simgeler** — CV'lerdeki telefon/zarf gibi simgeleri seçme, taşıma,
  boyutlandırma, silme
- **Üzerine ekleme** — metin, vurgu, alt/üst çizgi, serbest çizim,
  dikdörtgen, resim, imza, filigran
- **Form doldurma** — alanları doldurma ve formu sabitleme
- **Biçim dönüştürme** — iki yönlü (aşağıda)
- **Sıkıştırma ve karartma** — küçültme; seçilen alanı dosyadan kalıcı silme

## Biçim dönüştürme

| PDF'ten | PDF'e |
|---|---|
| PNG / JPEG (DPI seçilebilir) | Resimler (PNG, JPG, BMP, GIF, TIFF, WEBP…) |
| Word (.docx) | Word / Office (.docx, .doc, .rtf, .odt, .pptx, .xlsx) |
| Web sayfası (.html) | Metin ve Markdown (.txt, .md, .csv) |
| Vektör (.svg) | Web sayfası (.html) |
| Düz metin (.txt) | E-kitap ve diğerleri (.epub, .xps, .cbz, .fb2, .svg) |

Office → PDF dönüşümünde kurulu **Microsoft Word** kullanılır, biçim birebir
korunur. Word yoksa LibreOffice denenir; o da yoksa yalnızca metin aktarılır
ve program bunu açıkça söyler.

## Dil

**Dil** menüsünden 8 dil: Türkçe, English, Deutsch, Français, Español,
Русский, 中文, العربية. Arapçada arayüz sağdan sola çevrilir. Seçim kalıcıdır.

## Kısayollar

| Kısayol | İşlev | | Kısayol | İşlev |
|---|---|---|---|---|
| `Ctrl+O` | Aç | | `V` | Seç / Kaydır |
| `Ctrl+S` | Kaydet | | `E` | Metni düzenle |
| `Ctrl+Shift+S` | Farklı kaydet | | `T` | Metin ekle |
| `Ctrl+Z` / `Ctrl+Y` | Geri al / Yinele | | `M` / `P` | Taşı / Stil kopyala |
| `Ctrl+F` | Ara | | `H` | Vurgula |
| `Ctrl++` / `Ctrl+-` | Yakınlaştır | | `U` / `S` | Altını / Üstünü çiz |
| `Ctrl+1` / `Ctrl+0` | Genişliğe / Sayfaya sığdır | | `D` / `R` | Çizim / Dikdörtgen |
| `PgUp` / `PgDown` | Sayfa değiştir | | `I` / `G` | Resim ekle / Görsel düzenle |
| `Ctrl+←` / `Ctrl+→` | Sayfayı döndür | | `K` | Karart |

`Ctrl` + fare tekerleği ile de yakınlaştırılır. Pencereye PDF sürükleyip
bırakabilirsin.

## Bilinmesi gerekenler

**PDF bir kelime işlemci dosyası değil.** Metin akışkan değil, sayfaya
konumlandırılmış parçalar hâlinde durur. Program seçilen yazıyı kaldırıp
yerine yenisini yazar; düzenleme birimi **satır**, paragraf değil.

**Font.** Önce belgenin kendi gömülü fontu kullanılır. Gömülü font alt küme
ise (belgede geçmeyen harfleri içermez), sistemde kurulu aynı font, o da
yoksa aynı kalınlıkta bir sistem fontu denenir. Pratik sonuç: *belgenin fontu
sende kurulu değilse yeni harfler farklı görünebilir* — çözüm fontu kurmak.

**Geri alma.** Son 25 işlem geri alınabilir; her adımda belgenin tamamının
anlık görüntüsü tutulduğu için çok büyük belgelerde bellek kullanımı artar.

**Yol uzunluğu.** PySide6'nın DLL'leri Windows'un 260 karakterlik yol
sınırına takılabilir; projeyi kısa bir yolda tut.

Taranmış (resim) PDF'lerde metin düzenlenemez — OCR yoktur.

## Proje yapısı

```
main.py                 giriş noktası
pdfstudio/
  model.py              PDF işlemleri + geri alma (arayüzden bağımsız)
  mainwindow.py         menüler, araç çubukları, eylem bağlantıları
  pageview.py           sayfa tuvali, yakınlaştırma, araç etkileşimleri
  panels.py             küçük resim çubuğu ve form paneli
  dialogs.py            diyaloglar
  convert.py            biçim dönüştürme
  imaging.py            görsel piksel işlemleri
  fontfix.py            alt küme fontların eksik cmap tablosunu onarır
  verify.py             sonucu görsel olarak doğrulama
  branding.py           FMJ Software kimliği
  i18n.py               çeviriler
```

## Testler

Ekransız (offscreen) çalışır, her dosya tek başına:

```bat
.venv\Scripts\python.exe test_model.py
```

Toplam 24 test dosyası: model, arayüz, metin değiştirme, font seçimi, harf
aralığı, görsel ve vektör düzenleme, dönüştürme, çok dillilik.

## Tek dosya .exe

```bat
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\pyinstaller.exe --noconfirm --windowed --name "PDF Studio" main.py
```

Sonuç `dist\PDF Studio\` altında oluşur.

## Marka

Uygulama simgesi (belge + kalem) pencerede ve görev çubuğunda görünür; kurum
logosu Hakkında kutusunda kullanılır. Kaydedilen PDF'lerin üstverisine
`PDF Studio — FMJ Software` damgası işlenir, belgenin başlık/yazar bilgileri
korunur.
