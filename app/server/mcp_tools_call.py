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
from app.logics.logic_util import get_date_range, FIXED_KEY_MAP

# 1. サーバーインスタンスの作成
mcp_server = Server("attendance-management")


# 2. 利用可能なツールの一覧を定義
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="get_specific_attendance",
            description=(
                "【役割】あなたは新システムの集計ロジックを検証する『システム監査者』です。法規チェックではなく、計算仕様通りの出力かを判定してください。\n"
                "【目的】旧システムとの差分分析を行い、新システムのロジックの正当性を証明するためのエビデンスを確認すること。\n"
                "【重要定義：用語の取り違え厳禁】\n"
                "1. wt (実働時間): 休暇届出時間を含む集計値。契約労働時間(cw)との整合性が重要。\n"
                "2. rt (リアル実働時間): 【重要】実働時間から有休等の届出時間を差し引いた、現場での純粋な活動時間。\n"
                "3. ot (時間外): 残業時間のこと。cwとの差分。負の値は届出漏れの可能性を示唆します。\n"
                "4. ch (契約有休時間): 有給休暇等の契約上の休暇時間。扱いはcwと同じです。\n"
                "【判定基準（仕様）】\n"
                "- 時間休(tr)：【重要】出勤(in)・退勤(out) にあらかじめ反映されている場合もあります。\n"
                "- 通常休憩時間(nr): inが13:00以降、またはoutが13:00以下のとき適応されません。\n"
                "- 残業申請(oa)が'0'：原則として wt = cw となる仕様です。\n"
                "- 実働時間(wt)：tr が申請されているとき、wt はcw未満になるときがあり、os が'0'のとき、cw未満なら『イレギュラー』と判定します。 \n"
                "- 残業申請(oa)が'1'：wt は実測値((out - in) - nr)をそのまま返し、cw未満なら ot は負となります。\n"
                "- リアル実働時間(rt)：tr が申請されているとき、二重に引かれている可能性があります。\n"
                "- 備考(rmk): tr が申請されている場合、記載があるケースが多いです。\n"
                "- オンコール(oc)中：in が00:00でも仕様上正常です。"
                "その他、レスポンスの各キーの意味は以下の通りです：\n"
                "- d: 日付\n"
                "- sid: 社員ID\n"
                "- am: 届出(AM)\n"
                "- pm: 届出(PM)\n"
                "- typ: 勤務形態\n"
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
    # "社員ID": "sid",
    "オンコール": "oc",
    "出勤": "in",
    "退勤": "out",
    "届出(AM)": "am",
    "届出(PM)": "pm",
    "残業申請": "oa",
    # "勤務形態": "typ",
    # "契約労働時間": "cw",
    # "契約有休時間": "ch",
    "通常休憩時間": "nr",
    "時間休": "tr",
    "実働時間": "wt",
    "リアル実働時間": "rt",
    "時間外": "ot",
    "備考": "rmk",
}


def diet_collect_attendance_data(
    attendance_data: Dict[Any, Any],
) -> List[TextContent]:
    """
    元の巨大な辞書データから、必要なキーだけを短縮して抽出するユーティリティ。
    """
    lightweight_list = []
    shortened_fix_record = {}
    for key, value in attendance_data.items():
        if isinstance(key, str) and key in FIXED_KEY_MAP:
            # for full_key, short_key in FIXED_KEY_MAP.items():
            short_key = FIXED_KEY_MAP[key]
            shortened_fix_record[short_key] = value
        else:
            break
    lightweight_list.append(shortened_fix_record)
    print(f"Fixed part processed: {lightweight_list}")

    shortened_day_record = {}
    for day, record in attendance_data.items():
        if isinstance(day, int):
            shortened_day_record = {"d": day}

            for full_key, short_key in ATTENDANCE_KEY_MAP.items():
                # 同日で社員IDが重複する場合はスキップ
                # if day == shortened_record.get("d") and record.get(
                #     "社員ID"
                # ) == shortened_record.get("sid"):
                #     continue
                # if full_key in record and isinstance(record, dict):
                shortened_day_record[short_key] = record[full_key]

            lightweight_list.append(shortened_day_record)

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
            name="analyze_attendance_prompt",
            description="指定された期間、対象社員の勤怠データを分析し、異常がないかなどを確認します。",
            arguments=[
                PromptArgument(name="staff_id", description="社員ID", required=True),
                PromptArgument(
                    name="target_month", description="対象月", required=True
                ),
            ],
        )
    ]


@mcp_server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict):
    if name == "analyze_attendance_prompt":
        return GetPromptResult(
            description="勤怠一覧プロンプト",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=(
                            "あなたはシステムエンジニアとして、新旧システムの集計ロジックに乖離がないか検証しています。\n"
                            "提示するデータは新システムの計算過程です。ツール説明(description)に記載した【判定基準】に照らし、"
                            "計算ロジックとして不自然な箇所（仕様と出力の矛盾）を特定してください。\n"
                            "とりわけ、リアル実働時間(rt)の意味をよく理解してください。\n"
                            "問題のない箇所は、なるべく省き、問題のある日付とその理由を簡潔に列挙してください。\n\n"
                            "■分析の視点:\n"
                            "1. 残業申請(oa)の有無と、実働時間(wt)・契約時間(cw)の計算関係は仕様通りか？\n"
                            "2. rt が、有休等の届出(am / pm)と矛盾なく算出されているか？\n"
                            "3. 時間休(tr)が申請されている日は、wt が cw 未満になっていたら、wt に反映されていると判断すること。\n"
                            "4. tr が申請されている日は、備考(rmk)をチェックすること。\n"
                            "5. 法的な適否ではなく、『システムの計算仕様として正しいか』を最優先に判断すること。\n"
                            "※『信頼性を証明する』といったメタな目的を回答文に含める必要はありません。"
                        ),
                    ),
                ),
                # PromptMessage(
                #     role="assistant",
                #     content=TextContent(
                #         type="text",
                #         # text
                #     ),
                # ),
            ],
        )
    raise ValueError(f"Prompt not found: {name}")
