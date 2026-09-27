"""FastAPI 入口：提供求解接口并托管离线静态页面。"""

from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .solver import solve_family, validate_members

app = FastAPI(title="ABO 家系推演台", docs_url=None, redoc_url=None)


class MemberIn(BaseModel):
    id: str = Field(default="", description="成员唯一 ID")
    blood: str = Field(default="unknown", description="A / B / AB / O / unknown")
    parents: List[str] = Field(default_factory=list, description="0 或 2 个父母 ID")


class SolveRequest(BaseModel):
    members: List[MemberIn] = Field(default_factory=list)


@app.post("/api/solve")
def api_solve(req: SolveRequest):
    # 规范化输入：去空格、丢弃空白父母项
    members = []
    for m in req.members:
        members.append(
            {
                "id": m.id.strip(),
                "blood": (m.blood.strip() or "unknown"),
                "parents": [p.strip() for p in m.parents if p and p.strip()],
            }
        )

    errors = validate_members(members)
    if errors:
        return {"ok": False, "errors": errors}

    result = solve_family(members)
    return {"ok": True, **result}


@app.get("/api/health")
def api_health():
    return {"ok": True}


_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
