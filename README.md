python -m venv venv

source venv/bin/activate　#仮想環境を実行

cd app

pip install flask opencv-python　#必要なパッケージをインストール

python camera_stream_server.py  #まず、カメラを起動するプログラムを実行

#ここにアクセスしてカメラの起動を確認できたら

http://127.0.0.1:8090/video_feed

#実行したまま、新規ターミナルを開く

docker-compose up --build 　#dockerコンテナを起動

#起動したら、以下のURLにアクセス

http://127.0.0.1:8080/
