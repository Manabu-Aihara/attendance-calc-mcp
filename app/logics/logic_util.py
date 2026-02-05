import calendar
from typing import Dict, Tuple, Any

import pandas as pd


def get_date_range(specified_month: str) -> Tuple[str, str]:
    year, month = map(int, specified_month.split("-"))
    from_day = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    to_day = f"{year}-{month:02d}-{last_day}"

    return from_day, to_day


FIXED_KEY_MAP = {
    "社員ID": "sid",
    "勤務形態": "typ",
    "契約労働時間": "cw",
    "契約有休時間": "ch",
}


def convert_to_dataframe(dict_data: Dict[Any, Any]) -> "pd.DataFrame":
    for key in list(dict_data.keys()):
        if key in FIXED_KEY_MAP.keys():
            del dict_data[key]

    df = pd.DataFrame(dict_data).T  # Transpose to have days as rows
    return df
