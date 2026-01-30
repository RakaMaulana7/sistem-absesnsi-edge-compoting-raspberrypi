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
from pathlib import Path
from threading import Lock
import subprocess

# ----------------- CONFIG -----------------
DB_PATH = "/home/telkom/absensi/data.db"
ENCODING_FILE = "/home/telkom/absensi/encodings.pkl"
USERS_FILE = "/home/telkom/absensi/users.json"
TTS_CACHE_DIR = "/tmp/tts_cache_absen"
TTS_LANG = "id"

SCREEN_W = 1024
SCREEN_H = 600
CAM_WIDTH = 640
CAM_HEIGHT = 480
PROCESS_SCALE = 0.25
RECOG_EVERY_N_FRAMES = 6
DIST_TOLERANCE = 0.45

BTN_W = 260
BTN_H = 70
BTN_Y = SCREEN_H - BTN_H - 20
BTN_MASUK = (80, BTN_Y, 80 + BTN_W, BTN_Y + BTN_H)
BTN_PULANG = (SCREEN_W - BTN_W - 80, BTN_Y, SCREEN_W - 80, BTN_Y + BTN_H)

Path(TTS_CACHE_DIR).mkdir(parents=True, exist_ok=True)

# ----------------- LOAD USERS & ENCODINGS -----------------
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

# ----------------- CAMERA THREAD -----------------
frame_lock = Lock()
latest_frame = None
capture_running = True

def camera_thread_func():
    global latest_frame, capture_running
    picam = Picamera2()
    config = picam.create_preview_configuration(main={"size": (CAM_WIDTH, CAM_HEIGHT), "format": "RGB888"})
    picam.configure(config)
    picam.start()
    try:
        while capture_running:
            arr = picam.capture_array()
            if arr is None:
                continue
            with frame_lock:
                latest_frame = arr.copy()
            time.sleep(0.001)
    except Exception as e:
        print("❌ Camera thread error:", e)
    finally:
        try:
            picam.stop()
        except:
            pass

cam_thread = threading.Thread(target=camera_thread_func, daemon=True)
cam_thread.start()

# ----------------- DATABASE -----------------
def init_db():
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

