import csv
import json


def parse_csv(file_path):
    """
    CSVファイルを読み込み、指定されたデータを抽出してJSON形式のリストに変換する。

    Args:
        file_path (str): CSVファイルのパス。

    Returns:
        str: 抽出されたデータを含むJSON形式の文字列。
    """
    records = []
    # 旧システムのCSVヘッダー名と新システムのキー名のマッピング
    header_mapping = {
        "スタッフID": "staff_id",
        "日付": "date",
        "実働時間": "actual_work_time",
        "リアル時間": "real_time",
    }

    try:
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 空白行をスキップ
                if not any(row.values()):
                    continue

                record = {}
                for header_key, record_key in header_mapping.items():
                    record[record_key] = row.get(header_key)

                records.append(record)
    except FileNotFoundError:
        return json.dumps({"error": "File not found"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

    return json.dumps(records, indent=2)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        json_output = parse_csv(file_path)
        print(json_output)
    else:
        print("Usage: python csv_parser.py <file_path>")
