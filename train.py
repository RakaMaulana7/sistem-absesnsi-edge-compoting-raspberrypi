import face_recognition
import os
import pickle

dataset_dir = "dataset"
encodings = []
names = []

for person_name in os.listdir(dataset_dir):
    person_path = os.path.join(dataset_dir, person_name)
    if not os.path.isdir(person_path):
        continue

    for image_name in os.listdir(person_path):
        image_path = os.path.join(person_path, image_name)
        image = face_recognition.load_image_file(image_path)
        face_locations = face_recognition.face_locations(image)
        face_encs = face_recognition.face_encodings(image, face_locations)

        for enc in face_encs:
            encodings.append(enc)
            names.append(person_name)
        print(f"[OK] {person_name}/{image_name} trained.")

with open("encodings.pkl", "wb") as f:
    pickle.dump({"encodings": encodings, "names": names}, f)

print("[DONE] Semua wajah sudah ditraining dan disimpan ke encodings.pkl ✅")
