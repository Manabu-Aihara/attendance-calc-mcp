from fastapi import FastAPI, Request, status, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from mcp.server.sse import SseServerTransport
from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv
from google import genai

import os
import anyio
import jwt
from pathlib import Path
import uuid
from datetime import datetime

from app.logics.attendance_day_collect import collect_attendance_data
from app.logics.csv_comparator import compare_csv_files
from app.logics.logic_util import get_date_range, convert_to_dataframe, FIXED_KEY_MAP
from .mcp_tools_call import mcp_server  # MCPサーバーインスタンス

app = FastAPI()

# 先ほど定義したツール群を登録
# @mcp_server.list_tools() ...
# @mcp_server.call_tool() ...

# SSEトランスポートのインスタンス化
sse_transport = SseServerTransport("/messages")


async def sse_cleanup(client_ip: str):
    # ここでセッションの強制クローズやログ記録を行う
    print(f"Cleaning up resources for {client_ip}")


# @app.get("/sse")
# async def handle_sse(request: Request):
#     # 1. 二重送信防止のためのフラグとラッパー関数
#     response_started = False
#     original_send = request._send

#     async def wrapped_send(message):
#         nonlocal response_started
#         # すでにレスポンスが開始されている場合、二度目の http.response.start は無視する
#         if message["type"] == "http.response.start":
#             if response_started:
#                 return # 何もしない（エラーを回避）
#             response_started = True

#         await original_send(message)

#     # 2. ラップした send 関数を使用して SSE を開始
#     async with sse_transport.connect_sse(
#         request.scope, request.receive, wrapped_send
#     ) as (read_stream, write_stream):
#         try:
#             async with anyio.create_task_group() as tg:
#                 await mcp_server.run(
#                     read_stream,
#                     write_stream,
#                     mcp_server.create_initialization_options()
#                 )
#                 tg.cancel_scope.cancel()
#         except anyio.EndOfStream:
#             pass
#         except Exception as e:
#             print(f"MCP Run Error: {e}")

#     # 3. 正常なステータスコードを返すが、wrapped_send が二重送信をブロックする
#     return Response(content="", status_code=200)


