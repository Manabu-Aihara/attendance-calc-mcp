from app.csv_parser import parse_csv

def main():
    # ダミーのCSVファイルを作成 (テスト用)
    dummy_csv_content = """スタッフID,日付,実働時間,リアル時間
1,2025/01/01,8.0,8.0
2,2025/01/01,7.5,7.5
1,2025/01/02,8.0,8.0
, , , 
3,2025/01/02, 6.0, 6.0
"""
    dummy_csv_path = "sample.csv"
    with open(dummy_csv_path, "w", encoding="utf-8") as f:
        f.write(dummy_csv_content)

    print(f"Created dummy CSV: {dummy_csv_path}")

    # CSVファイルをパース
    parsed_data_json = parse_csv(dummy_csv_path)
    print("Parsed CSV data:")
    print(parsed_data_json)

    # ダミーファイルを削除 (オプション)
    import os
    os.remove(dummy_csv_path)
    print(f"Removed dummy CSV: {dummy_csv_path}")


if __name__ == "__main__":
    main()
