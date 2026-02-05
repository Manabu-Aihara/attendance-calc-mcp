import json
import time
from typing import Dict, Any
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.database.database_base import session
from app.database.attendance_contract_query import ContractTimeAttendance
from app.caluculation.calc_work_classes_4_mcp import CalcTimeFactory
from app.models.models import Attendance, Notification, Contract


def convert_time(str_value):
    if str_value == "":
        str_value = "00:00"
        return str_value
    else:
        return str_value


def get_notification_name(notification_code: str, db_session: Session) -> str:
    if notification_code != "":
        notification_query = db_session.get(Notification, notification_code)
        return notification_query.NAME


def get_user_contract(contract_code: int, db_session: Session) -> str:
    contract_query = db_session.get(Contract, contract_code)
    return contract_query.NAME


def collect_attendance_data(
    staff_id: int, from_day: str, to_day: str, db_session: Session = session
) -> Dict[Dict[str, int | str | float], Dict[int, Dict[str, Any]]]:
    """
    Collects attendance data from various sources and compiles it into a unified format.
    """
    # Placeholder for actual implementation
    attendance_data = {}
    # Logic to collect data goes here

    contract_attendance_object = ContractTimeAttendance(
        staff_id=staff_id, filter_from_day=from_day, filter_to_day=to_day
    )
    contract_attendance_query = (
        contract_attendance_object.get_perfect_contract_attendance()
    )
    records = contract_attendance_query.all()

    calc_time_factory = CalcTimeFactory()

    attendance_data["社員ID"] = staff_id
    # 月途中の契約変更を想定しない場合、最初のレコードから取得
    attendance_data["勤務形態"] = get_user_contract(
        records[0].StaffJobContract.CONTRACT_CODE, db_session
    )
    if records[0].StaffHolidayContract is not None:
        attendance_data["契約労働時間"] = records[0].StaffJobContract.PART_WORKTIME
        attendance_data["契約有休時間"] = records[0].StaffHolidayContract.HOLIDAY_TIME
    else:
        attendance_data["契約労働時間"] = records[0].WORKTIME
        attendance_data["契約有休時間"] = records[0].WORKTIME

    for record in records:
        attendance_obj: Attendance = record.Attendance
        print(f"Work Day: {attendance_obj.WORKDAY}, ID: {attendance_obj.id}")
        work_day = attendance_obj.WORKDAY.day

        # if work_day not in attendance_data:
        attendance_data[work_day] = {}

        # オンコール
        attendance_data[work_day]["オンコール"] = attendance_obj.ONCALL
        # 開始時間
        attendance_data[work_day]["出勤"] = convert_time(attendance_obj.STARTTIME)
        # 終了時間
        attendance_data[work_day]["退勤"] = convert_time(attendance_obj.ENDTIME)
        # 申請(AM)
        attendance_data[work_day]["届出(AM)"] = get_notification_name(
            attendance_obj.NOTIFICATION, db_session
        )
        # 申請(PM)
        attendance_data[work_day]["届出(PM)"] = get_notification_name(
            attendance_obj.NOTIFICATION2, db_session
        )
        # 残業申請
        attendance_data[work_day]["残業申請"] = attendance_obj.OVERTIME

        # if record.StaffHolidayContract is None:
        #     setting_contract_worktime = record.WORKTIME
        #     setting_contract_off_time = record.WORKTIME
        # else:
        #     setting_contract_worktime = record.StaffJobContract.PART_WORKTIME
        #     setting_contract_off_time = record.StaffHolidayContract.HOLIDAY_TIME

        # attendance_data[work_day]["勤務形態"] = get_user_contract(
        #     record.StaffJobContract.CONTRACT_CODE, db_session
        # )
        # attendance_data[work_day]["契約労働時間"] = setting_contract_worktime
        # attendance_data[work_day]["契約有休時間"] = setting_contract_off_time

        calculation_instance = calc_time_factory.get_instance(staff_id=staff_id)
        calculation_instance.set_data(
            contract_work_time=attendance_data["契約労働時間"],
            contract_holiday_time=attendance_data["契約有休時間"],
            start_time=attendance_obj.STARTTIME,
            end_time=attendance_obj.ENDTIME,
            notifications=(attendance_obj.NOTIFICATION, attendance_obj.NOTIFICATION2),
            overtime_check=attendance_obj.OVERTIME,
            holiday_work=attendance_obj.HOLIDAY,
        )

        input_work_time = calculation_instance.calc_base_work_time()
        normal_rest_time = calculation_instance.calc_normal_rest(input_work_time)
        normal_rest_time_str = (
            re.sub(r"([0-9]{1,2}):([0-9]{2}):00", r"\1:\2", f"{normal_rest_time}")
            if normal_rest_time > timedelta(hours=0)
            else "0.0"
        )
        attendance_data[work_day]["通常休憩時間"] = normal_rest_time_str

        # 時間休の有無
        attendance_data[work_day]["時間休"] = (
            "1"
            if attendance_obj.NOTIFICATION in calculation_instance.n_time_off_list
            or attendance_obj.NOTIFICATION2 in calculation_instance.n_time_off_list
            else "0"
        )

        # 実働時間
        actual_work_time = calculation_instance.get_actual_work_time()
        actual_work_time_str = (
            re.sub(r"([0-9]{1,2}):([0-9]{2}):00", r"\1:\2", f"{actual_work_time}")
            if actual_work_time > timedelta(hours=0)
            else "0.0"
        )
        attendance_data[work_day]["実働時間"] = actual_work_time_str

        # 実働時間(リアルタイム)
        real_time = calculation_instance.get_real_time()
        real_time_str = (
            re.sub(r"([0-9]{1,2}):([0-9]{2}):00", r"\1:\2", f"{real_time}")
            if real_time > timedelta(hours=0)
            else "0.0"
        )
        attendance_data[work_day]["リアル実働時間"] = real_time_str

        # 残業時間
        over_work_time = calculation_instance.get_over_time()
        over_work_time_str = (
            re.sub(r"([0-9]{1,2}):([0-9]{2}):00", r"\1:\2", f"{over_work_time}")
            if over_work_time > timedelta(hours=0)
            else "0.0"
        )
        attendance_data[work_day]["時間外"] = over_work_time_str

        # 備考
        attendance_data[work_day]["備考"] = attendance_obj.REMARK

    return attendance_data
