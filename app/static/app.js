"use strict";

// ---------- 状态 ----------
let members = []; // {id, blood_type, father, mother}
const BLOOD_TYPES = [
  ["unknown", "未知"],
  ["A", "A"],
  ["B", "B"],
  ["AB", "AB"],
  ["O", "O"],
];
const GENO_TO_PHENO = { AA: "A", AO: "A", BB: "B", BO: "B", AB: "AB", OO: "O" };

const tbody = document.getElementById("member-tbody");
const countEl = document.getElementById("member-count");
const formError = document.getElementById("form-error");
const resultPanel = document.getElementById("result-panel");
const resultStatus = document.getElementById("result-status");
const resultBody = document.getElementById("result-body");
const solveBtn = document.getElementById("btn-solve");

// ---------- 渲染编辑表 ----------
function currentIds() {
  return members.map((m) => m.id.trim()).filter((x) => x);
}

function parentSelect(rowIdx, field) {
  const sel = document.createElement("select");
  const selfId = members[rowIdx].id.trim();
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "（无）";
  sel.appendChild(empty);
  for (const id of currentIds()) {
    if (id === selfId) continue;
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = id;
    sel.appendChild(opt);
  }
  const val = members[rowIdx][field];
  if (val && val !== selfId && currentIds().includes(val)) {
    sel.value = val;
  } else {
    members[rowIdx][field] = "";
  }
  sel.addEventListener("change", () => {
    members[rowIdx][field] = sel.value;
  });
  return sel;
}

function render() {
  tbody.innerHTML = "";
  members.forEach((m, i) => {
    const tr = document.createElement("tr");

    const tdNo = document.createElement("td");
    tdNo.textContent = i + 1;
    tr.appendChild(tdNo);

    const tdId = document.createElement("td");
    const idInput = document.createElement("input");
    idInput.type = "text";
    idInput.value = m.id;
    idInput.placeholder = "唯一 ID";
    idInput.addEventListener("input", () => { m.id = idInput.value; });
    idInput.addEventListener("change", render); // ID 变化后刷新父母下拉
    tdId.appendChild(idInput);
    tr.appendChild(tdId);

    const tdBt = document.createElement("td");
    const btSel = document.createElement("select");
    for (const [val, label] of BLOOD_TYPES) {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = label;
      btSel.appendChild(opt);
    }
    btSel.value = m.blood_type;
    btSel.addEventListener("change", () => { m.blood_type = btSel.value; });
    tdBt.appendChild(btSel);
    tr.appendChild(tdBt);

    const tdF = document.createElement("td");
    tdF.appendChild(parentSelect(i, "father"));
    tr.appendChild(tdF);

    const tdM = document.createElement("td");
    tdM.appendChild(parentSelect(i, "mother"));
    tr.appendChild(tdM);

    const tdOp = document.createElement("td");
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "删除";
    del.className = "danger";
    del.addEventListener("click", () => {
      members.splice(i, 1);
      render();
    });
    tdOp.appendChild(del);
    tr.appendChild(tdOp);

    tbody.appendChild(tr);
  });
  countEl.textContent = members.length;
}

// ---------- 前端校验（与后端规则一致） ----------
function validate() {
  if (members.length < 2 || members.length > 18) {
    return "成员数量须在 2～18 名之间";
  }
  const ids = members.map((m) => m.id.trim());
  if (ids.some((x) => !x)) return "存在未填写 ID 的成员";
  if (new Set(ids).size !== ids.length) return "成员 ID 必须唯一";
  const idset = new Set(ids);

  for (const m of members) {
    const id = m.id.trim();
    const f = m.father, mo = m.mother;
    if (Boolean(f) !== Boolean(mo)) {
      return `成员 ${id} 须同时填写父亲和母亲，或两者都不填`;
    }
    if (f) {
      if (f === mo) return `成员 ${id} 的两名父母不能是同一人`;
      if (f === id || mo === id) return `成员 ${id} 不能是自己的父母`;
      if (!idset.has(f) || !idset.has(mo)) {
        return `成员 ${id} 的父母必须已录入`;
      }
    }
  }

  // 成环检测（孩子 -> 父母 方向 DFS）
  const parentMap = {};
  for (const m of members) {
    parentMap[m.id.trim()] = [m.father, m.mother].filter(Boolean);
  }
  const color = {};
  const dfs = (u) => {
    color[u] = 1;
    for (const v of parentMap[u] || []) {
      if (color[v] === 1) return true;
      if (!color[v] && dfs(v)) return true;
    }
    color[u] = 2;
    return false;
  };
  for (const id of idset) {
    if (!color[id] && dfs(id)) return "亲子关系存在环，请检查父母指向";
  }
  return null;
}

// ---------- 结果渲染 ----------
function chip(text, cls) {
  const s = document.createElement("span");
  s.className = "chip" + (cls ? " " + cls : "");
  s.textContent = text;
  return s;
}

function bloodLabel(bt) {
  return bt === "unknown" ? "未知" : bt;
}

