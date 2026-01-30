import cv2
import face_recognition
import numpy as np
import os
import time
import pickle
from datetime import datetime, date
from gtts import gTTS
import threading
import json
import sqlite3
from picamera2 import Picamera2
import subprocess
from collections import deque
from pathlib import Path
from threading import Lock

# ----------------- CONFIG -----------------
DB_PATH = "/home/telkom/absensi/data.db"
ENCODING_FILE = "/home/telkom/absensi/encodings.pkl"
USERS_FILE = "/home/telkom/absensi/users.json"
TTS_CACHE_DIR = "/tmp/tts_cache_absen"    # cached tts files per name+mode
TTS_LANG = "id"

# DISPLAY / PERFORMANCE
SCREEN_W = 1024
SCREEN_H = 600
CAM_WIDTH = 640    # camera capture width
CAM_HEIGHT = 480  # camera capture height
PROCESS_SCALE = 0.25    # scale for recognition (0.25 => 160x120 if camera 640x480)
RECOG_EVERY_N_FRAMES = 6  # 1 recognition every N frames
DIST_TOLERANCE = 0.45

# UI buttons
BTN_W = 260
BTN_H = 70
BTN_Y = SCREEN_H - BTN_H - 20
BTN_MASUK = (80, BTN_Y, 80 + BTN_W, BTN_Y + BTN_H)
BTN_PULANG = (SCREEN_W - BTN_W - 80, BTN_Y, SCREEN_W - 80, BTN_Y + BTN_H)

# Ensure cache dir
Path(TTS_CACHE_DIR).mkdir(parents=True, exist_ok=True)

# ----------------- LOAD USER INFO & ENCODINGS -----------------
if not Path(USERS_FILE).exists():
    print("❌ users.json tidak ditemukan:", USERS_FILE)
    raise SystemExit(1)

with open(USERS_FILE, "r") as f:
    INFO_ORANG = json.load(f)

if not Path(ENCODING_FILE).exists():
    print("❌ encodings.pkl tidak ditemukan:", ENCODING_FILE)
    raise SystemExit(1)

with open(ENCODING_FILE, "rb") as f:
    data = pickle.load(f)

encodeListKnown = data.get("encodings", [])
names = data.get("names", [])

# ----------------- THREAD-SAFE FRAME CAPTURE -----------------
frame_lock = Lock()
latest_frame = None       # Frame RGB (dari Picam) untuk Display & Recognition
capture_running = True

def camera_thread_func():
    global latest_frame, capture_running
    picam = Picamera2()
    # Kembali ke RGB888, dan TIDAK ADA KONVERSI
    config = picam.create_preview_configuration(main={"size": (CAM_WIDTH, CAM_HEIGHT), "format": "RGB888"})
    picam.configure(config)
    picam.start()
    try:
        while capture_running:
            arr = picam.capture_array()    # <-- RGB asli (Picamera2)
            if arr is None:
                continue

            with frame_lock:
                # Hanya simpan array RGB mentah
                latest_frame = arr.copy()            

            time.sleep(0.001)

    except Exception as e:
        print("❌ Camera thread error:", e)
    finally:
        try:
            picam.stop()
        except:
            pass

# Start camera thread
cam_thread = threading.Thread(target=camera_thread_func, daemon=True)
cam_thread.start()

# ----------------- DATABASE HELPERS (threaded writes) -----------------
def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS absensi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                mode TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print("❌ Init DB Error:", e)

def db_insert_worker(record):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO absensi (nama, date, time, mode, status)
            VALUES (?, ?, ?, ?, ?)
        """, (record['name'], record['date'], record['time'], record['mode'], record['status']))
        conn.commit()
        conn.close()
        # print minimal log
        print(f"[DB] {record['date']} {record['time']} | {record['name']} | {record['mode']} | {record['status']}")
    except Exception as e:
        print("❌ SQLite Error (thread):", e)

def save_to_sqlite_async(name, date_, time_, mode, status):
    record = {'name': name, 'date': date_, 'time': time_, 'mode': mode, 'status': status}
    t = threading.Thread(target=db_insert_worker, args=(record,), daemon=True)
    t.start()

def check_already_absent(name, date_, mode):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=3)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM absensi
            WHERE nama = ? AND date = ? AND mode = ?
            LIMIT 1
        """, (name, date_, mode))
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except Exception as e:
        print("❌ SQLite check error:", e)
        return False

init_db()

# ----------------- TTS: cached generation + non-blocking playback -----------------
def tts_filename_for(name, mode):
    safe = name.replace(" ", "_").lower()
    fn = f"tts_{safe}_{mode.lower()}.mp3"
    return os.path.join(TTS_CACHE_DIR, fn)

def generate_tts_file(text, filepath):
    try:
        tts = gTTS(text=text, lang=TTS_LANG)
        tts.save(filepath)
        # small sleep to ensure file visible to player
        time.sleep(0.05)
    except Exception as e:
        print("❌ gTTS generation error:", e)

