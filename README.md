# 🎯 Sistem Absensi Face Recognition - Raspberry Pi

Sistem absensi otomatis menggunakan teknologi face recognition yang berjalan pada Raspberry Pi dengan edge computing. Sistem ini mampu mengenali wajah secara real-time dan mencatat kehadiran (masuk/pulang) dengan antarmuka touchscreen yang user-friendly.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![Face Recognition](https://img.shields.io/badge/Face_Recognition-1.3+-red.svg)
![Platform](https://img.shields.io/badge/Platform-Raspberry_Pi-c51a4a.svg)

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Hardware Requirements](#-hardware-requirements)
- [Software Requirements](#-software-requirements)
- [Instalasi](#-instalasi)
- [Struktur Proyek](#-struktur-proyek)
- [Cara Penggunaan](#-cara-penggunaan)
- [Konfigurasi](#-konfigurasi)
- [Database Schema](#-database-schema)
- [Troubleshooting](#-troubleshooting)
- [Kontributor](#-kontributor)

## ✨ Fitur Utama

### 🔐 Face Recognition
- **Edge Computing**: Semua proses recognition dilakukan di Raspberry Pi tanpa koneksi cloud
- **Real-time Detection**: Deteksi wajah dengan HOG model untuk performa optimal
- **High Accuracy**: Menggunakan face_recognition library dengan tolerance 0.45
- **Multi-threading**: Camera capture dan processing berjalan di thread terpisah untuk performa maksimal

### 📊 Sistem Absensi
- **Dual Mode**: Absensi Masuk dan Pulang dengan button terpisah
- **Status Tracking**: 
  - Masuk: Tepat waktu (≤08:15) atau Terlambat (>08:15)
  - Pulang: Normal (≥17:00) atau Pulang sebelum waktunya (<17:00)
- **Duplicate Prevention**: Mencegah absensi ganda pada hari yang sama
- **Persistent Storage**: Database SQLite untuk menyimpan riwayat absensi

### 🎨 User Interface
- **Fullscreen Display**: Optimized untuk layar 1024x600
- **Touch Support**: Touchscreen-friendly buttons
- **Visual Feedback**: Pop-up overlay untuk konfirmasi absensi
- **Sleep Mode**: Otomatis mematikan display jika tidak ada wajah terdeteksi

### 🔊 Audio Feedback
- **Text-to-Speech**: Konfirmasi suara dalam Bahasa Indonesia
- **Cached TTS**: File audio di-cache untuk response yang lebih cepat
- **Non-blocking Playback**: Audio dimainkan tanpa menghambat proses recognition

### ⚡ Optimasi Performa
- **Frame Skipping**: Recognition setiap 6 frame untuk efisiensi
- **Resolution Scaling**: Frame di-downscale ke 25% untuk processing
- **Thread-safe Operations**: Lock mechanism untuk akses frame yang aman
- **Async Database**: Database writes dilakukan secara asynchronous

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI (Edge Device)                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌─────────────────┐                    │
│  │  PiCamera2   │───▶│  Camera Thread  │                    │
│  │  (RGB888)    │    │  (640x480)      │                    │
│  └──────────────┘    └────────┬────────┘                    │
│                               │                              │
│                               ▼                              │
│                      ┌─────────────────┐                     │
│                      │  Frame Buffer   │                     │
│                      │  (Thread-safe)  │                     │
│                      └────────┬────────┘                     │
│                               │                              │
│        ┌──────────────────────┼──────────────────────┐      │
│        ▼                      ▼                       ▼      │
│  ┌──────────┐          ┌───────────┐          ┌──────────┐ │
│  │ Display  │          │Face Recog │          │   UI     │ │
│  │ (1024x   │          │ (HOG)     │          │ Buttons  │ │
│  │  600)    │          │ (160x120) │          │          │ │
│  └──────────┘          └─────┬─────┘          └────┬─────┘ │
│                              │                      │        │
│                              ▼                      ▼        │
│                      ┌─────────────────────────────────┐    │
│                      │    Attendance Logic             │    │
│                      │  - Duplicate Check              │    │
│                      │  - Time Validation              │    │
│                      │  - Status Assignment            │    │
│                      └──────────┬──────────────────────┘    │
│                                 │                            │
│              ┌──────────────────┼──────────────────┐        │
│              ▼                  ▼                   ▼        │
│        ┌──────────┐      ┌──────────┐       ┌──────────┐   │
│        │ SQLite   │      │   TTS    │       │  Popup   │   │
│        │   DB     │      │ (gTTS)   │       │ Overlay  │   │
│        └──────────┘      └──────────┘       └──────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 💻 Hardware Requirements

### Minimum Requirements
- **Raspberry Pi 4** (4GB RAM recommended)
- **PiCamera Module** v2 atau HQ Camera
- **Display** 7" Touchscreen (1024x600) atau monitor eksternal
- **SD Card** 16GB minimum (Class 10)
- **Power Supply** 5V 3A USB-C

### Optional
- **Speaker/Audio Output** untuk TTS feedback
- **Cooling Fan/Heatsink** untuk operasi 24/7
- **Case** dengan mounting untuk kamera

## 📦 Software Requirements

### Operating System
- Raspberry Pi OS (64-bit recommended)
- Kernel 5.15+

### Python Version
- Python 3.8 atau lebih tinggi

### Dependencies
```
opencv-python>=4.5.0
face-recognition>=1.3.0
numpy>=1.21.0
picamera2>=0.3.12
gTTS>=2.3.0
pillow>=9.0.0
```

### System Packages
```bash
libatlas-base-dev
libhdf5-dev
libjasper-dev
libqtgui4
libqt4-test
libcamera-dev
mpg123
```

## 🚀 Instalasi

### 1. Update Sistem
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install System Dependencies
```bash
sudo apt install -y \
    python3-pip \
    python3-opencv \
    libatlas-base-dev \
    libhdf5-dev \
    libjasper-dev \
    libqtgui4 \
    libqt4-test \
    libcamera-dev \
    python3-picamera2 \
    mpg123
```

### 3. Install Python Packages
```bash
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

Jika tidak ada file `requirements.txt`, install manual:
```bash
pip3 install opencv-python face-recognition numpy picamera2 gTTS pillow
```

### 4. Clone/Download Project
```bash
git clone <repository-url>
cd absensi-face-recognition
```

Atau jika menggunakan file upload:
```bash
mkdir -p /home/telkom/absensi
cd /home/telkom/absensi
# Copy semua file ke direktori ini
```

### 5. Setup Permissions
```bash
# Pastikan user memiliki akses ke kamera
sudo usermod -a -G video $USER

# Set permissions untuk directory
chmod +x *.py
```

### 6. Konfigurasi Path
Edit path di file `absensi.py` sesuai dengan lokasi instalasi Anda:
```python
DB_PATH = "/home/telkom/absensi/data.db"
ENCODING_FILE = "/home/telkom/absensi/encodings.pkl"
USERS_FILE = "/home/telkom/absensi/users.json"
```

## 📁 Struktur Proyek

```
absensi-face-recognition/
│
├── absensi.py              # Main program - sistem absensi
├── daftar.py               # Program pendaftaran wajah baru
├── train.py                # Training face encodings
│
├── data.db                 # SQLite database (auto-generated)
├── encodings.pkl           # Trained face encodings
├── users.json              # Data user (nama, instansi, status)
├── credentials.json        # Google service account (optional)
│
├── dataset/                # Folder foto training
│   ├── RAKA/              # Foto-foto RAKA
│   │   ├── RAKA_20240115_100523.jpg
│   │   └── ...
│   ├── IRA/               # Foto-foto IRA
│   └── .../               # dst untuk setiap user
│
├── /tmp/tts_cache_absen/  # Cache file TTS (auto-generated)
│   ├── tts_raka_masuk.mp3
│   ├── tts_raka_pulang.mp3
│   └── ...
│
└── README.md              # Dokumentasi ini
```

## 📖 Cara Penggunaan

### 1️⃣ Pendaftaran User Baru

Jalankan program pendaftaran untuk mengambil foto wajah:

```bash
python3 daftar.py
```

**Langkah-langkah:**
1. Masukkan nama user (sesuai dengan yang ada di `users.json`)
2. Tekan **SPACE** untuk mengambil foto
3. Ambil minimal **10-15 foto** dari berbagai sudut dan ekspresi
4. Tekan **Q** untuk selesai

**Tips untuk foto berkualitas:**
- Pastikan pencahayaan cukup
- Ambil dari berbagai sudut (depan, kiri, kanan, atas, bawah)
- Gunakan berbagai ekspresi wajah
- Hindari background yang terlalu ramai
- Pastikan wajah terlihat jelas tanpa halangan

### 2️⃣ Training Model

Setelah mengambil foto, jalankan training:

```bash
python3 train.py
```

Program akan:
- Membaca semua foto di folder `dataset/`
- Mendeteksi wajah di setiap foto
- Membuat encoding untuk setiap wajah
- Menyimpan hasil ke `encodings.pkl`

**Output:**
```
[OK] RAKA/RAKA_20240115_100523.jpg trained.
[OK] RAKA/RAKA_20240115_100524.jpg trained.
...
[DONE] Semua wajah sudah ditraining dan disimpan ke encodings.pkl ✅
```

### 3️⃣ Update users.json

Pastikan user terdaftar di `users.json`:

```json
{
    "NAMA_USER": {
        "instansi": "Nama Instansi",
        "status": "Magang/Karyawan/dll"
    }
}
```

### 4️⃣ Jalankan Sistem Absensi

```bash
python3 absensi.py
```

**Cara penggunaan:**
1. Sistem akan menampilkan preview kamera fullscreen
2. User berdiri di depan kamera
3. Klik button **MASUK** atau **PULANG**
4. Sistem akan mendeteksi wajah dan mencatat absensi
5. Pop-up konfirmasi akan muncul dengan info user
6. Audio TTS akan memberikan konfirmasi suara

**Status Absensi:**
- **Masuk Tepat Waktu**: ≤ 08:15
- **Masuk Terlambat**: > 08:15
- **Pulang Normal**: ≥ 17:00
- **Pulang Sebelum Waktunya**: < 17:00

### 5️⃣ Auto-start saat Boot (Optional)

Untuk menjalankan otomatis saat Raspberry Pi boot:

```bash
sudo nano /etc/systemd/system/absensi.service
```

Isi dengan:
```ini
[Unit]
Description=Face Recognition Attendance System
After=network.target

[Service]
Type=simple
User=telkom
WorkingDirectory=/home/telkom/absensi
ExecStart=/usr/bin/python3 /home/telkom/absensi/absensi.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable absensi.service
sudo systemctl start absensi.service
```

Check status:
```bash
sudo systemctl status absensi.service
```

## ⚙️ Konfigurasi

### Display & Performance Settings

Edit di `absensi.py`:

```python
# Display Resolution
SCREEN_W = 1024           # Lebar layar
SCREEN_H = 600            # Tinggi layar

# Camera Settings
CAM_WIDTH = 640           # Resolusi kamera
CAM_HEIGHT = 480

# Performance
PROCESS_SCALE = 0.25      # Scale untuk recognition (lebih kecil = lebih cepat)
RECOG_EVERY_N_FRAMES = 6  # Recognition setiap N frame (lebih besar = lebih cepat)
DIST_TOLERANCE = 0.45     # Threshold similarity (0.0-1.0, lebih kecil = lebih strict)
```

### Time Settings

```python
# Di function markAttendance()
# Batas waktu masuk
batas = now.replace(hour=8, minute=15, second=0)

# Batas waktu pulang
batas = now.replace(hour=17, minute=0, second=0)
```

### Sleep Mode Settings

```python
# Matikan display setelah N deteksi kosong
if NO_FACE_TIMER > 8 and not SLEEP:  # 8 x 6 frames = ~8 detik
    SLEEP = True
    set_display(False)
```

### Audio Settings

```python
TTS_LANG = "id"  # Bahasa Indonesia
# Ganti ke "en" untuk English
```

## 🗄️ Database Schema

### Table: `absensi`

| Column | Type    | Description                    |
|--------|---------|--------------------------------|
| id     | INTEGER | Primary key (auto increment)   |
| nama   | TEXT    | Nama user                      |
| date   | TEXT    | Tanggal (YYYY-MM-DD)          |
| time   | TEXT    | Waktu (HH:MM:SS)              |
| mode   | TEXT    | MASUK atau PULANG             |
| status | TEXT    | Tepat waktu/Terlambat/etc     |

### Query Contoh

```sql
-- Lihat semua absensi hari ini
SELECT * FROM absensi 
WHERE date = date('now');

-- Lihat absensi user tertentu
SELECT * FROM absensi 
WHERE nama = 'RAKA' 
ORDER BY date DESC, time DESC;

-- Statistik keterlambatan
SELECT nama, COUNT(*) as jumlah_terlambat 
FROM absensi 
WHERE status = 'Terlambat' 
GROUP BY nama;
```

### Akses Database

```bash
# Menggunakan sqlite3 CLI
sqlite3 /home/telkom/absensi/data.db

# Query di dalam sqlite3
sqlite> SELECT * FROM absensi ORDER BY id DESC LIMIT 10;
sqlite> .exit
```

## 🐛 Troubleshooting

### Problem: Kamera tidak terdeteksi

**Solusi:**
```bash
# Check camera
vcgencmd get_camera

# Enable camera di raspi-config
sudo raspi-config
# Pilih: Interface Options > Camera > Enable

# Reboot
sudo reboot
```

### Problem: Face Recognition terlalu lambat

**Solusi:**
1. Kurangi resolusi camera:
   ```python
   CAM_WIDTH = 480
   CAM_HEIGHT = 360
   ```

2. Increase frame skipping:
   ```python
   RECOG_EVERY_N_FRAMES = 10
   ```

3. Reduce process scale:
   ```python
   PROCESS_SCALE = 0.2
   ```

### Problem: Wajah tidak terdeteksi dengan akurat

**Solusi:**
1. Tambah lebih banyak foto training (20-30 foto per orang)
2. Adjust tolerance:
   ```python
   DIST_TOLERANCE = 0.50  # Lebih permisif
   ```
3. Pastikan pencahayaan baik
4. Gunakan model CNN (lebih akurat tapi lebih lambat):
   ```python
   faces = face_recognition.face_locations(rgb_small, model="cnn")
   ```

### Problem: Audio TTS tidak keluar

**Solusi:**
```bash
# Test audio
speaker-test -t wav -c 2

# Install ulang mpg123
sudo apt install --reinstall mpg123

# Test TTS manual
python3 -c "from gtts import gTTS; tts = gTTS('test', lang='id'); tts.save('test.mp3')"
mpg123 test.mp3
```

### Problem: Display warna biru/aneh

**Penjelasan:**
Picamera2 menggunakan format RGB888, sedangkan OpenCV default menggunakan BGR. Jika Anda melihat warna biru, ada beberapa opsi:

**Solusi 1** (Recommended): Konversi ke BGR untuk display
```python
# Di camera_thread_func()
bgr_frame = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
latest_frame = bgr_frame.copy()
```

**Solusi 2**: Gunakan format BGR888 di Picamera2
```python
config = picam2.create_preview_configuration(
    main={"size": (CAM_WIDTH, CAM_HEIGHT), "format": "BGR888"}
)
```

### Problem: Database locked error

**Solusi:**
```bash
# Check proses yang menggunakan database
lsof /home/telkom/absensi/data.db

# Kill proses jika stuck
kill -9 <PID>

# Atau restart service
sudo systemctl restart absensi.service
```

### Problem: Memory leak / sistem lambat setelah lama berjalan

**Solusi:**
1. Tambahkan restart otomatis di systemd:
   ```ini
   [Service]
   RuntimeMaxSec=86400  # Restart setiap 24 jam
   ```

2. Atau gunakan cron untuk restart malam hari:
   ```bash
   crontab -e
   # Tambahkan:
   0 2 * * * sudo systemctl restart absensi.service
   ```

## 🔐 Security Notes

1. **credentials.json** berisi service account key Google Cloud
   - **JANGAN** commit ke public repository
   - Tambahkan ke `.gitignore`
   - Simpan backup di tempat aman

2. **Database SQLite**
   - Default tidak ada password
   - Untuk production, pertimbangkan enkripsi database
   - Atau gunakan PostgreSQL dengan proper authentication

3. **Face Data Privacy**
   - Data wajah termasuk sensitive personal information
   - Pastikan comply dengan regulasi privasi (GDPR, UU PDP Indonesia)
   - Inform user bahwa data wajah mereka disimpan

## 📊 Performance Benchmarks

Tested pada **Raspberry Pi 4 (4GB RAM)**:

| Metric | Value |
|--------|-------|
| FPS (Display) | ~30 FPS |
| Recognition FPS | ~5 FPS (setiap 6 frame) |
| Detection Time | ~120-180ms per frame |
| Memory Usage | ~400-600 MB |
| CPU Usage | ~40-60% (single core) |
| Startup Time | ~2-3 seconds |

## 🔄 Update & Maintenance

### Update User Data
1. Edit `users.json` untuk menambah/edit user info
2. Tidak perlu restart sistem, perubahan otomatis terload

### Re-train Model
Jika menambah user baru atau mengubah foto training:
```bash
# 1. Pastikan foto sudah ada di dataset/NAMA_USER/
# 2. Jalankan training ulang
python3 train.py

# 3. Restart sistem absensi
sudo systemctl restart absensi.service
# atau tekan Ctrl+C dan jalankan ulang
```

### Backup Data
```bash
# Backup database
cp data.db data.db.backup_$(date +%Y%m%d)

# Backup encodings
cp encodings.pkl encodings.pkl.backup_$(date +%Y%m%d)

# Export database ke CSV
sqlite3 data.db -header -csv "SELECT * FROM absensi;" > absensi_export.csv
```

### Clean Old Data
```bash
# Hapus data absensi lebih dari 1 tahun
sqlite3 data.db "DELETE FROM absensi WHERE date < date('now', '-1 year');"

# Vacuum database untuk recover space
sqlite3 data.db "VACUUM;"
```

## 👥 Kontributor

Proyek ini dikembangkan untuk sistem absensi di:
- **Universitas Muhammadiyah Surabaya**
- **Universitas Pakuan Bogor**
- **Politeknik Negeri Malang**
- **Politeknik Negeri Jakarta**
- **Institut Pertanian Bogor**
- **SMK Infokom**
- **IT Planning Department**

## 📝 License

Proyek ini menggunakan libraries open-source:
- [face_recognition](https://github.com/ageitgey/face_recognition) - MIT License
- [OpenCV](https://opencv.org/) - Apache 2.0 License
- [Picamera2](https://github.com/raspberrypi/picamera2) - BSD 2-Clause License

## 🆘 Support

Jika mengalami masalah atau ada pertanyaan:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review logs: `journalctl -u absensi.service -f`
3. Create issue di repository ini (jika menggunakan Git)

## 🚀 Future Improvements

Roadmap pengembangan:
- [ ] Web dashboard untuk monitoring real-time
- [ ] Export laporan ke Excel/PDF
- [ ] Multi-camera support
- [ ] Cloud backup otomatis
- [ ] Mobile app untuk notifikasi
- [ ] Anti-spoofing (liveness detection)
- [ ] Integration dengan sistem HR/payroll

---

**Built with ❤️ for Edge Computing on Raspberry Pi**
