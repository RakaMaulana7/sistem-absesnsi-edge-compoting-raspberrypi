from picamera2 import Picamera2
import cv2
import os
from datetime import datetime
import time

def create_folder(name):
    """Membuat folder 'dataset' dan sub-folder untuk setiap nama."""
    dataset_folder = "dataset"
    if not os.path.exists(dataset_folder):
        os.makedirs(dataset_folder)

    person_folder = os.path.join(dataset_folder, name)
    if not os.path.exists(person_folder):
        os.makedirs(person_folder)

    return person_folder

def capture_photos():
    """
    Menggunakan format RGB888 dari Picamera2 dan tidak melakukan konversi 
    (TIDAK ADA cv2.cvtColor) untuk tampilan atau penyimpanan.
    """
    name = input("Masukkan nama yang daftar: ").strip()
    if not name:
        print("❌ Nama tidak boleh kosong!")
        return

    folder = create_folder(name)

    picam2 = Picamera2()

    # --- KONFIGURASI KAMERA MENGGUNAKAN RGB888 ---
    # STREAM UNTUK PREVIEW (ringan)
    preview_config = picam2.create_preview_configuration(
        main={"size": (960, 540), "format": "RGB888"} # <-- DIPAKSA RGB888
    )

    # STREAM FULL RES UNTUK CAPTURE FOTO
    capture_config = picam2.create_still_configuration(
        main={"size": (3280, 2464), "format": "RGB888"} # <-- DIPAKSA RGB888
    )

    picam2.configure(preview_config)
    picam2.start()
    time.sleep(1.5)

    print(f"📸 Tekan SPACE untuk ambil foto, 'q' untuk keluar.")
    print("⚠️ Perhatian: Tampilan mungkin berwarna aneh (biru) karena frame RGB ditampilkan langsung di OpenCV.")

    photo_count = 0

    while True:
        # ambil frame. Frame ini sudah dalam urutan RGB.
        frame = picam2.capture_array()
        
        # cv2.cvtColor() TIDAK ADA DI SINI. Frame RGB ditampilkan langsung.
        cv2.imshow("Camera", frame) 
        key = cv2.waitKey(1) & 0xFF

        if key == ord(" "):
            picam2.switch_mode(capture_config)
            time.sleep(0.2)

            # Ambil foto full-res (sudah RGB)
            full = picam2.capture_array()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(folder, f"{name}_{timestamp}.jpg")

            # cv2.imwrite() TIDAK ADA KONVERSI. Simpan frame RGB langsung.
            cv2.imwrite(path, full) 
            photo_count += 1

            print(f"✅ Foto {photo_count} tersimpan: {path}")

            picam2.switch_mode(preview_config)
            time.sleep(0.2)

        elif key == ord("q"):
            break

    picam2.stop()
    cv2.destroyAllWindows()

    print(f"📂 Selesai. Total: {photo_count} foto.")

if __name__ == "__main__":
    capture_photos()
