import os
import calendar
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
import requests
from dotenv import load_dotenv
from tqdm import tqdm

# 1. 환경 변수 및 DB 설정
load_dotenv()

ECOS_KEY = os.getenv("ECOS_KEY")
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "stock_analysis"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

SERVICE_NAME = "StatisticSearch"
REQ_TYPE = "json"
LANG = "kr"


def get_monthly_ranges(start_dt: datetime, end_dt: datetime):
    """시작일부터 종료일까지 월별 날짜 구간(YYYYMMDD / YYYYMM) 생성"""
    ranges = []
    current_year = start_dt.year
    current_month = start_dt.month

    while (current_year, current_month) <= (end_dt.year, end_dt.month):
        _, last_day = calendar.monthrange(current_year, current_month)

        s_day = start_dt.day if (current_year == start_dt.year and current_month == start_dt.month) else 1
        e_day = min(last_day, end_dt.day) if (current_year == end_dt.year and current_month == end_dt.month) else last_day

        start_str = f"{current_year}{current_month:02d}{s_day:02d}"
        end_str = f"{current_year}{current_month:02d}{e_day:02d}"

        ranges.append((start_str, end_str))

        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1

    return ranges


def fetch_and_upsert(
    stat_code: str,
    cycle: str,
    start_dt: datetime,
    end_dt: datetime,
    table_name: str,
    value_col_name: str,
    value_type: type = float
):
    """
    ECOS API 데이터 수집 및 PostgreSQL 공통 UPSERT 적재 함수
    """
    if cycle == "M":
        date_ranges = [(start_dt.strftime("%Y%m"), end_dt.strftime("%Y%m"))]
    else:
        date_ranges = get_monthly_ranges(start_dt, end_dt)

    upsert_query = f"""
        INSERT INTO raw.{table_name} (
            date, stat_code, stat_name, item_code, item_name, cycle, unit_name, {value_col_name}
        ) VALUES %s
        ON CONFLICT (date, stat_code, item_code) 
        DO UPDATE SET 
            stat_name = EXCLUDED.stat_name,
            item_name = EXCLUDED.item_name,
            cycle = EXCLUDED.cycle,
            unit_name = EXCLUDED.unit_name,
            {value_col_name} = EXCLUDED.{value_col_name},
            created_at = CURRENT_TIMESTAMP;
    """

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    total_inserted = 0

    print(f"\n🚀 [{table_name} 적재 시작] {start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}")

    for start_str, end_str in tqdm(date_ranges, desc=f"{table_name} 수집"):
        url = f"https://ecos.bok.or.kr/api/{SERVICE_NAME}/{ECOS_KEY}/{REQ_TYPE}/{LANG}/1/5000/{stat_code}/{cycle}/{start_str}/{end_str}"

        try:
            res = requests.get(url, timeout=10)
            data = res.json()

            if "StatisticSearch" in data and "row" in data["StatisticSearch"]:
                rows = data["StatisticSearch"]["row"]
                insert_batch = []

                for row in rows:
                    raw_time = row.get("TIME", "")
                    if len(raw_time) == 8:
                        formatted_date = f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:]}"
                    elif len(raw_time) == 6:
                        formatted_date = f"{raw_time[:4]}-{raw_time[4:6]}-01"
                    else:
                        continue

                    raw_value = row.get("DATA_VALUE")
                    if raw_value is None or str(raw_value).strip() == "":
                        continue

                    try:
                        value = value_type(raw_value)
                    except (ValueError, TypeError):
                        continue

                    insert_batch.append((
                        formatted_date,
                        row.get("STAT_CODE"),
                        row.get("STAT_NAME"),
                        row.get("ITEM_CODE1"),
                        row.get("ITEM_NAME1"),
                        cycle,
                        row.get("UNIT_NAME"),
                        value
                    ))

                if insert_batch:
                    execute_values(cursor, upsert_query, insert_batch)
                    conn.commit()
                    total_inserted += len(insert_batch)

        except Exception as e:
            conn.rollback()
            print(f"\n[오류] {start_str}~{end_str} 수집 실패: {e}")

    cursor.close()
    conn.close()
    print(f"✅ [{table_name} 완료] 총 {total_inserted}건 적재 완료")


if __name__ == "__main__":
    now = datetime.now()

    # ===============================================
    #                   예시
    # ===============================================
    # 1. 환율 적재 (일별)
    fetch_and_upsert(
        stat_code="731Y001",
        cycle="D",
        start_dt=datetime(1964, 5, 4),
        end_dt=now,
        table_name="krw_exchange_rates",
        value_col_name="exchange_rate",
        value_type=float
    )

    # 2. 외환보유액 적재 (월별)
    fetch_and_upsert(
        stat_code="732Y001",
        cycle="M",
        start_dt=datetime(1971, 1, 1),
        end_dt=now,
        table_name="fx_reserves",
        value_col_name="amount",
        value_type=int
    )