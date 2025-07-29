from flask import Flask, render_template, Response, request, send_file, jsonify
from flask_socketio import SocketIO
import cv2
import threading
import time
import csv
from datetime import datetime
import numpy as np
from sklearn.linear_model import LinearRegression
from ultralytics import YOLO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
model = YOLO("yolov10n.pt")

# yolo_server.py の該当箇所（例）
cap = cv2.VideoCapture("http://host.docker.internal:8090/video_feed")
capacity = 0
crowd_log = []  # (timestamp, count)
INFERENCE_INTERVAL = 1.0
latest_frame = None
show_graph = False
latest_reduced = []


def detect_people(frame):
    results = model(frame)
    return sum(1 for c in results[0].boxes.cls if model.names[int(c)] == "person"), results[0].plot()


def get_congestion_level(count, capacity):
    if capacity == 0:
        return "未設定"
    rate = count / capacity
    if rate >= 1.0:
        return "満員"
    elif rate > 0.8:
        return "混雑"
    elif rate > 0.5:
        return "やや混雑"
    elif rate > 0.2:
        return "空きあり"
    else:
        return "空き"


def predict_future(log, minutes_ahead=10):
    if len(log) < 5:
        return None
    try:
        base_time = datetime.strptime(log[0][0], "%Y-%m-%d %H:%M:%S")
        timestamps = [(datetime.strptime(t, "%Y-%m-%d %H:%M:%S") - base_time).total_seconds() / 60 for t, _ in log]
        counts = [c for _, c in log]

        X = np.array(timestamps).reshape(-1, 1)
        y = np.array(counts)

        model = LinearRegression().fit(X, y)
        future = np.array([[timestamps[-1] + minutes_ahead]])
        prediction = model.predict(future)[0]
        return max(0, min(round(prediction), capacity))
    except:
        return None


def video_loop():
    global cap, latest_frame, crowd_log, latest_reduced

    ret, warmup_frame = cap.read()
    if ret:
        model(warmup_frame)

    last_time = 0
    interval = 10  # グラフとCSV共通の平均間隔（秒）
    buffer = []

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        count, annotated_frame = detect_people(frame)
        latest_frame = annotated_frame.copy()
        full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        buffer.append((full_timestamp, count))

        now = time.time()
        if now - last_time >= INFERENCE_INTERVAL:
            level = get_congestion_level(count, capacity)
            prediction_10min = predict_future(crowd_log, 10)
            timestamp_short = time.strftime('%H:%M:%S')

            socketio.emit('crowd_update', {
                'count': count,
                'level': level,
                'capacity': capacity,
                'show_graph': show_graph,
                'timestamp': timestamp_short,
                'prediction_10min': prediction_10min
            })
            last_time = now

        if len(buffer) >= interval:
            avg_count = sum(c for _, c in buffer) / len(buffer)
            crowd_log.append((buffer[len(buffer)//2][0], round(avg_count)))
            latest_reduced = crowd_log[-300:]
            buffer = []


def gen_frames():
    global latest_frame
    while True:
        if latest_frame is None:
            continue
        ret, buffer = cv2.imencode('.jpg', latest_frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/set_capacity', methods=['POST'])
def set_capacity():
    global capacity, show_graph
    try:
        capacity = int(request.form.get('capacity', 0))
        show_graph = True
        return 'OK'
    except:
        return 'Invalid capacity', 400


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/download_csv')
def download_csv():
    filename = 'crowd_summary.csv'
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Avg Count', 'Level'])
        for ts, count in latest_reduced:
            level = get_congestion_level(count, capacity)
            writer.writerow([ts, count, level])
    return send_file(filename, as_attachment=True)


threading.Thread(target=video_loop, daemon=True).start()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, allow_unsafe_werkzeug=True)