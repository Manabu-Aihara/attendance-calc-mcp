import argparse
import json
import pandas as pd
import sys

# 照合する項目リスト
REQUIRED_COLUMNS = [
    "社員ID",
    "勤務形態",
    "実働時間計",
    "リアル実働時間",
    "年休（全日）",
    "年休（半日）",
    "時間外",
    "時間休計",
]


def compare_csv_files(old_file_path: str, new_file_path: str) -> str:
    """
    新旧2つの勤怠集計CSVファイルを比較し、差異をJSON形式で返します。

    Args:
        old_file_path (str): 旧システムのCSVファイルパス。
        new_file_path (str): 新システムのCSVファイルパス。

    Returns:
        str: 差異をJSON形式で表現した文字列。差異がなければ空のJSON '{}' を返します。

    Raises:
        FileNotFoundError: 指定されたファイルが存在しない場合。
        ValueError: ファイルがCSV形式でない、または必要な項目が不足している場合。
    """
    # --- 1. ファイル形式チェック ---
    if not old_file_path.lower().endswith(".csv") or not new_file_path.lower().endswith(
        ".csv"
    ):
        raise ValueError("指定されたファイルはCSV形式ではありません。")

    # --- 2. CSV読み込みとヘッダー検証 ---
    try:
        # すべての列を文字列(object)として読み込み、pandasの型推論を避ける
        # これにより、"0.0" と "0" のようなデータ型の違いを厳密に比較できる
        df_old = pd.read_csv(old_file_path, dtype=object).fillna(pd.NA)
        df_new = pd.read_csv(new_file_path, dtype=object).fillna(pd.NA)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"ファイルが見つかりません: {e.filename}")

    # missing_cols_old = set(REQUIRED_COLUMNS) - set(df_old.columns)
    # if missing_cols_old:
    #     raise ValueError(f"旧CSVファイルに必要な項目が不足しています: {missing_cols_old}")

    # missing_cols_new = set(REQUIRED_COLUMNS) - set(df_new.columns)
    # if missing_cols_new:
    #     raise ValueError(f"新CSVファイルに必要な項目が不足しています: {missing_cols_new}")

    # --- 3. "社員ID"をキーに外部マージ ---
    # 必要な項目のみを対象にマージする
    df_merged = pd.merge(
        df_old[REQUIRED_COLUMNS],
        df_new[REQUIRED_COLUMNS],
        on="社員ID",
        how="outer",
        suffixes=("_old", "_new"),
    )

    # --- 4. 差分抽出 ---
    diff_results = {}
    compare_columns = [col for col in REQUIRED_COLUMNS if col != "社員ID"]
    # print(f"Comparing columns: {compare_columns}")

    for _, row in df_merged.iterrows():
        employee_id = row["社員ID"]
        differences = []

        for col in compare_columns:
            val_old = row[f"{col}_old"]
            val_new = row[f"{col}_new"]
            # print(f"New val for {employee_id} {col}: {val_new}")

            # pd.NA を None に変換してから比較
            v_old = None if pd.isna(val_old) else val_old
            v_new = None if pd.isna(val_new) else val_new

            if v_old != v_new and v_new is not None:
                # 元のCSVの値をそのまま使いたいので、数値への変換は行わない
                differences.append({col: {"旧": v_old, "新": v_new}})

        if differences:
            diff_results[employee_id] = differences

    # --- 5. JSON形式で返却 ---
    return json.dumps(diff_results, indent=2, ensure_ascii=False)


def main():
    """コマンドライン実行用のエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="新旧の勤怠集計CSVファイルを比較し、差異をJSONで出力します。"
    )
    parser.add_argument("old_file", help="旧システムのCSVファイルパス")
    parser.add_argument("new_file", help="新システムのCSVファイルパス")

    args = parser.parse_args()

    try:
        diff_json = compare_csv_files(args.old_file, args.new_file)
        print(diff_json)
    except (FileNotFoundError, ValueError) as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
