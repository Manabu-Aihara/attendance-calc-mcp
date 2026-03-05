import math
from typing import Dict, Any
import re
from datetime import timedelta

from sqlalchemy.orm import Session

from app.database.database_base import session
from app.database.attendance_contract_query import ContractTimeAttendance
from app.calculation.calc_work_classes_4_mcp import CalcTimeFactory
from app.models.models import Attendance, Notification, Contract


def convert_time(str_value):
    if str_value == "":
        str_value = "00:00"
        return str_value
    else:
        return str_value


def get_notification_name(notification_code: str, db_session: Session) -> str | None:
    if notification_code != "":
        notification_query = db_session.get(Notification, notification_code)
        return notification_query.NAME
    else:
        return None


def get_user_contract(contract_code: int, db_session: Session) -> str:
    contract_query = db_session.get(Contract, contract_code)
    return contract_query.NAME


def convert_time_to_str(time_value: timedelta) -> str:
    pattern = r"([0-9]{1,2}):([0-9]{2}):00"
    # re.subで HH:MM 形式にする
    match = re.search(pattern, time_value.__str__())
    if match:
        # グループ1(時)とグループ2(分)を取り出す
        h = match.group(1)
        m = match.group(2)
        # zfill(2)で1桁の場合に0埋めする
        time_value_str = f"{h.zfill(2)}:{m}"
    return time_value_str


def timedelta_to_hhmm(time_value: timedelta) -> str:
    total_seconds = int(time_value.total_seconds())
    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    return f"{sign}{h:02d}:{m:02d}"


"""
    @param a: 比較する timedelta オブジェクト
    @param b: 比較する timedelta オブジェクト
    @param tolerance_seconds: 許容する秒数の差（デフォルトは60秒）
    @return: a と b の差が tolerance_seconds 秒以内であれば True を返し、それ以外は False を返す
"""


def timedelta_eq(a: timedelta, b: timedelta, tolerance_seconds: int = 60) -> bool:
    return abs(a.total_seconds() - b.total_seconds()) <= tolerance_seconds


def timedelta_gt(a: timedelta, b: timedelta, tolerance_seconds: int = 60) -> bool:
    return a.total_seconds() >= (b.total_seconds() - tolerance_seconds)


def timedelta_lt(a: timedelta, b: timedelta, tolerance_seconds: int = 60) -> bool:
    return a.total_seconds() < (b.total_seconds() - tolerance_seconds)


