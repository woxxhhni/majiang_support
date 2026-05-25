const suits = [
  { id: "m", label: "万" },
  { id: "p", label: "筒" },
  { id: "s", label: "条" },
];

const hand = [];
const tilePool = document.querySelector("#tilePool");
const handEl = document.querySelector("#hand");
const handCount = document.querySelector("#handCount");
const stateText = document.querySelector("#stateText");
const result = document.querySelector("#result");
const resultStamp = document.querySelector("#resultStamp");

function tileLabel(tile) {
  return `${tile[0]}${suits.find((suit) => suit.id === tile[1]).label}`;
}

function tileSortValue(tile) {
  const suitValue = { m: 0, p: 1, s: 2 }[tile[1]];
  return suitValue * 10 + Number(tile[0]);
}

function tileCounts() {
  return hand.reduce((counts, tile) => {
    counts[tile] = (counts[tile] || 0) + 1;
    return counts;
  }, {});
}

function createTile(tile, options = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `tile ${tile[1]}`;
  button.draggable = !options.disabled;
  button.dataset.tile = tile;
  button.innerHTML = `<span><span class="rank">${tile[0]}</span><br><span class="suit">${tileLabel(tile).slice(1)}</span></span>`;
  button.setAttribute("aria-label", tileLabel(tile));
  if (options.disabled) {
    button.classList.add("used-up");
    button.disabled = true;
  }
  return button;
}

function renderPool() {
  tilePool.innerHTML = "";
  const counts = tileCounts();
  for (const suit of suits) {
    for (let rank = 1; rank <= 9; rank += 1) {
      const tile = `${rank}${suit.id}`;
      const button = createTile(tile, { disabled: (counts[tile] || 0) >= 4 });
      button.addEventListener("click", () => addTile(tile));
      button.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", JSON.stringify({ source: "pool", tile }));
      });
      tilePool.append(button);
    }
  }
}

function renderHand() {
  handEl.innerHTML = "";
  hand.forEach((tile, index) => {
    const button = createTile(tile);
    button.dataset.index = String(index);
    button.title = "点击移除，拖拽调整顺序";
    button.addEventListener("click", () => {
      hand.splice(index, 1);
      render();
    });
    button.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/plain", JSON.stringify({ source: "hand", index, tile }));
    });
    handEl.append(button);
  });

  handCount.textContent = `${hand.length} / 14`;
  if (hand.length === 14) {
    stateText.textContent = "可以分析";
  } else if (hand.length > 14) {
    stateText.textContent = "手牌过多";
  } else {
    stateText.textContent = "继续输入";
  }
}

function render() {
  renderPool();
  renderHand();
}

function addTile(tile) {
  if (hand.length >= 14) {
    stateText.textContent = "最多输入 14 张";
    return;
  }
  if ((tileCounts()[tile] || 0) >= 4) {
    stateText.textContent = `${tileLabel(tile)} 已经有 4 张`;
    return;
  }
  hand.push(tile);
  render();
}

function sortHand() {
  hand.sort((left, right) => tileSortValue(left) - tileSortValue(right));
  render();
}

function insertDraggedTile(payload, targetIndex = hand.length) {
  if (payload.source === "pool") {
    if (hand.length >= 14 || (tileCounts()[payload.tile] || 0) >= 4) {
      render();
      return;
    }
    hand.splice(targetIndex, 0, payload.tile);
  }

  if (payload.source === "hand") {
    const [tile] = hand.splice(payload.index, 1);
    const adjustedIndex = payload.index < targetIndex ? targetIndex - 1 : targetIndex;
    hand.splice(Math.max(0, adjustedIndex), 0, tile);
  }
  render();
}

handEl.addEventListener("dragover", (event) => {
  event.preventDefault();
  handEl.classList.add("drag-over");
});

handEl.addEventListener("dragleave", () => {
  handEl.classList.remove("drag-over");
});

