from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from starlette.responses import Response
from mcp.server.sse import SseServerTransport
import anyio

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