function renderResult(data) {
  resultPanel.hidden = false;
  resultStatus.innerHTML = "";
  resultBody.innerHTML = "";

  if (data.status === "error") {
    const b = document.createElement("div");
    b.className = "banner bad";
    b.textContent = "录入有误：" + data.message;
    resultStatus.appendChild(b);
    return;
  }
  if (data.status === "no_solution") {
    const b = document.createElement("div");
    b.className = "banner bad";
    b.textContent = "无解：" + (data.message || "不存在满足全部约束的分配。");
    resultStatus.appendChild(b);
    return;
  }

  const b = document.createElement("div");
  b.className = "banner ok";
  b.textContent = `有解：以下为 ${data.members.length} 名成员在全部相容分配中的可能取值。`;
  resultStatus.appendChild(b);

  const grid = document.createElement("div");
  grid.className = "result-grid";

  // 每人的可能基因型 / 血型
  const sec1 = document.createElement("div");
  sec1.innerHTML = "<h3>各成员可能的基因型与血型（联立全家约束后）</h3>";
  const t1 = document.createElement("table");
  t1.innerHTML = "<thead><tr><th>ID</th><th>录入血型</th><th>可能基因型</th><th>可能血型</th></tr></thead>";
  const tb1 = document.createElement("tbody");
  for (const m of data.members) {
    const tr = document.createElement("tr");
    const tdId = document.createElement("td");
    tdId.textContent = m.id;
    tr.appendChild(tdId);
    const tdBt = document.createElement("td");
    tdBt.appendChild(chip(bloodLabel(m.blood_type), "muted"));
    tr.appendChild(tdBt);
    const tdG = document.createElement("td");
    m.possible_genotypes.forEach((g) => tdG.appendChild(chip(g)));
    tr.appendChild(tdG);
    const tdP = document.createElement("td");
    m.possible_phenotypes.forEach((p) => tdP.appendChild(chip(p, "pheno")));
    tr.appendChild(tdP);
    tb1.appendChild(tr);
  }
  t1.appendChild(tb1);
  sec1.appendChild(t1);
  grid.appendChild(sec1);

  // 一组完整见证
  const sec2 = document.createElement("div");
  sec2.innerHTML = "<h3>一组完整见证（满足全部约束的一种分配）</h3>";
  const t2 = document.createElement("table");
  t2.innerHTML = "<thead><tr><th>ID</th><th>基因型</th><th>对应血型</th></tr></thead>";
  const tb2 = document.createElement("tbody");
  for (const m of data.members) {
    const g = data.witness[m.id];
    const tr = document.createElement("tr");
    const tdId = document.createElement("td");
    tdId.textContent = m.id;
    tr.appendChild(tdId);
    const tdG = document.createElement("td");
    tdG.appendChild(chip(g));
    tr.appendChild(tdG);
    const tdP = document.createElement("td");
    tdP.appendChild(chip(GENO_TO_PHENO[g] || "?", "pheno"));
    tr.appendChild(tdP);
    tb2.appendChild(tr);
  }
  t2.appendChild(tb2);
  sec2.appendChild(t2);
  grid.appendChild(sec2);

  resultBody.appendChild(grid);
}

// ---------- 求解 ----------
async function solve() {
  formError.textContent = "";
  const err = validate();
  if (err) {
    formError.textContent = err;
    return;
  }
  const payload = {
    members: members.map((m) => ({
      id: m.id.trim(),
      blood_type: m.blood_type,
      father: m.father || null,
      mother: m.mother || null,
    })),
  };
  solveBtn.disabled = true;
  solveBtn.textContent = "推演中…";
  try {
    const resp = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      renderResult({ status: "error", message: data.message || data.detail || "请求失败" });
    } else {
      renderResult(data);
    }
  } catch (e) {
    renderResult({ status: "error", message: "无法连接服务器：" + e.message });
  } finally {
    solveBtn.disabled = false;
    solveBtn.textContent = "② 开始推演";
  }
}

// ---------- 工具栏 ----------
document.getElementById("btn-add").addEventListener("click", () => {
  if (members.length >= 18) {
    formError.textContent = "最多 18 名成员";
    return;
  }
  formError.textContent = "";
  members.push({ id: "", blood_type: "unknown", father: "", mother: "" });
  render();
});

document.getElementById("btn-clear").addEventListener("click", () => {
  members = [];
  formError.textContent = "";
  resultPanel.hidden = true;
  render();
});

document.getElementById("btn-example").addEventListener("click", () => {
  members = [
    { id: "爷爷", blood_type: "unknown", father: "", mother: "" },
    { id: "奶奶", blood_type: "O", father: "", mother: "" },
    { id: "父亲", blood_type: "A", father: "爷爷", mother: "奶奶" },
    { id: "母亲", blood_type: "B", father: "", mother: "" },
    { id: "孩子甲", blood_type: "AB", father: "父亲", mother: "母亲" },
    { id: "孩子乙", blood_type: "O", father: "父亲", mother: "母亲" },
  ];
  formError.textContent = "";
  resultPanel.hidden = true;
  render();
});

solveBtn.addEventListener("click", solve);

// 初始给两行，方便直接上手
members = [
  { id: "", blood_type: "unknown", father: "", mother: "" },
  { id: "", blood_type: "unknown", father: "", mother: "" },
];
render();
