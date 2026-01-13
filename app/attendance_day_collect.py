from typing import Dict, Any
import re
from datetime import timedelta

from .database_base import session
from .attendance_contract_query import ContractTimeAttendance
from .calc_work_classes4 import CalcTimeFactory
from .models import Attendance, Notification, Contract


def convert_time(str_value):
    if str_value == "":
        str_value = "00:00"
        return str_value
    else:
        return str_value


def get_notification_name(notification_code: str) -> str:
    notification_query = session.get(Notification, notification_code)
    return notification_query.NAME


def get_user_contract(contract_code: int) -> str:
    contract_query = session.get(Contract, contract_code)
    return contract_query.NAME


def collect_attendance_data(
    staff_id: int, from_day: str, to_day: str
) -> Dict[int, Dict[str, Any]]:
    """
    Collects attendance data from various sources and compiles it into a unified format.
    """
    # Placeholder for actual implementation
    attendance_data = []
    # Logic to collect data goes here
    contract_attendance_object = ContractTimeAttendance(
        staff_id=staff_id, filter_from_day=from_day, filter_to_day=to_day
    )
    contract_attendance_query = (
        contract_attendance_object.get_perfect_contract_attendance()
    )

    calc_time_factory = CalcTimeFactory()
    for record in contract_attendance_query:
        attendance_obj: Attendance = record.Attendance
        work_day = attendance_obj.WORKDAY.day

        attendance_data[work_day]["社員ID"] = attendance_obj.id
        # 開始時間
        attendance_data[work_day]["出勤"] = convert_time(attendance_obj.STARTTIME)
        # 終了時間
        attendance_data[work_day]["退勤"] = convert_time(attendance_obj.ENDTIME)
        # 申請(AM)
        attendance_data[work_day]["届出(AM)"] = get_notification_name(
            attendance_obj.NOTIFICATION
        )
        # 申請(PM)
        attendance_data[work_day]["届出(PM)"] = get_notification_name(
            attendance_obj.NOTIFICATION2
        )
        # 残業申請
        attendance_data[work_day]["残業申請"] = attendance_obj.OVERTIME
        # 備考
        attendance_data[work_day]["備考"] = attendance_obj.REMARK

        if record.StaffHolidayContract is None:
            setting_contract_worktime = record.WORKTIME
            setting_contract_off_time = record.WORKTIME
        else:
            setting_contract_worktime = record.StaffJobContract.PART_WORKTIME
            setting_contract_off_time = record.StaffHolidayContract.HOLIDAY_TIME

        attendance_data[work_day]["勤務形態"] = get_user_contract(
            record.StaffJobContract.CONTRACT_CODE
        )
        attendance_data[work_day]["契約労働時間"] = setting_contract_worktime
        attendance_data[work_day]["契約有休時間"] = setting_contract_off_time

        calculation_instance = calc_time_factory.get_instance(staff_id=staff_id)
        calculation_instance.set_data(
            c_work_time=setting_contract_worktime,
            c_holiday_time=setting_contract_off_time,
            sh_starttime=attendance_obj.STARTTIME,
            sh_endtime=attendance_obj.ENDTIME,
            notifications=(attendance_obj.NOTIFICATION, attendance_obj.NOTIFICATION2),
            sh_overtime=attendance_obj.OVERTIME,
            sh_holiday=attendance_obj.HOLIDAY,
        )

        # 実働時間
        actual_work_time = calculation_instance.get_actual_work_time()
        # actual_work_time_str = (
        #     re.sub(r"([0-9]{1,2}):([0-9]{2}):00", r"\1:\2", f"{actual_work_time}")
        #     if actual_work_time > timedelta(hours=0)
        #     else "0.0"
        # )
        attendance_data[work_day]["実働時間"] = actual_work_time

        # 実働時間(リアルタイム)
        real_time = calculation_instance.get_real_time()
        attendance_data[work_day]["リアル実働時間"] = real_time

    return attendance_data
