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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Ek Komutlar ve Modlar

### /HTSEO fix
Otomatik düzeltme modu. Tespit edilen tüm SEO sorunlarını otomatik olarak düzeltir.

```
/HTSEO fix [dosya_yolu]
```

Bu mod şunları otomatik yapar:
- Eksik meta etiketlerini ekler
- Open Graph ve Twitter Card ekler
- Canonical URL ekler
- Schema.org JSON-LD ekler
- Favicon link'i ekler

### /HTSEO robots
robots.txt dosyası oluşturur.

```
/HTSEO robots
```

### /HTSEO sitemap
sitemap.xml dosyası oluşturur.

```
/HTSEO sitemap
```

### /HTSEO meta
Sadece meta tag analizi ve önerileri sunar.

```
/HTSEO meta [dosya_yolu]
```

### /HTSEO schema [type]
Belirtilen tipte Schema.org JSON-LD oluşturur.

```
/HTSEO schema LocalBusiness
/HTSEO schema Organization
/HTSEO schema WebSite
/HTSEO schema Course
```

### /HTSEO compare [url]
Mevcut sayfayı bir rakip URL ile karşılaştırır.

```
/HTSEO compare https://rakipsite.com
```

---

## Generator Talimatları

### robots.txt Generator

`/HTSEO robots` komutu çalıştırıldığında:

1. Proje kök dizininde `robots.txt` dosyası oluştur
2. Aşağıdaki şablonu kullan:

```txt
# robots.txt for [Site Adı]
# Generated by HTSEO

User-agent: *
Allow: /

# Crawl-delay (optional)
# Crawl-delay: 10

# Disallow admin/private areas
Disallow: /admin/
Disallow: /private/
Disallow: /*.json$
Disallow: /*.xml$

# Allow important resources
Allow: /css/
Allow: /js/
Allow: /images/

# Sitemap location
Sitemap: [SITE_URL]/sitemap.xml
```

3. Kullanıcıya site URL'ini sor ve Sitemap satırını güncelle

---

### sitemap.xml Generator

`/HTSEO sitemap` komutu çalıştırıldığında:

1. Projedeki tüm HTML dosyalarını bul (Glob ile `**/*.html`)
2. Her dosya için bir `<url>` girişi oluştur
3. Aşağıdaki şablonu kullan:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>[SITE_URL]/</loc>
        <lastmod>[YYYY-MM-DD]</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>[SITE_URL]/about.html</loc>
        <lastmod>[YYYY-MM-DD]</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
    <!-- Diğer sayfalar -->
</urlset>
```

4. Öncelik değerleri:
   - Ana sayfa (index.html): 1.0
   - Ana bölümler: 0.8
   - Alt sayfalar: 0.6
   - Diğer: 0.4

---

### Schema.org Generator

`/HTSEO schema [type]` komutu çalıştırıldığında:

#### LocalBusiness (Yerel İşletme)
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "[İşletme Adı]",
  "description": "[Açıklama]",
  "url": "[Website URL]",
  "telephone": "[Telefon]",
  "email": "[Email]",
  "image": "[Logo URL]",
  "priceRange": "$$",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[Sokak Adresi]",
    "addressLocality": "[Şehir]",
    "addressRegion": "[Bölge]",
    "postalCode": "[Posta Kodu]",
    "addressCountry": "[Ülke Kodu]"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "[Enlem]",
    "longitude": "[Boylam]"
  },
  "openingHoursSpecification": [
    {
      "@type": "OpeningHoursSpecification",
      "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
      "opens": "09:00",
      "closes": "18:00"
    }
  ],
  "sameAs": [
    "[Facebook URL]",
    "[Instagram URL]",
    "[Twitter URL]"
  ]
}
```

