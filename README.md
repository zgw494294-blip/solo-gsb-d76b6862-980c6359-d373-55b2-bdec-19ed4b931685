# ABO 家系推演台

可**完全离线**使用的 ABO 血型家系推演工具：在浏览器中录入家系成员及其血型，
后端用 **OR-Tools CP-SAT** 对整张家系联立求解，给出

- 每名成员在**全家相容分配**中可能出现的**基因型**与**血型**；
- 一组**完整见证**（所有成员的一组可行基因型）；
- 约束互相矛盾时明确报告**无解**。

技术栈：FastAPI（接口）+ OR-Tools CP-SAT（联立求解）+ 原生 HTML / CSS / JavaScript（页面，无任何外部 CDN 依赖）。

## 快速开始（Docker / Compose，一条命令）

```bash
docker compose up --build
```

启动后在浏览器访问：

> **http://localhost:8000**

（默认端口 **8000**；如需修改，编辑 `docker-compose.yml` 中的 `ports`，如 `"8080:8000"` 后访问 `http://localhost:8080`。）

停止服务：`docker compose down`。

## 本地开发（不用 Docker）

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

同样访问 http://localhost:8000 。

## 使用规则

1. 录入 **2～18 名**成员，ID 必须唯一且非空。
2. 每名成员的血型可选 **A / B / AB / O / 未知**。
3. 父母两栏须**同时填写或同时留空**；填写时必须是**两名不同的、已录入的**成员。
4. 亲子关系**不得成环**（任何人不能是自己的祖先）。
5. 遗传模型：等位基因仅 A、B、O；A 型＝AA/AO，B 型＝BB/BO，AB＝AB，O＝OO；
   孩子从双亲**各继承一个**等位基因。

页面提供「载入示例（有解）」与「载入示例（无解）」两个演示家系，
可直接体验联立推理（例如：A 型母亲与 AB 型父亲生出 B 型孩子，可推出母亲必为 AO）。

## 接口

`POST /api/solve`

```json
{
  "members": [
    {"id": "父亲", "blood": "AB", "parents": []},
    {"id": "母亲", "blood": "O",  "parents": []},
    {"id": "孩子", "blood": "O",  "parents": ["父亲", "母亲"]}
  ]
}
```

- 录入非法：`{"ok": false, "errors": ["..."]}`
- 无解：`{"ok": true, "solvable": false, ...}`
- 有解：`{"ok": true, "solvable": true, "witness": {"父亲": "AB", ...},
  "members": [{"id": "父亲", "genotypes": ["AB"], "blood_types": ["AB"]}, ...]}`

其中 `genotypes` 是该成员在**所有**相容分配中能够出现的基因型集合
（通过对每个候选基因型追加约束后做可行性检查得到），`witness` 是其中一组完整解。

## 目录结构

```
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── app/
    ├── main.py        # FastAPI 入口：/api/solve 接口 + 静态页面托管
    ├── solver.py      # CP-SAT 建模、录入校验、逐基因型可行性枚举
    └── static/
        ├── index.html # 页面结构
        ├── style.css  # 样式
        └── app.js     # 原生 JS：家系编辑、调用接口、渲染结果
```
