# Issue #14: MCP勤怠診断機能の強化と検証

## 現状の進捗
- [x] `app/server/mcp_tools_call.py` のツール説明 (description) の改善
- [x] `app/server/mcp_tools_call.py` の MCP prompt (`analyze_attendance_prompt`) の改善
- [x] `app/logics/attendance_day_collect.py` の診断ロジックの改善
    - [x] `total_work_time_calc_mode` の判定ロジックの整理
    - [x] `time_off_input_pattern` の判定バグの修正（時間休ありかつ打刻時間が契約時間と一致する場合）
    - [x] `diagnosis` メッセージの多重化・詳細化
- [x] 評価用データの準備と簡易検証テストの作成
    - [x] 代表的なパターン（時間休事前反映あり/なし、残業申請あり/なし、届出漏れなど）のテストデータ作成
    - [x] 期待される診断結果の定義

## 詳細タスク

### 1. 診断ロジックの改善 (`app/logics/attendance_day_collect.py`)
- [x] `total_work_time_calc_mode` を、契約時間ベースか打刻時間ベースかをより正確に判定するように修正。
- [x] 時間休がある場合に、`timeoff_pre_reflected`（打刻に反映済み）か `timeoff_not_pre_reflected`（打刻は実時刻）かを、`clock_work_time` と `contract_work_time` の比較から正確に判定。
- [x] 診断メッセージを、複数の異常がある場合に連結して表示できるように修正。

### 2. 評価データの準備
- [x] `tests/test_issue14_diagnosis.py` を作成。（`docs/Issue14_tasks.md` 内の予定名 `tests/test_attendance_diagnosis.py` から変更）
- [x] Mockデータを用いて、様々なケースでの診断フラグとメッセージが期待通りであることを確認。
