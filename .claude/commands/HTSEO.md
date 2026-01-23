# HTSEO - HTML SEO Analyzer Skill

Bir web sitesinin SEO analizini yapıp detaylı öneriler sunan Claude skill.

## Kullanım

```
/HTSEO [dosya_yolu]
```

Örnek: `/HTSEO index.html` veya `/HTSEO` (otomatik olarak index.html analiz eder)

---

## Analiz Talimatları

Bu skill çalıştırıldığında aşağıdaki adımları takip et:

### 1. Dosyayı Oku

Belirtilen HTML dosyasını oku. Dosya belirtilmemişse `index.html` dosyasını analiz et.

### 2. SEO Analiz Kategorileri

Her kategori için analiz yap ve 0-100 arası puan ver:

#### A. META TAGS ANALİZİ (20 puan)
- [ ] `<title>` etiketi var mı? (50-60 karakter ideal)
- [ ] `<meta name="description">` var mı? (150-160 karakter ideal)
- [ ] `<meta name="viewport">` var mı?
- [ ] `<meta charset>` var mı?
- [ ] `<meta name="robots">` var mı?
- [ ] Open Graph etiketleri (og:title, og:description, og:image) var mı?
- [ ] Twitter Card etiketleri var mı?
- [ ] Canonical URL tanımlı mı?

#### B. HEADING YAPISI (15 puan)
- [ ] Sayfada tek bir `<h1>` var mı?
- [ ] Heading hiyerarşisi doğru mu? (H1 > H2 > H3...)
- [ ] Heading'lerde anahtar kelimeler var mı?
- [ ] Heading'ler anlamlı ve açıklayıcı mı?

#### C. İÇERİK ANALİZİ (15 puan)
- [ ] Yeterli metin içeriği var mı? (minimum 300 kelime önerisi)
- [ ] Paragraflar okunabilir uzunlukta mı?
- [ ] İç linkler (internal links) var mı?
- [ ] Dış linkler (external links) var mı?
- [ ] Call-to-action (CTA) öğeleri var mı?

#### D. GÖRSEL OPTİMİZASYONU (15 puan)
- [ ] Tüm `<img>` etiketlerinde `alt` attribute var mı?
- [ ] Alt metinleri açıklayıcı mı?
- [ ] `loading="lazy"` kullanılmış mı?
- [ ] Görsel boyutları (width/height) belirtilmiş mi?
- [ ] WebP veya optimize edilmiş formatlar kullanılıyor mu?

#### E. TEKNİK SEO (15 puan)
- [ ] Semantic HTML kullanılmış mı? (header, nav, main, section, article, footer)
- [ ] `lang` attribute tanımlı mı?
- [ ] Yapısal veri (Schema.org / JSON-LD) var mı?
- [ ] Favicon tanımlı mı?
- [ ] 404 sayfası var mı?
- [ ] robots.txt var mı?
- [ ] sitemap.xml var mı?

#### F. PERFORMANS (10 puan)
- [ ] CSS dosyaları minimize edilmiş mi?
- [ ] JavaScript dosyaları minimize edilmiş mi?
- [ ] Kritik CSS inline mı?
- [ ] JavaScript defer/async kullanılmış mı?
- [ ] Gereksiz kod/yorum var mı?

#### G. MOBİL UYUMLULUK (10 puan)
- [ ] Responsive tasarım var mı? (media queries)
- [ ] Touch-friendly butonlar var mı? (min 44x44px)
- [ ] Font boyutları okunabilir mi? (min 16px)
- [ ] Viewport doğru ayarlanmış mı?

---

### 3. Rapor Formatı

Analiz sonucunu aşağıdaki formatta sun:

