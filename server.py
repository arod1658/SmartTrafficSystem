import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import time

# Windows 環境下強制 UTF-8 輸出，避免 cp950 解碼錯誤
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
CORS(app)

DB_FILE = 'traffic.db'

def get_db_connection():
    # 開啟 check_same_thread=False 支援 Flask 高並發
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化 12 張實體資料表與預設資料"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            email TEXT,
            register_time TEXT,
            status BOOLEAN
        )
    ''')
    
    # 2. accounts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            account_id TEXT PRIMARY KEY,
            user_id TEXT,
            username TEXT,
            password TEXT,
            role TEXT,
            status TEXT,
            create_time TEXT,
            last_login_time TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # 3. locations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            location_id TEXT PRIMARY KEY,
            user_id TEXT,
            latitude REAL,
            longitude REAL,
            address TEXT,
            rcv_time TEXT,
            source TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # 4. incidents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            reporter_id TEXT,
            lat REAL,
            lng REAL,
            title TEXT,
            desc TEXT,
            time TEXT,
            severity TEXT,
            status TEXT,
            image_path TEXT
        )
    ''')
    
    # 5. traffic_lights
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS traffic_lights (
            light_id TEXT PRIMARY KEY,
            name TEXT,
            lat REAL,
            lng REAL,
            signal_type TEXT,
            cycle_time INTEGER,
            status TEXT
        )
    ''')
    
    # 6. routes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY,
            user_id TEXT,
            origin TEXT,
            destination TEXT,
            start_time TEXT,
            end_time TEXT,
            travel_mode TEXT,
            preference TEXT,
            traffic_condition TEXT
        )
    ''')
    
    # 7. parking_lots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            parking_id TEXT PRIMARY KEY,
            name TEXT,
            address TEXT,
            total_spaces INTEGER,
            avail_spaces INTEGER,
            fare TEXT,
            update_time TEXT
        )
    ''')
    
    # 8. transit_info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transit_info (
            transit_id TEXT PRIMARY KEY,
            type TEXT,
            route_name TEXT,
            operator TEXT,
            current_position TEXT,
            est_arrival_time TEXT,
            delay_minutes INTEGER,
            update_time TEXT
        )
    ''')
    
    # 9. shared_vehicles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_vehicles (
            vehicle_id TEXT PRIMARY KEY,
            type TEXT,
            provider TEXT,
            battery_level REAL,
            lat REAL,
            lng REAL,
            status TEXT,
            update_time TEXT
        )
    ''')
    
    # 10. weather_info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_info (
            weather_id TEXT PRIMARY KEY,
            station_id TEXT,
            temperature REAL,
            rainfall REAL,
            wind_direction TEXT,
            status TEXT,
            data_time TEXT,
            data_source TEXT
        )
    ''')
    
    # 11. cctv_monitors
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cctv_monitors (
            cctv_id TEXT PRIMARY KEY,
            name TEXT,
            camera_type TEXT,
            lat REAL,
            lng REAL,
            department TEXT,
            status TEXT,
            install_time TEXT
        )
    ''')
    
    # 12. analysis_reports
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_reports (
            report_id TEXT PRIMARY KEY,
            analyst_count INTEGER,
            scope TEXT,
            contact_method TEXT,
            traffic_data_log TEXT,
            output_result TEXT
        )
    ''')

    # SEEDING: 寫入信義路五大智慧號誌預設資料
    cursor.execute("SELECT COUNT(*) FROM traffic_lights")
    if cursor.fetchone()[0] == 0:
        lights_data = [
            ("L1", "信義新生南路口", 25.03332, 121.53322, "Smart", 60, "Active"),
            ("L2", "信義建國南路口", 25.03328, 121.53738, "Smart", 60, "Active"),
            ("L3", "信義敦化南路口", 25.03310, 121.54911, "Smart", 60, "Active"),
            ("L4", "信義光復南路口", 25.03303, 121.55745, "Smart", 60, "Active"),
            ("L5", "信義基隆路口", 25.03341, 121.56524, "Smart", 60, "Active")
        ]
        cursor.executemany("INSERT INTO traffic_lights VALUES (?, ?, ?, ?, ?, ?, ?)", lights_data)
        
    # SEEDING: CCTV 預設資料
    cursor.execute("SELECT COUNT(*) FROM cctv_monitors")
    if cursor.fetchone()[0] == 0:
        cctv_data = [
            ("C1", "市府廣場CCTV", "PTZ", 25.0375, 121.5637, "POLICE", "Active", "2023-01-01"),
            ("C2", "台北101周邊CCTV", "Fixed", 25.0339, 121.5644, "MANAGEMENT", "Active", "2023-02-01")
        ]
        cursor.executemany("INSERT INTO cctv_monitors VALUES (?, ?, ?, ?, ?, ?, ?, ?)", cctv_data)

    conn.commit()
    conn.close()
    print("✅ 實體資料表與關聯模型建置完成，並已注入基礎設施預設資料。")

