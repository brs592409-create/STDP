# STDP - Depotbox ve Veri Çekme Spesifikasyonu (DEPOTBOX_SPEC.md)

Bu doküman, `depotbox.org` üzerinden oyun arama, manifest ve kilit dosyalarını indirme, veri modelleri ve yerel arşiv paketlerinin (ZIP/RAR) ayrıştırılma kurallarını tanımlar.

---

## 1. Veri Kaynakları ve İletişim Protokolü

Depotbox, Steam oyunlarına ait manifest dosyalarını, depot anahtarlarını ve hazır kilit betiklerini barındıran bir veri tabanıdır.

### Temel Veri Modeli
```json
{
  "app_id": 1091500,
  "game_name": "Cyberpunk 2077",
  "thumbnail_url": "https://cdn.cloudflare.steamstatic.com/steam/apps/1091500/capsule_231x87.jpg",
  "depots": [
    {
      "depot_id": 1091501,
      "manifest_id": "8472918392817281920",
      "depot_key": "A1B2C3D4E5F60718293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90",
      "manifest_url": "https://depotbox.org/download/1091501/8472918392817281920.manifest",
      "size_bytes": 73400320000,
      "type": "base"
    }
  ],
  "lua_script_url": "https://depotbox.org/scripts/1091500.lua"
}
```

---

## 2. Arama ve Scraping İş Akışı

1. **Arama İsteği:**
   - Kullanıcı oyun adı veya `AppID` girdiğinde:
   - `GET /search?q=<query>` veya `POST /api/search` sorgusu gönderilir.
2. **Sonuçların Ayrıştırılması (`BeautifulSoup4` / `Regex`):**
   - Oyun listesi, kapak görselleri ve `AppID` bilgileri parse edilerek `AppInfo` listesine dönüştürülür.
3. **Manifest ve Kilit İndirme:**
   - Seçilen oyun için manifest dosyaları ve varsa Lua betiği asenkron iş parçacıklarıyla indirilir.
   - İndirme tamamlandığında dosyanın bozuk olmaması için boyut/hash doğrulaması yapılır.

---

## 3. Hibrit Mod: Manuel ZIP / Paket İçe Aktarma Formatı

Kullanıcı `depotbox.org` üzerinden veya başka bir kaynaktan indirdiği bir `.zip` dosyasını uygulamanın **İçe Aktar (Dropzone)** alanına sürüklediğinde `src/depotbox/extractor.py` arşivi otomatik inceler:

### Tipik Paket İçeriği Senaryoları:
1. **Senaryo A (Standart Depotbox Paketi):**
   ```
   Oyun_Paketi.zip/
   ├── 1091501_8472918392817281920.manifest   --> Steam/depotcache/
   └── 1091500.lua                           --> Steam/config/st_scripts/
   ```
2. **Senaryo B (SteamTools Hazır Paketi):**
   ```
   Oyun_Paketi.zip/
   ├── depotcache/
   │   └── 1091501_8472918392817281920.manifest
   └── st_scripts/
       └── 1091500.lua
   ```
3. **Senaryo C (Yalnızca Manifest Dosyaları):**
   - Kullanıcı doğrudan bir veya birden fazla `.manifest` dosyası bıraktığında, dosya adından (`<depotid>_<manifestid>.manifest`) depot ve manifest bilgileri regex ile çözümlenir ve `depotcache`'e aktarılır.

---

## 4. Hata Yönetimi ve Yeniden Deneme (Retry Policy)

- **Zaman Aşımı (Timeout):** Ağ isteklerinde standart zaman aşımı **15 saniye** olarak ayarlanır.
- **Yeniden Deneme:** Başarısız isteklerde 3 kez katlanarak artan gecikmeyle (Exponential Backoff: 1s, 2s, 4s) tekrar denenir.
- **Ağ Kesintisi:** Ağ bağlantısı yoksa kullanıcıya net bir uyarı verilir ve "Çevrimdışı / Manuel İçe Aktarma" sekmesine yönlendirilir.
