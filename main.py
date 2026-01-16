import calendar

from fastapi import FastAPI
from fastmcp import FastMCP
import uvicorn

from app.database_base import init_db
from app.attendance_day_collect import collect_attendance_data
from app.attendance_collect_logic import get_attendance_details_logic

mcp_router = FastMCP()


@mcp_router.tool()
def get_attendance_details_wrapper(staff_id: int, target_month: str) -> str:
    """MCPツール"""
    year, month = map(int, target_month.split("-"))
    from_day = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    to_day = f"{year}-{month:02d}-{last_day}"

    try:
        data = collect_attendance_data(staff_id, from_day, to_day)
        return str(data)
    except Exception as e:
        return f"Error: {e}"


# 最初のFastAPIインスタンス
app = FastAPI()


# テストエンドポイントを、 app に追加
@app.get("/test/attendance/{staff_id}/{target_month}")
def get_attendance_details(staff_id: int, target_month: str):
    return get_attendance_details_logic(staff_id, target_month)


# MCPの設定
mcp = FastMCP.from_fastapi(app)
mcp_app = mcp_router.http_app(path="/mcp")
# シンプルにするため、直接マウント
app.mount("/mcp", mcp.http_app())

# 複雑な方法で final_app を作成
# final_app = FastAPI(
#     title="Attemdance start API with MCP",
#     routes=[
#         *mcp_app.routes,
#         *app.routes,
#     ],
#     lifespan=mcp_app.lifespan,
# )

# データベース初期化
init_db()

if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)
    # mcp_router.run()
