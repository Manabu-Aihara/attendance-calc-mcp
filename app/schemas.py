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
    time_off_hours: int = Field(description="時間休 (時間単位)")
    break_time: int = Field(description="中抜け (時間単位)")


class NewCalcDataSchema(BaseModel):
    staff_id: int
    contract_work_time: float
    contract_holiday_time: float
    start_time: str
    end_time: str
    notifications: list[str]
    overtime: str
    holiday: str
