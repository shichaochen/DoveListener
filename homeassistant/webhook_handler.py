#!/usr/bin/env python3
"""
Home Assistant Webhook 处理器（Python 脚本版本）
用于接收 ESP32 发送的斑鸠检测事件并写入数据库

如果 Home Assistant 的 webhook 自动化不够灵活，可以使用这个 Python 脚本
通过 Home Assistant 的 Python Scripts 集成或 AppDaemon 运行
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = os.getenv('DOVE_DB_PATH', '/config/dove_events.db')

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dove_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            device_id TEXT,
            species TEXT,
            confidence REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def handle_webhook(data):
    """处理 webhook 数据"""
    try:
        event_type = data.get('event_type')
        if event_type != 'dove_detected':
            return {'success': False, 'error': 'Invalid event type'}
        
        # 写入数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO dove_events (timestamp, device_id, species, confidence)
            VALUES (?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            data.get('device_id', 'unknown'),
            data.get('species', 'dove'),
            data.get('confidence', 0.0)
        ))
        conn.commit()
        conn.close()
        
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # 测试
    init_database()
    test_data = {
        'event_type': 'dove_detected',
        'device_id': 'esp32_dove_detector_01',
        'confidence': 0.85,
        'timestamp': datetime.now().isoformat()
    }
    result = handle_webhook(test_data)
    print(json.dumps(result, indent=2))

