"use strict";

/* ============================ 常量 ============================ */

const BLOODS = ["unknown", "A", "B", "AB", "O"];
const BLOOD_LABEL = {
  unknown: "未知",
  A: "A 型",
  B: "B 型",
  AB: "AB 型",
  O: "O 型",
};
const GENO_BLOOD = {
  AA: "A", AO: "A",
  BB: "B", BO: "B",
  AB: "AB",
  OO: "O",
};
const MAX_MEMBERS = 18;

/* ============================ 示例 ============================ */

// 有解示例：三代家系。孩子二是 B 型而妈妈是 A 型，
// 可推出妈妈必须携带 O（妈妈为 AO），展示联立推理。
const SAMPLE_SOLVABLE = [
  { id: "爷爷", blood: "A",  p1: "", p2: "" },
  { id: "奶奶", blood: "B",  p1: "", p2: "" },
  { id: "外公", blood: "O",  p1: "", p2: "" },
  { id: "外婆", blood: "A",  p1: "", p2: "" },
  { id: "爸爸", blood: "AB", p1: "爷爷", p2: "奶奶" },
  { id: "妈妈", blood: "A",  p1: "外公", p2: "外婆" },
  { id: "孩子一", blood: "AB", p1: "爸爸", p2: "妈妈" },
  { id: "孩子二", blood: "B",  p1: "爸爸", p2: "妈妈" },
];

// 无解示例：AB × O 的夫妇不可能生出 O 型孩子
const SAMPLE_UNSAT = [
  { id: "父亲", blood: "AB", p1: "", p2: "" },
  { id: "母亲", blood: "O",  p1: "", p2: "" },
  { id: "孩子", blood: "O",  p1: "父亲", p2: "母亲" },
];

/* ============================ 状态与 DOM ============================ */

let rows = []; // {id, blood, p1, p2}

const tbody = document.getElementById("member-tbody");
const resultBox = document.getElementById("result-box");
const btnSolve = document.getElementById("btn-solve");
const btnAdd = document.getElementById("btn-add");
const memberCount = document.getElementById("member-count");

/* ============================ 编辑器渲染 ============================ */

function availableParentIds(selfId) {
  const ids = [];
  for (const r of rows) {
    const id = r.id.trim();
    if (id && id !== selfId && !ids.includes(id)) ids.push(id);
  }
  return ids;
}

function render() {
  tbody.innerHTML = "";

  rows.forEach((row, i) => {
    const tr = document.createElement("tr");

    const tdNo = document.createElement("td");
    tdNo.className = "no";
    tdNo.textContent = String(i + 1);
    tr.appendChild(tdNo);

    // 成员 ID
    const tdId = document.createElement("td");
    const idInput = document.createElement("input");
    idInput.type = "text";
    idInput.value = row.id;
    idInput.maxLength = 30;
    idInput.placeholder = "如：爷爷";
    idInput.addEventListener("input", () => {
      row.id = idInput.value;
      refreshParentOptions();
    });
    tdId.appendChild(idInput);
    tr.appendChild(tdId);

    // 血型
    const tdBlood = document.createElement("td");
    const bloodSel = document.createElement("select");
    for (const b of BLOODS) {
      const opt = document.createElement("option");
      opt.value = b;
      opt.textContent = BLOOD_LABEL[b];
      bloodSel.appendChild(opt);
    }
    bloodSel.value = row.blood;
    bloodSel.addEventListener("change", () => { row.blood = bloodSel.value; });
    tdBlood.appendChild(bloodSel);
    tr.appendChild(tdBlood);

    // 父母① / 父母②
    for (const key of ["p1", "p2"]) {
      const td = document.createElement("td");
      const sel = document.createElement("select");
      sel.dataset.key = key;
      sel.dataset.idx = String(i);
      sel.addEventListener("change", () => { row[key] = sel.value; });
      td.appendChild(sel);
      tr.appendChild(td);
    }

    // 删除
    const tdDel = document.createElement("td");
    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "del";
    delBtn.title = "删除该成员";
    delBtn.textContent = "✕";
    delBtn.addEventListener("click", () => {
      rows.splice(i, 1);
      render();
    });
    tdDel.appendChild(delBtn);
    tr.appendChild(tdDel);

    tbody.appendChild(tr);
  });

  refreshParentOptions();
  memberCount.textContent = `当前 ${rows.length} 名成员（允许 2～18 名）`;
  btnAdd.disabled = rows.length >= MAX_MEMBERS;
}

