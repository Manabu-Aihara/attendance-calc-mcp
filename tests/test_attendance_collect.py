from app.logics.attendance_collect_logic import get_attendance_details_logic
from app.logics.logic_util import convert_to_dataframe


def test_get_attendance_details():
    mcp_result = get_attendance_details_logic(staff_id=201, target_month="2025-12")
    print(mcp_result)


def test_convert_to_dataframe():
    sample_data = {
        1: {"社員ID": 201, "出勤": "09:00", "退勤": "18:00"},
        2: {"社員ID": 201, "出勤": "09:15", "退勤": "18:05"},
        3: {"社員ID": 201, "出勤": "08:55", "退勤": "17:50"},
    }
    df = convert_to_dataframe(sample_data)
    print(df)