def save_to_sqlite_async(name, date_, time_, mode, status):
    def worker():
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO absensi (nama, date, time, mode, status)
                VALUES (?, ?, ?, ?, ?)
            """, (name, date_, time_, mode, status))
            conn.commit()
            conn.close()
            print(f"[DB] {date_} {time_} | {name} | {mode} | {status}")
        except Exception as e:
            print("❌ SQLite Error:", e)
    threading.Thread(target=worker, daemon=True).start()

def check_already_absent(name, date_, mode):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM absensi WHERE nama=? AND date=? AND mode=? LIMIT 1", (name, date_, mode))
        row = cursor.fetchone()
        conn.close()
        return row is not None
    except:
        return False

init_db()

# ----------------- TTS -----------------
def tts_filename_for(name, mode):
    safe = name.replace(" ", "_").lower()
    return os.path.join(TTS_CACHE_DIR, f"tts_{safe}_{mode.lower()}.mp3")

def generate_tts_file(text, filepath):
    try:
        gTTS(text=text, lang=TTS_LANG).save(filepath)
        time.sleep(0.05)
    except Exception as e:
        print("❌ gTTS error:", e)

def play_audio_nonblocking(filepath):
    try:
        subprocess.Popen(["mpg123", "-q", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

def speak_cached(name, mode, fallback_text=None):
    filepath = tts_filename_for(name, mode)
    if os.path.exists(filepath):
        play_audio_nonblocking(filepath)
        return

    text = fallback_text or f"Terima kasih, absensi {mode.lower()} {name} berhasil"
    def gen_play():
        generate_tts_file(text, filepath)
        play_audio_nonblocking(filepath)
    threading.Thread(target=gen_play, daemon=True).start()

# ----------------- UI -----------------
POPUP_TEXT = ""
POPUP_COLOR = (0,255,0)
POPUP_EXPIRE = 0

def show_popup_overlay(frame, text, color):
    h, w, _ = frame.shape
    box_w, box_h = min(700, w-40), 140
    x1, y1 = (w - box_w)//2, 10
    x2, y2 = x1 + box_w, y1 + box_h
    overlay = frame.copy()
    alpha = 0.55
    cv2.rectangle(overlay, (x1,y1), (x2,y2), (30,30,30), -1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
    cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
    for i, line in enumerate(text.split("\n")):
        cv2.putText(frame, line, (x1+20, y1+35+i*30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)

def draw_button(frame, coords, text, color):
    x1,y1,x2,y2 = coords
    cv2.rectangle(frame, (x1+3,y1+3), (x2+3,y2+3), (30,30,30), -1)
    cv2.rectangle(frame, (x1,y1), (x2,y2), color, -1)
    cv2.rectangle(frame, (x1,y1), (x2,y2), (40,40,40), 2)
    (tw,th),_ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX,1.05,3)
    tx = x1 + (BTN_W - tw)//2
    ty = y1 + (BTN_H + th)//2 - 6
    cv2.putText(frame, text, (tx,ty), cv2.FONT_HERSHEY_SIMPLEX,1.05,(0,0,0),3)

# ----------------- MOUSE -----------------
MODE = None
def on_click(event,x,y,flags,param):
    global MODE
    if event == cv2.EVENT_LBUTTONDOWN:
        if BTN_MASUK[0]<=x<=BTN_MASUK[2] and BTN_MASUK[1]<=y<=BTN_MASUK[3]:
            MODE = "MASUK"
        elif BTN_PULANG[0]<=x<=BTN_PULANG[2] and BTN_PULANG[1]<=y<=BTN_PULANG[3]:
            MODE = "PULANG"

cv2.namedWindow("ABSENSI", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("ABSENSI", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback("ABSENSI", on_click)

# ----------------- Display power -----------------
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

NO_FACE_TIMER = 0
SLEEP = False

# ----------------- MAIN LOOP -----------------
FRAME_COUNT = 0
ABSEN_LOG = {}

def markAttendance(name):
    global MODE, POPUP_TEXT, POPUP_COLOR, POPUP_EXPIRE, ABSEN_LOG
    if MODE is None:
        return
    today = date.today().isoformat()
    if name not in ABSEN_LOG or ABSEN_LOG[name].get("date") != today:
        ABSEN_LOG[name] = {"date": today, "MASUK": False, "PULANG": False}

    already_absent = check_already_absent(name, today, MODE) or ABSEN_LOG[name][MODE]
    now = datetime.now()
    time_now = now.strftime("%H:%M:%S")

    if MODE == "MASUK":
        batas = now.replace(hour=8, minute=15, second=0)
        status = "Tepat waktu" if now <= batas else "Terlambat"
        POPUP_COLOR = (0, 200, 0)
        tts_text_new = f"Terima kasih, absensi masuk {name} berhasil"
        tts_text_old = f"{name} sudah absen MASUK hari ini"
    else:
        batas = now.replace(hour=17, minute=0, second=0)
        status = "Pulang" if now >= batas else "Pulang sebelum waktunya"
        POPUP_COLOR = (0, 0, 200)
        tts_text_new = f"Terima kasih, absensi pulang {name} berhasil, hati-hati di jalan"
        tts_text_old = f"{name} sudah absen PULANG hari ini"

    if not already_absent:
        # absen baru → popup + TTS + simpan DB
        info = INFO_ORANG.get(name, {"instansi": "-", "status": "-"})
        POPUP_TEXT = f"Name: {name}\nInstansi: {info.get('instansi')}\nStatus: {info.get('status')}"
        POPUP_EXPIRE = time.time() + 4.5
        save_to_sqlite_async(name, today, time_now, MODE, status)
        speak_cached(name, MODE, fallback_text=tts_text_new)
        ABSEN_LOG[name][MODE] = True
    else:
        # sudah absen → TTS saja, popup ga muncul
        speak_cached(name, MODE, fallback_text=tts_text_old)

try:
    while True:
        with frame_lock:
            frame = latest_frame.copy() if latest_frame is not None else None
        if frame is None:
            time.sleep(0.01)
            continue

        FRAME_COUNT += 1
        small = cv2.resize(frame, (0,0), fx=PROCESS_SCALE, fy=PROCESS_SCALE)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)

        do_recog = (FRAME_COUNT % RECOG_EVERY_N_FRAMES) == 0
        faces, encodings = [], []
        if do_recog:
            faces = face_recognition.face_locations(rgb_small, model="hog")
            encodings = face_recognition.face_encodings(rgb_small, faces) if faces else []

        detected_name = "UNKNOWN"
        for enc in encodings:
            matches = face_recognition.compare_faces(encodeListKnown, enc, tolerance=DIST_TOLERANCE)
            dist = face_recognition.face_distance(encodeListKnown, enc)
            if len(dist) > 0:
                best = np.argmin(dist)
                if matches[best] and dist[best] < DIST_TOLERANCE:
                    detected_name = names[best].upper()
                    break

        # ----------------- Sleep mode logic -----------------
        if do_recog:
            NO_FACE_TIMER = NO_FACE_TIMER + 1 if len(faces) == 0 else 0
            if NO_FACE_TIMER > 8 and not SLEEP:
                SLEEP = True
                set_display(False)
            if SLEEP and len(faces) >= 1:
                SLEEP = False
                set_display(True)

        if SLEEP:
            key = cv2.waitKey(1)
            if key == 27:
                break
            continue

        display_frame = cv2.resize(frame, (SCREEN_W, SCREEN_H))
        draw_button(display_frame, BTN_MASUK, "MASUK", (0,200,0))
        draw_button(display_frame, BTN_PULANG, "PULANG", (0,0,200))
        if time.time() < POPUP_EXPIRE:
            show_popup_overlay(display_frame, POPUP_TEXT, POPUP_COLOR)

        cv2.imshow("ABSENSI", display_frame)

        if MODE in ["MASUK","PULANG"] and detected_name != "UNKNOWN":
            markAttendance(detected_name)
            MODE = None
            time.sleep(0.55)

        key = cv2.waitKey(1)
        if key == 27:
            break
except KeyboardInterrupt:
    pass
finally:
    capture_running = False
    try:
        cam_thread.join(timeout=1.0)
    except:
        pass
    cv2.destroyAllWindows()
    print("Exiting...")
