# STDP - 6 Katmanlı Geliştirme Yol Haritası ve Faz Kontrol Listesi (ROADMAP_AND_PHASES.md)

Bu doküman, projenin adım adım geliştirilme sürecini ve her fazın kontrol listesini içerir.

---

## 📋 Faz 1: Mimari, Dokümantasyon & Standartların Kurulması (TAMAMLANDI)
- [x] `docs/ARCHITECTURE.md` oluşturuldu.
- [x] `docs/DESIGN.md` (PyQt6 UI/UX Kılavuzu) oluşturuldu.
- [x] `docs/HOOK_MECHANISMS.md` oluşturuldu.
- [x] `docs/DEPOTBOX_SPEC.md` oluşturuldu.
- [x] `docs/AGENT_GUIDELINES.md` oluşturuldu.
- [x] `docs/ROADMAP_AND_PHASES.md` oluşturuldu.
- [x] `README.md` oluşturuldu.

---

## 📋 Faz 2: Çekirdek Veri & Steam Entegrasyon Katmanı (TAMAMLANDI)
- [x] `requirements.txt` dosyasının hazırlanması (`PyQt6`, `requests`, `beautifulsoup4`, `psutil`, `vdf`, `pydantic`).
- [x] `src/core/models.py`: `AppInfo`, `DepotInfo`, `ManifestInfo`, `GamePackage` sınıfları.
- [x] `src/core/config.py`: Ayarların JSON olarak kaydedilmesi ve yüklenmesi.
- [x] `src/core/logger.py`: Konsol ve dosyaya çift yönlü loglama altyapısı.
- [x] `src/steam/detector.py`: Windows Registry (`HKCU\Software\Valve\Steam`) ve `libraryfolders.vdf` ayrıştırma (Çoklu disk tespiti).
- [x] `src/steam/acf_builder.py`: Steam VDF formatında `appmanifest_<appid>.acf` üretimi.
- [x] `src/steam/depotcache_manager.py`: Manifest dosyalarının `Steam/depotcache/` dizinine yerleştirilmesi.
- [x] `src/steam/process_manager.py`: Steam sürecini tespit etme, kapatma (`-shutdown`), yeniden başlatma ve URI (`steam://`) tetikleme.

---

## 📋 Faz 3: Modüler Kilit Açıcı (Hook / Unlocker) Katmanı (TAMAMLANDI)
- [x] `src/unlockers/base.py`: `UnlockerAdapter` soyut sınıfı.
- [x] `src/unlockers/steamtools_adapter.py`: Yerleşik SteamTools / Lua kanca yöneticisi (`st_scripts/<appid>.lua` üretimi ve Steam entegrasyonu).
- [x] `src/unlockers/greenluma_adapter.py`: GreenLuma `AppList` akıllı birleştirme (`0.txt`, `1.txt` indeksleyici) ve yedekleme sistemi.

---

## 📋 Faz 4: Depotbox & Hibrit İçe Aktarma Katmanı (TAMAMLANDI)
- [x] `src/depotbox/client.py`: `depotbox.org` arama ve veri çekme motoru.
- [x] `src/depotbox/downloader.py`: Asenkron ve iş parçacıklı manifest indirici.
- [x] `src/depotbox/extractor.py`: Sürükle-bırak ile gelen `.zip`, `.rar`, `.manifest`, `.lua` dosyalarını ayrıştıran arşiv motoru.

---

## 📋 Faz 5: Modern PyQt6 Masaüstü Arayüzü (UI/UX) (TAMAMLANDI)
- [x] `src/ui/theme.py`: `docs/DESIGN.md` QSS renk ve stil motoru.
- [x] `src/ui/components/dropzone.py`: Animasyonlu, sürükle-bırak dosya yükleyici bileşeni.
- [x] `src/ui/components/disk_selector.py`: Çoklu disk ve boş alan göstergesi.
- [x] `src/ui/components/game_card.py`: Oyun kapağı, depot listesi ve "1-Tıkla Aktar" kartı.
- [x] `src/ui/components/log_console.py`: Canlı renkli konsol izleyici.
- [x] `src/ui/search_view.py`: Canlı arama ve indirme sekmesi.
- [x] `src/ui/import_view.py`: Manuel arşiv aktarım sekmesi.
- [x] `src/ui/health_view.py`: Sistem teşhis, izin ve tek tıkla kanca kurulum sekmesi.
- [x] `src/ui/settings_view.py`: Dizinler, kütüphaneler ve aktif kanca ayarları.
- [x] `src/ui/main_window.py`: Ana pencere montajı.

---

## 📋 Faz 6: Testler, Doğrulama & Giriş Noktası (TAMAMLANDI)
- [x] `tests/test_vdf_parser.py`: VDF ve ACF üretim testleri.
- [x] `tests/test_extractor.py`: ZIP arşiv ayrıştırma testleri.
- [x] `tests/test_applist_merger.py`: AppList çakışma önleme testleri.
- [x] `main.py`: Uygulama başlatıcı ve bağımlılık kontrolü.
