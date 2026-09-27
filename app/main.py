"""FastAPI 入口：提供家系推演接口并托管静态页面。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .solver import solve_family, validate_members

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="ABO 家系推演台")


class SolveRequest(BaseModel):
    members: list[dict]


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/solve")
def solve(req: SolveRequest):
    members = req.members
    error = validate_members(members)
    if error:
        return JSONResponse(status_code=400,
                            content={"status": "error", "message": error})
    result = solve_family(members)
    if result["status"] == "no_solution":
        result["message"] = "不存在满足全部血型与遗传约束的分配，家系记录相互矛盾。"
    return result


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
