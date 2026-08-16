# STDP - Kullanıcı Arayüzü ve Tasarım Kılavuzu (DESIGN.md)

Bu doküman, **STDP (Steam Tool Depotbox Pipeline)** masaüstü uygulamasının PyQt6 görsel tasarım sistemini, renk paletini, tipografisini, bileşen hiyerarşisini ve kullanıcı deneyimi (UX) standartlarını tanımlar.

---

## 1. Tasarım Felsefesi ve Görsel Kimlik

- **Tema:** Modern Steam Koyu Teması (Deep Dark Steam + Cyan Accent).
- **Temel Amaç:** Sıfır görsel karmaşa, tek tıkla hedef tamamlama, canlı süreç geri bildirimi.
- **Tasarım Kuralları:**
  - Asla sönük, gri-içinde-gri veya aşırı karmaşık menüler kullanılmayacak.
  - Tüm interaktif öğelerin (butonlar, kartlar, sekmeler) net hover ve active durumları olacak.
  - Uzun süren işlemlerde (indirme, arşiv çıkarma, Steam kapatma) kullanıcıya anlık durum ve ilerleme çubuğu gösterilecek.

---

## 2. Renk Paleti (Color Tokens)

| Token Adı | Hex Kodu | Kullanım Alanı |
| :--- | :--- | :--- |
| **`--bg-primary`** | `#101822` | Uygulama ana arka planı (En koyu katman) |
| **`--bg-surface`** | `#172332` | Kartlar, paneller ve sekme arka planları |
| **`--bg-elevated`** | `#1e3048` | Hover durumundaki kartlar, girdi kutuları |
| **`--border-subtle`** | `#2a425f` | Kart kenarlıkları, ayraç çizgileri |
| **`--accent-primary`** | `#66c0f4` | Steam Mavisi (Ana butonlar, aktif sekmeler, bağlantılar) |
| **`--accent-hover`** | `#80d0ff` | Vurgu butonu hover durumu |
| **`--accent-gradient`** | `qlineargradient(#417a9b, #1b384c)` | Başlık ve vurgulu kart gradyanları |
| **`--text-primary`** | `#f3f6f9` | Ana başlıklar, buton metinleri |
| **`--text-secondary`** | `#93a7ba` | Alt başlıklar, açıklamalar, metadata |
| **`--text-muted`** | `#627588` | Pasif metinler, ipuçları |
| **`--status-success`** | `#57cb65` | Başarılı işlemler, yeşil sağlık durumu |
| **`--status-warning`** | `#f9a825` | Uyarılar, eksik anahtar bildirimleri |
| **`--status-error`** | `#ef5350` | Hatalar, izin/kilitlenme problemleri |

---

## 3. Tipografi Standartları

- **Font Ailesi:** `Segoe UI`, `Inter`, `system-ui`, `sans-serif`
- **Hiyerarşi:**
  - **H1 (Sayfa Başlığı):** 20px, Bold, `#f3f6f9`
  - **H2 (Kart / Bölüm Başlığı):** 15px, Semi-Bold, `#f3f6f9`
  - **Body (Standart Metin):** 13px, Regular, `#93a7ba`
  - **Small / Tag (Etiket & Rozetler):** 11px, Medium, `#66c0f4`
  - **Code / Log (Konsol Metni):** 12px, Monospace (`Consolas`, `Cascadia Code`), `#e0e0e0`

---

## 4. Ana Ekran ve Sekme Düzeni (App Layout)

Pencere minimum **960x640px** çözünürlükte, sabit sol gezinme çubuğu (Sidebar) ve sağ ana içerik alanından oluşur:

