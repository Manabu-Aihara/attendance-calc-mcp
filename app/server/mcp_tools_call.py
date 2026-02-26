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
                "【役割】あなたは勤怠管理の『抽出エージェント』として、法規チェックではなく、一覧結果についての検証・判定を行ってください。\n"
                "【目的】旧システムとの差分分析を行い、新システムのロジックの正当性を証明するためのエビデンスを確認すること。\n"
                "【重要定義：用語の取り違え厳禁】\n"
                "1. total_work_time (実働時間): 届出(notification_am / notification_pm)が、有休・出張等の時間を含む値。\n"
                "2. actual_site_time (リアル実働時間): total_work_time から、notification_am / notification_pm の「年休(全日・半日)」「出張(全日・半日)」「時間休」の届出時間を除いた、現場での純粋な活動時間。\n"
                "3. time_off_hour_flag (時間休フラグ): notification_am / notification_pm に時間休の取得の有無を示すもの。['1h時間休', '2h時間休', '3h時間休', '1h中抜時休', '2h中抜時休', '3h中抜時休]のみ含まれると、1 になります。\n"
                "4. normal_rest_time (通常休憩時間): 1日の中で決められた休憩時間、notification_am / notification_pm とは関係ありません。計算ロジック上、出勤(in)が13:00以降、または退勤(out)が13:00以下のとき適応されません。\n"
                "5. overtime_request (残業申請): 残業の有無を(0, 1)で表示します。\n"
                "6. contract_work_time(契約労働時間): 契約上の労働時間を表す、メタ情報です。total_work_time と異なっていたら、notification_am / notification_pm または overtime_request をチェックする。\n"
                "7. contract_holiday_time (契約有休時間): 有給休暇における契約上の休暇時間です。notification_am / notification_pm が「年休全日・年休半日」のとき、total_work_time, actual_site_time の計算に用いられます。 \n"
                "8. overtime (時間外): 残業時間を示します。overtime_request が 1 なら、total_work_time から contract_work_time との差分をとります。\n"
                "【判定基準（仕様）】\n"
                "- time_off_hour_flag が 1: 【重要】total_work_time < contract_work_time になる場合、notification_am / notification_pm の時間休分が、in・out にあらかじめ反映させているケースとして、注意が必要です。\n"
                "- time_off_hour_flag が 1: 備考(remark)に記載があるケースが多いです。\n"
                "- overtime_request が 0： notification_am / notification_pm に「遅刻・早退・欠勤」が含まなければ、原則として total_work_time = contract_work_time となります。\n"
                "- overtime_request が 0： total_work_time < contract_work_time で、且つ notification_am / notification_pm に何もなければ、total_work_time は out - in - normal_rest_time で算出され、その日は『イレギュラー』と判定します。\n"
                "- overtime_request が 1： total_work_time は out - in - normal_rest_time で計算され、overtime が負の場合は、 notification_am / notification_pm 漏れの可能性を示唆します。\n"
                "その他、レスポンスの各キーの意味は以下の通りです：\n"
                "- day: 日付\n"
                "- staff_id: 社員ID\n"
                "- job_type: 勤務形態\n"
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
    # "社員ID": "staff_id",
    # "オンコール": "oc",
    "日付": "day",
    "出勤": "in",
    "退勤": "out",
    "届出(AM)": "notification_am",
    "届出(PM)": "notification_pm",
    "残業申請": "overtime_request",
    # "勤務形態": "job_type",
    # "契約労働時間": "contract_work_time",
    # "契約有休時間": "contract_holiday_time",
    "通常休憩時間": "normal_rest_time",
    "時間休フラグ": "time_off_hour_flag",
    "実働時間": "total_work_time",
    "リアル実働時間": "actual_site_time",
    "時間外": "overtime",
    "備考": "remark",
}


def diet_collect_attendance_data(
    attendance_data: Dict[Any, Any],
) -> List[TextContent]:
    """
    元の巨大な辞書データから、必要なキーだけを短縮して抽出するユーティリティ。
    """
    lightweight_dict = {}
    shortened_meta_record = {}
    for key, value in attendance_data.items():
        if isinstance(key, str) and key in FIXED_KEY_MAP:
            # for full_key, short_key in FIXED_KEY_MAP.items():
            short_key = FIXED_KEY_MAP[key]
            shortened_meta_record[short_key] = value
        else:
            break
    lightweight_dict["meta"] = shortened_meta_record
    print(f"Fixed part processed: {lightweight_dict}")

    shortened_day_record = {}
    shortened_day_list = []
    for day, record in attendance_data.items():
        if isinstance(day, int):
            shortened_day_record = {"day": day}

            for full_key, short_key in ATTENDANCE_KEY_MAP.items():
                # 同日で社員IDが重複する場合はスキップ
                # if day == shortened_record.get("d") and record.get(
                #     "社員ID"
                # ) == shortened_record.get("staff_id"):
                #     continue
                # if full_key in record and isinstance(record, dict):
                shortened_day_record[short_key] = record[full_key]
            shortened_day_list.append(shortened_day_record)

        lightweight_dict["records"] = shortened_day_list

    # MCPのレスポンス形式（TextContent）に変換
    return [
        TextContent(
            type="text",
            text=json.dumps(
                lightweight_dict, ensure_ascii=False, separators=(",", ":")
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
                            "提示するデータは新システムの集計に用いるための計算過程です。ツール説明(description)をよく読んでください。\n"
                            "【判定基準】に照らし、勤怠データの不自然な箇所や矛盾点を特定してください。\n"
                            "■分析の視点:\n"
                            "1. 残業申請(overtime_request)の有無と、実働時間(total_work_time)・契約時間(contract_work_time)の計算関係は仕様通りか？\n"
                            "2. リアル実働時間(actual_site_time)が、有休等の届出(notification_am / notification_pm)による計算が反映されているか？\n\n"
                            "■回答における規則:\n"
                            "total_work_time が、退勤(out) - 出勤(in) - 通常の休憩時間(normal_rest_time)で算出されていると判断した場合は、可能な限りその理由を加えてください。\n"
                            "【重要】JSONスキーマのキー名('records'キーのリスト内も含む)は、システム管理者としての用語であり使用は禁止とします。回答の際は、これらを必ず日本語に置き換え、"
                            "また、会社特有の用語として、total_work_time → '実働時間'、actual_site_time → 'リアル実働時間'と置き換えてください。\n"
                            "問題のない箇所は、なるべく省き、問題のある日付とその理由を簡潔に列挙してください。\n"
                            "システム上における(提供データへの)、修正提案は結構です。\n\n"
                            "■回答の構成例:\n"
                            "〇〇日: 実働時間が契約労働時間未満ですが、時間休分があらかじめ出退勤に反映されていると思われます。よって「退勤時間 - 出勤時間 - 通常の休憩時間」で計算されています。\n"
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