# 秒数を HH:MM に変換する処理を追加
def format_rt(seconds: float) -> str:
    if seconds == 0.0:
        return "00:00"
    # //演算子は負の無限大方向に丸める（(-2.5 -> -3)）ため、切り上げには適しません。
    h = math.ceil(seconds / 3600) if seconds < 0 else int(seconds // 3600)
    # 演算子の結合順序について、Python では % より単項のマイナス - の方が優先度が高いので、たとえば -7 % 2 は (-7) % 2 と解釈されます。
    print(f"seconds % 3600 // 60: {(-seconds % 3600) // 60}")
    m = int((-seconds % 3600) // 60) if seconds < 0 else int((seconds % 3600) // 60)
    # print(f"h: {h}, m: {m}")
    return f"{h:03d}:{m:02d}" if seconds < 0 else f"{h:02d}:{m:02d}"


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

    part_work_time = timedelta(0)
    part_holiday_time = timedelta(0)
    regular_work_time = timedelta(0)
    try:
        if records[0].StaffHolidayContract is not None:
            part_work_time = timedelta(hours=records[0].StaffJobContract.PART_WORKTIME)
            attendance_data["契約労働時間"] = convert_time_to_str(part_work_time)
            part_holiday_time = timedelta(
                hours=records[0].StaffHolidayContract.HOLIDAY_TIME
            )
            attendance_data["契約有休時間"] = convert_time_to_str(part_holiday_time)
        else:
            regular_work_time = timedelta(hours=records[0].WORKTIME)
            attendance_data["契約労働時間"] = convert_time_to_str(regular_work_time)
            attendance_data["契約有休時間"] = convert_time_to_str(regular_work_time)
    except TypeError as e:
        raise TypeError("契約時間の取得に失敗しました。") from e

    for record in records:
        attendance_obj: Attendance = record.Attendance
        print(f"Work Day: {attendance_obj.WORKDAY}, ID: {attendance_obj.id}")
        work_day = attendance_obj.WORKDAY.day

        # if work_day not in attendance_data:
        attendance_data[work_day] = {}

        attendance_data[work_day]["日付"] = f"{work_day}日"
        # オンコール
        attendance_data[work_day]["オンコール"] = (
            attendance_obj.ONCALL if attendance_obj.ONCALL != "0" else None
        )
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
        attendance_data[work_day]["残業申請"] = (
            1 if attendance_obj.OVERTIME == "1" else 0
        )

        # 月途中の契約変更する場合の保険
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

        which_contract_worktime = (
            part_work_time
            if record.StaffHolidayContract is not None
            else regular_work_time
        )
        which_contract_holiday_time = (
            part_holiday_time
            if record.StaffHolidayContract is not None
            else regular_work_time
        )

        calculation_instance = calc_time_factory.get_instance(staff_id=staff_id)
        calculation_instance.set_data(
            contract_work_time=which_contract_worktime,
            contract_holiday_time=which_contract_holiday_time,
            start_time=attendance_obj.STARTTIME,
            end_time=attendance_obj.ENDTIME,
            notifications=(attendance_obj.NOTIFICATION, attendance_obj.NOTIFICATION2),
            overtime_check=attendance_obj.OVERTIME,
            holiday_work=attendance_obj.HOLIDAY,
        )

        input_work_time = calculation_instance.calc_base_work_time()
        normal_rest_time = calculation_instance.calc_normal_rest(input_work_time)
        normal_rest_time_str = convert_time_to_str(normal_rest_time)
        attendance_data[work_day]["通常休憩時間"] = normal_rest_time_str

        clock_work_time = input_work_time - normal_rest_time
        attendance_data[work_day]["打刻実働時間"] = timedelta_to_hhmm(clock_work_time)

        time_off_hours = calculation_instance.get_time_off_hour()
        attendance_data[work_day]["時間休合計"] = timedelta_to_hhmm(time_off_hours)

        # 時間休の有無
        # attendance_data[work_day]["時間休フラグ"] = (
        #     1
        #     if attendance_obj.NOTIFICATION in calculation_instance.n_time_off_list
        #     or attendance_obj.NOTIFICATION2 in calculation_instance.n_time_off_list
        #     else 0
        # )

        # 実働時間
        actual_work_time = calculation_instance.get_actual_work_time()
        actual_work_time_str = convert_time_to_str(actual_work_time)
        attendance_data[work_day]["実働時間"] = actual_work_time_str

        # [1, 2, 8] = ["遅刻", "早退", "欠勤"]
        total_work_time_calc_mode = (
            "contract_based"
            if timedelta_lt(actual_work_time, clock_work_time)
            and attendance_obj.OVERTIME == "0"
            and (
                attendance_obj.NOTIFICATION not in [1, 2, 8]
                or attendance_obj.NOTIFICATION2 not in [1, 2]
            )
            else "clock_based"
        )
        attendance_data[work_day]["実働時間算出モード"] = total_work_time_calc_mode

        # 実働時間(リアルタイム)
        real_time = calculation_instance.get_real_time()
        attendance_data[work_day]["リアル実働時間"] = format_rt(real_time)

        # 残業時間
        over_work_time = calculation_instance.get_over_time()
        print(f"Over time (seconds): {over_work_time}")
        attendance_data[work_day]["時間外"] = format_rt(over_work_time)

        oncall_zero_pattern = None
        if (
            attendance_data[work_day]["オンコール"] is not None
            and attendance_data[work_day]["出勤"] == "00:00"
        ):
            oncall_zero_pattern = "oncall_waited"

        # 時間休入力パターン: 追加ツール用
        time_off_input_pattern = None
        diagnostic_flags = []
        if attendance_data[work_day]["時間休合計"] != "00:00":
            if timedelta_lt(actual_work_time, which_contract_worktime):
                time_off_input_pattern = "timeoff_pre_reflected"
                diagnostic_flags.append("TIMEOFF_PRE_REFLECTED_SUSPECT")  # 時刻ベース
            elif total_work_time_calc_mode == "contract_based":
                time_off_input_pattern = "timeoff_not_pre_reflected"
                diagnostic_flags.append(
                    "TIMEOFF_NOT_PRE_REFLECTED_SUSPECT"
                )  # 契約時間ベース
        # else:
        #     time_off_input_pattern = "timeoff_not_pre_reflected"
        # diagnostic_flags.append("TIMEOFF_FLAG_OFF")
        attendance_data[work_day]["時間休入力パターン"] = time_off_input_pattern

        # まだ必要性が不明 25/3/3
        # if total_work_time_calc_mode == "clock_based":
        #     diagnostic_flags.append("TOTAL_CLOCK_BASED")
        # else:
        #     diagnostic_flags.append("TOTAL_CONTRACT_BASED")

        # # if attendance_obj.OVERTIME == "0":
        # if timedelta_lt(actual_work_time, which_contract_worktime):
        #     diagnostic_flags.append("TOTAL_LT_CONTRACT")

        # if attendance_obj.OVERTIME == "1":
        #     diagnostic_flags.append("OVERTIME_REQUEST_ON")

        if over_work_time < 0:
            diagnostic_flags.append("OVERTIME_NEGATIVE")

        if (
            attendance_obj.ONCALL == "0"
            and attendance_obj.OVERTIME == "0"
            and attendance_obj.NOTIFICATION == ""
            and attendance_obj.NOTIFICATION2 == ""
            and timedelta_lt(clock_work_time, which_contract_worktime)
        ):
            diagnostic_flags.append("IRREGULAR_NO_NOTIFICATION")
        elif timedelta_lt(actual_work_time, which_contract_worktime):
            diagnostic_flags.append("BASIC_IRREGULAR")
        attendance_data[work_day]["診断フラグ"] = diagnostic_flags

        diagnosis = None
        if time_off_input_pattern == "timeoff_pre_reflected":
            diagnosis = (
                "時間休を事前に反映した打刻の可能性が高く、"
                "実働時間は打刻ベース（退勤-出勤-通常休憩）で算出されています。"
            )
        elif time_off_input_pattern == "timeoff_not_pre_reflected":
            diagnosis = (
                "時間休を事前反映しない打刻の可能性が高く、"
                "実働時間は契約ベースです。"
            )
        elif oncall_zero_pattern == "oncall_waited":
            diagnosis = "オンコールがあり、出勤時刻が'00:00'ですが、出勤扱いです。"
        elif "OVERTIME_NEGATIVE" in diagnostic_flags:
            diagnosis = "残業申請ありですが時間外がマイナスです。届出漏れなどの可能性があります。"
        elif "IRREGULAR_NO_NOTIFICATION" in diagnostic_flags:
            diagnosis = "有休等の届出なしで実働時間が契約労働時間未満です。打刻ベース算出のイレギュラーの可能性があります。"
        elif "BASIC_IRREGULAR" in diagnostic_flags:
            diagnosis = "実働時間が契約労働時間未満です。打刻ベース算出のイレギュラーの可能性があります。"
        attendance_data[work_day]["診断"] = diagnosis

        # 備考
        attendance_data[work_day]["備考"] = (
            attendance_obj.REMARK if attendance_obj.REMARK else None
        )

    return attendance_data
