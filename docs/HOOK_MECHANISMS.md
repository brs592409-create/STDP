# STDP - Steam Kanca (Hook) ve Dosya Mekanizmaları (HOOK_MECHANISMS.md)

Bu doküman, Steam istemcisinin içerik teslim sistemi, manifest dosyalarının doğrulanması, kütüphanede olmayan oyunların kilitlerinin açılması ve yerleşik kanca (hook) motorunun teknik çalışma prensiplerini açıklar.

---

## 1. Steam İçerik Teslimatının (Content Delivery) Temel Mantığı

Steam bir oyunu indirirken ve çalıştırırken şu 4 temel bileşene bakar:

```
+--------------------------------------------------------------------------------+
|  1. Lisans / Sahiplik Kontrolü  -->  SteamTools Lua Kancası / GreenLuma        |
|  2. Depot Manifest Dosyası      -->  Steam/depotcache/<depotid>_<manifestid>   |
|  3. Şifre Çözme Anahtarı        -->  Depot Keys (config.vdf / Lua script)     |
|  4. Oyun Durum & Konfigürasyonu -->  Steam/steamapps/appmanifest_<appid>.acf   |
+--------------------------------------------------------------------------------+
```

---

## 2. Manifest Dosyaları ve `depotcache/`

### A. Manifest Nedir?
Steam'de her oyun bir veya birden fazla **Depot** (Depo) içerir. Örneğin:
- Depot 1: Oyunun ana çalıştırılabilir dosyaları (Base Game x64)
- Depot 2: İngilizce seslendirme ve altyazılar
- Depot 3: Türkçe dil desteği
- Depot 4: DLC veya Bonus İçerik

Her depot'un belirli bir versiyonuna ait dosya listesi, SHA-1 parçaları (chunks) ve dizin yapısı **Manifest** (`.manifest`) dosyasında saklanır.

### B. Dosya Konumu ve Adlandırma Kuralı
Manifest dosyaları Steam ana dizini altındaki `depotcache/` klasörüne şu formatta yerleştirilmelidir:
```
<SteamDizini>/depotcache/<DepotID>_<ManifestID>.manifest
```
*Örnek:* `Steam/depotcache/1091501_8472918392817281920.manifest`

---

## 3. `appmanifest_<appid>.acf` Dosyası Formatı

Steam, bir oyunun yüklü olup olmadığını, hangi kütüphanede bulunduğunu ve hangi depot versiyonlarını kullandığını `steamapps/` altındaki `.acf` (Valve KeyValues VDF) dosyalarından okur.

### Örnek Geçerli `appmanifest_<appid>.acf`:
```vdf
"AppState"
{
	"appid"		"1091500"
	"Universe"		"1"
	"LauncherPath"		"C:\\Program Files (x86)\\Steam\\steam.exe"
	"name"		"Cyberpunk 2077"
	"StateFlags"		"4"
	"installdir"		"Cyberpunk 2077"
	"LastUpdated"		"1700000000"
	"UpdateResult"		"0"
	"BytesToDownload"		"73400320000"
	"BytesDownloaded"		"73400320000"
	"AutoUpdateBehavior"		"0"
	"AllowOtherDownloadsWhileRunning"		"0"
	"ScheduledAutoUpdate"		"0"
	"InstalledDepots"
	{
		"1091501"
		{
			"manifest"		"8472918392817281920"
			"size"		"73400320000"
		}
	}
	"UserConfig"
	{
		"language"		"english"
	}
}
```

- **`StateFlags`:**
  - `4`: Oyun tamamen yüklü veya indirilmeye hazır (Fully Installed / Ready).
  - `1026`: İndirme duraklatıldı veya güncelleme bekliyor.
  - `0`: Yüklü değil.

---

## 4. Yerleşik Kanca (Embedded Hook / Lua) Motoru Nasıl Çalışır?

### A. SteamTools / Lua Kancası (Tercih Edilen Yerleşik Motor)
SteamTools kancası, Steam'in yerel dinamik kütüphanelerine (örneğin `steamclient.dll` veya Chromium Embedded Framework CEF modüllerine) bir proxy/loader DLL yerleştirerek çalışır.

1. **Entegrasyon:**
   - Loader dosyaları Steam'in ana dizinine yerleştirilir.
   - `Steam/config/st_scripts/` klasörü oluşturulur.
2. **Lua Betiği Üretimi:**
   - Aracımız, eklenen her oyun için bir `<appid>.lua` dosyası üretir ve bu klasöre koyar:
   ```lua
   -- STDP Otomatik Üretilen Kilit Betiği
   addappid(1091500, 1, "Cyberpunk 2077")
   addappid(1091501, 1, "Cyberpunk 2077 Content")
   setdepotkey(1091501, "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF")
   ```
3. **Steam Başlatıldığında:**
   - Steam açılırken bu Lua dosyalarını okur, yerel Steam API'sinde bu AppID'lerin "satın alınmış" olduğunu bildirir ve depot anahtarını Steam'in indirme yöneticisine iletir.
   - Steam istemcisi resmi CDN sunucularından doğrudan indirmeyi başlatır.

---

## 5. GreenLuma (AppList) Alternatifi

GreenLuma kullanılmak istendiğinde:
- `Steam/AppList/` klasörüne `0.txt`, `1.txt`, `2.txt` ... formatında metin dosyaları yazılır.
- Her `.txt` dosyası tek bir satırda sadece `AppID` veya `DepotID` içerir.
- **Akıllı Birleştirme (Smart Merge):** Aracımız mevcut `AppList` klasöründeki en son index numarasını tespit eder (örn. `14.txt`) ve yeni oyunun ID'lerini `15.txt`, `16.txt` olarak ekler; eski oyunları asla ezmez.
