import pytest

from app.logics.logic_util import convert_to_dataframe
from app.logics.attendance_day_collect import format_rt


@pytest.mark.skip
def test_format_rt():
    assert format_rt(0.0) == "00:00"
    assert format_rt(3600) == "01:00"
    assert format_rt(-11880) == "-03:18"
    assert format_rt(13500) == "03:45"


# @pytest.mark.skip
def test_collect_attendance_data():
    from app.logics.attendance_day_collect import collect_attendance_data

    attendance_data = collect_attendance_data(
        staff_id=118, from_day="2025-12-01", to_day="2025-12-31"
    )
    # print(attendance_data)

    from app.server.mcp_tools_call import diet_collect_attendance_data

    diet_data = diet_collect_attendance_data(attendance_data)
    print(diet_data)

    conv_df = convert_to_dataframe(attendance_data)
    print(conv_df)


@pytest.mark.skip
def test_convert_to_dataframe():
    sample_data = {
        1: {"社員ID": 201, "出勤": "09:00", "退勤": "18:00"},
        2: {"社員ID": 201, "出勤": "09:15", "退勤": "18:05"},
        3: {"社員ID": 201, "出勤": "08:55", "退勤": "17:50"},
    }
    df = convert_to_dataframe(sample_data)
    print(df)
