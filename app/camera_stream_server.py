# camera_stream_server.py
import cv2
from flask import Flask, Response

app = Flask(__name__)
camera = cv2.VideoCapture(0)  # Macの内蔵カメラ

def generate_frames():
    while True:
        camera.grab()  # 最新フレームを掴む（古いバッファは破棄）
        success, frame = camera.read()
        if not success:
            break
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)