def play_audio_nonblocking(filepath):
    # Using mpg123 in background (non-blocking)
    try:
        subprocess.Popen(["mpg123", "-q", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        try:
            os.system(f"mpg123 '{filepath}' >/dev/null 2>&1 &")
        except:
            pass

def speak_cached(name, mode, fallback_text=None):
    """
    Play cached TTS for (name,mode). If file missing, start generating in background and play
    after generation (background). If generation takes too long, fallback to a short generic beep speech.
    """
    filepath = tts_filename_for(name, mode)
    if os.path.exists(filepath):
        # fast path: play immediately non-blocking
        play_audio_nonblocking(filepath)
        return

    # prepare message
    if fallback_text is None:
        if mode.upper() == "MASUK":
            text = f"Terima kasih, absensi masuk {name} berhasil"
        else:
            text = f"Terima kasih, absensi pulang {name} berhasil. Hati-hati di jalan."
    else:
        text = fallback_text

    # generate in background and play when done
    def gen_and_play():
        try:
            generate_tts_file(text, filepath)
            play_audio_nonblocking(filepath)
        except Exception as e:
            print("❌ TTS gen+play error:", e)

    t = threading.Thread(target=gen_and_play, daemon=True)
    t.start()

# Small helper to force-generate & play a one-off TTS (used for duplicate notices)
def speak_force(text):
    try:
        # use a temp filename with timestamp to avoid race/collision
        ts = int(time.time() * 1000)
        filepath = os.path.join("/tmp", f"tts_force_{ts}.mp3")
        generate_tts_file(text, filepath)
        play_audio_nonblocking(filepath)
    except Exception as e:
        print("❌ speak_force error:", e)

# ----------------- UI helpers (lightweight popup) -----------------
POPUP_TEXT = ""
POPUP_COLOR = (0, 255, 0)
POPUP_EXPIRE = 0

def show_popup_overlay(display_frame, text, color):
    # lightweight semi-transparent rectangle with text (no heavy blur)
    h, w, _ = display_frame.shape
    box_w, box_h = min(700, w-40), 140
    x1 = (w - box_w) // 2
    y1 = 10
    x2 = x1 + box_w
    y2 = y1 + box_h
    overlay = display_frame.copy()
    alpha = 0.55
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (30,30,30), -1)
    cv2.addWeighted(overlay, alpha, display_frame, 1 - alpha, 0, display_frame)
    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)

    # draw text lines
    lines = text.split("\n")
    for i, line in enumerate(lines):
        cv2.putText(display_frame, line, (x1 + 20, y1 + 35 + i*30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2, cv2.LINE_AA)

def draw_button(frame, coords, text, color):
    x1, y1, x2, y2 = coords
    # shadow
    cv2.rectangle(frame, (x1+3, y1+3), (x2+3, y2+3), (30, 30, 30), -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (40,40,40), 2)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.05, 3)
    tx = x1 + (BTN_W - tw)//2
    ty = y1 + (BTN_H + th)//2 - 6
    cv2.putText(frame, text, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 1.05, (0, 0, 0), 3)

# ----------------- Mouse callback -----------------
MODE = None
def on_click(event, x, y, flags, param):
    global MODE
    if event == cv2.EVENT_LBUTTONDOWN:
        if BTN_MASUK[0] <= x <= BTN_MASUK[2] and BTN_MASUK[1] <= y <= BTN_MASUK[3]:
            MODE = "MASUK"
        elif BTN_PULANG[0] <= x <= BTN_PULANG[2] and BTN_PULANG[1] <= y <= BTN_PULANG[3]:
            MODE = "PULANG"