handEl.addEventListener("drop", (event) => {
  event.preventDefault();
  handEl.classList.remove("drag-over");
  const raw = event.dataTransfer.getData("text/plain");
  if (!raw) return;
  const payload = JSON.parse(raw);
  const target = event.target.closest(".tile");
  const targetIndex = target ? Number(target.dataset.index) : hand.length;
  insertDraggedTile(payload, targetIndex);
});

document.querySelector("#sortHand").addEventListener("click", sortHand);

document.querySelector("#suggestMissing").addEventListener("click", async () => {
  if (hand.length === 0) {
    result.className = "result";
    result.innerHTML = `<div class="error">先输入手牌，再推荐定缺。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }

  result.className = "result";
  result.innerHTML = "正在推荐定缺...";

  const response = await fetch("/api/recommend-dingque", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ hand }),
  });
  const payload = await response.json();

  if (!response.ok) {
    result.innerHTML = `<div class="error">${payload.error || "推荐定缺失败"}</div>`;
    resultStamp.textContent = "失败";
    return;
  }

  document.querySelector("#missingSuit").value = payload.best.suit;
  showDingQueResult(payload);
});

document.querySelector("#clearHand").addEventListener("click", () => {
  hand.splice(0, hand.length);
  result.className = "result empty";
  result.textContent = "输入 14 张手牌并点击确认分析，推荐结果会显示在这里。";
  resultStamp.textContent = "未分析";
  render();
});

document.querySelector("#analyze").addEventListener("click", async () => {
  if (hand.length !== 14) {
    result.className = "result";
    result.innerHTML = `<div class="error">现在是 ${hand.length} 张手牌，需要 14 张才能分析。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }

  result.className = "result";
  result.innerHTML = "正在分析...";

  const response = await fetch("/api/recommend", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hand,
      missing: document.querySelector("#missingSuit").value,
    }),
  });
  const payload = await response.json();

  if (!response.ok) {
    result.innerHTML = `<div class="error">${payload.error || "分析失败"}</div>`;
    resultStamp.textContent = "失败";
    return;
  }

  showResult(payload);
});

function showResult(payload) {
  resultStamp.textContent = "已输出";
  const notice = payload.missing_suit_active
    ? `<div class="notice">定缺还没打完，候选牌已限制在缺门内。</div>`
    : "";
  const candidates = payload.candidates
    .map(
      (candidate) => `
        <div class="candidate">
          <div class="candidate-head">
            <span>${candidate.label}</span>
            <span>${candidate.score}</span>
          </div>
          <div class="metrics">
            <span>向听 ${candidate.shanten}</span>
            <span>进张 ${candidate.effective_count}</span>
            <span>结构 ${candidate.structure_score}</span>
          </div>
        </div>
      `,
    )
    .join("");

  result.innerHTML = `
    ${notice}
    <div class="best">
      推荐打
      <strong>${payload.best.label}</strong>
    </div>
    <ol class="reasons">
      ${payload.best.reasons.map((reason) => `<li>${reason}</li>`).join("")}
    </ol>
    <div class="candidate-list">
      ${candidates}
    </div>
  `;
}

function showDingQueResult(payload) {
  resultStamp.textContent = "已推荐定缺";
  const candidates = payload.candidates
    .map(
      (candidate) => `
        <div class="candidate">
          <div class="candidate-head">
            <span>缺${candidate.label}</span>
            <span>${candidate.score}</span>
          </div>
          <div class="metrics">
            <span>张数 ${candidate.tile_count}</span>
            <span>结构 ${candidate.structure_value}</span>
            <span>成本越低越好</span>
          </div>
        </div>
      `,
    )
    .join("");

  result.innerHTML = `
    <div class="best">
      推荐定缺
      <strong>${payload.best.label}</strong>
    </div>
    <ol class="reasons">
      ${payload.best.reasons.map((reason) => `<li>${reason}</li>`).join("")}
    </ol>
    <div class="candidate-list">
      ${candidates}
    </div>
  `;
}

render();
