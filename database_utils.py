"""
데이터베이스 유틸리티 모듈
챗봇 정보를 SQLite 데이터베이스에 저장하고 관리합니다.
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

class ChatbotDatabase:
    def __init__(self, db_path: str = "chatbots.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 기존 테이블 구조 확인
            cursor.execute("PRAGMA table_info(chatbots)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 테이블이 없거나 index_name 컬럼이 없으면 생성/업데이트
            if not columns:
                # 새 테이블 생성
                cursor.execute('''
                    CREATE TABLE chatbots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chatbotname TEXT NOT NULL UNIQUE,
                        foldername TEXT,
                        description TEXT,
                        index_status BOOLEAN DEFAULT FALSE,
                        index_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("✅ 새 chatbots 테이블이 생성되었습니다.")
            
            elif 'index_name' not in columns:
                # index_name 컬럼 추가
                cursor.execute('ALTER TABLE chatbots ADD COLUMN index_name TEXT')
                print("✅ index_name 컬럼이 추가되었습니다.")
            
            conn.commit()
    
    def get_chatbot_count(self) -> int:
        """등록된 챗봇 수 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chatbots")
            return cursor.fetchone()[0]

# 전역 데이터베이스 인스턴스
chatbot_db = ChatbotDatabase()

def add_chatbot(chatbot_name: str, folder_name: str = None, description: str = None) -> bool:
    """새 챗봇 추가"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chatbots (chatbotname, foldername, description, index_status, index_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (chatbot_name, folder_name, description, False, None))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # 중복된 챗봇 이름
        return False
    except Exception as e:
        print(f"챗봇 추가 오류: {e}")
        return False

def get_all_chatbots() -> List[Dict]:
    """모든 챗봇 정보 조회"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, chatbotname, foldername, description, index_status, 
                   index_name, created_at, updated_at
            FROM chatbots 
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_chatbot_by_id(chatbot_id: int) -> Optional[Dict]:
    """ID로 특정 챗봇 정보 조회"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, chatbotname, foldername, description, index_status, 
                   index_name, created_at, updated_at
            FROM chatbots 
            WHERE id = ?
        ''', (chatbot_id,))
        result = cursor.fetchone()
        return dict(result) if result else None

def get_chatbot_by_name(chatbot_name: str) -> Optional[Dict]:
    """이름으로 특정 챗봇 정보 조회"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, chatbotname, foldername, description, index_status, 
                   index_name, created_at, updated_at
            FROM chatbots 
            WHERE chatbotname = ?
        ''', (chatbot_name,))
        result = cursor.fetchone()
        return dict(result) if result else None

def update_chatbot_index(chatbot_id: int, index_status: bool, index_name: str = None) -> bool:
    """챗봇 인덱스 상태 및 인덱스명 업데이트"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chatbots 
                SET index_status = ?, index_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (index_status, index_name, chatbot_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"인덱스 상태 업데이트 오류: {e}")
        return False

def update_chatbot_folder(chatbot_id: int, folder_name: str) -> bool:
    """챗봇 폴더명 업데이트"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chatbots 
                SET foldername = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (folder_name, chatbot_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"폴더명 업데이트 오류: {e}")
        return False

def delete_chatbot(chatbot_id: int) -> bool:
    """챗봇 삭제"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chatbots WHERE id = ?', (chatbot_id,))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"챗봇 삭제 오류: {e}")
        return False