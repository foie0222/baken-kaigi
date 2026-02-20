"""HRDB定数・コード変換モジュール."""

VENUE_CODE_MAP: dict[str, str] = {
    "01": "札幌",
    "02": "函館",
    "03": "福島",
    "04": "新潟",
    "05": "東京",
    "06": "中山",
    "07": "中京",
    "08": "阪神",
    "09": "京都",
    "10": "小倉",
}


def hrdb_to_race_id(opdt: str, rcoursecd: str, rno: str) -> str:
    """HRDBカラムから12桁のrace_idに変換する.

    Args:
        opdt: 開催日 (例: "20260214")
        rcoursecd: 競馬場コード (例: "05")
        rno: レース番号 (例: "05")

    Returns:
        12桁のrace_id (例: "202602140505")
    """
    return f"{opdt}{rcoursecd.zfill(2)}{rno.zfill(2)}"


def parse_race_id(race_id: str) -> tuple[str, str, str]:
    """12桁のrace_idをパースする.

    Args:
        race_id: 12桁のrace_id (例: "202602140511")

    Returns:
        (date, venue_code, race_number) のタプル
    """
    return race_id[:8], race_id[8:10], race_id[10:12]
