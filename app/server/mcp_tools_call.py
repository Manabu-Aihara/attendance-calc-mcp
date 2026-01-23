from fastapi.concurrency import run_in_threadpool  # FastAPIのユーティリティ
from mcp.types import Tool, TextContent
from mcp.server import Server

import json
from typing import Dict, List, Any, Callable
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
            description="指定された社員の特定期間の勤怠一覧データを取得します。1ヶ月単位のデータを、1日毎に出力します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "staff_id": {"type": "integer", "description": "社員ID (例: 123)"},
                    "from_day": {
                        "type": "string",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                        "description": "開始日 (YYYY-MM-DD形式)",
                    },
                    "to_day": {
                        "type": "string",
                        "pattern": r"^\d{4}-\d{2}-\d{2}$",
                        "description": "終了日 (YYYY-MM-DD形式)",
                    },
                },
                "required": ["staff_id", "from_day", "to_day"],
            },
        )
    ]


def diet_collect_attendance_data(
    func: Callable[..., Dict[int, Dict[str, Any]]] = collect_attendance_data,
) -> List[TextContent]:
    """
    A lightweight version of collect_attendance_data that only retrieves essential fields.
    """
    collection_attend_dict = func
    lightweight_list = [
        {
            "d": day,
            "sid": record.get("社員ID"),
            "in": record.get("出勤"),
            "out": record.get("退勤"),
            "am": record.get("届出(AM)"),
            "pm": record.get("届出(PM)"),
            "oa": record.get("残業申請"),
            "typ": record.get("勤務形態"),
            "cw": record.get("契約労働時間"),
            "ch": record.get("契約有休時間"),
            "nr": record.get("通常休憩時間"),
            "wt": record.get("実働時間"),
            "rt": record.get("リアル実働時間"),
            "ot": record.get("時間外"),
            "rmk": record.get("備考"),
        }
        for day, record in collection_attend_dict.items()
    ]

    # MCPのレスポンス形式（TextContent）に変換
    return [
        TextContent(
            type="text",
            text=json.dumps(
                lightweight_list, ensure_ascii=False, separators=(",", ":")
            ),
        )
    ]


# @mcp_server.tool_function("get_specific_attendance")
async def get_specific_attendance(arguments: Dict):
    """
    Retrieves specific attendance data for a given staff member and date range.
    This function is a wrapper around collect_attendance_data to fit the MCP tool format.
    """
    # year, month = map(int, target_month.split("-"))
    # from_day = f"{year}-{month:02d}-01"
    # last_day = calendar.monthrange(year, month)[1]
    # to_day = f"{year}-{month:02d}-{last_day}"

    # 1. ツール実行ごとに新しいセッションを生成
    with Session() as db:
        try:
            # 2. 同期関数をスレッドプールで実行（FastAPIを止めないため）
            # run_in_threadpool を使うことで、同期的なDB操作を安全に非同期実行できます
            data = await run_in_threadpool(
                collect_attendance_data,
                staff_id=arguments["staff_id"],
                from_day=arguments["from_day"],
                to_day=arguments["to_day"],
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
        # # 1. ツール実行ごとに新しいセッションを生成
        # with Session() as db:
        #     try:
        #         # 2. 同期関数をスレッドプールで実行（FastAPIを止めないため）
        #         # run_in_threadpool を使うことで、同期的なDB操作を安全に非同期実行できます
        #         data = await run_in_threadpool(
        #             collect_attendance_data,
        #             staff_id=arguments["staff_id"],
        #             from_day=arguments["from_day"],
        #             to_day=arguments["to_day"],
        #             db_session=db,  # セッションを注入
        #         )

        #         # MCPのレスポンス形式（TextContent）に変換
        #         return [
        #             TextContent(
        #                 type="text", text=json.dumps(data, ensure_ascii=False, indent=2)
        #             )
        #         ]
        #     except Exception as e:
        #         return [TextContent(type="text", text=f"Error: {str(e)}")]
        return await get_specific_attendance(arguments)

    raise ValueError(f"Tool not found: {name}")
