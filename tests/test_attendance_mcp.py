from app.logics.attendance_collect_logic import get_attendance_details_logic


def test_get_attendance_details():
    mcp_result = get_attendance_details_logic(staff_id=201, target_month="2025-12")
    print(mcp_result)
