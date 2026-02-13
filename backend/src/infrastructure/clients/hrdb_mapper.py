"""HRDB CSVカラム→DynamoDBアイテム変換."""


def _make_race_id(opdt: str, rcoursecd: str, rno: str) -> str:
    """レースIDを生成する."""
    return f"{opdt}_{rcoursecd}_{int(rno):02d}"


def map_racemst_to_race_item(row: dict) -> dict:
    """RACEMSTレコードをracesテーブルアイテムに変換する."""
    opdt = row["OPDT"]
    race_id = _make_race_id(opdt, row["RCOURSECD"], row["RNO"])
    return {
        "race_date": opdt,
        "race_id": race_id,
        "race_number": int(row.get("RNO", "0")),
        "race_name": row.get("RNAME", ""),
        "venue_code": row.get("RCOURSECD", ""),
        "track_code": row.get("TRACKCD", ""),
        "distance": int(row.get("KYORI", "0")),
        "track_condition": row.get("BABA", ""),
        "horse_count": int(row.get("TOSU", "0")),
        "grade_code": row.get("GRADECD", ""),
        "condition_code": row.get("JYOKENCD", ""),
        "start_time": row.get("HTIME", ""),
    }


def map_racedtl_to_runner_item(row: dict) -> dict:
    """RACEDTLレコードをrunnersテーブルアイテムに変換する."""
    opdt = row["OPDT"]
    race_id = _make_race_id(opdt, row["RCOURSECD"], row["RNO"])
    return {
        "race_id": race_id,
        "race_date": opdt,
        "horse_number": int(row.get("UMABAN", "0")),
        "horse_name": row.get("BAMEI", ""),
        "horse_id": row.get("BLDNO", ""),
        "jockey_id": row.get("JKYCD", ""),
        "jockey_name": row.get("JKYNAME", ""),
        "trainer_id": row.get("TRNRCD", ""),
        "odds": row.get("ODDS", ""),
        "popularity": int(row.get("NINKI", "0")),
        "waku_ban": int(row.get("WAKUBAN", "0")),
        "weight_carried": row.get("FUTAN", ""),
        "finish_position": int(row.get("KAKUTEI", "0")),
        "time": row.get("TIME", ""),
        "last_3f": row.get("AGARI3F", ""),
    }


def map_horse_to_horse_item(row: dict) -> dict:
    """HORSEレコードをhorsesテーブルアイテムに変換する."""
    return {
        "horse_id": row.get("BLDNO", ""),
        "sk": "info",
        "horse_name": row.get("BAMEI", ""),
        "sire_name": row.get("FTNAME", ""),
        "dam_name": row.get("MTNAME", ""),
        "broodmare_sire": row.get("BMSTNAME", ""),
        "birth_year": row.get("BNEN", ""),
        "sex": row.get("SEX", ""),
        "coat_color": row.get("KEIRO", ""),
    }


def map_jky_to_jockey_item(row: dict) -> dict:
    """JKYレコードをjockeysテーブルアイテムに変換する."""
    return {
        "jockey_id": row.get("JKYCD", ""),
        "sk": "info",
        "jockey_name": row.get("JKYNAME", ""),
        "jockey_name_kana": row.get("JKYKANA", ""),
        "affiliation": row.get("SHOZOKU", ""),
    }


def map_trnr_to_trainer_item(row: dict) -> dict:
    """TRNRレコードをtrainersテーブルアイテムに変換する."""
    return {
        "trainer_id": row.get("TRNRCD", ""),
        "sk": "info",
        "trainer_name": row.get("TRNRNAME", ""),
        "trainer_name_kana": row.get("TRNRKANA", ""),
        "affiliation": row.get("SHOZOKU", ""),
    }
