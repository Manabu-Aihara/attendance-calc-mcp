from fastapi.concurrency import run_in_threadpool  # FastAPIのユーティリティ
from mcp.types import Tool, TextContent
from mcp.server import Server
import json

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
            description="指定された社員の特定期間の勤怠一覧データを取得します。1ヶ月単位の集計などに使用します。",
            inputSchema={
                "type": "object",
                "properties": {
                    "staff_id": {"type": "integer", "description": "社員ID (例: 123)"},
                    "from_day": {
                        "type": "string",
                        "pattern": r"^\d{4}-\d{2}$",
                        "description": "開始日 (YYYY-MM形式)",
                    },
                    "to_day": {
                        "type": "string",
                        "pattern": r"^\d{4}-\d{2}$",
                        "description": "終了日 (YYYY-MM形式)",
                    },
                },
                "required": ["staff_id", "from_day", "to_day"],
            },
        )
    ]


# 3. ツールの実行ロジック
@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "get_specific_attendance":
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

                # MCPのレスポンス形式（TextContent）に変換
                return [
                    TextContent(
                        type="text", text=json.dumps(data, ensure_ascii=False, indent=2)
                    )
                ]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    raise ValueError(f"Tool not found: {name}")
