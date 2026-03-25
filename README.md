# 📚 BookForge

**PDF → EPUB & A5 PDF dönüştürücü** — Saf Python. Calibre gerekmez.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## ✨ Özellikler

- 🔍 **Otomatik OCR** — Taranmış sayfaları metne çevirir (Türkçe + İngilizce karışık)
- 📖 **EPUB** — Telefon, tablet, e-reader için akıcı format
- 📄 **A5 PDF** — Roman boyutunda, okunması kolay
- 🎛️ **Tarayıcı arayüzü** — Sürükle-bırak, canlı log
- ⚡ **Karışık PDF** — Metin olan sayfalar OCR'ı otomatik atlar
- 🐍 **Saf Python** — Calibre kurulumu gerekmez

---

## 📦 Kullanılan Kütüphaneler

| Görev | Kütüphane |
|---|---|
| OCR | `ocrmypdf` + Tesseract |
| PDF okuma | `pymupdf` (fitz) |
| EPUB oluşturma | `ebooklib` |
| A5 PDF oluşturma | `reportlab` |
| Web arayüz | `flask` |

---

## 🛠️ Kurulum

### 1. Tesseract kur (sistem uygulaması, bir kez)

**Windows:**
→ https://github.com/UB-Mannheim/tesseract/wiki
Kurulumda "Additional language data" → Türkçe'yi seç

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install tesseract-ocr tesseract-ocr-tur tesseract-ocr-eng
```

### 2. Python bağımlılıklarını kur

```bash
pip install -r requirements.txt
```

### 3. Çalıştır

```bash
python app.py
```

Tarayıcıda aç: **http://localhost:5000**

---

## 🚀 Kullanım

1. PDF'i sürükle veya seç
2. Kitap adı gir (opsiyonel)
3. Dil seç → Çıktı formatı seç
4. OCR aç/kapat
5. **Dönüştür** → İndir

---

## 📂 Proje Yapısı

```
bookforge/
├── app.py           # Flask sunucu
├── converter.py     # PDF → EPUB / A5 PDF pipeline
├── templates/
│   └── index.html   # Arayüz
├── uploads/         # Geçici yüklemeler (git'e girmez)
├── output/          # Çıktılar (git'e girmez)
├── requirements.txt
└── README.md
```

---

## ⚙️ Pipeline

```
PDF Girdi
  │
  ├─► ocrmypdf     → Taranmış sayfaları metne çevir (metin olanları atlar)
  │
  ├─► pymupdf      → Sayfa sayfa metin çıkar
  │
  ├─► Bölüm tespiti → Başlık satırlarından bölümlere ayır
  │
  ├─► ebooklib     → EPUB oluştur
  │
  └─► reportlab    → A5 PDF oluştur (Georgia, justify, 10.5pt)
```

---

## 🔧 Sorun Giderme

**Tesseract bulunamıyor:**
`tesseract --version` komutu çalışıyor mu? Windows'ta PATH'e eklenmeli.

**OCR kalitesi düşük:**
Türkçe dil paketi kurulu olmalı. Kurulumda seçilmemişse tekrar kur.

**EPUB boş çıkıyor:**
PDF tamamen görsel (taranmış) olabilir — OCR'yi açık bırak.

---

## 📄 Lisans

MIT License
