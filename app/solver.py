"""ABO 家系基因型联立求解（OR-Tools CP-SAT）。

建模约定
========
* 等位基因只有三种：``A=0``、``B=1``、``O=2``。
* 每名成员有两个整数变量 ``x1 / x2``，分别表示其从“父母①/父母②”继承的
  等位基因；无父母记录的始祖成员则视为一对无序等位基因。
* 血型用表约束（allowed assignments）限定有序等位基因对的集合：

  - A 型 = AA / AO
  - B 型 = BB / BO
  - AB 型 = AB
  - O 型 = OO

* 遗传关系：孩子的 x1 必须等于父母①的两个等位基因之一，x2 同理取自父母②，
  同样用表约束表达。

每名成员“可能的基因型”通过逐基因型追加约束后做可行性检查得到，因此给出的
是在 **全家所有相容分配** 中真正能够出现的基因型，而不是仅凭血型的先验集合。
"""

from __future__ import annotations

from typing import Any

from ortools.sat.python import cp_model

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_A, _B, _O = 0, 1, 2
_ALLELE_NAME = "ABO"

MIN_MEMBERS = 2
MAX_MEMBERS = 18

# 六种基因型，按界面展示顺序排列
GENOTYPES = ["AA", "AO", "BB", "BO", "AB", "OO"]

# 基因型 -> 允许的有序等位基因对（变量 x1, x2 的取值组合）
GENO_PAIRS: dict[str, list[tuple[int, int]]] = {
    "AA": [(_A, _A)],
    "AO": [(_A, _O), (_O, _A)],
    "BB": [(_B, _B)],
    "BO": [(_B, _O), (_O, _B)],
    "AB": [(_A, _B), (_B, _A)],
    "OO": [(_O, _O)],
}

# 基因型 -> 血型（表型）
GENO_BLOOD: dict[str, str] = {
    "AA": "A",
    "AO": "A",
    "BB": "B",
    "BO": "B",
    "AB": "AB",
    "OO": "O",
}

BLOOD_TYPES = ["A", "B", "AB", "O"]

UNKNOWN = "unknown"
VALID_BLOODS = {"A", "B", "AB", "O", UNKNOWN}

# 声明血型 -> 候选基因型
BLOOD_GENOS: dict[str, list[str]] = {
    "A": ["AA", "AO"],
    "B": ["BB", "BO"],
    "AB": ["AB"],
    "O": ["OO"],
    UNKNOWN: list(GENOTYPES),
}

# 声明血型 -> 允许的有序等位基因对
BLOOD_PAIRS: dict[str, list[tuple[int, int]]] = {
    blood: [pair for geno in genos for pair in GENO_PAIRS[geno]]
    for blood, genos in BLOOD_GENOS.items()
}

# 遗传表约束：亲本等位基因为 (x, y) 时，孩子继承到的 z 必为 x 或 y。
# (x, y) 无序（AA 亲本只能给 A，AB 亲本可给 A/B），共 15 个三元组。
INHERIT_TUPLES = sorted(
    {(x, y, x) for x in range(3) for y in range(3)}
    | {(x, y, y) for x in range(3) for y in range(3)}
)

_FEASIBLE_STATUSES = (cp_model.OPTIMAL, cp_model.FEASIBLE)


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------

def validate_members(members: list[dict[str, Any]]) -> list[str]:
    """返回错误信息列表；为空表示录入合法。"""
    errors: list[str] = []
    n = len(members)
    if not MIN_MEMBERS <= n <= MAX_MEMBERS:
        errors.append(
            f"成员数量须为 {MIN_MEMBERS}～{MAX_MEMBERS} 名，当前为 {n} 名。"
        )

    seen: dict[str, int] = {}
    ids: list[str] = []
    for i, m in enumerate(members):
        mid = m["id"]
        if not mid:
            errors.append(f"第 {i + 1} 行：成员 ID 不能为空。")
            continue
        if mid in seen:
            errors.append(
                f"成员 ID「{mid}」重复（第 {seen[mid] + 1} 行与第 {i + 1} 行）。"
            )
        else:
            seen[mid] = i
            ids.append(mid)
        if m["blood"] not in VALID_BLOODS:
            errors.append(f"成员「{mid}」的血型「{m['blood']}」无效。")

    id_set = set(ids)
    for m in members:
        mid = m["id"]
        if not mid:
            continue
        parents = m["parents"]
        if len(parents) > 2:
            errors.append(f"成员「{mid}」的父母记录超过两人。")
            parents = parents[:2]
        if len(parents) == 1:
            errors.append(
                f"成员「{mid}」只填写了一位父母：须同时指定两位不同的父母，"
                "或两栏都留空（表示始祖）。"
            )
            continue
        if len(parents) == 2:
            if parents[0] == parents[1]:
                errors.append(f"成员「{mid}」的两位父母不能是同一人。")
            for p in parents:
                if p == mid:
                    errors.append(f"成员「{mid}」不能把自己列为父母。")
                elif p not in id_set:
                    errors.append(
                        f"成员「{mid}」的父母「{p}」尚未录入（请先录入该成员）。"
                    )

    cycle = find_cycle(members, id_set)
    if cycle is not None:
        errors.append("亲子关系成环：" + " → ".join(cycle) + "。")

    return errors


