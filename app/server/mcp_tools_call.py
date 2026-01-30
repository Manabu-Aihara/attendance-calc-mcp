from fastapi.concurrency import run_in_threadpool  # FastAPIのユーティリティ
from mcp.types import Tool, TextContent
from mcp.server import Server
from mcp.types import (
    Prompt,
    PromptMessage,
    PromptArgument,
    GetPromptResult,
    TextContent,
)

import json
from typing import Dict, List, Any

from app.database.database_base import Session
from app.logics.attendance_day_collect import collect_attendance_data
from app.logics.logic_util import get_date_range

# 1. サーバーインスタンスの作成
mcp_server = Server("attendance-management")


# 2. 利用可能なツールの一覧を定義
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="get_specific_attendance",
            description=(
                "新システムの集計ロジックの信頼性を検証するために、1ヶ月分の詳細な計算過程（日次データ）を取得します。"
                "このデータは旧システムとの集計差分を分析し、新システムの正当性を証明するためのエビデンスとして使用されます。"
                "分析時は、実働時間やリアル実働時間の算出根拠に矛盾がないか、計算アルゴリズムの観点で確認してください。\n"
                "社員の勤怠一覧を取得します。レスポンスの各キーの意味は以下の通りです：\n"
                "- d: 日付\n"
                "- sid: 社員ID\n"
                "- oc: オンコール\n"
                "- in: 出勤\n"
                "- out: 退勤\n"
                "- am: 届出(AM)\n"
                "- pm: 届出(PM)\n"
                "- oa: 残業申請\n"
                "- typ: 勤務形態\n"
                "- cw: 契約労働時間\n"
                "- ch: 契約有休時間\n"
                "- nr: 通常休憩時間\n"
                "- tr: 時間休\n"
                "- wt: 実働時間\n"
                "- rt: リアル実働時間\n"
                "- ot: 時間外\n"
                "- rmk: 備考\n"
                "オンコール(oc)は、「待機」を意味し、値があるにも関わらず、出勤が00:00であっても、問題はないとします。\n"
                "実働時間(wt)は、通常休憩時間(nr)を除き、有休等の届出時間を含めた勤務時間です。\n"
                "残業申請(oa)が'0'の場合、実働時間は、原則として契約労働時間(cw)を返します。契約労働時間未満の場合は、そのままの実働時間の値を返し、「イレギュラー」とします。\n"
                "残業申請が'1'の場合、実働時間はそのままの値を返し、そのうえで契約労働時間未満の場合は、時間外(ot)は負の値になり、「イレギュラー」とします。\n"
                "時間外が負の値の場合は、届出(am, pm)の抜けの可能性があります。\n"
                "リアル実働時間(rt)は、実働時間から有休等の届出時間を差し引いた、現場での純粋な活動時間。※賃金や給与とは無関係です。\n"
                "通常休憩時間は、出勤(in)が13:00以降、または退勤(out)が13:00以下のとき適応されません。\n"
                "実働時間は、通常休憩時間、また時間休(tr)の有無で、それらが出勤・退勤に反映されているかが、大きく影響します。\n"
                "時間休が、出勤・退勤時間にあらかじめ反映されている場合もあり、そのため、リアル実働時間の算出のときに、二重に引かれている可能性があります。\n"
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
    "オンコール": "oc",
    "出勤": "in",
    "退勤": "out",
    "届出(AM)": "am",
    "届出(PM)": "pm",
    "残業申請": "oa",
    "勤務形態": "typ",
    "契約労働時間": "cw",
    "契約有休時間": "ch",
    "通常休憩時間": "nr",
    "時間休": "tr",
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
            # if day == shortened_record.get("d") and record.get(
            #     "社員ID"
            # ) == shortened_record.get("sid"):
            #     continue
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
    from_day, to_day = get_date_range(arguments["target_month"])
    print(
        f"Fetching attendance for Staff ID: {type(arguments['staff_id'])} from {from_day} to {to_day}"
    )

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


@mcp_server.list_prompts()
async def handle_list_prompts():
    return [
        Prompt(
            name="fetch_attendance",
            description="指定された期間、対象社員の勤怠データを分析しまし、未入力がないかなどを確認します。",
            arguments=[
                PromptArgument(name="staff_id", description="社員ID", required=True)
            ],
        )
    ]


@mcp_server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    if name == "fetch_attendance":
        staff_id = arguments.get("staff_id", "社員ID")
        return GetPromptResult(
            description="勤怠一覧プロンプト",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text="以下のデータは新システムの計算過程です。集計ロジックに不自然な点がないか分析してください。"
                        "なお、回答の目的はあくまでユーザーの疑問（なぜマイナスか、など）に答えることであり、"
                        "『信頼性を証明する』といったメタな目的を回答文に含める必要はありません。",
                    ),
                ),
                PromptMessage(
                    role="assistant",
                    content=TextContent(
                        type="text",
                        # text
                    ),
                ),
            ],
        )
    raise ValueError(f"Prompt not found: {name}")
