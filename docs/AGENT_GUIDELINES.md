# STDP - AI Agent Geliştirme Yönergeleri (AGENT_GUIDELINES.md)

Bu doküman, **STDP** projesinde kod yazacak, değişiklik yapacak veya modül ekleyecek tüm **AI Agent'lar (ve yazılımcılar)** için katı davranış, kodlama ve mimari kurallarını içerir.

---

## 1. Temel Davranış Kuralları

1. **Önce Dokümantasyonu Oku:**
   - Herhangi bir kod yazmadan önce mutlaka `docs/ARCHITECTURE.md`, `docs/DESIGN.md` ve `docs/HOOK_MECHANISMS.md` dosyalarını inceleyin.
2. **Kendi Başına Harici Bağımlılık Yaratma:**
   - Uygulama **tamamen bağımsız (self-contained)** olmalıdır. Kullanıcıdan harici üçüncü parti yazılımlar kurmasını istemeyin; gerekli tüm motor ve script mantığı `src/` ve `bin/` altında çözülmelidir.
3. **Mevcut Dosyaları Asla Ezme (Preserve Existing Files):**
   - Steam dizinindeki mevcut `appmanifest`, `libraryfolders.vdf` veya `AppList` dosyalarını değiştirirken asla tüm dizini silmeyin. Daima birleştirme (merge) veya yedek alma (backup) mantığı uygulayın.
4. **Platform Uyumluluğu:**
   - Kod Windows işletim sisteminde çalışacak şekilde yazılmalıdır (Steam Registry, `winreg`, `psutil`, Windows dosya yolları). Ancak dosya yolu manipülasyonlarında her zaman `pathlib.Path` kullanılmalıdır.

---

## 2. Kodlama ve Mimari Standartları

- **Python Sürümü:** Python 3.11+
- **Tip Belirtimleri (Type Hints):** Tüm fonksiyon parametreleri ve dönüş değerleri katı tip ipuçları (`typing`, `Path`, `Optional`, `List`, `Dict`) içermelidir.
- **Hata Yönetimi (Error Handling):**
  - Dosya I/O ve ağ işlemlerinde genel `except Exception:` yerine özel istisnalar (`FileNotFoundError`, `PermissionError`, `requests.RequestException`) yakalanmalıdır.
  - Hatalar sessizce geçiştirilmemeli, hem `logger` üzerinden loglanmalı hem de UI katmanına sinyal gönderilmelidir.
- **Asenkron / İş Parçacığı (Threading):**
  - PyQt6 arayüzünü kilitlememek için tüm uzun süren I/O, indirme, arşiv açma ve Steam süreç işlemleri `QThread` veya `asyncio` worker sınıfları üzerinden yürütülmelidir.

---

## 3. Yeni Bir Kilit Açıcı (Unlocker) Adaptörü Ekleme Kuralı

Yeni bir unlocker adaptörü ekleneceğinde:
1. `src/unlockers/base.py` içerisindeki `UnlockerAdapter` sınıfından miras alınmalıdır.
2. `is_installed()`, `install_hook()`, `uninstall_hook()`, `inject_game()`, `remove_game()` metodları eksiksiz uygulanmalıdır.
3. `src/core/models.py` ve `src/ui/settings_view.py` üzerinde yeni adaptör seçenek olarak tanımlanmalıdır.

---

## 4. Test Standartları

- Yapılan her mantıksal değişiklik için `tests/` klasörüne ilgili birim testi eklenmelidir.
- `tests/test_vdf_parser.py`: VDF formatının geçerli üretildiğini doğrulamalıdır.
- `tests/test_extractor.py`: ZIP arşivlerinin doğru ayrıştırıldığını doğrulamalıdır.
- `pytest` çalıştırıldığında tüm testler yeşil (Passed) olmalıdır.