// ID 变化时只重建下拉选项，避免打断正在输入 ID 的光标
function refreshParentOptions() {
  const selects = tbody.querySelectorAll("select[data-key]");
  selects.forEach((sel) => {
    const i = Number(sel.dataset.idx);
    const row = rows[i];
    const key = sel.dataset.key;
    const previous = row[key];

    sel.innerHTML = "";
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "（无 / 未知）";
    sel.appendChild(none);
    for (const id of availableParentIds(row.id.trim())) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = id;
      sel.appendChild(opt);
    }

    if (previous && Array.from(sel.options).some((o) => o.value === previous)) {
      sel.value = previous;
    } else {
      sel.value = "";
      row[key] = "";
    }
  });
}

/* ============================ 工具按钮 ============================ */

btnAdd.addEventListener("click", () => {
  if (rows.length >= MAX_MEMBERS) return;
  rows.push({ id: "", blood: "unknown", p1: "", p2: "" });
  render();
});

document.getElementById("btn-clear").addEventListener("click", () => {
  rows = [];
  render();
  resultBox.innerHTML = '<p class="muted">尚未推演。编辑家系后点击「开始推演」。</p>';
});

function loadSample(sample) {
  rows = sample.map((r) => ({ id: r.id, blood: r.blood, p1: r.p1, p2: r.p2 }));
  render();
  resultBox.innerHTML =
    '<p class="muted">已载入示例，点击「开始推演」查看结果。</p>';
}
document.getElementById("btn-sample").addEventListener("click", () => loadSample(SAMPLE_SOLVABLE));
document.getElementById("btn-sample-unsat").addEventListener("click", () => loadSample(SAMPLE_UNSAT));

/* ============================ 求解 ============================ */

btnSolve.addEventListener("click", async () => {
  btnSolve.disabled = true;
  const oldText = btnSolve.textContent;
  btnSolve.textContent = "推演中…";
  try {
    const payload = {
      members: rows.map((r) => ({
        id: r.id.trim(),
        blood: r.blood,
        parents: [r.p1, r.p2].filter((x) => x),
      })),
    };
    const res = await fetch("/api/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    renderResult(data);
  } catch (err) {
    resultBox.innerHTML =
      `<div class="banner error">请求后端失败：${escapeHtml(String(err))}</div>`;
  } finally {
    btnSolve.disabled = false;
    btnSolve.textContent = oldText;
  }
});

function renderResult(data) {
  if (!data.ok) {
    const items = data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("");
    resultBox.innerHTML =
      '<div class="banner input-error">录入有误，请先修正以下问题：</div>'
      + `<ul class="errors">${items}</ul>`;
    return;
  }

  if (!data.solvable) {
    resultBox.innerHTML =
      '<div class="banner unsat">✖ 无解：不存在同时满足全部血型记录与遗传约束的基因型分配。'
      + "请核对血型录入或亲子关系（例如 AB 型与 O 型父母不可能生育 O 型孩子）。</div>";
    return;
  }

  const declaredById = {};
  rows.forEach((r) => { declaredById[r.id.trim()] = r.blood; });

  let html =
    '<div class="banner ok">✔ 有解。下表列出每名成员在 <strong>全家相容分配</strong> 中'
    + "可能出现的基因型与血型，并给出一组完整见证（各成员的具体可行基因型）。</div>";
  html +=
    '<div class="table-wrap"><table class="grid result"><thead><tr>'
    + "<th>成员</th><th>录入血型</th><th>可能基因型</th><th>可能血型</th>"
    + "<th>见证基因型</th></tr></thead><tbody>";

  for (const m of data.members) {
    const chips = m.genotypes.map((g) => `<span class="chip">${g}</span>`).join("");
    const certain = m.genotypes.length === 1
      ? '<span class="tag">唯一确定</span>' : "";
    const bloods = m.blood_types.map((b) => BLOOD_LABEL[b] || `${b} 型`).join("、");
    const w = data.witness[m.id];
    const declared = BLOOD_LABEL[declaredById[m.id]] || BLOOD_LABEL.unknown;
    html +=
      `<tr>`
      + `<td class="mid">${escapeHtml(m.id)}</td>`
      + `<td>${declared}</td>`
      + `<td>${chips}${certain}</td>`
      + `<td>${bloods}</td>`
      + `<td><span class="chip witness">${w}</span>`
      + `<span class="muted">（${GENO_BLOOD[w]} 型）</span></td>`
      + `</tr>`;
  }
  html += "</tbody></table></div>";
  resultBox.innerHTML = html;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

/* ============================ 初始化 ============================ */

render();
loadSample(SAMPLE_SOLVABLE);
