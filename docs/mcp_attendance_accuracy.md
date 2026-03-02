## 今回の流れ（MCP勤怠診断の強化）

- 目的: 旧勤怠システムから新システムへの移行に際し、新システムの計算ロジック（特に時間休と実働時間）の正当性と算出方法を、MCP経由の回答で説明・検証できるようにする。
- 論点:
  - 時間休を「出退勤打刻にあらかじめ反映する」社員と、「打刻は実時刻のまま＋届出で処理する」社員が混在しており、入力が統一されていない。
  - time_off_hour_flag=1 かつ contract_work_time 未満の場合、total_work_time が契約ベースから打刻ベースに切り替わる仕様を、LLMが誤解しやすい。

### 実施した変更（ツール側）

- `attendance_day_collect.collect_attendance_data` に、日別の診断用フィールドを追加した。
  - 打刻実働時間: `打刻実働時間`（clock_work_time = 退勤 - 出勤 - 通常休憩時間）
  - 時間休合計: `時間休合計`（time_off_hours = 時間休の合計）
  - 実働時間算出モード: `実働時間算出モード`（total_work_time_calc_mode = `contract_based`/`clock_based`）
  - 時間休入力パターン: `時間休入力パターン`（time_off_input_pattern = `timeoff_pre_reflected`/`timeoff_not_pre_reflected`/None）
  - 診断フラグ: `診断フラグ`（diagnostic_flags = `TIMEOFF_FLAG_ON` などのタグ配列）
  - 診断メッセージ: `診断`（日本語1〜2文での簡易コメント）
- `mcp_tools_call.ATTENDANCE_KEY_MAP` に上記キーのショート名を追加し、MCPレスポンスにも含めるようにした。
- 既存ツール `get_specific_attendance`:
  - これまで通り meta + records を返すが、records に診断用フィールドも含まれる。
  - 整形時に欠損キーがあっても落ちないように防御的アクセスに変更。
- 新ツール `diagnose_attendance_records` を追加。
  - meta（社員ID・勤務形態・契約時間）と、日別に以下だけを返す軽量JSON。
    - day
    - time_off_input_pattern
    - total_work_time_calc_mode
    - clock_work_time
    - time_off_hours
    - diagnostic_flags
    - diagnosis
  - LLMはこのツールの結果を日本語に言い換えるだけで、「どちらの時間休入力パターンか」「前者のときに計算方法が変わる」点を説明できる。

### 次回以降のタスクリスト（プロンプト／運用）

- プロンプト・descriptionの改良:
  - `diagnose_attendance_records` の description を、
    - 「時間休を事前に打刻へ反映した入力／事前に反映しない入力」という2パターンを必ず言及させる
    - `time_off_input_pattern` と `total_work_time_calc_mode` を参照して、「どちらの入力パターンか」「契約ベースか打刻ベースか」を一言で説明させる
    という方針で書き換える。
  - `get_specific_attendance` の description に、
    - JSONキー名と社内用語（実働時間・リアル実働時間・時間休など）の対応表
    - 「ツールレスポンス内のキー名（staff_id や total_work_time など）はそのまま使わず、必ず社内の日本語表現に置き換えて回答する」こと
    を明示する。
  - MCP prompt (`analyze_attendance_prompt`) 側で、
    - JSONキー名は管理用語であること
    - 回答では「実働時間」「リアル実働時間」「時間休を事前に反映した打刻」等の社内表現に置き換えること
    - time_off_input_pattern / total_work_time_calc_mode を参照して、「時間休入力パターン」と「計算方法の切り替え」があれば必ず触れること
    - 「問題のある日」だけを列挙すること
    を明示する。
- 評価データの準備:
  - 代表的なパターン（時間休事前反映あり/なし・残業申請あり/なし・届出漏れ疑い等）ごとに、実データを数件ずつ用意。
  - 各パターンに対して期待される自然言語の回答例を作成し、LLMの出力と比較する簡易テストを作る。
- モデル選定とコスト最適化:
  - 現状の `gemini-2.5-flash` に加え、安価な Flash-Lite 系や Mini/Nano 系モデル、DeepSeek などを少数サンプルで比較。
  - 「説明の一貫性」「ルール遵守度」「コスト/1000件あたり」の3観点でログを取り、運用モデルを決める。
- 将来的な拡張:
  - 月途中の契約変更を扱う必要が出た場合、meta だけでなく日別にも契約時間を展開し、診断ロジックに反映する。
  - 新旧システムの双方の結果を同時に提示し、「どちらのロジックでどう差が出ているか」を比較するツールを追加する。

