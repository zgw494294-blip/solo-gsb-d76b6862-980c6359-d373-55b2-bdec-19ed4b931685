"""ABO 家系推演核心：用 OR-Tools CP-SAT 联立整张家系的约束并求解。

等位基因编码：A=0, B=1, O=2。
基因型用有序对 (a1, a2) 且 a1 <= a2 表示，共 6 种：
    AA=(0,0) AB=(0,1) AO=(0,2) BB=(1,1) BO=(1,2) OO=(2,2)
血型（表现型）：
    AA/AO -> A, BB/BO -> B, AB -> AB, OO -> O
"""
from ortools.sat.python import cp_model

ALLELE_NAMES = ["A", "B", "O"]
GENOTYPES = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2)]
GENOTYPE_NAMES = ["AA", "AB", "AO", "BB", "BO", "OO"]

# 每种录入血型允许的基因型下标
ALLOWED_BY_PHENOTYPE = {
    "A": [0, 2],       # AA, AO
    "B": [3, 4],       # BB, BO
    "AB": [1],         # AB
    "O": [5],          # OO
    "unknown": [0, 1, 2, 3, 4, 5],
}

VALID_BLOOD_TYPES = set(ALLOWED_BY_PHENOTYPE.keys())


def genotype_phenotype(g):
    """由基因型有序对推出血型。"""
    a, b = g
    if a == b:
        return {0: "A", 1: "B", 2: "O"}[a]
    if (a, b) == (0, 1):
        return "AB"
    # AO -> A, BO -> B（O 为隐性）
    return "A" if 0 in (a, b) else "B"


def validate_members(members):
    """校验录入数据，返回错误信息字符串；合法时返回 None。"""
    if not isinstance(members, list) or not (2 <= len(members) <= 18):
        return "成员数量须在 2～18 名之间"

    ids = []
    for m in members:
        mid = (m.get("id") or "").strip()
        if not mid:
            return "存在未填写 ID 的成员"
        ids.append(mid)
    if len(set(ids)) != len(ids):
        return "成员 ID 必须唯一"
    idset = set(ids)

    for m in members:
        mid = m["id"].strip()
        bt = (m.get("blood_type") or "unknown").strip()
        if bt not in VALID_BLOOD_TYPES:
            return f"成员 {mid} 的血型取值非法（应为 A/B/AB/O/unknown）"
        father = (m.get("father") or "").strip()
        mother = (m.get("mother") or "").strip()
        if bool(father) != bool(mother):
            return f"成员 {mid} 须同时填写父亲和母亲，或两者都不填"
        if father:
            if father == mother:
                return f"成员 {mid} 的两名父母不能是同一人"
            for p in (father, mother):
                if p == mid:
                    return f"成员 {mid} 不能是自己的父母"
                if p not in idset:
                    return f"成员 {mid} 的父母 {p} 尚未录入"

    # 亲子关系不得成环：沿 孩子->父母 方向做 DFS 三色标记
    parent_map = {}
    for m in members:
        f = (m.get("father") or "").strip()
        mo = (m.get("mother") or "").strip()
        parent_map[m["id"].strip()] = [p for p in (f, mo) if p]

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {i: WHITE for i in idset}

    def dfs(u):
        color[u] = GRAY
        for v in parent_map.get(u, []):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False

    for u in idset:
        if color[u] == WHITE and dfs(u):
            return "亲子关系存在环，请检查父母指向"
    return None


def build_model(members, fixed=None):
    """构建 CP-SAT 模型。

    fixed: 可选的 {成员下标: 基因型下标}，用于逐基因型探测可能性。
    返回 (model, a1_vars, a2_vars)。
    """
    model = cp_model.CpModel()
    index = {m["id"].strip(): i for i, m in enumerate(members)}
    a1, a2 = [], []

    for i, m in enumerate(members):
        x = model.NewIntVar(0, 2, f"a1_{i}")
        y = model.NewIntVar(0, 2, f"a2_{i}")
        model.Add(x <= y)  # 规范化，消除 (A,O)/(O,A) 这类对称
        a1.append(x)
        a2.append(y)

        bt = (m.get("blood_type") or "unknown").strip()
        allowed = ALLOWED_BY_PHENOTYPE[bt]
        if len(allowed) < len(GENOTYPES):
            flags = []
            for g in allowed:
                ga, gb = GENOTYPES[g]
                b = model.NewBoolVar(f"g_{i}_{g}")
                model.Add(x == ga).OnlyEnforceIf(b)
                model.Add(y == gb).OnlyEnforceIf(b)
                flags.append(b)
            model.AddExactlyOne(flags)

    # 遗传约束：孩子从双亲各继承一个等位基因
    for i, m in enumerate(members):
        f = (m.get("father") or "").strip()
        mo = (m.get("mother") or "").strip()
        if not f:
            continue
        p, q = index[f], index[mo]

        pick_f = model.NewBoolVar(f"pickf_{i}")
        inh_f = model.NewIntVar(0, 2, f"inhf_{i}")
        model.AddElement(pick_f, [a1[p], a2[p]], inh_f)

        pick_m = model.NewBoolVar(f"pickm_{i}")
        inh_m = model.NewIntVar(0, 2, f"inhm_{i}")
        model.AddElement(pick_m, [a1[q], a2[q]], inh_m)

        # 孩子基因型 = 两个继承等位基因排序后的结果
        lo = model.NewIntVar(0, 2, f"lo_{i}")
        hi = model.NewIntVar(0, 2, f"hi_{i}")
        model.AddMinEquality(lo, [inh_f, inh_m])
        model.AddMaxEquality(hi, [inh_f, inh_m])
        model.Add(a1[i] == lo)
        model.Add(a2[i] == hi)

    for i, g in (fixed or {}).items():
        ga, gb = GENOTYPES[g]
        model.Add(a1[i] == ga)
        model.Add(a2[i] == gb)

    return model, a1, a2


def _solve(model, time_limit=5.0):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 1  # 结果可复现
    status = solver.Solve(model)
    return solver, status


def solve_family(members):
    """联立求解整张家系。

    返回：
      有解: {"status": "ok",
             "members": [{id, blood_type, possible_genotypes, possible_phenotypes}],
             "witness": {id: 基因型}}
      无解: {"status": "no_solution"}
    """
    model, a1, a2 = build_model(members)
    solver, status = _solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "no_solution"}

    # 一组完整见证
    witness = {}
    for i, m in enumerate(members):
        g = (solver.Value(a1[i]), solver.Value(a2[i]))
        witness[m["id"].strip()] = GENOTYPE_NAMES[GENOTYPES.index(g)]

    # 逐成员、逐基因型探测：在全部相容分配中该成员能否取该基因型
    result_members = []
    for i, m in enumerate(members):
        possible_g = []
        for gi, g in enumerate(GENOTYPES):
            probe, _, _ = build_model(members, fixed={i: gi})
            _, st = _solve(probe, time_limit=2.0)
            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                possible_g.append(GENOTYPE_NAMES[gi])
        possible_p = sorted(
            {genotype_phenotype(GENOTYPES[GENOTYPE_NAMES.index(name)])
             for name in possible_g},
            key=lambda x: ["A", "B", "AB", "O"].index(x),
        )
        result_members.append({
            "id": m["id"].strip(),
            "blood_type": (m.get("blood_type") or "unknown").strip(),
            "possible_genotypes": possible_g,
            "possible_phenotypes": possible_p,
        })

    return {"status": "ok", "members": result_members, "witness": witness}
