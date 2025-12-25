import csv


def parse_csv(file_path, header_mapping=None):
    """
    CSVファイルを読み込み、指定されたデータを抽出してJSON形式のリストに変換する。

    Args:
        file_path (str): CSVファイルのパス。
        header_mapping (dict, optional): 旧システムのCSVヘッダー名と新システムのキー名のマッピング。
                                          指定しない場合はデフォルトのマッピングを使用。

    Returns:
        list: 抽出されたデータを含む辞書のリスト。
        list: エラーメッセージのリスト。
    """
    records = []
    errors = []
    # 旧システムのCSVヘッダー名と新システムのキー名のデフォルトマッピング
    default_header_mapping = {
        "社員ID": "staff_id",
        "勤務形態": "work_type",
        "実働時間計": "actual_work_time",
        "リアル実働時間": "real_time",
        "年休(全日)": "annual_leave_full",
        "年休(半日)": "annual_leave_half",
        "時間外": "overtime_hours",
        # "時間休": "time_off_hours",
        # "中抜け": "break_time",
        "時間休計": "time_off_total",
    }
    # 引数で指定されたマッピングがあればそれを使用、なければデフォルトを使用
    current_header_mapping = (
        header_mapping if header_mapping is not None else default_header_mapping
    )

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            line_num = 0
            for row in reader:
                line_num += 1
                # 空白行をスキップ
                if not any(row.values()):
                    continue

                record = {}
                row_has_error = False
                for header_key, record_key in current_header_mapping.items():
                    value = row.get(header_key)
                    if value is None:
                        errors.append(
                            f"Line {line_num}: Missing expected header '{header_key}'"
                        )
                        row_has_error = True
                        break  # Stop processing this row if a critical header is missing
                    record[record_key] = value

                if not row_has_error:
                    records.append(record)
    except FileNotFoundError:
        errors.append(f"File not found: {file_path}")
    except Exception as e:
        errors.append(f"An unexpected error occurred: {e}")

    return records, errors


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # Example of how to use custom mapping
        # custom_mapping = {
        #     "EmployeeID": "staff_id",
        #     "WorkDate": "date",
        #     "HoursWorked": "actual_work_time",
        #     "RealTime": "real_time",
        # }
        # records, errors = parse_csv(file_path, header_mapping=custom_mapping)
        records, errors = parse_csv(file_path)

        if errors:
            print(json.dumps({"records": records, "errors": errors}, indent=2))
        else:
            print(json.dumps(records, indent=2))
    else:
        print("Usage: python csv_parser.py <file_path>")
