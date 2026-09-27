# ABO 家系推演台

离线可用的家系血型推演工具：录入 2～18 名成员及其血型（A / B / AB / O / 未知）与亲子关系，
后端用 OR-Tools CP-SAT 联立整张家系的遗传约束，给出：

- 每名成员在**全部相容分配**中可能的基因型（AA / AB / AO / BB / BO / OO）与血型；
- 一组满足全部约束的**完整见证**（每个人的一种具体基因型分配）；
- 约束相互矛盾时明确报**无解**。

## 遗传模型

- 等位基因仅 A、B、O：A 型 = AA/AO，B 型 = BB/BO，AB 型 = AB，O 型 = OO；
- 孩子从双亲各继承一个等位基因；
- 有父母记录的成员须指定两名不同且已录入的父母，亲子关系不得成环。

## 启动（Docker，一条命令）

```bash
docker compose up --build
```

启动后在浏览器访问：**http://localhost:8000**

停止：`docker compose down`。

## 本地开发（不用 Docker）

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

同样访问 http://localhost:8000 。

## 接口

`POST /api/solve`

```json
{
  "members": [
    {"id": "父亲", "blood_type": "A", "father": null, "mother": null},
    {"id": "母亲", "blood_type": "B", "father": null, "mother": null},
    {"id": "孩子", "blood_type": "unknown", "father": "父亲", "mother": "母亲"}
  ]
}
```

- `blood_type` 取值：`A` / `B` / `AB` / `O` / `unknown`；
- `father` / `mother` 同时填写（已录入的其他成员 ID）或同时为 `null`。

响应：

- 有解：`{"status": "ok", "members": [{id, blood_type, possible_genotypes, possible_phenotypes}], "witness": {id: 基因型}}`
- 无解：`{"status": "no_solution", "message": "..."}`
- 录入非法：HTTP 400，`{"status": "error", "message": "..."}`

## 目录结构

```
app/
  main.py            FastAPI 入口与接口
  solver.py          CP-SAT 建模、校验与求解
  static/            原生 HTML / CSS / JavaScript 页面
Dockerfile
docker-compose.yml
requirements.txt
```
