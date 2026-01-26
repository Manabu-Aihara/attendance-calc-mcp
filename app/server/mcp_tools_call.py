from fastapi.concurrency import run_in_threadpool  # FastAPIのユーティリティ
from mcp.types import Tool, TextContent
from mcp.server import Server

import json
from typing import Dict, List, Any
import calendar

from app.database_base import Session
from app.logics.attendance_day_collect import collect_attendance_data

# 1. サーバーインスタンスの作成
mcp_server = Server("attendance-management")


# 2. 利用可能なツールの一覧を定義
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="get_specific_attendance",
            description=(
                "指定された社員の特定期間の勤怠一覧データを取得します。1ヶ月単位のデータを、1日毎に出力します。",
                "社員の勤怠一覧を取得します。レスポンスの各キーの意味は以下の通りです：\n"
                "- d: 日付\n"
                "- sid: 社員ID\n"
                "- in: 出勤\n"
                "- out: 退勤\n"
                "- am: 届出(AM)\n"
                "- pm: 届出(PM)\n"
                "- oa: 残業申請\n"
                "- typ: 勤務形態\n"
                "- cw: 契約労働時間\n"
                "- ch: 契約有休時間\n"
                "- nr: 通常休憩時間\n"
                "- wt: 実働時間\n"
                "- rt: リアル実働時間\n"
                "- ot: 時間外\n"
                "- rmk: 備考",
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "staff_id": {"type": "integer", "description": "社員ID (例: 123)"},
                    "target_month": {
                        "type": "string",
                        "pattern": r"^\d{4}-\d{2}$",
                        "description": "開始日 (YYYY-MM形式)",
                    },
                },
                "required": ["staff_id", "target_month"],
            },
        )
    ]


# mcp_tools_call.py への実装例
ATTENDANCE_KEY_MAP = {
    "社員ID": "sid",
    "出勤": "in",
    "退勤": "out",
    "届出(AM)": "am",
    "届出(PM)": "pm",
    "残業申請": "oa",
    "勤務形態": "typ",
    "契約労働時間": "cw",
    "契約有休時間": "ch",
    "実働時間": "wt",
    "リアル実働時間": "rt",
    "時間外": "ot",
    "備考": "rmk",
}


def diet_collect_attendance_data(
    attendance_data: Dict[int, Dict[str, Any]],
) -> List[TextContent]:
    """
    元の巨大な辞書データから、必要なキーだけを短縮して抽出するユーティリティ。
    """
    lightweight_list = []
    for day, record in attendance_data.items():
        shortened_record = {"d": day}

        for full_key, short_key in ATTENDANCE_KEY_MAP.items():
            # 同日で社員IDが重複する場合はスキップ
            if day == shortened_record.get("d") and record.get(
                "社員ID"
            ) == shortened_record.get("sid"):
                continue
            if full_key in record:
                shortened_record[short_key] = record[full_key]

        lightweight_list.append(shortened_record)

    # MCPのレスポンス形式（TextContent）に変換
    return [
        TextContent(
            type="text",
            text=json.dumps(
                lightweight_list, ensure_ascii=False, separators=(",", ":")
            ),
        )
    ]


async def get_specific_attendance(arguments: Dict):
    """
    Retrieves specific attendance data for a given staff member and date range.
    This function is a wrapper around collect_attendance_data to fit the MCP tool format.
    """
    year, month = map(int, arguments["target_month"].split("-"))
    from_day = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    to_day = f"{year}-{month:02d}-{last_day}"

    # 1. ツール実行ごとに新しいセッションを生成
    with Session() as db:
        try:
            # 2. 同期関数をスレッドプールで実行（FastAPIを止めないため）
            # run_in_threadpool を使うことで、同期的なDB操作を安全に非同期実行できます
            data = await run_in_threadpool(
                collect_attendance_data,
                staff_id=arguments["staff_id"],
                from_day=from_day,
                to_day=to_day,
                db_session=db,  # セッションを注入
            )
            shaped_data = diet_collect_attendance_data(data)
            return shaped_data
            # MCPのレスポンス形式（TextContent）に変換
            # return [
            #     TextContent(
            #         type="text", text=json.dumps(data, ensure_ascii=False, indent=2)
            #     )
            # ]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]


# 3. ツールの実行ロジック
@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: Dict):
    if name == "get_specific_attendance":
        return await get_specific_attendance(arguments)

    raise ValueError(f"Tool not found: {name}")
