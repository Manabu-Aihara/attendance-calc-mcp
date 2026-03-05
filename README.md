# Attendance Calculation MCP

勤怠管理システムの計算ロジック（特に時間休と実働時間）を検証・診断するためのMCP（Model Context Protocol）サーバーを備えたアプリケーションです。
旧システムから新システムへの移行において、複雑な計算過程の透明性を高め、正当性を検証することを目的としています。

## 主な機能

- **勤怠データ抽出 (`get_specific_attendance`)**: 特定の社員・対象月の詳細な勤怠データを抽出します。
- **勤怠診断 (`diagnose_attendance_records`)**: 勤怠データから、実働時間の算出モードや時間休の入力パターンを自動診断し、要約情報を抽出します。
- **MCPプロンプト (`analyze_attendance_prompt`)**: LLMが診断結果を分析し、ユーザーに分かりやすく説明するための最適なコンテキストを提供します。

## 技術スタック

- **Backend**: Python (FastAPI, SQLAlchemy)
- **MCP Framework**: FastMCP
- **Database**: MySQL (PyMySQL)
- **Testing**: pytest

## 診断ロジックの概要

本システムでは、以下の2つの時間休入力パターンを自動的に判別します：

1. **時間休を事前に反映した打刻 (`timeoff_pre_reflected`)**: 出退勤の打刻自体が、既に時間休分を差し引いた時刻で行われているパターン。実働時間は「打刻ベース」で算出されます。
2. **時間休を事前反映しない打刻 (`timeoff_not_pre_reflected`)**: 出退勤の打刻は実時刻で行われ、別途届出で時間休を処理するパターン。実働時間は「契約ベース」で算出されます。

また、残業申請の有無や、実働時間が契約時間に満たない場合のイレギュラー判定（遅刻・早退・欠勤・届出漏れなど）も行います。

## 開発とテスト

### 環境構築
```bash
# 依存関係のインストール
uv sync
```

### テストの実行
```bash
source .venv/bin/activate
pytest tests/test_issue14_diagnosis.py
```

## 運用
Dockerを使用してデプロイ可能です。詳細は `docker-compose.yml` を参照してください。
