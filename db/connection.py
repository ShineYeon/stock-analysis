import os
from contextlib import contextmanager
import psycopg2
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


def get_db_config():
    """환경 변수에서 DB 접속 정보를 가져오는 함수"""
    return {
        "dbname": os.getenv("DB_NAME", "stock_analysis"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }


@contextmanager
def get_db_connection():
    """PostgreSQL 커넥션 관리를 위한 컨텍스트 매니저"""
    conn = None
    try:
        conn = psycopg2.connect(**get_db_config())
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ [DB Connection Error] {e}")
        raise e
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor():
    """커서 생성, 자동 커밋/롤백 및 자원 해제를 위한 컨텍스트 매니저"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor, conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ [DB Transaction Error] {e}")
            raise e
        finally:
            cursor.close()