```
+-----------------------------------------------------------------------------------+
|  [STDP LOGO]  Steam Tool Depotbox Pipeline                     [-][口][X]         |
+-----------------------------------------------------------------------------------+
|  [NAV SIDEBAR]   |  [ANA İÇERİK ALANI]                                            |
|                  |                                                                |
|  [🔍 Arama]      |  Arama Çubuğu: [ Cyberpunk 2077                        ] [ARA] |
|  [📦 İçe Aktar]  |                                                                |
|  [🩺 Teşhis]     |  +----------------------------------------------------------+  |
|  [⚙️ Ayarlar]    |  | [Oyun Görseli]  Cyberpunk 2077 (AppID: 1091500)          |  |
|                  |  |                 Depot Sayısı: 12 | Boyut: ~70 GB         |  |
|                  |  |                 [Kütüphane Seç: D:\Steam (420GB Boş) v]  |  |
|                  |  |                 [ ⚡ 1-TIKLA STEAM'E AKTAR ]              |  |
|                  |  +----------------------------------------------------------+  |
|                  |                                                                |
| ---------------- | -------------------------------------------------------------- |
|  Steam: [BAĞLI]  |  [CANLI LOG AKIŞI / DURUM BİLGİSİ]                             |
|  Hook:  [AKTİF]  |  [INFO] Manifest 1091501 depotcache klasörüne yazıldı.         |
+-----------------------------------------------------------------------------------+
```

---

## 5. Kritik Bileşen Tasarımları (Components)

### A. Sürükle-Bırak Yükleme Alanı (`DropZoneWidget`)
- Kesikli kenarlık (`border: 2px dashed #2a425f`), yuvarlatılmış köşeler (`border-radius: 12px`).
- Dosya üzerine sürüklendiğinde (`dragEnterEvent`): Kenarlık rengi parlayan maviye (`#66c0f4`) döner, arka plan hafif aydınlanır.
- Desteklenen formatlar: `.zip`, `.rar`, `.manifest`, `.lua`.

### B. Disk Seçici & Boş Alan Çubuğu (`DiskSelectorWidget`)
- Kullanıcının `libraryfolders.vdf` içindeki tüm sürücülerini listeler.
- Her sürücünün yanında yatay doluluk çubuğu (Yeşil/Sarı/Kırmızı) ve `"D:\SteamLibrary (380 GB Boş)"` formatında net gösterim.

### C. Sistem Sağlık & Teşhis Kartı (`HealthCardWidget`)
- 5 Temel Kontrol Noktası:
  1. **Steam Kurulum Yolu:** `C:\Program Files (x86)\Steam` [Doğrulandı ✓]
  2. **Yerleşik Kanca Motoru:** [Kurulu / Aktif ✓]
  3. **Yönetici İzinleri:** [Tam Yetkili ✓]
  4. **Steam Süreci:** [Çalışıyor - PID: 14208]
  5. **Depotcache Erişimi:** [Yazılabilir ✓]
- Eksik veya hatalı bir durum varsa yanında kırmızı ünlem ve sağında **`[Otomatik Onar / Kur]`** aksiyon butonu.

### D. Canlı Konsol / Log Görüntüleyici (`LogConsoleWidget`)
- Monospace font, koyu zemin (`#0d131a`).
- Seviyeye göre renklendirme:
  - `[INFO]` -> Beyaz / Gri (`#c7d5e0`)
  - `[SUCCESS]` -> Canlı Yeşil (`#57cb65`)
  - `[WARN]` -> Sarı (`#f9a825`)
  - `[ERROR]` -> Kırmızı (`#ef5350`)
- Temizle, Dışa Aktar ve Otomatik Kaydır (Auto-scroll) butonları.

---

## 6. PyQt6 QSS (Stil Sayfası) Şablonu

```css
QMainWindow {
    background-color: #101822;
}

QTabWidget::pane {
    border: 1px solid #1e3048;
    background-color: #172332;
    border-radius: 8px;
}

QPushButton.primary-btn {
    background-color: #66c0f4;
    color: #101822;
    font-weight: bold;
    font-size: 13px;
    border-radius: 6px;
    padding: 8px 16px;
    border: none;
}

QPushButton.primary-btn:hover {
    background-color: #80d0ff;
}

QPushButton.primary-btn:pressed {
    background-color: #4196c7;
}

QLineEdit {
    background-color: #1e3048;
    border: 1px solid #2a425f;
    border-radius: 6px;
    color: #f3f6f9;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border: 1px solid #66c0f4;
}

QProgressBar {
    background-color: #1e3048;
    border-radius: 4px;
    text-align: center;
    color: #f3f6f9;
    font-size: 11px;
}

QProgressBar::chunk {
    background-color: #66c0f4;
    border-radius: 4px;
}
```
