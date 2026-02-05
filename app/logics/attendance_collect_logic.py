# attendance_logic.py (新規作成)
from datetime import datetime, timedelta
import calendar
from typing import Any, Dict, List


from .attendance_day_collect import collect_attendance_data

"""
指定された社員IDと対象月の勤怠詳細を取得します。

:param staff_id: 社員ID
:param target_month: 対象月 (YYYY-MM)
:return: 勤怠詳細の計算過程
"""


def get_attendance_details_logic(staff_id: int, target_month: str) -> Dict[str, Any]:
    """ツールのコアロジック(テスト可能)"""
    year, month = map(int, target_month.split("-"))
    from_day = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    to_day = f"{year}-{month:02d}-{last_day}"

    try:
        data = collect_attendance_data(staff_id, from_day, to_day)
        # timedelta等をシリアライズ可能な形式に変換
        serializable_data = {}
        for day, record in data.items():
            serializable_data[day] = {}
            for key, value in record.items():
                if isinstance(value, timedelta):
                    # timedeltaを時間数(float)に変換
                    serializable_data[day][key] = value.total_seconds() / 3600
                elif callable(value):
                    # 関数オブジェクトはスキップ
                    continue
                else:
                    serializable_data[day][key] = value

        return {"status": "success", "data": serializable_data}
    except Exception as e:
        return {"status": "error", "message": str(e)}
