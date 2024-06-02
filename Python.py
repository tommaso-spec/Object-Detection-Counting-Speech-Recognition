import cv2
import numpy as np
import serial
import speech_recognition as sr
import threading
from datetime import datetime

# Definizione dei range di colore per i vari Lego
colors = {
    'red': ([0, 70, 50], [10, 255, 255]),
    'blue': ([90, 50, 50], [130, 255, 255]),
    'yellow': ([20, 100, 100], [30, 255, 255]),
    'green': ([30, 50, 50], [80, 255, 255])
}

# Colori accesi per il testo
bright_colors = {
    'red': (0, 0, 255),
    'blue': (255, 0, 0),
    'yellow': (0, 255, 255),
    'green': (0, 255, 0)
}

# Inizializza la connessione seriale con Arduino
ser = serial.Serial('COM3', 115200)

# Configurazione del riconoscitore vocale
r = sr.Recognizer()
mic = sr.Microphone()

# Variabile globale per controllare lo stato di esecuzione
is_running = False

# Variabile globale per tenere traccia degli oggetti già contati
objects_counted = []

# Variabile globale per il frame della webcam
ret = False
frame = None


def ascolta_comando():
    global is_running
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source)
            print("Microfono pronto, in attesa di comandi...")
            while True:
                if cv2.getWindowProperty('Lego Detection', cv2.WND_PROP_VISIBLE) == 0:
                    is_running = False
                    continue
                print("Ascoltando il comando...")
                try:
                    audio = r.listen(source, timeout=10, phrase_time_limit=5)
                    comando = r.recognize_google(audio, language="en-EN")
                    print(f"Comando riconosciuto: {comando}")
                    comando = comando.upper()
                    if comando == "START":
                        is_running = True
                    elif comando == "STOP":
                        is_running = False
                        log_risultati()
                        reset_contatori()
                except sr.WaitTimeoutError:
                    print("Tempo di attesa scaduto, riprovando...")
                except sr.UnknownValueError:
                    print("Non ho capito il comando.")
                except sr.RequestError as e:
                    print(f"Errore nel servizio di riconoscimento vocale: {e}")
    except Exception as ex:
        print("Errore durante l'inizializzazione del microfono:", ex)


def capture_frame():
    global ret, frame
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 420)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 340)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Errore nella lettura del frame dalla fotocamera.")
            break

    cap.release()


def reset_contatori():
    global lego_counts, tracked_objects, object_id_count, objects_counted
    lego_counts = {color: 0 for color in colors}
    tracked_objects = {color: {} for color in colors}
    object_id_count = {color: 0 for color in colors}
    objects_counted = []


def log_risultati():
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    log_file = "lego_detection_log.txt"

    with open(log_file, "a") as f:
        f.write(f"Risultati al {timestamp}:\n")
        for color, count in lego_counts.items():
            f.write(f"{color.capitalize()} Legos: {count}\n")
        total_piece_count = sum(lego_counts.values())
        f.write(f"Totale Legos: {total_piece_count}\n\n")


def preprocess_image(frame):
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    return blurred


def detect_lego(frame, color, tracked_objects, object_id_count):
    processed_frame = preprocess_image(frame)
    hsv = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2HSV)

    lower_color = np.array(colors[color][0], dtype=np.uint8)
    upper_color = np.array(colors[color][1], dtype=np.uint8)

    mask = cv2.inRange(hsv, lower_color, upper_color)

    kernel = np.ones((5, 5), np.uint8)
    opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    height, width = frame.shape[:2]
    threshold_line = int(height * 0.65)

    piece_count = 0
    max_age = 10

    new_tracked_objects = {}
    new_obj_id = None

    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 200:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                x, y, w, h = cv2.boundingRect(contour)

                already_counted = False
                for counted_obj in objects_counted:
                    if abs(cx - counted_obj['cx']) < 50 and abs(cy - counted_obj['cy']) < 50 and abs(
                            area - counted_obj['area']) < 500:
                        already_counted = True
                        break

                if not already_counted:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), bright_colors[color], 2)
                    cv2.circle(frame, (cx, cy), 5, (255, 255, 255), -1)

                    found = False
                    for obj_id, obj in tracked_objects.items():
                        prev_cx, prev_cy = obj['center']
                        if abs(cx - prev_cx) < 50 and abs(cy - prev_cy) < 50:
                            new_tracked_objects[obj_id] = {'center': (cx, cy), 'counted': obj['counted'], 'age': 0}
                            if cy > threshold_line and prev_cy <= threshold_line and not obj['counted']:
                                piece_count += 1
                                new_tracked_objects[obj_id]['counted'] = True
                                objects_counted.append({'cx': cx, 'cy': cy, 'area': area})
                            found = True
                            break

                    if not found:
                        new_obj_id = object_id_count[color]
                        new_tracked_objects[new_obj_id] = {'center': (cx, cy), 'counted': False, 'age': 0}

    if new_obj_id is not None:
        new_tracked_objects[new_obj_id]['counted'] = True
        if cy > threshold_line:
            piece_count += 1
            objects_counted.append({'cx': cx, 'cy': cy, 'area': area})
            object_id_count[color] += 1

    for obj_id in list(tracked_objects.keys()):
        obj = tracked_objects[obj_id]
        obj['age'] += 1
        if obj['age'] < max_age:
            new_tracked_objects[obj_id] = obj

    cv2.line(frame, (0, threshold_line), (width, threshold_line), (255, 255, 255), 2)

    return piece_count, new_tracked_objects


# Inizializza il thread per ascoltare i comandi vocali
threading.Thread(target=ascolta_comando, daemon=True).start()

# Inizializza la webcam nel thread principale
frame_capture_thread = threading.Thread(target=capture_frame, daemon=True)
frame_capture_thread.start()

lego_counts = {color: 0 for color in colors}
tracked_objects = {color: {} for color in colors}
object_id_count = {color: 0 for color in colors}

while True:
    if ret:
        width = int(frame.shape[1] * 1.2)
        height = int(frame.shape[0] * 1.2)
        dim = (width, height)
        frame_resized = cv2.resize(frame, dim, interpolation=cv2.INTER_LINEAR)

        if is_running:
            overlay = frame_resized.copy()
            for color in colors:
                piece_count, tracked_objects[color] = detect_lego(overlay, color, tracked_objects[color],
                                                                  object_id_count)
                lego_counts[color] += piece_count

            total_piece_count = sum(lego_counts.values())

            cv2.putText(overlay, f'Total Legos: {total_piece_count}', (10, 30), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 0),
                        2, cv2.LINE_AA)
            for i, (color, count) in enumerate(lego_counts.items()):
                text = f'{color.capitalize()} Legos: {count}'
                text_color = bright_colors[color]
                cv2.putText(overlay, text, (10, 70 + 40 * i), cv2.FONT_HERSHEY_DUPLEX, 1, text_color, 2, cv2.LINE_AA)

            alpha = 0.6
            cv2.addWeighted(overlay, alpha, frame_resized, 1 - alpha, 0, frame_resized)

            cv2.imshow('Lego Detection', frame_resized)

            for color in lego_counts:
                ser.write(f"{color}:{lego_counts[color]}\n".encode())
        else:
            cv2.putText(frame_resized, "In attesa del comando 'START'...", (10, 30), cv2.FONT_HERSHEY_DUPLEX, 1,
                        (0, 0, 255), 2, cv2.LINE_AA)
            cv2.imshow('Lego Detection', frame_resized)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
ser.close()
