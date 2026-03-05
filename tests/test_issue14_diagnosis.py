import pytest
from unittest.mock import MagicMock, patch
from datetime import timedelta, date
from app.logics.attendance_day_collect import collect_attendance_data

@patch('app.logics.attendance_day_collect.ContractTimeAttendance')
@patch('app.logics.attendance_day_collect.CalcTimeFactory')
@patch('app.logics.attendance_day_collect.get_notification_name')
@patch('app.logics.attendance_day_collect.get_user_contract')
def test_diagnosis_scenarios(mock_get_contract, mock_get_notif, mock_factory, mock_cta):
    # Setup
    mock_db = MagicMock()
    mock_get_contract.return_value = "常勤"
    mock_get_notif.return_value = None
    
    mock_calc = MagicMock()
    mock_factory.return_value.get_instance.return_value = mock_calc
    
    # 共通の設定
    mock_calc.calc_normal_rest.return_value = timedelta(hours=1)
    mock_calc.get_over_time.return_value = 0.0

    # --- Case 1: timeoff_not_pre_reflected (Clock == Contract, TimeOff > 0) ---
    # 契約8h, 打刻8h, 時間休1h -> モード: contract_based, パターン: timeoff_not_pre_reflected
    mock_calc.calc_base_work_time.return_value = timedelta(hours=9) # 9h - 1h(rest) = 8h
    mock_calc.get_actual_work_time.return_value = timedelta(hours=8)
    mock_calc.get_time_off_hour.return_value = timedelta(hours=1)
    mock_calc.get_real_time.return_value = 7 * 3600.0
    
    attendance_obj1 = MagicMock()
    attendance_obj1.WORKDAY = date(2026, 1, 1)
    attendance_obj1.ONCALL = "0"
    attendance_obj1.STARTTIME = "09:00"
    attendance_obj1.ENDTIME = "18:00"
    attendance_obj1.NOTIFICATION = "10" # 1h時間休
    attendance_obj1.NOTIFICATION2 = ""
    attendance_obj1.OVERTIME = "0"
    
    mock_record1 = MagicMock()
    mock_record1.Attendance = attendance_obj1
    mock_record1.StaffHolidayContract = None
    mock_record1.WORKTIME = 8
    
    # --- Case 2: timeoff_pre_reflected (Clock < Contract, TimeOff > 0) ---
    # 契約8h, 打刻7h, 時間休1h -> モード: clock_based, パターン: timeoff_pre_reflected
    mock_calc2 = MagicMock()
    mock_calc2.calc_base_work_time.return_value = timedelta(hours=8) # 8h - 1h(rest) = 7h
    mock_calc2.calc_normal_rest.return_value = timedelta(hours=1)
    mock_calc2.get_actual_work_time.return_value = timedelta(hours=7)
    mock_calc2.get_time_off_hour.return_value = timedelta(hours=1)
    mock_calc2.get_real_time.return_value = 7 * 3600.0
    mock_calc2.get_over_time.return_value = 0.0
    
    attendance_obj2 = MagicMock()
    attendance_obj2.WORKDAY = date(2026, 1, 2)
    attendance_obj2.ONCALL = "0"
    attendance_obj2.STARTTIME = "10:00"
    attendance_obj2.ENDTIME = "18:00"
    attendance_obj2.NOTIFICATION = "10"
    attendance_obj2.NOTIFICATION2 = ""
    attendance_obj2.OVERTIME = "0"
    
    mock_record2 = MagicMock()
    mock_record2.Attendance = attendance_obj2
    mock_record2.StaffHolidayContract = None
    mock_record2.WORKTIME = 8

    # --- Case 3: OVERTIME_NEGATIVE ---
    # 残業申請ありだが、実働が契約未満
    mock_calc3 = MagicMock()
    mock_calc3.calc_base_work_time.return_value = timedelta(hours=7) # 7h - 1h(rest) = 6h
    mock_calc3.calc_normal_rest.return_value = timedelta(hours=1)
    mock_calc3.get_actual_work_time.return_value = timedelta(hours=6)
    mock_calc3.get_time_off_hour.return_value = timedelta(0)
    mock_calc3.get_real_time.return_value = 6 * 3600.0
    mock_calc3.get_over_time.return_value = -2.0 * 3600.0 # 6h - 8h = -2h
    
    attendance_obj3 = MagicMock()
    attendance_obj3.WORKDAY = date(2026, 1, 3)
    attendance_obj3.ONCALL = "0"
    attendance_obj3.STARTTIME = "09:00"
    attendance_obj3.ENDTIME = "16:00"
    attendance_obj3.NOTIFICATION = ""
    attendance_obj3.NOTIFICATION2 = ""
    attendance_obj3.OVERTIME = "1"
    
    mock_record3 = MagicMock()
    mock_record3.Attendance = attendance_obj3
    mock_record3.StaffHolidayContract = None
    mock_record3.WORKTIME = 8

    # Mock return list
    mock_cta.return_value.get_perfect_contract_attendance.return_value.all.return_value = [mock_record1, mock_record2, mock_record3]
    
    # CalcTimeFactory.get_instance must return different mocks for different staff_id? 
    # No, collect_attendance_data uses same staff_id for all records.
    # So we need to make get_instance return side_effect.
    mock_factory.return_value.get_instance.side_effect = [mock_calc, mock_calc2, mock_calc3]

    result = collect_attendance_data(staff_id=1, from_day="2026-01-01", to_day="2026-01-31", db_session=mock_db)
    
    # Verify Case 1
    assert result[1]["実働時間算出モード"] == "contract_based"
    assert result[1]["時間休入力パターン"] == "timeoff_not_pre_reflected"
    assert "時間休を事前反映しない打刻の可能性が高く、実働時間は契約ベースです。" in result[1]["診断"]

    # Verify Case 2
    assert result[2]["実働時間算出モード"] == "clock_based"
    assert result[2]["時間休入力パターン"] == "timeoff_pre_reflected"
    assert "時間休を事前に反映した打刻の可能性が高く、実働時間は打刻ベース（退勤-出勤-通常休憩）で算出されています。" in result[2]["診断"]

    # Verify Case 3
    assert result[3]["実働時間算出モード"] == "clock_based"
    assert "OVERTIME_NEGATIVE" in result[3]["診断フラグ"]
    assert "残業申請ありですが時間外がマイナスです。" in result[3]["診断"]
