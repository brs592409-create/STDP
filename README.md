# STDP (Steam Tool Depotbox & Online-Fix Pipeline)

[![Release](https://img.shields.io/github/v/release/brs592409-create/STDP?label=Portable%20Release&color=orange)](https://github.com/brs592409-create/STDP/releases/latest)
[![Download ZIP](https://img.shields.io/badge/Download-STDP--Portable.zip-blueviolet?style=for-the-badge&logo=windows)](https://github.com/brs592409-create/STDP/releases/download/v1.1.0/STDP-Portable-v1.1.0.zip)

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

## 🚀 Hızlı Başlangıç (100% Portable)

Bu klasör **tamamen taşınabilir (Portable)** olarak yapılandırılmıştır:
- Sistemde Python kurulu olması gerekmez.
- Hiçbir derleme (Build / .exe) yapılmamıştır, tüm kaynak kodlar açıktır.
- Klasör içindeki gömülü `python_runtime` motoru sayesinde herhangi bir bilgisayarda (veya USB bellekte) doğrudan çalışır.

### Çalıştırma:
1. Klasörü istediğiniz yere kopyalayın.
2. **`BASLAT.bat`** dosyasına çift tıklayın!


