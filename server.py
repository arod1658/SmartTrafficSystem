import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys

# Windows 環境下強制 UTF-8 輸出，避免 cp950 解碼錯誤
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
# 允許跨網域請求，確保 Live Server (127.0.0.1:5500) 可以正常存取 API
CORS(app)

DB_FILE = 'traffic.db'

def init_db():
    """初始化資料庫與資料表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # 建立 incidents 資料表，儲存即時事故回報
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            title TEXT NOT NULL,
            desc TEXT NOT NULL,
            time TEXT NOT NULL,
            image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ SQLite 資料庫 `traffic.db` 初始化完成！")

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """取得所有歷史事故回報"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY time DESC")
        rows = cursor.fetchall()
        
        incidents = []
        for row in rows:
            incidents.append({
                "id": row["id"],
                "lat": row["lat"],
                "lng": row["lng"],
                "title": row["title"],
                "desc": row["desc"],
                "time": row["time"],
                "image_path": row["image_path"]
            })
        conn.close()
        return jsonify({"status": "success", "data": incidents}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/incidents', methods=['POST'])
def add_incident():
    """新增一筆事故回報"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "無效的 JSON 資料"}), 400
        
        # 準備資料
        incident_id = str(data.get("id", ""))
        lat = float(data.get("lat", 0.0))
        lng = float(data.get("lng", 0.0))
        title = data.get("title", "未命名事件")
        desc = data.get("desc", "無描述")
        time = data.get("time", "剛剛")
        image_path = data.get("image_path", "")

        # 寫入 SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO incidents (id, lat, lng, title, desc, time, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (incident_id, lat, lng, title, desc, time, image_path))
        conn.commit()
        conn.close()
        
        print(f"📥 成功寫入新事故：{title} - {desc}")
        return jsonify({"status": "success", "message": "事件已成功記錄"}), 201

    except Exception as e:
        print(f"❌ 寫入失敗：{str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # 啟動前先初始化資料庫
    init_db()
    # 執行於 127.0.0.1:5000
    print("🚀 後端伺服器啟動，正在監聽 http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