#### Organization (Kuruluş)
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "[Kuruluş Adı]",
  "url": "[Website URL]",
  "logo": "[Logo URL]",
  "description": "[Açıklama]",
  "foundingDate": "[Kuruluş Yılı]",
  "contactPoint": {
    "@type": "ContactPoint",
    "telephone": "[Telefon]",
    "contactType": "customer service",
    "availableLanguage": ["Turkish", "English"]
  },
  "sameAs": [
    "[Sosyal Medya URL'leri]"
  ]
}
```

#### WebSite (Web Sitesi)
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "[Site Adı]",
  "url": "[Site URL]",
  "description": "[Site Açıklaması]",
  "publisher": {
    "@type": "Organization",
    "name": "[Yayıncı Adı]",
    "logo": {
      "@type": "ImageObject",
      "url": "[Logo URL]"
    }
  },
  "potentialAction": {
    "@type": "SearchAction",
    "target": "[Site URL]/search?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

#### Course (Kurs/Ders)
```json
{
  "@context": "https://schema.org",
  "@type": "Course",
  "name": "[Kurs Adı]",
  "description": "[Kurs Açıklaması]",
  "provider": {
    "@type": "Organization",
    "name": "[Sağlayıcı Adı]",
    "sameAs": "[Website URL]"
  },
  "educationalLevel": "[Seviye: Beginner/Intermediate/Advanced]",
  "audience": {
    "@type": "Audience",
    "audienceType": "[Hedef Kitle]"
  },
  "offers": {
    "@type": "Offer",
    "price": "[Fiyat]",
    "priceCurrency": "TRY",
    "availability": "https://schema.org/InStock"
  }
}
```

#### DanceSchool (Dans Okulu - EducationalOrganization)
```json
{
  "@context": "https://schema.org",
  "@type": "DanceSchool",
  "name": "[Okul Adı]",
  "description": "[Açıklama]",
  "url": "[Website URL]",
  "telephone": "[Telefon]",
  "email": "[Email]",
  "image": "[Görsel URL]",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "[Adres]",
    "addressLocality": "[Şehir]",
    "postalCode": "[Posta Kodu]",
    "addressCountry": "TR"
  },
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Dans Dersleri",
    "itemListElement": [
      {
        "@type": "Course",
        "name": "[Ders Adı 1]",
        "description": "[Ders Açıklaması]"
      },
      {
        "@type": "Course",
        "name": "[Ders Adı 2]",
        "description": "[Ders Açıklaması]"
      }
    ]
  }
}
```

---

### Auto-Fix Talimatları

`/HTSEO fix` komutu çalıştırıldığında:

1. Önce normal SEO analizi yap
2. Tespit edilen eksiklikleri listele
3. Kullanıcıya onay sor: "Bu düzeltmeleri uygulamak istiyor musunuz? (E/H)"
4. Onay alınırsa, sırasıyla:

#### Adım 1: Meta Tags Ekle
`<head>` bölümüne eksik meta etiketlerini ekle:
- `<meta name="robots" content="index, follow">`
- `<link rel="canonical" href="...">`
- Open Graph etiketleri
- Twitter Card etiketleri

#### Adım 2: Favicon Ekle
```html
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
```

#### Adım 3: Schema.org Ekle
Sayfa türüne uygun JSON-LD script'i ekle (</head> öncesi)

#### Adım 4: robots.txt Oluştur
Proje kökünde robots.txt dosyası oluştur

#### Adım 5: sitemap.xml Oluştur
Proje kökünde sitemap.xml dosyası oluştur

#### Adım 6: Rapor
Yapılan tüm değişiklikleri listele:
```
✅ UYGULANAN DEĞİŞİKLİKLER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ✅ Meta robots eklendi
2. ✅ Canonical URL eklendi
3. ✅ Open Graph etiketleri eklendi
4. ✅ Twitter Card eklendi
5. ✅ Schema.org JSON-LD eklendi
6. ✅ robots.txt oluşturuldu
7. ✅ sitemap.xml oluşturuldu

📊 Yeni SEO Skoru: 85/100 (+27 puan)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Rakip Analizi Modu

`/HTSEO compare [url]` komutu çalıştırıldığında:

1. WebFetch ile rakip URL'yi çek
2. Aynı SEO kriterlerini uygula
3. Karşılaştırmalı tablo oluştur:

```
📊 KARŞILAŞTIRMALI ANALİZ
┌─────────────────────┬──────────┬──────────┐
│ Kriter              │ Sizin    │ Rakip    │
├─────────────────────┼──────────┼──────────┤
│ Meta Tags           │ 10/20    │ 18/20    │
│ Heading Yapısı      │ 14/15    │ 12/15    │
│ İçerik              │ 10/15    │ 14/15    │
│ Görseller           │ 3/15     │ 13/15    │
│ Teknik SEO          │ 8/15     │ 15/15    │
│ Performans          │ 6/10     │ 8/10     │
│ Mobil               │ 7/10     │ 9/10     │
├─────────────────────┼──────────┼──────────┤
│ TOPLAM              │ 58/100   │ 89/100   │
└─────────────────────┴──────────┴──────────┘

💡 Rakipten Öğrenilecekler:
• Open Graph etiketleri kullanıyor
• Schema.org markup var
• Tüm görsellerde alt text mevcut
```

---

## Hızlı Referans

| Komut | Açıklama |
|-------|----------|
| `/HTSEO` | Temel SEO analizi |
| `/HTSEO [dosya]` | Belirtilen dosyayı analiz et |
| `/HTSEO fix` | Otomatik düzeltme modu |
| `/HTSEO robots` | robots.txt oluştur |
| `/HTSEO sitemap` | sitemap.xml oluştur |
| `/HTSEO meta` | Sadece meta tag analizi |
| `/HTSEO schema [type]` | Schema.org JSON-LD oluştur |
| `/HTSEO compare [url]` | Rakip karşılaştırması |