cv2.namedWindow("ABSENSI", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("ABSENSI", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("ABSENSI", on_click)

# ----------------- Attendance logic -----------------
ABSEN_LOG = {}    # memory check
SLEEP = False
NO_FACE_TIMER = 0

def markAttendance(name):
    global MODE, POPUP_TEXT, POPUP_COLOR, POPUP_EXPIRE, ABSEN_LOG

    if MODE is None:
        return

    today = date.today().isoformat()

    if name not in ABSEN_LOG or ABSEN_LOG[name].get("date") != today:
        ABSEN_LOG[name] = {"date": today, "MASUK": False, "PULANG": False}

    # CHECK DUPLICATE IN DB
    if check_already_absent(name, today, MODE):
        # only speak the duplicate message, no popup
        speak_force(f"{name} sudah absen {MODE} hari ini")
        # ensure popup disabled
        POPUP_EXPIRE = 0
        return

    # CHECK DUPLICATE IN MEMORY
    if ABSEN_LOG[name][MODE]:
        speak_force(f"{name} sudah absen {MODE} hari ini")
        POPUP_EXPIRE = 0
        return

    now = datetime.now()
    time_now = now.strftime("%H:%M:%S")
    info = INFO_ORANG.get(name, {"instansi":"-", "status":"-"})

    popup_msg = (f"Name    : {name}\n"
                 f"Instansi: {info.get('instansi','-')}\n"
                 f"Status : {info.get('status','-')}")

    if MODE == "MASUK":
        batas = now.replace(hour=8, minute=15, second=0)
        status = "Tepat waktu" if now <= batas else "Terlambat"
        POPUP_COLOR = (0,200,0)
        # speak (cached)
        speak_cached(name, "MASUK")
    elif MODE == "PULANG":
        batas = now.replace(hour=17, minute=0, second=0)
        status = "Pulang" if now >= batas else "Pulang sebelum waktunya"
        POPUP_COLOR = (0,0,200)
        speak_cached(name, "PULANG")

    POPUP_TEXT = popup_msg
    POPUP_EXPIRE = time.time() + 4.5

    # Save to sqlite in background
    save_to_sqlite_async(name, today, time_now, MODE, status)
    ABSEN_LOG[name][MODE] = True

# ----------------- Display power (sleep mode) -----------------
def set_display(on):
    try:
        if on:
            os.system("vcgencmd display_power 1")
            os.system("echo 0 > /sys/class/backlight/rpi_backlight/bl_power")
        else:
            os.system("vcgencmd display_power 0")
            os.system("echo 1 > /sys/class/backlight/rpi_backlight/bl_power")
    except Exception:
        pass

# ----------------- MAIN LOOP (NON-BLOCKING) -----------------
FRAME_COUNT = 0
last_detected_name = "UNKNOWN"
t0 = time.time()

try:
    while True:
        # read latest frame produced by camera thread
        with frame_lock:
            # Mengambil frame yang isinya RGB dari Picam
            frame = None if latest_frame is None else latest_frame.copy()

        if frame is None:
            # no frame yet; small wait
            time.sleep(0.01)
            continue

        FRAME_COUNT += 1

        # create small frame for recognition (scale down once)
        small = cv2.resize(frame, (0,0), fx=PROCESS_SCALE, fy=PROCESS_SCALE, interpolation=cv2.INTER_LINEAR)
        
        # *** TIDAK ADA KONVERSI WARNA SAMA SEKALI UNTUK FACE_RECOGNITION ***
        # Diharapkan small (yang isinya RGB) dapat langsung digunakan oleh face_recognition.
        rgb_small = small # Ini adalah pengganti cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        # recognition only on some frames
        do_recog = (FRAME_COUNT % RECOG_EVERY_N_FRAMES) == 0

        faces = []
        encodings = []
        if do_recog:
            # use hog model (faster on CPU) — can switch to 'cnn' if you have GPU
            # Menggunakan RGB_small yang aslinya adalah frame RGB (atau apa pun yang dikeluarkan Picam)
            faces = face_recognition.face_locations(rgb_small, model="hog")
            if faces:
                encodings = face_recognition.face_encodings(rgb_small, faces)

        # recognition result
        detected_name = "UNKNOWN"
        if encodings:
            # compare each face encoding to known encodings
            for enc in encodings:
                matches = face_recognition.compare_faces(encodeListKnown, enc, tolerance=DIST_TOLERANCE)
                dist = face_recognition.face_distance(encodeListKnown, enc)
                if len(dist) > 0:
                    best = np.argmin(dist)
                    if matches[best] and dist[best] < DIST_TOLERANCE:
                        detected_name = names[best].upper()
                        break

        # Sleep mode logic
        if do_recog:
            if len(faces) == 0:
                NO_FACE_TIMER += 1
            else:
                NO_FACE_TIMER = 0

            if NO_FACE_TIMER > 8 and not SLEEP:
                SLEEP = True
                set_display(False)
            if SLEEP and len(faces) >= 1:
                SLEEP = False
                set_display(True)

        if SLEEP:
            # still allow exit key
            if cv2.waitKey(1) == 27:
                break
            continue

        # Draw UI on a copy for display
        # Menggunakan frame RGB (dari Picam) langsung untuk display, berharap OpenCV mau menampilkannya dengan benar.
        display_frame = cv2.resize(frame, (SCREEN_W, SCREEN_H), interpolation=cv2.INTER_LINEAR)

        draw_button(display_frame, BTN_MASUK, "MASUK", (0,200,0))
        draw_button(display_frame, BTN_PULANG, "PULANG", (0,0,200))

        # Popup
        if time.time() < POPUP_EXPIRE:
            show_popup_overlay(display_frame, POPUP_TEXT, POPUP_COLOR)

        cv2.imshow("ABSENSI", display_frame)

        # if button pressed (MODE set via mouse callback) and face detected -> mark attendance
        if MODE in ["MASUK", "PULANG"] and detected_name != "UNKNOWN":
            markAttendance(detected_name)
            MODE = None
            # short sleep avoid double mark quickly
            time.sleep(0.55)

        # Key handling
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

except KeyboardInterrupt:
    pass
finally:
    # stop camera thread
    capture_running = False
    try:
        cam_thread.join(timeout=1.0)
    except:
        pass
    cv2.destroyAllWindows()
    print("Exiting...")
