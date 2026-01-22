from fastapi import FastAPI, Request, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response
from mcp.server.sse import SseServerTransport

import anyio
import jwt
from pathlib import Path
import uuid
from datetime import datetime

from .csv_comparator import compare_csv_files
from .mcp_tools_call import mcp_server  # MCPサーバーインスタンス

app = FastAPI()

# 先ほど定義したツール群を登録
# @mcp_server.list_tools() ...
# @mcp_server.call_tool() ...

# SSEトランスポートのインスタンス化
sse_transport = SseServerTransport("/messages")


@app.get("/sse")
async def handle_sse(request: Request):
    """MCPクライアントが最初に接続するエンドポイント"""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        # MCPサーバーをこのSSEコネクション上で実行
        await mcp_server.run(
            read_stream, write_stream, mcp_server.create_initialization_options()
        )


@app.post("/messages")
async def handle_messages(request: Request):
    """クライアントからのJSON-RPCリクエストを受けるエンドポイント"""
    await sse_transport.handle_post_request(
        request.scope, request.receive, request._send
    )


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
print(f"どこdir: {BASE_DIR}")

templates = Jinja2Templates(directory=str(Path(BASE_DIR, "templates")))


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
async def handle_csv_diff(request: Request, uuid: str):
    # UUIDを使ってトークンを取得
    stored_uuid = token_store.get("UUID")
    if stored_uuid != uuid:
        return {"error": "無効なUUIDです"}

    return templates.TemplateResponse(
        "csv/csv_diff.html", {"request": request, "uuid": uuid}
    )


@app.post("/output-csv-compare")
async def handle_output_csv_diff(
    request: Request, old_csv: str = Form(...), new_csv: str = Form(...)
):
    json_data = compare_csv_files(old_csv, new_csv)

    dateime_format = datetime.today().strftime("%Y%m%d%H%M")
    output_file = Path("output_json", f"csv_diff_{dateime_format}.json")
    with output_file.open("w", encoding="utf-8") as f:
        f.write(json_data)
    # ここでCSV差分データの処理を行う
    return {"message": "CSV差分データを受け取りました"}
