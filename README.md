# ECOFUAV Hangar

Teknofest Savaşan İHA geliştirme ortamı için kontrol paneli. Gazebo, PX4 SITL, XRCE-DDS Agent,
ROS 2 düğümleri ve QGroundControl'ü terminal açmadan başlatır, durdurur ve yeniden başlatır.
Takımdaki herkesin aynı sürümleri kurmasını da sağlar.

Hedef sistem: **Ubuntu 22.04 + ROS 2 Humble** (Windows'ta WSL2 içinde de çalışır, aşağıya bakın).

📖 **Her ekranın, butonun ve ayarın ayrıntılı anlatımı: [Kullanım Kılavuzu](docs/KULLANIM_KILAVUZU.md)**

## Kurulum

```bash
git clone https://github.com/furkannpala/ecofuav-hangar.git ~/ecofuav-hangar
cd ~/ecofuav-hangar
./setup.sh
```

Ardından uygulama menüsünden **ECOFUAV Hangar**'ı açın ya da terminale `ecofuav-hangar` yazın.

## Güncelleme

```bash
cd ~/ecofuav-hangar
git pull
./setup.sh   # yalnızca requirements.txt değiştiyse gerekir
```

Sadece takım sürümleri değiştiyse uygulamadaki **Kurulum → Sürüm Listesini Güncelle** de aynı işi yapar.

## Geliştirmeye katkı

Yeni özellik ya da düzeltme için `main` dalına doğrudan push'lamak yerine ayrı dal açın:

```bash
git checkout -b ozellik/kisa-aciklama
# ... değişiklikler ...
git add .
git commit -m "Ne değişti, kısaca"
git push -u origin ozellik/kisa-aciklama
```

Sonra GitHub'da Pull Request açın; bir takım arkadaşı baktıktan sonra `main`'e alınır.
Uygulamayı geliştirirken terminalden çalıştırmak için: `.venv/bin/python main.py`

## Sayfalar

**Kontrol Paneli:** Her modül için Başlat / Durdur / Restart, durum ve çalışma süresi gösterilir.
Alttaki panelde her modülün canlı çıktısı ayrı sekmede görünür. Alttaki satırdan çalışan
modüle komut gönderilebilir (ör. PX4 konsoluna `commander status`).

- **Tümünü Başlat:** "Tümünü Başlat'a dahil" işaretli modülleri sırayla açar. *Hazır deseni*
  olan modülde (ör. PX4: `Ready for takeoff`) o satır görülene kadar bekler, sonra sıradakine geçer.
- **Durdur:** Modülün tüm süreç grubuna önce SIGINT gönderir, kapanmazsa SIGTERM, en son SIGKILL.
  Böylece arkada `gz sim` ya da `px4` kalmaz.
- **Artıkları Temizle:** Uygulama dışında açılıp asılı kalmış süreçleri öldürür.

**Filo:** Aynı Gazebo dünyasında birden fazla İHA uçurmak için. *Filo Düzeni* sekmesinde İHA
ekleyip kaldırın; her biri için model, başlangıç konumu ve isteğe bağlı bir *eşlik eden komut*
(ör. o araca ait offboard ya da takip düğümü) girin. *Uçuş* sekmesinde **Filoyu Başlat**:

- Agent bir kez açılır. İlk İHA Gazebo'yu başlatır, diğerleri `PX4_GZ_STANDALONE=1` ile aynı
  dünyaya katılır. Her biri hazır olunca sıradaki açılır.
- ROS 2'de her araç kendi isim alanında görünür: `/px4_1/fmu/...`, `/px4_2/fmu/...`
  (MAV_SYS_ID = örnek no + 1). QGroundControl tüm araçları otomatik bulur.
- Eşlik eden komutta `{i}`, `{ns}`, `{sysid}`, `{name}`, `{gz_model}` yer tutucuları kullanılabilir:
  `ros2 run iha_control offboard_node --ros-args -r __ns:=/{ns}`
- Laptopta 4-5 araçtan fazlası yavaşlayabilir; *headless* seçeneği Gazebo arayüzünü kapatıp hafifletir.

Filo ayarları `~/.config/ecofuav-hangar/fleet.yaml` dosyasında tutulur.

**Modüller:** Yeni modül/makro ekleme ve düzenleme. Kaydedince Kontrol Paneli'nde kart olarak
çıkar. Ayarlar `~/.config/ecofuav-hangar/modules.yaml` dosyasında tutulur. *Dışa Aktar / İçe Aktar*
ile takım arkadaşlarınızla paylaşabilirsiniz.

**Kurulum:** `install/versions.yaml` dosyasındaki takım sürümlerini, sizde yüklü olanlarla
karşılaştırır ve tek tıkla kurar/günceller. Yönetici şifresi gerektiğinde grafik pencere açılır.

## Takım sürümünü değiştirmek

1. `install/versions.yaml` içinde ilgili `version` / `required` / `match` alanlarını güncelleyin.
2. Commit + push.
3. Herkes Kurulum sayfasında **Sürüm Listesini Güncelle** → **Eksikleri Kur**.

Not: PX4 sürümü ile `px4_msgs` dalı birbirine uymalıdır (ör. `v1.15.x` ↔ `release/1.15`).

## Windows'ta (WSL2) çalıştırma

Gazebo, PX4 ve ROS 2 Windows'ta doğrudan çalışmaz, ama Windows 11'de **WSL2 + WSLg** ile
Ubuntu 22.04 içinde grafik arayüzleriyle birlikte çalışır:

```powershell
# PowerShell (yönetici)
wsl --install -d Ubuntu-22.04
```

Yeniden başlattıktan sonra Ubuntu terminalinde yukarıdaki **Kurulum** adımlarını izleyin;
uygulama penceresi Windows masaüstünde açılır.

Bilinen kısıtlar:
- Gazebo WSL2'de daha yavaş çalışır (GPU desteği sınırlı). Test için yeterli, ama
  sorun yaşarsanız `LIBGL_ALWAYS_SOFTWARE=1` ortam değişkenini deneyin.
- Pixhawk'ı USB ile WSL2'ye bağlamak için `usbipd-win` gerekir.
- Kalıcı geliştirme için gerçek Ubuntu kurulumu (dual-boot) daha sorunsuzdur.

## Proje yapısı

```
main.py                       giriş noktası
hangar/process.py       süreç grubu başlat/durdur (SIGINT→SIGTERM→SIGKILL)
hangar/runner.py        modül ↔ süreç eşleme, toplu başlatma sırası
hangar/config.py        modules.yaml okuma/yazma
hangar/installer.py     versions.yaml ve sürüm kontrolü
hangar/fleet.py         filo tanımı → çoklu PX4 SITL modülleri
hangar/ui/              arayüz sayfaları
config/default_modules.yaml   ilk açılıştaki modüller
install/versions.yaml         takım sürüm seti
install/scripts/*.sh          bileşen kurulum betikleri
```