# endpoint.py に追加
# 以前提供してくれたもの
class SuppressResponseStartMiddleware:
    """SSE終了後の二重 http.response.start エラーを抑制するミドルウェア"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def wrapped_send(message):
            nonlocal response_started
            # すでに送信開始している場合、二度目の開始メッセージを無視する
            if message["type"] == "http.response.start":
                if response_started:
                    return
                response_started = True
            await send(message)

        await self.app(scope, receive, wrapped_send)


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. 前処理
        response = await call_next(request)
        # 2. 戻り値が正しいか確認
        return response


# アプリに登録
# ミドルウェアの登録（順番も重要です）
app.add_middleware(SuppressResponseStartMiddleware)  # ← これを追加
app.add_middleware(CustomMiddleware)


@app.get("/sse")
async def handle_sse(request: Request):
    """MCPクライアントが最初に接続するエンドポイント"""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send  # type: ignore[reportPrivateUsage]
    ) as (read_stream, write_stream):
        # MCPサーバーをこのSSEコネクション上で実行
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
        )


@app.post("/messages")
async def handle_messages(request: Request):
    scope = request.scope
    recieve = request.receive
    send = request._send  # type: ignore[reportPrivateUsage]
    # send = request.scope.get("send")
    """クライアントからのJSON-RPCリクエストを受けるエンドポイント"""
    await sse_transport.handle_post_message(scope, recieve, send)


# 補足: Webで公開する場合、CORS設定が必要になることが多いです
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 運用に合わせて制限してください
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "you-will-never-guess"
ALGORITHM = "HS256"


def verify_token(token: str):
    try:
        # デコードと検証を一気に行う
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # {'user_id': 123, 'exp': ...} などの辞書が返る
    except jwt.ExpiredSignatureError:
        return "期限切れです"
    except jwt.InvalidTokenError:
        return "無効なトークンです"


token_store = {}


@app.get("/secure-data")
async def read_users_me(request: Request):
    param_token = request.query_params.get("token")

    # トークンを一時的に保存
    token_store["Auth token"] = param_token

    # リダイレクト時にトークンIDのみを渡す
    # 303 See Other - Must
    # https://stackoverflow.com/questions/73076517/how-to-send-redirectresponse-from-a-post-to-a-get-route-in-fastapi
    return RedirectResponse(
        url=f"/read-secure?token_id={param_token}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# Fastapi : jinja2.exceptions.TemplateNotFound
# https://stackoverflow.com/questions/67668606/fastapi-jinja2-exceptions-templatenotfound-index-html
BASE_DIR = Path(__file__).resolve().parent.parent
# print(f"どこdir: {BASE_DIR}")

templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))
app.mount(
    path="/static",
    app=StaticFiles(directory=str(Path(BASE_DIR, "static"))),
    name="static",
)


@app.get("/read-secure")
async def read_secure_data(request: Request):
    token_id = request.query_params.get("token_id")
    print(f"Received url token: {token_id}")
    token = token_store.get("Auth token")

    verification_result = verify_token(token)
    # 新しいトークンIDを生成
    inner_token_id = str(uuid.uuid4())
    token_store["UUID"] = inner_token_id

    if isinstance(verification_result, dict):
        # トークンが有効な場合の処理
        # return {
        #     "message": "セキュアデータにアクセスしました",
        #     "user_data": verification_result,
        # }
        return templates.TemplateResponse(
            "select_home.html",
            {
                "request": request,
                "user_data": verification_result,
                "uuid": inner_token_id,
            },
        )
    else:
        # トークンが無効または期限切れの場合の処理
        return {"error": verification_result}


@app.get("/csv-diff")
async def handle_csv_diff(request: Request, uuid: str, filename: str = ""):
    # UUIDを使ってトークンを取得
    stored_uuid = token_store.get("UUID")
    if stored_uuid != uuid:
        return {"error": "無効なUUIDです"}

    return templates.TemplateResponse(
        "csv/csv_diff.html",
        {"request": request, "uuid": uuid, "json_file_name": filename},
    )


@app.post("/output-csv-compare")
async def handle_output_csv_diff(
    request: Request,
    uuid: str = Form(...),
    old_csv: UploadFile = File(...),
    new_csv: UploadFile = File(...),
):
    # print(f"Old CSV Path: {old_csv.filename}, New CSV Path: {new_csv.filename}")
    print(f"Received UUID: {uuid}")
    stored_uuid = token_store.get("UUID")
    if stored_uuid != uuid:
        return {"error": "無効なUUIDです"}

    # ここでCSV差分データの処理を行う
    json_data = compare_csv_files(old_csv.filename, new_csv.filename)
    # print(f"CSV差分JSONデータ: {json_data}")

    dateime_format = datetime.today().strftime("%Y%m%d%H%M")
    json_file = f"csv_diff_{dateime_format}.json"
    output_file = Path("output_json", json_file)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(json_data)

    # return {"message": "CSV差分データを受け取りました"}
    return RedirectResponse(
        url=f"/csv-diff?uuid={uuid}&filename={json_file}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/make-attendance-list")
async def get_attendance(
    request: Request,
    uuid: str = Form(...),
    staff_id: str = Form(...),
    target_month: str = Form(...),
):
    # UUIDを使ってトークンを取得
    stored_uuid = token_store.get("UUID")
    if stored_uuid != uuid:
        return {"error": "無効なUUIDです"}

    os.remove("app/templates/prompt/user_attendance.html")
    import shutil

    # ファイルの入れ替え（移動と上書き）
    source = "app/templates/user_attendance_front.html"  # 元のファイル
    destination = (
        "app/templates/prompt/user_attendance.html"  # 移動先または新しいファイル名
    )

    # 移動を実行（同名ファイルがある場合は上書き）
    shutil.copyfile(source, destination)

    from_day, to_day = get_date_range(target_month)
    staff_data_dict = collect_attendance_data(
        staff_id=int(staff_id), from_day=from_day, to_day=to_day
    )

    head_section_html = "<section><div class='flex gap-10 p-4 bg-purple-200 mb-4'>"
    for head_key, head_value in staff_data_dict.items():
        if head_key in FIXED_KEY_MAP:
            head_section_html += f"<div>{head_key}: {head_value}</div>"
    head_section_html += "</div></section>"
    template_content = head_section_html

    table_wrap = "<div class='w-[80%] mx-auto border-2 table-wrap overflow-y-auto'>"
    template_content += table_wrap

    staff_data_df = convert_to_dataframe(staff_data_dict)
    template_content += staff_data_df.to_html(
        classes="table table-striped", index=False
    )
    close_table = "</div>"
    template_content += close_table
    # print(f"Template Content: {template_content}")
    # close_html = """</body></html>"""
    # template_content += close_html

    # with open(
    #     Path("app/templates/prompt/user_attendance.html"), "a", encoding="utf-8"
    # ) as f:
    #     f.write(template_content)

    with open(
        Path("app/templates/prompt/user_attendance.html"),
        "a",
        encoding="utf-8",
    ) as f:
        f.write(template_content)

    return RedirectResponse(
        # url="/user-attendance",
        url=f"/chat-with-ai?staff_id={staff_id}&target_month={target_month}&list_table=prompt/user_attendance.html",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/user-attendance")
async def render_user_attendance(request: Request):

    return templates.TemplateResponse(
        "prompt/user_attendance.html",
        {"request": request},
    )


# The client gets the API key from the environment variable `GEMINI_API_KEY`.
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)


@app.get("/chat-with-ai")
async def chat_with_ai(
    request: Request,
    list_table: str,
    # uuid: str,  # = Form(...),
    staff_id: str,  # = Form(...),
    target_month: str,  # = Form(...),
):
    # with open(Path(list_table), "r", encoding="utf-8") as f:
    #     table_content = f.read()

    """Renders the initial prompt page for attendance analysis."""
    return templates.TemplateResponse(
        "prompt/mcp_prompt.html",
        {
            "request": request,
            # "uuid": uuid,
            "staff_id": staff_id,
            "target_month": target_month,
            "list_table": list_table,
        },
    )


@app.post("/analyze-attendance-prompt")
async def analyze_attendance_prompt(
    request: Request,
    staff_id: str = Form(...),
    target_month: str = Form(...),
    user_input: str = Form(...),
):
    """Fetches attendance data by calling the MCP tool
    and returns the result rendered in HTML."""
    # 1. MCP サーバーに接続（SSEクライアントとして）
    async with sse_client("http://127.0.0.1:8001/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print(f"Staff ID: {request.query_params.get('staff_id')}")
            print(f"Staff ID: {type(staff_id)}, Target Month: {target_month}")

            # 2. ツールを呼び出す
            result = await session.call_tool(
                "get_specific_attendance",
                arguments={
                    "staff_id": int(staff_id),
                    "target_month": target_month,
                },
            )
            raw_json = result.content[0].text

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        # contents=f"次の勤怠データを解析して、異常がないか確認してください：{raw_json}",
        contents=f"{user_input}\n\n{raw_json}",
    )

    # 3. 結果を Jinja2 で HTML に変換して返す（htmxがこれを受け取って画面を更新）
    return templates.TemplateResponse(
        "prompt/ai_response.html",
        {
            "request": request,
            "user_input": user_input,
            "ai_response": response.text,
        },
    )