# ================= RESTful API Routes =================

@app.route('/api/auth/login', methods=['POST', 'GET'])
def auth_login():
    """處理登入與註冊，並驗證 accounts 表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'PUBLIC') # 註冊時會有 role
        is_register = data.get('is_register', False)
        
        if is_register:
            # 檢查是否已存在
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                return jsonify({"status": "error", "message": "該 Email 已被註冊"}), 400
            
            user_id = "U" + str(int(time.time()))
            account_id = "A" + str(int(time.time()))
            now_str = time.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("INSERT INTO users (user_id, email, register_time, status) VALUES (?, ?, ?, ?)", 
                           (user_id, email, now_str, True))
            cursor.execute("INSERT INTO accounts (account_id, user_id, username, password, role, status, create_time, last_login_time) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (account_id, user_id, email, password, role, "Active", now_str, now_str))
            conn.commit()
            token = f"jwt_{user_id}_{role}"
            return jsonify({"status": "success", "token": token, "email": email, "role": role})
        else:
            # 登入驗證
            cursor.execute("SELECT a.account_id, a.user_id, a.role, u.email FROM accounts a JOIN users u ON a.user_id = u.user_id WHERE u.email=? AND a.password=?", (email, password))
            row = cursor.fetchone()
            if row:
                now_str = time.strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("UPDATE accounts SET last_login_time=? WHERE account_id=?", (now_str, row['account_id']))
                conn.commit()
                token = f"jwt_{row['user_id']}_{row['role']}"
                return jsonify({"status": "success", "token": token, "email": row['email'], "role": row['role']})
            else:
                return jsonify({"status": "error", "message": "帳號或密碼錯誤"}), 401
    else:
        # GET 用於檢查 Auth Token (保留擴充用)
        return jsonify({"status": "success", "message": "Auth API 運作中"})

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """取得所有歷史事故回報"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM incidents ORDER BY time DESC")
        rows = cursor.fetchall()
        incidents = [dict(row) for row in rows]
        conn.close()
        return jsonify({"status": "success", "data": incidents}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/incidents', methods=['POST'])
def add_incident():
    """新增一筆事故回報"""
    try:
        data = request.json
        if not data: return jsonify({"status": "error", "message": "無效的 JSON 資料"}), 400
        
        incident_id = str(data.get("id", str(int(time.time()*1000))))
        lat = float(data.get("lat", 0.0))
        lng = float(data.get("lng", 0.0))
        title = data.get("title", "未命名事件")
        desc = data.get("desc", "無描述")
        timestamp = data.get("time", time.strftime('%Y-%m-%d %H:%M:%S'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO incidents (id, lat, lng, title, desc, time, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                       (incident_id, lat, lng, title, desc, timestamp, ""))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "事件已成功記錄"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/routes', methods=['POST', 'GET'])
def handle_routes():
    """導航紀錄"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        route_id = "R" + str(int(time.time()*1000))
        user_id = data.get('user_id', 'Guest')
        origin = data.get('origin')
        dest = data.get('destination')
        mode = data.get('travel_mode')
        
        cursor.execute("INSERT INTO routes (route_id, user_id, origin, destination, start_time, travel_mode) VALUES (?, ?, ?, ?, ?, ?)",
                       (route_id, user_id, origin, dest, time.strftime('%Y-%m-%d %H:%M:%S'), mode))
        conn.commit()
        return jsonify({"status": "success", "route_id": route_id})
    else:
        cursor.execute("SELECT * FROM routes ORDER BY start_time DESC")
        rows = cursor.fetchall()
        routes = [dict(r) for r in rows]
        return jsonify({"status": "success", "data": routes})

@app.route('/api/traffic-lights/cycle', methods=['PUT'])
def update_traffic_light():
    """變時調整號誌"""
    try:
        data = request.json
        light_name = data.get('name')
        extended_time = data.get('extended_time', 0)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 先抓出現有 cycle
        cursor.execute("SELECT cycle_time FROM traffic_lights WHERE name=?", (light_name,))
        row = cursor.fetchone()
        if row:
            new_cycle = row['cycle_time'] + extended_time
            cursor.execute("UPDATE traffic_lights SET cycle_time=? WHERE name=?", (new_cycle, light_name))
            conn.commit()
            return jsonify({"status": "success", "new_cycle_time": new_cycle})
        else:
            return jsonify({"status": "error", "message": "找不到該路口號誌"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/infrastructure/all', methods=['GET'])
def get_infrastructure():
    """一次性撈取常駐基礎設施"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM traffic_lights")
    lights = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM cctv_monitors")
    cctvs = [dict(r) for r in cursor.fetchall()]
    
    return jsonify({
        "status": "success",
        "data": {
            "traffic_lights": lights,
            "cctv_monitors": cctvs
        }
    })

if __name__ == '__main__':
    init_db()
    print("🚀 後端伺服器啟動，正在監聽 http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)
