from pydantic import BaseModel, Field


class CSVFileSchema(BaseModel):
    staff_id: int = Field(description="社員ID")
    work_type: str = Field(description="勤務形態")
    actual_work_time: float = Field(description="実働時間 (時間単位)")
    real_time: float = Field(description="リアル実働時間 (時間単位)")
    annual_leave_full: int = Field(
        description="年休(全日) (1日の場合は1、0日の場合は0)"
    )
    annual_leave_half: int = Field(
        description="年休(半日) (0.5日の場合は0.5、0日の場合は0)"
    )
    overtime_hours: float = Field(description="時間外 (時間単位)")
    time_off_total: int = Field(description="時間休計 (時間単位)")


class CalcDataSchema(BaseModel):
    staff_id: int
    contract_work_time: float = Field(description="契約勤務時間 (時間単位)")
    contract_holiday_time: float = Field(description="契約休日時間 (時間単位)")
    start_time: str = Field(description="勤務開始時間 (HH:MM形式)")
    end_time: str = Field(description="勤務終了時間 (HH:MM形式)")
    notifications: list[str] = Field(description="申請番号リスト")
    overtime: str = Field(description="時間外の有無")
    holiday_work: str = Field(description="休日出勤")


class AttendanceDataSchema(BaseModel):
    work_day: str = Field(description="勤務日 (YYYY-MM-DD形式)")
    staff_id: int = Field(description="社員ID")
    start_time: str = Field(description="出勤時間 (HH:MM形式)")
    end_time: str = Field(description="退勤時間 (HH:MM形式)")
    notification_am: str = Field(description="届出(AM)")
    notification_pm: str = Field(description="届出(PM)")
    overtime_application: str = Field(description="残業申請")
    work_type: str = Field(description="勤務形態")
    contract_work_time: float = Field(description="契約労働時間 (時間単位)")
    contract_holiday_time: float = Field(description="契約有休時間 (時間単位)")
    normal_rest_time: float = Field(description="通常休憩時間 (時間単位)")
    actual_work_time: str = Field(description="実働時間 (時間単位)")
    real_time: float = Field(description="リアル実働時間 (時間単位)")
    overtime_hours: float = Field(description="残業時間 (時間単位)")
    remarks: str = Field(description="備考")
