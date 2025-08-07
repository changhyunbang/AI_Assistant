"""
데이터베이스 유틸리티 모듈 (Container 기반)
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
        """데이터베이스 초기화 (Container 기반으로 업데이트)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 기존 테이블 구조 확인
            cursor.execute("PRAGMA table_info(chatbots)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 테이블이 없으면 생성
            if not columns:
                # 새 테이블 생성 (container 기반)
                cursor.execute('''
                    CREATE TABLE chatbots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chatbotname TEXT NOT NULL UNIQUE,
                        containername TEXT,
                        description TEXT,
                        index_status BOOLEAN DEFAULT FALSE,
                        index_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                print("✅ 새 chatbots 테이블이 생성되었습니다. (Container 기반)")
            
            else:
                # 기존 테이블 업데이트 (folder -> container 마이그레이션)
                migration_needed = []
                
                if 'containername' not in columns:
                    migration_needed.append('containername')
                
                if 'index_name' not in columns:
                    migration_needed.append('index_name')
                
                # 마이그레이션 수행
                for column in migration_needed:
                    if column == 'containername':
                        cursor.execute('ALTER TABLE chatbots ADD COLUMN containername TEXT')
                        print("✅ containername 컬럼이 추가되었습니다.")
                        
                        # foldername이 있으면 containername으로 데이터 복사
                        if 'foldername' in columns:
                            cursor.execute('UPDATE chatbots SET containername = foldername WHERE containername IS NULL')
                            print("✅ foldername 데이터가 containername으로 복사되었습니다.")
                    
                    elif column == 'index_name':
                        cursor.execute('ALTER TABLE chatbots ADD COLUMN index_name TEXT')
                        print("✅ index_name 컬럼이 추가되었습니다.")
                
                # 더 이상 필요 없는 foldername 컬럼 제거 (SQLite에서는 직접 삭제 불가능하므로 생략)
                # 실제 운영환경에서는 별도의 마이그레이션 스크립트로 처리
            
            conn.commit()
    
    def get_chatbot_count(self) -> int:
        """등록된 챗봇 수 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chatbots")
            return cursor.fetchone()[0]

# 전역 데이터베이스 인스턴스
chatbot_db = ChatbotDatabase()

def add_chatbot(chatbot_name: str, container_name: str = None, description: str = None) -> bool:
    """새 챗봇 추가 (Container 기반)"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chatbots (chatbotname, containername, description, index_status, index_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (chatbot_name, container_name, description, False, None))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        # 중복된 챗봇 이름
        return False
    except Exception as e:
        print(f"챗봇 추가 오류: {e}")
        return False

def get_all_chatbots() -> List[Dict]:
    """모든 챗봇 정보 조회 (Container 기반)"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 컬럼 존재 여부 확인
        cursor.execute("PRAGMA table_info(chatbots)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # containername이 없으면 foldername을 사용
        if 'containername' in columns:
            cursor.execute('''
                SELECT id, chatbotname, containername, description, index_status, 
                       index_name, created_at, updated_at
                FROM chatbots 
                ORDER BY created_at DESC
            ''')
        else:
            # 호환성을 위해 foldername을 containername으로 반환
            cursor.execute('''
                SELECT id, chatbotname, foldername as containername, description, index_status, 
                       index_name, created_at, updated_at
                FROM chatbots 
                ORDER BY created_at DESC
            ''')
        
        return [dict(row) for row in cursor.fetchall()]

def get_chatbot_by_id(chatbot_id: int) -> Optional[Dict]:
    """ID로 특정 챗봇 정보 조회 (Container 기반)"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 컬럼 존재 여부 확인
        cursor.execute("PRAGMA table_info(chatbots)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'containername' in columns:
            cursor.execute('''
                SELECT id, chatbotname, containername, description, index_status, 
                       index_name, created_at, updated_at
                FROM chatbots 
                WHERE id = ?
            ''', (chatbot_id,))
        else:
            cursor.execute('''
                SELECT id, chatbotname, foldername as containername, description, index_status, 
                       index_name, created_at, updated_at
                FROM chatbots 
                WHERE id = ?
            ''', (chatbot_id,))
        
        result = cursor.fetchone()
        return dict(result) if result else None

def get_chatbot_by_name(chatbot_name: str) -> Optional[Dict]:
    """이름으로 특정 챗봇 정보 조회 (Container 기반)"""
    with sqlite3.connect(chatbot_db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 컬럼 존재 여부 확인
        cursor.execute("PRAGMA table_info(chatbots)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'containername' in columns:
            cursor.execute('''
                SELECT id, chatbotname, containername, description, index_status, 
                       index_name, created_at, updated_at
                FROM chatbots 
                WHERE chatbotname = ?
            ''', (chatbot_name,))
        else:
            cursor.execute('''
                SELECT id, chatbotname, foldername as containername, description, index_status, 
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

def update_chatbot_container(chatbot_id: int, container_name: str) -> bool:
    """챗봇 컨테이너명 업데이트"""
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            
            # 컬럼 존재 여부 확인
            cursor.execute("PRAGMA table_info(chatbots)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'containername' in columns:
                cursor.execute('''
                    UPDATE chatbots 
                    SET containername = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (container_name, chatbot_id))
            else:
                # 호환성을 위해 foldername 업데이트
                cursor.execute('''
                    UPDATE chatbots 
                    SET foldername = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (container_name, chatbot_id))
            
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"컨테이너명 업데이트 오류: {e}")
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

def migrate_folder_to_container():
    """
    기존 foldername을 containername으로 마이그레이션하는 유틸리티 함수
    """
    try:
        with sqlite3.connect(chatbot_db.db_path) as conn:
            cursor = conn.cursor()
            
            # 컬럼 존재 여부 확인
            cursor.execute("PRAGMA table_info(chatbots)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'foldername' in columns and 'containername' in columns:
                # foldername 데이터를 containername으로 복사 (containername이 NULL인 경우만)
                cursor.execute('''
                    UPDATE chatbots 
                    SET containername = foldername 
                    WHERE containername IS NULL AND foldername IS NOT NULL
                ''')
                
                updated_rows = cursor.rowcount
                conn.commit()
                
                print(f"✅ {updated_rows}개 레코드의 foldername이 containername으로 마이그레이션되었습니다.")
                return True
            else:
                print("마이그레이션이 필요하지 않습니다.")
                return False
                
    except Exception as e:
        print(f"마이그레이션 오류: {e}")
        return False

# 호환성을 위한 별칭 함수들
def update_chatbot_folder(chatbot_id: int, folder_name: str) -> bool:
    """폴더명 업데이트 (호환성을 위한 별칭)"""
    return update_chatbot_container(chatbot_id, folder_name)

if __name__ == "__main__":
    print("🧪 데이터베이스 유틸리티 테스트 시작")
    
    # 데이터베이스 상태 확인
    total_chatbots = chatbot_db.get_chatbot_count()
    print(f"등록된 챗봇 수: {total_chatbots}")
    
    if total_chatbots > 0:
        chatbots = get_all_chatbots()
        print("등록된 챗봇 목록:")
        for chatbot in chatbots:
            print(f"  - ID: {chatbot['id']}")
            print(f"    이름: {chatbot['chatbotname']}")
            print(f"    컨테이너: {chatbot.get('containername', 'N/A')}")
            print(f"    인덱스 상태: {chatbot['index_status']}")
            print()
    
    # 마이그레이션 실행 (필요한 경우)
    migrate_folder_to_container()
    
    print("✅ 데이터베이스 유틸리티 테스트 완료")