```
╔══════════════════════════════════════════════════════════════╗
║                    HTSEO ANALİZ RAPORU                       ║
╠══════════════════════════════════════════════════════════════╣
║  Dosya: [dosya_adı]                                          ║
║  Tarih: [tarih]                                              ║
║  Genel Puan: [TOPLAM]/100                                    ║
╚══════════════════════════════════════════════════════════════╝

📊 KATEGORİ PUANLARI
┌─────────────────────────────┬────────┬─────────┐
│ Kategori                    │ Puan   │ Durum   │
├─────────────────────────────┼────────┼─────────┤
│ Meta Tags                   │ XX/20  │ 🟢/🟡/🔴 │
│ Heading Yapısı              │ XX/15  │ 🟢/🟡/🔴 │
│ İçerik Analizi              │ XX/15  │ 🟢/🟡/🔴 │
│ Görsel Optimizasyonu        │ XX/15  │ 🟢/🟡/🔴 │
│ Teknik SEO                  │ XX/15  │ 🟢/🟡/🔴 │
│ Performans                  │ XX/10  │ 🟢/🟡/🔴 │
│ Mobil Uyumluluk             │ XX/10  │ 🟢/🟡/🔴 │
└─────────────────────────────┴────────┴─────────┘

Durum Göstergeleri:
🟢 İyi (80%+) | 🟡 Orta (50-79%) | 🔴 Zayıf (<50%)
```

### 4. Detaylı Bulgular

Her kategori için bulunan sorunları listele:

```
## ❌ BULUNAN SORUNLAR

### Meta Tags
- ⚠️ Description meta etiketi eksik
- ⚠️ Open Graph etiketleri yok

### Görseller
- ❌ 3 görsel alt text içermiyor
- ⚠️ Lazy loading kullanılmamış
```

### 5. İyileştirme Önerileri

Öncelik sırasına göre öneriler sun:

```
## 💡 İYİLEŞTİRME ÖNERİLERİ

### 🔴 Kritik (Hemen Yapılmalı)
1. **Meta Description Ekle**
   ```html
   <meta name="description" content="...">
   ```

### 🟡 Önemli (Yakın Zamanda)
1. **Open Graph Etiketleri Ekle**

### 🟢 İyileştirme (Zaman Buldukça)
1. **Schema.org Yapısal Veri Ekle**
```

### 6. Kod Örnekleri

Eksik olan öğeler için hazır kod örnekleri sun. Örneğin:

```html
<!-- Önerilen Meta Tags -->
<meta name="description" content="[site açıklaması - 150-160 karakter]">
<meta name="keywords" content="[anahtar kelimeler]">
<link rel="canonical" href="[sayfa URL'i]">

<!-- Open Graph -->
<meta property="og:title" content="[başlık]">
<meta property="og:description" content="[açıklama]">
<meta property="og:image" content="[görsel URL]">
<meta property="og:url" content="[sayfa URL]">
<meta property="og:type" content="website">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="[başlık]">
<meta name="twitter:description" content="[açıklama]">
<meta name="twitter:image" content="[görsel URL]">

<!-- Schema.org JSON-LD Örneği -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "[İşletme Adı]",
  "description": "[Açıklama]",
  "url": "[Website URL]",
  "telephone": "[Telefon]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[Adres]",
    "addressLocality": "[Şehir]",
    "postalCode": "[Posta Kodu]",
    "addressCountry": "[Ülke Kodu]"
  }
}
</script>
```

---

## Ek Özellikler

### Rakip Analizi Modu
Eğer kullanıcı bir URL verirse, WebFetch ile sayfayı çekip analiz et.

### Karşılaştırmalı Analiz
Birden fazla dosya verilirse, karşılaştırmalı tablo oluştur.

### Otomatik Düzeltme
Kullanıcı isterse, önerilen düzeltmeleri otomatik olarak uygula.

---

## Örnek Çıktı Özeti

Analizin sonunda kısa bir özet sun:

```
📈 ÖZET
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Genel SEO Skoru: 72/100 (İYİ)

✅ Güçlü Yönler:
   • Semantic HTML yapısı
   • Mobil uyumluluk
   • Heading hiyerarşisi

❌ İyileştirilmesi Gerekenler:
   • Meta description eksik
   • Görsellerde alt text yok
   • Schema.org markup eksik

⏱️ Tahmini İyileştirme Süresi: 2-3 saat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
