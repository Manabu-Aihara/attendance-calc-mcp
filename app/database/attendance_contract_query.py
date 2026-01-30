from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func

from app.database.database_base import session

# from .database_async import get_session
from app.models.models import (
    User,
    Attendance,
    Contract,
    StaffJobContract,
    StaffHolidayContract,
)


@dataclass
class ContractTimeAttendance:
    staff_id: int
    filter_from_day: date
    filter_to_day: date

    def _get_base_filter(self) -> list:
        attendance_filters = []
        attendance_filters.append(Attendance.STAFFID == self.staff_id)
        # pymysql.err.OperationalError: (1241, 'Operand should contain 1 column(s)')対策も、
        # 🙅ファクトリーにしているため、単体のインスタンスで値が合算される
        # attendance_filters.append(Attendance.STAFFID.in_(self.staff_id))
        attendance_filters.append(
            Attendance.WORKDAY.between(self.filter_from_day, self.filter_to_day)
        )
        return attendance_filters

    @staticmethod
    def _get_job_filter(part_timer_flag: bool = False):
        attendance_filters = []
        attendance_filters.append(Attendance.STAFFID == StaffJobContract.STAFFID)
        attendance_filters.append(StaffJobContract.START_DAY <= Attendance.WORKDAY)
        attendance_filters.append(StaffJobContract.END_DAY >= Attendance.WORKDAY)
        (
            attendance_filters.append(StaffJobContract.CONTRACT_CODE != 2)
            if part_timer_flag is False
            else attendance_filters.append(StaffJobContract.CONTRACT_CODE == 2)
        )
        return attendance_filters

    @staticmethod
    def _get_holiday_filter() -> list:
        attendance_filters = []
        # attendance_filters.append(Attendance.WORKDAY >= StaffHolidayContract.START_DAY)
        attendance_filters.append(Attendance.WORKDAY <= StaffHolidayContract.END_DAY)
        return attendance_filters

    def get_perfect_contract_attendance(self):
        base_filters = self._get_base_filter()

        # with get_session() as session:
        queries_for_calc_member = (
            session.query(
                Attendance, StaffJobContract, StaffHolidayContract, Contract.WORKTIME
            )
            .join(
                StaffJobContract,
                and_(
                    StaffJobContract.STAFFID == Attendance.STAFFID,
                    Attendance.WORKDAY >= StaffJobContract.START_DAY,  # この条件が重要
                    Attendance.WORKDAY <= StaffJobContract.END_DAY,
                ),
            )
            .join(Contract, Contract.CONTRACT_CODE == StaffJobContract.CONTRACT_CODE)
            .outerjoin(
                StaffHolidayContract,
                and_(
                    StaffHolidayContract.STAFFID == Attendance.STAFFID,
                    Attendance.WORKDAY
                    >= StaffHolidayContract.START_DAY,  # この条件も重要
                    Attendance.WORKDAY <= StaffHolidayContract.END_DAY,
                ),
            )
            .filter(
                and_(
                    *base_filters,
                    # Attendance.WORKDAY >= self.filter_from_day,
                )
            )
            .order_by(StaffJobContract.STAFFID)
        )

        return queries_for_calc_member

    # Query[(User, int)]
    def get_distinct_user_query(self):
        # 出勤実績があれば、引っかかる
        user_filters = self._get_base_filter()[1:] + self._get_job_filter()[0:3]
        # こちらはあくまで重複を消す
        # サブクエリでSTAFFIDごとの最新のSTART_DAYを取得
        subquery = (
            session.query(
                StaffJobContract.STAFFID,
                func.max(StaffJobContract.START_DAY).label("max_start_day"),
            ).group_by(StaffJobContract.STAFFID)
            # .filter(*user_filters)
            .subquery()
        )

        # サブクエリとStaffJobContractを結合して、各STAFFIDの最新レコードを取得
        user_order_query = (
            session.query(User, StaffJobContract.CONTRACT_CODE)
            .join(
                subquery,
                (StaffJobContract.STAFFID == subquery.c.STAFFID)
                & (StaffJobContract.START_DAY == subquery.c.max_start_day),
            )
            .join(User, User.STAFFID == StaffJobContract.STAFFID)
            .filter(and_(*user_filters))
            .order_by(StaffJobContract.START_DAY.desc())
        )
        return user_order_query