def find_cycle(
    members: list[dict[str, Any]], id_set: set[str]
) -> list[str] | None:
    """在“子女 -> 父母”有向图中查找一个环，返回环上的 ID 序列。"""
    graph: dict[str, list[str]] = {}
    for m in members:
        mid = m["id"]
        if not mid:
            continue
        graph[mid] = [
            p
            for p in m["parents"][:2]
            if p in id_set and p != mid
        ]

    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)
    stack: list[str] = []

    def dfs(u: str) -> list[str] | None:
        color[u] = GRAY
        stack.append(u)
        for v in graph.get(u, []):
            if color.get(v) == GRAY:
                start = stack.index(v)
                return stack[start:] + [v]
            if color.get(v) == WHITE:
                found = dfs(v)
                if found is not None:
                    return found
        stack.pop()
        color[u] = BLACK
        return None

    for node in graph:
        if color[node] == WHITE:
            found = dfs(node)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# CP-SAT 建模与求解
# ---------------------------------------------------------------------------

def _build_model(
    members: list[dict[str, Any]],
) -> tuple[cp_model.CpModel, dict[str, cp_model.IntVar], dict[str, cp_model.IntVar]]:
    model = cp_model.CpModel()
    x1: dict[str, cp_model.IntVar] = {}
    x2: dict[str, cp_model.IntVar] = {}

    for i, m in enumerate(members):
        mid = m["id"]
        x1[mid] = model.new_int_var(0, 2, f"x1_{i}")
        x2[mid] = model.new_int_var(0, 2, f"x2_{i}")

    # 血型（表型）约束
    for m in members:
        blood = m["blood"]
        if blood != UNKNOWN:
            model.add_allowed_assignments(
                [x1[m["id"]], x2[m["id"]]], BLOOD_PAIRS[blood]
            )

    # 遗传约束：孩子从双亲各继承一个等位基因
    for m in members:
        parents = m["parents"]
        if len(parents) != 2:
            continue
        p1, p2 = parents
        if p1 in x1 and p2 in x1:  # 校验通过后恒成立，防御性判断
            mid = m["id"]
            model.add_allowed_assignments(
                [x1[p1], x2[p1], x1[mid]], INHERIT_TUPLES
            )
            model.add_allowed_assignments(
                [x1[p2], x2[p2], x2[mid]], INHERIT_TUPLES
            )

    return model, x1, x2


def _solve(model: cp_model.CpModel, time_limit: float = 10.0):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    status = solver.solve(model)
    return solver, status


def _genotype(a: int, b: int) -> str:
    lo, hi = sorted((a, b))
    return _ALLELE_NAME[lo] + _ALLELE_NAME[hi]


def solve_family(
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    """联立求解全家系。

    返回::

        {"solvable": True,
         "witness": {id: "AO", ...},          # 一组完整见证
         "members": [{"id": ...,
                      "genotypes": [...],     # 全家相容分配中可能的基因型
                      "blood_types": [...]}, ...]}

    无解时返回 ``{"solvable": False, ...}``。
    """
    model, x1, x2 = _build_model(members)
    solver, status = _solve(model)
    if status not in _FEASIBLE_STATUSES:
        return {"solvable": False, "witness": {}, "members": []}

    # 一组完整见证
    witness: dict[str, str] = {}
    for m in members:
        mid = m["id"]
        witness[mid] = _genotype(
            solver.value(x1[mid]), solver.value(x2[mid])
        )

    # 逐成员、逐候选基因型做可行性检查：
    # 该基因型能出现在某一相容分配中，当且仅当追加约束后模型仍可行。
    result_members: list[dict[str, Any]] = []
    for m in members:
        mid = m["id"]
        possible: list[str] = []
        for geno in BLOOD_GENOS[m["blood"]]:
            if witness[mid] == geno:
                possible.append(geno)  # 见证已证明其可行，无需重复求解
                continue
            sub_model, sub_x1, sub_x2 = _build_model(members)
            sub_model.add_allowed_assignments(
                [sub_x1[mid], sub_x2[mid]], GENO_PAIRS[geno]
            )
            _, sub_status = _solve(sub_model, time_limit=5.0)
            if sub_status in _FEASIBLE_STATUSES:
                possible.append(geno)
        possible.sort(key=GENOTYPES.index)
        blood_types = sorted(
            {GENO_BLOOD[g] for g in possible}, key=BLOOD_TYPES.index
        )
        result_members.append(
            {"id": mid, "genotypes": possible, "blood_types": blood_types}
        )

    return {
        "solvable": True,
        "witness": witness,
        "members": result_members,
    }
