# STDP (Steam Tool Depotbox & Online-Fix Pipeline)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-PyQt6-green.svg)](https://riverbankcomputing.com/software/pyqt/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

**STDP**, `depotbox.org` üzerinden oyun manifestlerini tek tıkla Steam kütüphanenize işleyen ve `online-fix.me` üzerinden çok oyunculu (multiplayer) **Steam_Fix** dosyalarını otomatik olarak oyun dizinlerine kurup yedekleyen, **tamamen bağımsız (self-contained)** bir masaüstü aracıdır.

---

## ✨ Temel Özellikler

- 🌐 **Dahili DepotBox Web Tarayıcısı:** Chromium tabanlı web motoru ile `depotbox.org`'da gezinirken indirmeleri otomatik yakalama ve tek tıkla Steam'e aktarma.
- 🎮 **Online-Fix.me Steam_Fix Otomasyonu:**
  - Yüklü Steam oyunlarını tüm disklerde otomatik tespit etme.
  - İndirilen veya sürüklenen `Steam_Fix` arşivlerinin şifresini (`online-fix.me`) otomatik çözme.
  - Orijinal dosyaları (`steam_api64.dll` vb.) `.stdp_fix_backup` içine otomatik yedekleyerek fix'i kurma.
  - `OnlineFix.ini` üzerinden Nickname ve Dil ayarlarını tek ekrandan düzenleme.
  - **Tek Tıkla Geri Alma (Revert):** Dilediğiniz zaman fix'i kaldırıp oyunu orijinal haline döndürme.
- 🔌 **Yerleşik Kanca Motoru (Self-Contained):** Harici araç kurma zorunluluğu olmadan yerleşik Steam kancası (SteamTools / Lua & GreenLuma adaptörleri).
- 💾 **Çoklu Disk ve Kütüphane Desteği:** `libraryfolders.vdf` üzerinden farklı sürücülerdeki (`C:`, `D:`, `E:`) kütüphane yollarını ve boş alanları otomatik tespit etme.
- 🩺 **Otomatik Sistem Teşhisi:** Steam durumu, dosya izinleri ve kanca sağlığını kontrol eden dahili tanı ve 1-tıkla onarım aracı.
- 🎨 **Modern Koyu Tema Arayüzü:** Steam estetiğine uygun, akıcı ve duyarlı PyQt6 masaüstü deneyimi.

---

## 📚 Dokümantasyon

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Sistem mimarisi, veri akışları ve bileşen sorumlulukları.
- [DESIGN.md](docs/DESIGN.md) - UI/UX tasarım sistemi, renk paleti ve bileşen standartları.
- [HOOK_MECHANISMS.md](docs/HOOK_MECHANISMS.md) - Steam içerik teslimi, manifest, ACF ve kanca mekanizmaları.
- [DEPOTBOX_SPEC.md](docs/DEPOTBOX_SPEC.md) - Veri çekme modelleri ve arşiv formatları.
- [AGENT_GUIDELINES.md](docs/AGENT_GUIDELINES.md) - AI Agent kodlama standartları ve kuralları.

---

## 🚀 Hızlı Başlangıç (100% Taşınabilir / Portable)

Bu klasör **tamamen taşınabilir (Portable)** olarak yapılandırılmıştır:
- Sistemde Python kurulu olması gerekmez (`python_runtime` gömülüdür).
- Otomatik Yönetici İzni (UAC) desteği ile `C:\Program Files (x86)\Steam` izin hatalarını önler.
- Çoklu disk ve sürücü tespiti (`C:`, `D:`, `E:` vb.) tamamen dinamiktir.

### İlk Kurulum (Yeni / Formatlı Bilgisayarlar İçin):
Format atılmış veya yeni bir bilgisayarda ilk kez çalıştırıyorsanız:
1. **`BAGIMLILIKLARI_KUR.bat`** dosyasına çift tıklayın. (Visual C++, 7-Zip ve kütüphaneleri otomatik tamamlar).

### Normal Çalıştırma:
1. **`BASLAT.bat`** dosyasına çift tıklayın!



