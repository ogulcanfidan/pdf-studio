"""Arayuz dili: 7 dil destegi.

Tasarim: kaynak dil Turkce. Ceviriler Turkce metnin KENDISIYLE anahtarlanir,
boylece kod okunur kalir (tr("Kaydet") gibi) ve ceviri eksikse program yine
calisir - Turkce metni gosterir.

Qt'nin kendi standart dugmeleri ("OK", "Cancel", "Save"...) her zaman
Ingilizce geliyordu; button_text() ile onlari da ceviriyoruz.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from .i18n_cjk import AR, ZH

#: (kod, kendi dilindeki adi) - menude bu sirayla gorunur.
LANGUAGES = [
    ("tr", "Türkçe"),
    ("en", "English"),
    ("de", "Deutsch"),
    ("fr", "Français"),
    ("es", "Español"),
    ("ru", "Русский"),
    ("zh", "中文"),
    ("ar", "العربية"),
]

#: _ROWS satirlarindaki demetlerin sirasi.
ORDER = ("en", "de", "fr", "es", "ru")

#: Cince ve Arapca ayri sozluklerde (i18n_cjk.py).
EXTRA = {"zh": ZH, "ar": AR}

#: Sagdan sola yazilan diller.
RTL = {"ar"}

_current = "tr"

# Turkce  ->  (en, de, fr, es, it, ru)
_ROWS = {
    '&Dosya':
        ('&File', '&Datei', '&Fichier', '&Archivo', '&Файл'),
    'Dü&zen':
        ('&Edit', '&Bearbeiten', '&Édition', '&Editar', '&Правка'),
    '&Sayfa':
        ('&Page', '&Seite', '&Page', '&Página', '&Страница'),
    '&Araçlar':
        ('&Tools', '&Werkzeuge', '&Outils', '&Herramientas', '&Инструменты'),
    '&Görünüm':
        ('&View', '&Ansicht', '&Affichage', '&Ver', '&Вид'),
    '&Yardım':
        ('&Help', '&Hilfe', '&Aide', '&Ayuda', '&Справка'),
    '&Dil':
        ('&Language', '&Sprache', '&Langue', '&Idioma', '&Язык'),
    "PDF'i dönüştür":
        ('Convert PDF', 'PDF konvertieren', 'Convertir le PDF', 'Convertir PDF', 'Конвертировать PDF'),
    '&Yeni boş PDF':
        ('&New blank PDF', '&Neues leeres PDF', '&Nouveau PDF vierge', '&Nuevo PDF en blanco', '&Новый пустой PDF'),
    '&Aç…':
        ('&Open…', '&Öffnen…', '&Ouvrir…', '&Abrir…', '&Открыть…'),
    '&Kaydet':
        ('&Save', '&Speichern', '&Enregistrer', '&Guardar', '&Сохранить'),
    'Farklı k&aydet…':
        ('Save &as…', 'Speichern &unter…', 'Enregistrer &sous…', 'Guardar &como…', 'Сохранить &как…'),
    'Sıkıştırarak kaydet…':
        ('Save compressed…', 'Komprimiert speichern…', 'Enregistrer compressé…', 'Guardar comprimido…', 'Сохранить сжатым…'),
    'Metin (.txt)…':
        ('Text (.txt)…', 'Text (.txt)…', 'Texte (.txt)…', 'Texto (.txt)…', 'Текст (.txt)…'),
    'Resim (PNG / JPEG)…':
        ('Image (PNG / JPEG)…', 'Bild (PNG / JPEG)…', 'Image (PNG / JPEG)…', 'Imagen (PNG / JPEG)…', 'Изображение (PNG / JPEG)…'),
    'Web sayfası (.html)…':
        ('Web page (.html)…', 'Webseite (.html)…', 'Page web (.html)…', 'Página web (.html)…', 'Веб-страница (.html)…'),
    'Vektör (.svg)…':
        ('Vector (.svg)…', 'Vektor (.svg)…', 'Vectoriel (.svg)…', 'Vectorial (.svg)…', 'Вектор (.svg)…'),
    'Word belgesi (.docx)…':
        ('Word document (.docx)…', 'Word-Dokument (.docx)…', 'Document Word (.docx)…', 'Documento de Word (.docx)…', 'Документ Word (.docx)…'),
    "PDF'e dönüştürerek aç…":
        ('Convert to PDF and open…', 'In PDF umwandeln und öffnen…', 'Convertir en PDF et ouvrir…', 'Convertir a PDF y abrir…', 'Преобразовать в PDF и открыть…'),
    'Çı&kış':
        ('E&xit', '&Beenden', '&Quitter', '&Salir', '&Выход'),
    '&Geri al':
        ('&Undo', '&Rückgängig', '&Annuler', '&Deshacer', '&Отменить'),
    '&Yinele':
        ('&Redo', '&Wiederholen', '&Rétablir', '&Rehacer', '&Повторить'),
    '&Ara…':
        ('&Find…', '&Suchen…', '&Rechercher…', '&Buscar…', '&Найти…'),
    'Sola döndür':
        ('Rotate left', 'Nach links drehen', 'Pivoter à gauche', 'Girar a la izquierda', 'Повернуть влево'),
    'Sağa döndür':
        ('Rotate right', 'Nach rechts drehen', 'Pivoter à droite', 'Girar a la derecha', 'Повернуть вправо'),
    'Sayfayı sil':
        ('Delete page', 'Seite löschen', 'Supprimer la page', 'Eliminar página', 'Удалить страницу'),
    'Sayfayı çoğalt':
        ('Duplicate page', 'Seite duplizieren', 'Dupliquer la page', 'Duplicar página', 'Дублировать страницу'),
    'Boş sayfa ekle':
        ('Insert blank page', 'Leere Seite einfügen', 'Insérer une page vierge', 'Insertar página en blanco', 'Вставить пустую страницу'),
    'PDF ekle (birleştir)…':
        ('Append PDF (merge)…', 'PDF anhängen (zusammenführen)…', 'Ajouter un PDF (fusionner)…', 'Añadir PDF (combinar)…', 'Добавить PDF (объединить)…'),
    'Seçili sayfaları çıkar…':
        ('Extract selected pages…', 'Ausgewählte Seiten extrahieren…', 'Extraire les pages sélectionnées…', 'Extraer páginas seleccionadas…', 'Извлечь выбранные страницы…'),
    'Filigran ekle…':
        ('Add watermark…', 'Wasserzeichen hinzufügen…', 'Ajouter un filigrane…', 'Añadir marca de agua…', 'Добавить водяной знак…'),
    'Formu sabitle':
        ('Flatten form', 'Formular fixieren', 'Aplatir le formulaire', 'Aplanar formulario', 'Свести форму'),
    'Seç / Kaydır':
        ('Select / Pan', 'Auswählen / Verschieben', 'Sélection / Déplacer', 'Seleccionar / Desplazar', 'Выбор / Панорама'),
    'Metni düzenle':
        ('Edit text', 'Text bearbeiten', 'Modifier le texte', 'Editar texto', 'Редактировать текст'),
    'Taşı':
        ('Move', 'Verschieben', 'Déplacer', 'Mover', 'Переместить'),
    'Stil kopyala':
        ('Copy style', 'Stil kopieren', 'Copier le style', 'Copiar estilo', 'Копировать стиль'),
    'Metin ekle':
        ('Add text', 'Text hinzufügen', 'Ajouter du texte', 'Añadir texto', 'Добавить текст'),
    'Vurgula':
        ('Highlight', 'Hervorheben', 'Surligner', 'Resaltar', 'Выделить'),
    'Altını çiz':
        ('Underline', 'Unterstreichen', 'Souligner', 'Subrayar', 'Подчеркнуть'),
    'Üstünü çiz':
        ('Strikethrough', 'Durchstreichen', 'Barrer', 'Tachar', 'Зачеркнуть'),
    'Serbest çizim':
        ('Freehand', 'Freihand', 'Dessin libre', 'Dibujo libre', 'Рисование'),
    'Dikdörtgen':
        ('Rectangle', 'Rechteck', 'Rectangle', 'Rectángulo', 'Прямоугольник'),
    'Resim / İmza':
        ('Image / Signature', 'Bild / Unterschrift', 'Image / Signature', 'Imagen / Firma', 'Изображение / Подпись'),
    'Karart':
        ('Redact', 'Schwärzen', 'Caviarder', 'Redactar', 'Удалить данные'),
    'Yakınlaştır':
        ('Zoom in', 'Vergrößern', 'Zoom avant', 'Acercar', 'Увеличить'),
    'Uzaklaştır':
        ('Zoom out', 'Verkleinern', 'Zoom arrière', 'Alejar', 'Уменьшить'),
    'Genişliğe sığdır':
        ('Fit width', 'Breite anpassen', 'Ajuster à la largeur', 'Ajustar al ancho', 'По ширине'),
    'Sayfaya sığdır':
        ('Fit page', 'Seite anpassen', 'Ajuster à la page', 'Ajustar a la página', 'Страница целиком'),
    'Önceki sayfa':
        ('Previous page', 'Vorherige Seite', 'Page précédente', 'Página anterior', 'Предыдущая страница'),
    'Sonraki sayfa':
        ('Next page', 'Nächste Seite', 'Page suivante', 'Página siguiente', 'Следующая страница'),
    'Hakkında':
        ('About', 'Über', 'À propos', 'Acerca de', 'О программе'),
    'Klavye kısayolları':
        ('Keyboard shortcuts', 'Tastenkürzel', 'Raccourcis clavier', 'Atajos de teclado', 'Сочетания клавиш'),
    'Dosya':
        ('File', 'Datei', 'Fichier', 'Archivo', 'Файл'),
    'Araçlar':
        ('Tools', 'Werkzeuge', 'Outils', 'Herramientas', 'Инструменты'),
    'Görünüm':
        ('View', 'Ansicht', 'Affichage', 'Ver', 'Вид'),
    'Aç':
        ('Open', 'Öffnen', 'Ouvrir', 'Abrir', 'Открыть'),
    'Kaydet':
        ('Save', 'Speichern', 'Enregistrer', 'Guardar', 'Сохранить'),
    'Geri al':
        ('Undo', 'Rückgängig', 'Annuler', 'Deshacer', 'Отменить'),
    'Yinele':
        ('Redo', 'Wiederholen', 'Rétablir', 'Rehacer', 'Повторить'),
    'Renk:':
        ('Color:', 'Farbe:', 'Couleur :', 'Color:', 'Цвет:'),
    'Kalınlık:':
        ('Width:', 'Stärke:', 'Épaisseur :', 'Grosor:', 'Толщина:'),
    'Stili bırak':
        ('Drop style', 'Stil verwerfen', 'Abandonner le style', 'Soltar estilo', 'Сбросить стиль'),
    'Sayfalar':
        ('Pages', 'Seiten', 'Pages', 'Páginas', 'Страницы'),
    'Form alanları':
        ('Form fields', 'Formularfelder', 'Champs de formulaire', 'Campos del formulario', 'Поля формы'),
    'Alan':
        ('Field', 'Feld', 'Champ', 'Campo', 'Поле'),
    'Sayfa':
        ('Page', 'Seite', 'Page', 'Página', 'Страница'),
    'Değer':
        ('Value', 'Wert', 'Valeur', 'Valor', 'Значение'),
    'İşaretsiz':
        ('Unchecked', 'Nicht markiert', 'Non coché', 'Sin marcar', 'Не отмечено'),
    'İşaretli':
        ('Checked', 'Markiert', 'Coché', 'Marcado', 'Отмечено'),
    'Belge açılmadı.':
        ('No document open.', 'Kein Dokument geöffnet.', 'Aucun document ouvert.', 'No hay documento abierto.', 'Документ не открыт.'),
    'Bu belgede doldurulabilir form alanı yok.':
        ('This document has no fillable form fields.', 'Dieses Dokument hat keine ausfüllbaren Formularfelder.', 'Ce document ne contient aucun champ de formulaire.', 'Este documento no tiene campos de formulario.', 'В этом документе нет заполняемых полей.'),
    'Formu sabitle (düzenlenemez yap)':
        ('Flatten form (make non-editable)', 'Formular fixieren (nicht mehr bearbeitbar)', 'Aplatir le formulaire (non modifiable)', 'Aplanar formulario (no editable)', 'Свести форму (без редактирования)'),
    'Seç: işaretlemeye çift tıkla → sil. Boşlukta sürükle → kaydır.':
        ('Select: double-click a markup to delete it. Drag empty space to pan.', 'Auswählen: Markierung doppelklicken zum Löschen. Leerraum ziehen zum Verschieben.', 'Sélection : double-cliquez sur une annotation pour la supprimer. Faites glisser le vide pour déplacer.', 'Seleccionar: doble clic en una marca para borrarla. Arrastra el vacío para desplazar.', 'Выбор: двойной щелчок по пометке удаляет её. Перетаскивание пустого места — панорама.'),
    'Metin ekle: yazının geleceği kutuyu sürükleyerek çiz.':
        ('Add text: drag a box where the text should go.', 'Text hinzufügen: Rahmen ziehen, wo der Text stehen soll.', "Ajouter du texte : tracez un cadre à l'emplacement voulu.", 'Añadir texto: arrastra un cuadro donde irá el texto.', 'Добавить текст: растяните рамку в нужном месте.'),
    'Metni düzenle: değiştirmek istediğin yazıya tıkla.':
        ('Edit text: click the text you want to change.', 'Text bearbeiten: auf den zu ändernden Text klicken.', 'Modifier le texte : cliquez sur le texte à changer.', 'Editar texto: haz clic en el texto que quieras cambiar.', 'Редактирование: щёлкните по тексту, который нужно изменить.'),
    'Taşı: önce taşınacak alanı kutuyla seç (tek harf de olur), sonra seçimi sürükle.':
        ('Move: first box-select what to move (even one letter), then drag the selection.', 'Verschieben: erst den Bereich auswählen (auch ein Buchstabe), dann die Auswahl ziehen.', "Déplacer : sélectionnez d'abord la zone (même une lettre), puis faites glisser la sélection.", 'Mover: primero selecciona el área (incluso una letra), luego arrastra la selección.', 'Перемещение: сначала выделите область (хоть одну букву), затем перетащите выделение.'),
    'Stil kopyala: önce kaynak yazıya, sonra uygulanacak yazıya tıkla.':
        ('Copy style: click the source text, then the text to apply it to.', 'Stil kopieren: erst auf den Quelltext, dann auf den Zieltext klicken.', 'Copier le style : cliquez sur le texte source, puis sur le texte cible.', 'Copiar estilo: haz clic en el texto origen y luego en el destino.', 'Копирование стиля: щёлкните исходный текст, затем целевой.'),
    'Vurgula: metnin üzerinden sürükle.':
        ('Highlight: drag across the text.', 'Hervorheben: über den Text ziehen.', 'Surligner : faites glisser sur le texte.', 'Resaltar: arrastra sobre el texto.', 'Выделение: проведите по тексту.'),
    'Altını çiz: metnin üzerinden sürükle.':
        ('Underline: drag across the text.', 'Unterstreichen: über den Text ziehen.', 'Souligner : faites glisser sur le texte.', 'Subrayar: arrastra sobre el texto.', 'Подчёркивание: проведите по тексту.'),
    'Üstünü çiz: metnin üzerinden sürükle.':
        ('Strikethrough: drag across the text.', 'Durchstreichen: über den Text ziehen.', 'Barrer : faites glisser sur le texte.', 'Tachar: arrastra sobre el texto.', 'Зачёркивание: проведите по тексту.'),
    'Serbest çizim: basılı tutup çiz.':
        ('Freehand: hold and draw.', 'Freihand: gedrückt halten und zeichnen.', 'Dessin libre : maintenez et dessinez.', 'Dibujo libre: mantén pulsado y dibuja.', 'Рисование: удерживайте и рисуйте.'),
    'Dikdörtgen: çizmek istediğin alanı sürükle.':
        ('Rectangle: drag the area to draw.', 'Rechteck: den Bereich aufziehen.', 'Rectangle : faites glisser la zone à dessiner.', 'Rectángulo: arrastra el área a dibujar.', 'Прямоугольник: растяните нужную область.'),
    'Resim/İmza: yerleştireceğin alanı sürükle, sonra dosya seç.':
        ('Image/Signature: drag the area, then pick a file.', 'Bild/Unterschrift: Bereich ziehen, dann Datei wählen.', 'Image/Signature : tracez la zone, puis choisissez un fichier.', 'Imagen/Firma: arrastra el área y elige un archivo.', 'Изображение/Подпись: растяните область, затем выберите файл.'),
    'Karart: alanı sürükle — içerik dosyadan kalıcı silinir.':
        ('Redact: drag the area — the content is permanently removed from the file.', 'Schwärzen: Bereich ziehen — der Inhalt wird dauerhaft aus der Datei entfernt.', 'Caviarder : tracez la zone — le contenu est supprimé définitivement du fichier.', 'Redactar: arrastra el área — el contenido se elimina del archivo de forma permanente.', 'Удаление данных: растяните область — содержимое навсегда удаляется из файла.'),
    'Yazı silinip aynı taban çizgisine yeniden yazılır; belgenin kendi fontu, punto ve harf aralığı korunur.':
        ("The text is removed and rewritten on the same baseline; the document's own font, size and letter spacing are preserved.", 'Der Text wird entfernt und auf derselben Grundlinie neu geschrieben; Schriftart, Größe und Laufweite des Dokuments bleiben erhalten.', "Le texte est supprimé puis réécrit sur la même ligne de base ; la police, la taille et l'interlettrage du document sont conservés.", 'El texto se elimina y se reescribe en la misma línea base; se conservan la fuente, el tamaño y el espaciado del documento.', 'Текст удаляется и переписывается по той же базовой линии; шрифт, размер и межбуквенный интервал сохраняются.'),
    'Bu satırda birden fazla yazı tipi var; tamamı tek bir yazı tipiyle yeniden yazılacak.':
        ('This line uses more than one font; it will be rewritten in a single font.', 'Diese Zeile verwendet mehrere Schriftarten; sie wird in einer einzigen neu geschrieben.', 'Cette ligne utilise plusieurs polices ; elle sera réécrite avec une seule.', 'Esta línea usa más de una fuente; se reescribirá con una sola.', 'В этой строке несколько шрифтов; она будет переписана одним.'),
    'Font:':
        ('Font:', 'Schrift:', 'Police :', 'Fuente:', 'Шрифт:'),
    'Harf aralığı:':
        ('Letter spacing:', 'Laufweite:', 'Interlettrage :', 'Espaciado:', 'Интервал:'),
    'Özgün punto':
        ('Original size', 'Originalgröße', "Taille d'origine",
         'Tamaño original', 'Исходный размер'),
    'Özgün renk':
        ('Original color', 'Originalfarbe', "Couleur d'origine", 'Color original', 'Исходный цвет'),
    'Taşındı':
        ('Moved', 'Verschoben', 'Déplacé', 'Movido', 'Перемещено'),
    'eski yazının üzeri örtüldü':
        ('the old text was covered', 'der alte Text wurde überdeckt',
         "l'ancien texte a été recouvert", 'el texto anterior fue cubierto',
         'старый текст закрыт'),
    'belgenin fontu bu harfleri çizemedi, tamamı %s ile yazıldı':
        ("the document font could not draw these letters; all of it was written in %s",
         'die Dokumentschrift konnte diese Buchstaben nicht darstellen; alles wurde in %s geschrieben',
         "la police du document ne pouvait pas dessiner ces lettres ; tout a été écrit en %s",
         'la fuente del documento no pudo dibujar estas letras; todo se escribió en %s',
         'шрифт документа не смог отрисовать эти буквы; всё написано шрифтом %s'),
    'Burada görsel ya da çizim yok.':
        ('No image or drawing here.', 'Hier ist kein Bild und keine Zeichnung.', 'Aucune image ni dessin ici.', 'No hay imagen ni dibujo aquí.', 'Здесь нет изображения или рисунка.'),
    'Çizim seçildi':
        ('Drawing selected', 'Zeichnung ausgewählt', 'Dessin sélectionné', 'Dibujo seleccionado', 'Рисунок выбран'),
    'Çizim güncellendi':
        ('Drawing updated', 'Zeichnung aktualisiert', 'Dessin mis à jour', 'Dibujo actualizado', 'Рисунок обновлён'),
    'Çizim silindi.':
        ('Drawing deleted.', 'Zeichnung gelöscht.', 'Dessin supprimé.', 'Dibujo eliminado.', 'Рисунок удалён.'),
    'Çizim taşınamadı: %s':
        ('Could not move the drawing: %s', 'Zeichnung konnte nicht verschoben werden: %s', 'Impossible de déplacer le dessin : %s', 'No se pudo mover el dibujo: %s', 'Не удалось переместить рисунок: %s'),
    'Çizim silinemedi: %s':
        ('Could not delete the drawing: %s', 'Zeichnung konnte nicht gelöscht werden: %s', 'Impossible de supprimer le dessin : %s', 'No se pudo eliminar el dibujo: %s', 'Не удалось удалить рисунок: %s'),
    'Çizim için geçerli bir alan seçilmedi.':
        ('No valid area was selected for the drawing.', 'Für die Zeichnung wurde kein gültiger Bereich gewählt.', "Aucune zone valide n'a été choisie pour le dessin.", 'No se seleccionó un área válida para el dibujo.', 'Для рисунка не выбрана подходящая область.'),
    'Çizim okunamadı.':
        ('The drawing could not be read.', 'Die Zeichnung konnte nicht gelesen werden.', "Le dessin n'a pas pu être lu.", 'No se pudo leer el dibujo.', 'Не удалось прочитать рисунок.'),
    'Görsel ve simge: tıkla seç, içinden sürükle taşı, köşeden sürükle boyutlandır, Delete sil.':
        ('Image and icon: click to select, drag inside to move, a corner to resize, Delete to remove', 'Bild und Symbol: klicken zum Auswählen, hineinziehen zum Verschieben, Ecke ziehen zum Skalieren, Entf zum Löschen', "Image et icône : cliquez pour sélectionner, glissez à l'intérieur pour déplacer, un coin pour redimensionner, Suppr pour supprimer", 'Imagen e icono: haz clic para seleccionar, arrastra dentro para mover, una esquina para redimensionar, Supr para eliminar', 'Изображение и значок: щёлкните, чтобы выбрать, тяните внутри — переместить, за угол — размер, Delete — удалить'),
    'Görsel düzenle':
        ('Edit image', 'Bild bearbeiten', "Modifier l'image", 'Editar imagen', 'Правка изображения'),
    'Burada görsel yok.':
        ('No image here.', 'Hier ist kein Bild.', 'Aucune image ici.', 'No hay imagen aquí.', 'Здесь нет изображения.'),
    'Görsel seçildi':
        ('Image selected', 'Bild ausgewählt', 'Image sélectionnée', 'Imagen seleccionada', 'Изображение выбрано'),
    'taşımak için içinden, boyutlandırmak için köşeden sürükle; silmek için Delete':
        ('drag inside to move, a corner to resize, Delete to remove', 'hineinziehen zum Verschieben, Ecke ziehen zum Skalieren, Entf zum Löschen', "glissez à l'intérieur pour déplacer, un coin pour redimensionner, Suppr pour supprimer", 'arrastra dentro para mover, una esquina para redimensionar, Supr para eliminar', 'тяните внутри — переместить, за угол — размер, Delete — удалить'),
    'Görsel güncellendi':
        ('Image updated', 'Bild aktualisiert', 'Image mise à jour', 'Imagen actualizada', 'Изображение обновлено'),
    'Görsel silindi.':
        ('Image deleted.', 'Bild gelöscht.', 'Image supprimée.', 'Imagen eliminada.', 'Изображение удалено.'),
    'Görsel yerleştirilemedi: %s':
        ('Could not place the image: %s', 'Bild konnte nicht platziert werden: %s', "Impossible de placer l'image : %s", 'No se pudo colocar la imagen: %s', 'Не удалось разместить изображение: %s'),
    'Görsel silinemedi: %s':
        ('Could not delete the image: %s', 'Bild konnte nicht gelöscht werden: %s', "Impossible de supprimer l'image : %s", 'No se pudo eliminar la imagen: %s', 'Не удалось удалить изображение: %s'),
    'Görsel: tıkla seç, içinden sürükle taşı, köşeden sürükle boyutlandır, Delete sil.':
        ('Image: click to select, drag inside to move, a corner to resize, Delete to remove.', 'Bild: klicken zum Auswählen, hineinziehen zum Verschieben, Ecke ziehen zum Skalieren, Entf zum Löschen.', 'Image : cliquez pour sélectionner, glissez pour déplacer, un coin pour redimensionner, Suppr pour supprimer.', 'Imagen: clic para seleccionar, arrastra para mover, una esquina para redimensionar, Supr para eliminar.', 'Изображение: щёлкните для выбора, тяните внутри — переместить, за угол — размер, Delete — удалить.'),
    'Yatay aynala':
        ('Flip horizontally', 'Horizontal spiegeln', 'Miroir horizontal', 'Voltear horizontalmente', 'Отразить по горизонтали'),
    'Dikey aynala':
        ('Flip vertically', 'Vertikal spiegeln', 'Miroir vertical', 'Voltear verticalmente', 'Отразить по вертикали'),
    'Kırp…':
        ('Crop…', 'Zuschneiden…', 'Rogner…', 'Recortar…', 'Обрезать…'),
    'Gri tonlama':
        ('Grayscale', 'Graustufen', 'Niveaux de gris', 'Escala de grises', 'Оттенки серого'),
    'Parlaklık ve kontrast…':
        ('Brightness and contrast…', 'Helligkeit und Kontrast…', 'Luminosité et contraste…', 'Brillo y contraste…', 'Яркость и контраст…'),
    'Parlaklık ve kontrast':
        ('Brightness and contrast', 'Helligkeit und Kontrast', 'Luminosité et contraste', 'Brillo y contraste', 'Яркость и контраст'),
    'Parlaklık:':
        ('Brightness:', 'Helligkeit:', 'Luminosité :', 'Brillo:', 'Яркость:'),
    'Kontrast:':
        ('Contrast:', 'Kontrast:', 'Contraste :', 'Contraste:', 'Контраст:'),
    'Başka görselle değiştir…':
        ('Replace with another image…', 'Durch anderes Bild ersetzen…', 'Remplacer par une autre image…', 'Reemplazar con otra imagen…', 'Заменить другим изображением…'),
    'Görseli dışa aktar…':
        ('Export image…', 'Bild exportieren…', "Exporter l'image…", 'Exportar imagen…', 'Экспорт изображения…'),
    'Sil':
        ('Delete', 'Löschen', 'Supprimer', 'Eliminar', 'Удалить'),
    'Görsel düzenlenemedi: %s':
        ('Could not edit the image: %s', 'Bild konnte nicht bearbeitet werden: %s', "Impossible de modifier l'image : %s", 'No se pudo editar la imagen: %s', 'Не удалось изменить изображение: %s'),
    'Kırpmak istediğin alanı görselin içinde sürükleyerek seç.':
        ('Drag inside the image to select the area to keep.', 'Ziehen Sie im Bild den Bereich auf, der erhalten bleiben soll.', "Faites glisser dans l'image pour choisir la zone à conserver.", 'Arrastra dentro de la imagen para elegir el área a conservar.', 'Растяните область внутри изображения, которую нужно оставить.'),
    'Kırpma alanı görselin dışında kaldı.':
        ('The crop area fell outside the image.', 'Der Zuschneidebereich lag außerhalb des Bildes.', "La zone de rognage était en dehors de l'image.", 'El área de recorte quedó fuera de la imagen.', 'Область обрезки оказалась вне изображения.'),
    'Kaydedildi':
        ('Saved', 'Gespeichert', 'Enregistré', 'Guardado', 'Сохранено'),
    'Kaydedilemedi: %s':
        ('Could not save: %s', 'Konnte nicht gespeichert werden: %s', "Impossible d'enregistrer : %s", 'No se pudo guardar: %s', 'Не удалось сохранить: %s'),
    'Tamam':
        ('OK', 'OK', 'OK', 'Aceptar', 'ОК'),
    'İptal':
        ('Cancel', 'Abbrechen', 'Annuler', 'Cancelar', 'Отмена'),
    'Evet':
        ('Yes', 'Ja', 'Oui', 'Sí', 'Да'),
    'Hayır':
        ('No', 'Nein', 'Non', 'No', 'Нет'),
    'Kaydetme':
        ("Don't save", 'Nicht speichern', 'Ne pas enregistrer', 'No guardar', 'Не сохранять'),
    'Metin ekle başlığı':
        ('Add text', 'Text hinzufügen', 'Ajouter du texte', 'Añadir texto', 'Добавить текст'),
    'Yazıyı buraya gir…':
        ('Type your text here…', 'Text hier eingeben…', 'Saisissez le texte ici…', 'Escribe el texto aquí…', 'Введите текст…'),
    'Punto:':
        ('Size:', 'Größe:', 'Taille :', 'Tamaño:', 'Размер:'),
    'Renk':
        ('Color', 'Farbe', 'Couleur', 'Color', 'Цвет'),
    'Kalın':
        ('Bold', 'Fett', 'Gras', 'Negrita', 'Полужирный'),
    'Renk seç':
        ('Choose color', 'Farbe wählen', 'Choisir une couleur', 'Elegir color', 'Выбрать цвет'),
    'Metni düzenle başlığı':
        ('Edit text', 'Text bearbeiten', 'Modifier le texte', 'Editar texto', 'Редактировать текст'),
    'Kapsam:':
        ('Scope:', 'Bereich:', 'Portée :', 'Alcance:', 'Область:'),
    'Yalnızca bu satır':
        ('This line only', 'Nur diese Zeile', 'Cette ligne seulement', 'Solo esta línea', 'Только эта строка'),
    'Paragrafın tamamı':
        ('Whole paragraph', 'Ganzer Absatz', 'Paragraphe entier', 'Párrafo completo', 'Весь абзац'),
    'Filigran ekle':
        ('Add watermark', 'Wasserzeichen hinzufügen', 'Ajouter un filigrane', 'Añadir marca de agua', 'Добавить водяной знак'),
    'Metin:':
        ('Text:', 'Text:', 'Texte :', 'Texto:', 'Текст:'),
    'Açı:':
        ('Angle:', 'Winkel:', 'Angle :', 'Ángulo:', 'Угол:'),
    'Saydamlık:':
        ('Opacity:', 'Deckkraft:', 'Opacité :', 'Opacidad:', 'Прозрачность:'),
    'Filigran belgedeki tüm sayfalara eklenir.':
        ('The watermark is added to every page.', 'Das Wasserzeichen wird auf allen Seiten hinzugefügt.', 'Le filigrane est ajouté à toutes les pages.', 'La marca de agua se añade a todas las páginas.', 'Водяной знак добавляется на все страницы.'),
    'Resim olarak dışa aktar':
        ('Export as image', 'Als Bild exportieren', 'Exporter comme image', 'Exportar como imagen', 'Экспорт в изображение'),
    'Çözünürlük:':
        ('Resolution:', 'Auflösung:', 'Résolution :', 'Resolución:', 'Разрешение:'),
    'Biçim:':
        ('Format:', 'Format:', 'Format :', 'Formato:', 'Формат:'),
    'Tüm sayfalar':
        ('All pages', 'Alle Seiten', 'Toutes les pages', 'Todas las páginas', 'Все страницы'),
    'Yalnızca geçerli sayfa':
        ('Current page only', 'Nur aktuelle Seite', 'Page courante seulement', 'Solo la página actual', 'Только текущая страница'),
    'PDF dosyaları (*.pdf);;Tüm dosyalar (*)':
        ('PDF files (*.pdf);;All files (*)', 'PDF-Dateien (*.pdf);;Alle Dateien (*)', 'Fichiers PDF (*.pdf);;Tous les fichiers (*)', 'Archivos PDF (*.pdf);;Todos los archivos (*)', 'Файлы PDF (*.pdf);;Все файлы (*)'),
    'PDF aç':
        ('Open PDF', 'PDF öffnen', 'Ouvrir un PDF', 'Abrir PDF', 'Открыть PDF'),
    'Farklı kaydet':
        ('Save as', 'Speichern unter', 'Enregistrer sous', 'Guardar como', 'Сохранить как'),
    'Sıkıştırarak kaydet':
        ('Save compressed', 'Komprimiert speichern', 'Enregistrer compressé', 'Guardar comprimido', 'Сохранить сжатым'),
    'Kaydedilecek klasör':
        ('Destination folder', 'Zielordner', 'Dossier de destination', 'Carpeta de destino', 'Папка назначения'),
    'Resim seç':
        ('Choose image', 'Bild wählen', 'Choisir une image', 'Elegir imagen', 'Выбрать изображение'),
    'Ara':
        ('Find', 'Suchen', 'Rechercher', 'Buscar', 'Найти'),
    'Aranacak metin:':
        ('Text to find:', 'Suchtext:', 'Texte à rechercher :', 'Texto a buscar:', 'Искомый текст:'),
    'Kaydedilmemiş değişiklikler var. Kaydedilsin mi?':
        ('There are unsaved changes. Save them?', 'Es gibt ungespeicherte Änderungen. Speichern?', 'Des modifications ne sont pas enregistrées. Enregistrer ?', 'Hay cambios sin guardar. ¿Guardarlos?', 'Есть несохранённые изменения. Сохранить?'),
    'Burada düzenlenebilir metin yok. (Taranmış PDF olabilir.)':
        ('No editable text here. (The PDF may be scanned.)', 'Hier ist kein bearbeitbarer Text. (Das PDF ist evtl. gescannt.)', 'Aucun texte modifiable ici. (Le PDF est peut-être scanné.)', 'No hay texto editable aquí. (El PDF puede estar escaneado.)', 'Здесь нет редактируемого текста. (Возможно, PDF отсканирован.)'),
    'Seçilen alanda metin yok — işaretleme yapılmadı.':
        ('No text in the selected area — nothing was marked.', 'Kein Text im gewählten Bereich — nichts markiert.', "Aucun texte dans la zone sélectionnée — rien n'a été marqué.", 'No hay texto en el área seleccionada — no se marcó nada.', 'В выбранной области нет текста — ничего не отмечено.'),
    'Burada stil alınacak yazı yok.':
        ('No text here to copy a style from.', 'Hier gibt es keinen Text, dessen Stil kopiert werden könnte.', 'Aucun texte ici pour copier un style.', 'No hay texto aquí para copiar un estilo.', 'Здесь нет текста для копирования стиля.'),
    'Burada stil uygulanacak yazı yok.':
        ('No text here to apply the style to.', 'Hier gibt es keinen Text, auf den der Stil angewendet werden könnte.', 'Aucun texte ici auquel appliquer le style.', 'No hay texto aquí al que aplicar el estilo.', 'Здесь нет текста для применения стиля.'),
    'Stil bırakıldı.':
        ('Style dropped.', 'Stil verworfen.', 'Style abandonné.', 'Estilo soltado.', 'Стиль сброшен.'),
    'Taşıma seçimi bırakıldı.':
        ('Move selection cleared.', 'Verschiebe-Auswahl aufgehoben.', 'Sélection de déplacement annulée.', 'Selección de movimiento cancelada.', 'Выделение для перемещения снято.'),
    'Seçim hazır — içine basıp sürükle. Vazgeçmek için Esc.':
        ('Selection ready — press inside and drag. Esc to cancel.', 'Auswahl bereit — hineinklicken und ziehen. Esc zum Abbrechen.', 'Sélection prête — cliquez dedans et faites glisser. Échap pour annuler.', 'Selección lista — pulsa dentro y arrastra. Esc para cancelar.', 'Выделение готово — нажмите внутри и перетащите. Esc — отмена.'),
    'Taşınacak yazı bulunamadı — yazının üzerinden sürükle.':
        ('No text to move — drag over the text.', 'Kein Text zum Verschieben — über den Text ziehen.', 'Aucun texte à déplacer — faites glisser sur le texte.', 'No hay texto que mover — arrastra sobre el texto.', 'Нет текста для перемещения — проведите по тексту.'),
    'Dil değişikliği için pencere yeniden açılacak.':
        ('The window will reopen to apply the language change.', 'Das Fenster wird für die Sprachumstellung neu geöffnet.', 'La fenêtre sera rouverte pour appliquer la langue.', 'La ventana se reabrirá para aplicar el idioma.', 'Окно будет открыто заново для смены языка.'),
}

def available_languages():
    return list(LANGUAGES)


def current_language() -> str:
    return _current


def set_language(code: str) -> None:
    """Dili degistir ve tercihi kalici olarak sakla."""
    global _current
    if code not in dict(LANGUAGES):
        return
    _current = code
    try:
        QSettings("FMJ Software", "PDF Studio").setValue("language", code)
    except Exception:
        pass


def load_language() -> str:
    """Kayitli dil tercihini yukle (yoksa Turkce)."""
    global _current
    try:
        value = QSettings("FMJ Software", "PDF Studio").value("language")
        if value and value in dict(LANGUAGES):
            _current = str(value)
    except Exception:
        pass
    return _current


def is_rtl(code: str = None) -> bool:
    """Bu dil sagdan sola mi yaziliyor?"""
    return (code or _current) in RTL


def tr(text: str) -> str:
    """Turkce kaynagi gecerli dile cevir; ceviri yoksa kaynagi dondur."""
    if _current == "tr":
        return text

    ozel = EXTRA.get(_current)
    if ozel is not None:
        return ozel.get(text, text)

    row = _ROWS.get(text)
    if not row:
        return text
    try:
        return row[ORDER.index(_current)]
    except (ValueError, IndexError):
        return text


def apply_buttons(box) -> None:
    """QDialogButtonBox / QMessageBox dugmelerini cevir.

    Qt'nin standart dugmeleri kendi dil dosyalarina bagli ve bizim
    kurulumumuzda hep Ingilizce ('OK', 'Cancel') geliyor.
    """
    from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

    eslesme = {
        QDialogButtonBox.StandardButton.Ok: "Tamam",
        QDialogButtonBox.StandardButton.Cancel: "İptal",
        QDialogButtonBox.StandardButton.Yes: "Evet",
        QDialogButtonBox.StandardButton.No: "Hayır",
        QDialogButtonBox.StandardButton.Save: "Kaydet",
        QDialogButtonBox.StandardButton.Discard: "Kaydetme",
    }
    msg_eslesme = {
        QMessageBox.StandardButton.Ok: "Tamam",
        QMessageBox.StandardButton.Cancel: "İptal",
        QMessageBox.StandardButton.Yes: "Evet",
        QMessageBox.StandardButton.No: "Hayır",
        QMessageBox.StandardButton.Save: "Kaydet",
        QMessageBox.StandardButton.Discard: "Kaydetme",
    }

    tablo = msg_eslesme if isinstance(box, QMessageBox) else eslesme
    for standart, kaynak in tablo.items():
        try:
            button = box.button(standart)
        except Exception:
            button = None
        if button is not None:
            button.setText(tr(kaynak))
