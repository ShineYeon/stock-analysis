from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any, Type, TypeVar

T = TypeVar("T")


@dataclass
class ExchangeRate:
    """raw.krw_exchange_rates 매핑 모델"""
    date: str
    stat_code: str
    stat_name: Optional[str]
    item_code: str
    item_name: Optional[str]
    cycle: str
    unit_name: Optional[str]
    exchange_rate: float

    def to_tuple(self) -> Tuple:
        return (
            self.date, self.stat_code, self.stat_name, 
            self.item_code, self.item_name, self.cycle, 
            self.unit_name, self.exchange_rate
        )


@dataclass
class FXReserve:
    """raw.fx_reserves 매핑 모델"""
    date: str
    stat_code: str
    stat_name: Optional[str]
    item_code: str
    item_name: Optional[str]
    cycle: str
    unit_name: Optional[str]
    amount: int

    def to_tuple(self) -> Tuple:
        return (
            self.date, self.stat_code, self.stat_name, 
            self.item_code, self.item_name, self.cycle, 
            self.unit_name, self.amount
        )


@dataclass
class BOKBaseRate:
    """raw.bok_base_rates 매핑 모델"""
    date: str
    stat_code: str
    stat_name: Optional[str]
    item_code: str
    item_name: Optional[str]
    cycle: str
    unit_name: Optional[str]
    base_rate: float

    def to_tuple(self) -> Tuple:
        return (
            self.date, self.stat_code, self.stat_name, 
            self.item_code, self.item_name, self.cycle, 
            self.unit_name, self.base_rate
        )


@dataclass
class KTBYield:
    """raw.ktb_yields 매핑 모델"""
    date: str
    stat_code: str
    stat_name: Optional[str]
    item_code: str
    item_name: Optional[str]
    cycle: str
    unit_name: Optional[str]
    yield_rate: float

    def to_tuple(self) -> Tuple:
        return (
            self.date, self.stat_code, self.stat_name, 
            self.item_code, self.item_name, self.cycle, 
            self.unit_name, self.yield_rate
        )


# --------------------------------------------------
# API 파싱 공통 헬퍼 함수
# --------------------------------------------------
def parse_ecos_row(
    model_cls: Type[T], 
    row: Dict[str, Any], 
    cycle: str, 
    value_field_name: str, 
    value_type: type = float
) -> Optional[T]:
    """ECOS API JSON row 단건을 파싱하여 모델 객체로 변환 (유효하지 않은 데이터는 None 반환)"""
    raw_time = row.get("TIME", "")
    
    # 날짜 포맷팅 (YYYYMMDD -> YYYY-MM-DD / YYYYMM -> YYYY-MM-01)
    if len(raw_time) == 8:
        formatted_date = f"{raw_time[:4]}-{raw_time[4:6]}-{raw_time[6:]}"
    elif len(raw_time) == 6:
        formatted_date = f"{raw_time[:4]}-{raw_time[4:6]}-01"
    else:
        return None

    raw_value = row.get("DATA_VALUE")
    if raw_value is None or str(raw_value).strip() == "":
        return None

    try:
        if value_type == int:
            parsed_value = int(float(raw_value))
        else:
            parsed_value = float(raw_value)
    except (ValueError, TypeError):
        return None

    kwargs = {
        "date": formatted_date,
        "stat_code": row.get("STAT_CODE", ""),
        "stat_name": row.get("STAT_NAME"),
        "item_code": row.get("ITEM_CODE1", ""),
        "item_name": row.get("ITEM_NAME1"),
        "cycle": cycle,
        "unit_name": row.get("UNIT_NAME"),
        value_field_name: parsed_value
    }
    
    return model_cls(**kwargs)