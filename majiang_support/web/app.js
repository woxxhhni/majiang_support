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
const screenshotInput = document.querySelector("#screenshotInput");
const screenshotPreview = document.querySelector("#screenshotPreview");
const handCaptures = document.querySelector("#handCaptures");
const discardCaptures = document.querySelector("#discardCaptures");
let screenshotImage = null;
let screenshotDataUrl = "";
let screenshotHandTiles = [];
let screenshotDiscardTiles = [];

function populateIncomingTileSelect() {
  const select = document.querySelector("#incomingTile");
  select.innerHTML = "";
  for (const suit of suits) {
    for (let rank = 1; rank <= 9; rank += 1) {
      const tile = `${rank}${suit.id}`;
      const option = document.createElement("option");
      option.value = tile;
      option.textContent = tileLabel(tile);
      select.append(option);
    }
  }
}

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
  const counter = options.countText ? `<span class="tile-count">${options.countText}</span>` : "";
  button.innerHTML = `
    ${counter}
    <span><span class="rank">${tile[0]}</span><br><span class="suit">${tileLabel(tile).slice(1)}</span></span>
  `;
  const countLabel = options.countText ? `，已选 ${options.countText}` : "";
  button.setAttribute("aria-label", `${tileLabel(tile)}${countLabel}`);
  if (options.disabled) {
    button.classList.add("used-up");
    button.disabled = true;
    button.draggable = false;
  }
  return button;
}

function renderPool() {
  tilePool.innerHTML = "";
  const counts = tileCounts();
  for (const suit of suits) {
    for (let rank = 1; rank <= 9; rank += 1) {
      const tile = `${rank}${suit.id}`;
      const selectedCount = counts[tile] || 0;
      const button = createTile(tile, {
        disabled: selectedCount >= 4,
        countText: `${selectedCount}/4`,
      });
      button.addEventListener("click", () => addTile(tile));
      button.addEventListener("dragstart", (event) => {
        if (selectedCount >= 4) {
          event.preventDefault();
          return;
        }
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

function randomInt(maxExclusive) {
  return Math.floor(Math.random() * maxExclusive);
}

function generateRandomReadyMissingHand() {
  const missingSuit = suits[randomInt(suits.length)].id;
  const availableTiles = [];
  for (const suit of suits) {
    if (suit.id === missingSuit) continue;
    for (let rank = 1; rank <= 9; rank += 1) {
      const tile = `${rank}${suit.id}`;
      for (let copy = 0; copy < 4; copy += 1) {
        availableTiles.push(tile);
      }
    }
  }

  hand.splice(0, hand.length);
  while (hand.length < 14) {
    const index = randomInt(availableTiles.length);
    const [tile] = availableTiles.splice(index, 1);
    hand.push(tile);
  }

  document.querySelector("#missingSuit").value = missingSuit;
  sortHand();
  result.className = "result empty";
  result.textContent = `已随机生成 14 张，并自动定缺${suits.find((suit) => suit.id === missingSuit).label}。点击确认分析查看结果。`;
  resultStamp.textContent = "已生成";
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

document.querySelector("#randomHand").addEventListener("click", generateRandomReadyMissingHand);

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

document.querySelector("#analyzeAction").addEventListener("click", async () => {
  const scene = document.querySelector("#actionScene").value;
  if (scene === "after_draw" && hand.length !== 14) {
    result.className = "result";
    result.innerHTML = `<div class="error">我摸牌后需要 14 张手牌。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }
  if (scene === "after_discard" && hand.length !== 13) {
    result.className = "result";
    result.innerHTML = `<div class="error">别人打牌后通常需要输入你当前 13 张手牌。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }

  result.className = "result";
  result.innerHTML = "正在分析碰杠...";
  const response = await fetch("/api/recommend-action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      hand,
      missing: document.querySelector("#missingSuit").value,
      scene,
      incoming: document.querySelector("#incomingTile").value,
    }),
  });
  const payload = await response.json();

  if (!response.ok) {
    result.innerHTML = `<div class="error">${payload.error || "动作分析失败"}</div>`;
    resultStamp.textContent = "失败";
    return;
  }

  showActionResult(payload);
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
            <span>弃牌价值 ${candidate.discard_value}</span>
            <span>路线 ${candidate.best_route.label}</span>
            <span>EV ${candidate.ev.toFixed(3)}</span>
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
    <div class="candidate">
      <div class="candidate-head">
        <span>推荐路线：${payload.best.best_route.label}</span>
        <span>EV ${payload.best.ev.toFixed(3)}</span>
      </div>
      <div class="metrics">
        <span>番数 ${payload.best.best_route.fan}</span>
        <span>概率 ${payload.best.best_route.probability.toFixed(3)}</span>
        <span>进张 ${payload.best.best_route.effective_count}</span>
      </div>
    </div>
    <ol class="reasons">
      ${payload.best.reasons.map((reason) => `<li>${reason}</li>`).join("")}
    </ol>
    <div class="candidate-list">
      ${payload.best.routes
        .map(
          (route) => `
            <div class="candidate">
              <div class="candidate-head">
                <span>${route.label}</span>
                <span>EV ${route.ev.toFixed(3)}</span>
              </div>
              <div class="metrics">
                <span>向听 ${route.shanten}</span>
                <span>番数 ${route.fan}</span>
                <span>进张 ${route.effective_count}</span>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
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

function showActionResult(payload) {
  resultStamp.textContent = "已分析动作";
  const candidates = payload.candidates
    .map(
      (candidate) => `
        <div class="candidate">
          <div class="candidate-head">
            <span>${candidate.label}</span>
            <span>${candidate.delta.toFixed(3)}</span>
          </div>
          <div class="metrics">
            <span>前 ${candidate.ev_before.toFixed(3)}</span>
            <span>后 ${candidate.ev_after.toFixed(3)}</span>
            <span>路线 ${candidate.route.label}</span>
          </div>
          ${
            candidate.discard
              ? `<div class="notice">后续推荐打：${candidate.discard.best.label}</div>`
              : ""
          }
        </div>
      `,
    )
    .join("");

  result.innerHTML = `
    <div class="best">
      推荐动作
      <strong>${payload.best.label}</strong>
    </div>
    <div class="candidate">
      <div class="candidate-head">
        <span>动作收益差</span>
        <span>${payload.best.delta.toFixed(3)}</span>
      </div>
      <div class="metrics">
        <span>动作前 ${payload.best.ev_before.toFixed(3)}</span>
        <span>动作后 ${payload.best.ev_after.toFixed(3)}</span>
        <span>路线 ${payload.best.route.label}</span>
      </div>
    </div>
    <ol class="reasons">
      ${payload.best.reasons.map((reason) => `<li>${reason}</li>`).join("")}
    </ol>
    <div class="candidate-list">
      ${candidates}
    </div>
  `;
}

function allTileOptions() {
  const options = ['<option value="">待确认</option>'];
  for (const suit of suits) {
    for (let rank = 1; rank <= 9; rank += 1) {
      const tile = `${rank}${suit.id}`;
      options.push(`<option value="${tile}">${tileLabel(tile)}</option>`);
    }
  }
  return options.join("");
}

screenshotInput.addEventListener("change", () => {
  const file = screenshotInput.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  const image = new Image();
  image.onload = () => {
    screenshotImage = image;
    screenshotPreview.innerHTML = "";
    screenshotPreview.append(image);
    handCaptures.innerHTML = "";
    discardCaptures.innerHTML = "";
    screenshotHandTiles = [];
    screenshotDiscardTiles = [];
    result.className = "result empty";
    result.textContent = "截图已加载，点击识别截图。第一版会切出牌面，需要你确认牌名。";
    resultStamp.textContent = "截图已加载";
  };
  reader.onload = () => {
    screenshotDataUrl = String(reader.result || "");
    image.src = screenshotDataUrl;
  };
  reader.readAsDataURL(file);
});

document.querySelector("#scanScreenshot").addEventListener("click", async () => {
  if (!screenshotImage) {
    result.className = "result";
    result.innerHTML = `<div class="error">先上传截图。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }
  result.className = "result";
  result.innerHTML = "正在裁剪截图并调用识别模型...";
  resultStamp.textContent = "识别中";

  screenshotHandTiles = extractHandTiles(screenshotImage);
  screenshotDiscardTiles = extractDiscardTiles(screenshotImage);

  let modelPayload = null;
  try {
    const response = await fetch("/api/detect-screenshot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: screenshotDataUrl }),
    });
    modelPayload = await response.json();
    if (!response.ok) throw new Error(modelPayload.error || "模型识别失败");
  } catch (error) {
    renderCaptureCards(handCaptures, screenshotHandTiles, "handCapture");
    renderCaptureCards(discardCaptures, screenshotDiscardTiles, "discardCapture");
    result.className = "result";
    result.innerHTML = `<div class="error">${error.message}</div>`;
    resultStamp.textContent = "识别失败";
    return;
  }

  renderCaptureCards(handCaptures, screenshotHandTiles, "handCapture", modelPayload.hand.tiles);
  renderCaptureCards(discardCaptures, screenshotDiscardTiles, "discardCapture", modelPayload.discards.tiles);
  result.className = "result empty";
  result.textContent = `模型识别到手牌 ${modelPayload.hand.tiles.length} 张，牌河区域 ${modelPayload.discards.tiles.length} 张。请检查牌名，确认后导入手牌。`;
  resultStamp.textContent = "已识别截图";
});

document.querySelector("#importScreenshotHand").addEventListener("click", () => {
  const selectedTiles = [...document.querySelectorAll("#handCaptures select")]
    .map((select) => select.value)
    .filter(Boolean);
  if (selectedTiles.length === 0) {
    result.className = "result";
    result.innerHTML = `<div class="error">请先在手牌截图里确认牌名。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }
  if (selectedTiles.length > 14) {
    result.className = "result";
    result.innerHTML = `<div class="error">截图手牌超过 14 张，请只保留自己的手牌。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }
  const counts = selectedTiles.reduce((acc, tile) => {
    acc[tile] = (acc[tile] || 0) + 1;
    return acc;
  }, {});
  const invalid = Object.entries(counts).find(([, count]) => count > 4);
  if (invalid) {
    result.className = "result";
    result.innerHTML = `<div class="error">${tileLabel(invalid[0])} 超过 4 张。</div>`;
    resultStamp.textContent = "未完成";
    return;
  }
  hand.splice(0, hand.length, ...selectedTiles);
  sortHand();
  result.className = "result empty";
  result.textContent = `已导入 ${selectedTiles.length} 张手牌。13 张时说明还没摸牌，摸到后补一张再确认分析。`;
  resultStamp.textContent = "已导入";
});

function renderCaptureCards(container, captures, namePrefix, predictions = []) {
  container.innerHTML = "";
  const options = allTileOptions();
  const count = Math.max(captures.length, predictions.length);
  for (let index = 0; index < count; index += 1) {
    const capture = captures[index];
    const predicted = normalizePredictedTile(predictions[index] || "");
    const card = document.createElement("div");
    card.className = "capture-card";
    card.innerHTML = `
      ${capture ? `<img src="${capture.url}" alt="${namePrefix} ${index + 1}" />` : `<div class="capture-placeholder">模型识别</div>`}
      <select aria-label="${namePrefix} ${index + 1}">
        ${options}
      </select>
      ${predicted ? `<span class="model-tag">模型：${tileLabel(predicted)}</span>` : `<span class="model-tag muted">未识别</span>`}
    `;
    const select = card.querySelector("select");
    if (predicted) {
      select.value = predicted;
    }
    container.append(card);
  }
}

function normalizePredictedTile(tile) {
  if (!tile || tile.length < 2) return "";
  const suit = tile.slice(-1);
  const rank = tile.slice(0, -1);
  if (!["m", "p", "s"].includes(suit)) return "";
  if (!/^[1-9]$/.test(rank)) return "";
  return `${rank}${suit}`;
}

function extractHandTiles(image) {
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d");
  context.drawImage(image, 0, 0);

  const width = canvas.width;
  const height = canvas.height;
  const regionX = Math.round(width * 0.015);
  const regionY = Math.round(height * 0.795);
  const regionW = Math.round(width * 0.940);
  const regionH = Math.round(height * 0.200);
  const region = cropCanvas(canvas, regionX, regionY, regionW, regionH);
  const rowSplit = extractHandTilesByRows(region, regionX, regionY, width, height);
  if (rowSplit.length >= 2 && rowSplit.length <= 14) {
    return rowSplit;
  }

  return extractHandTilesByGrid(canvas);
}

function extractHandTilesByRows(regionCanvas, offsetX, offsetY, imageWidth, imageHeight) {
  const expectedTileW = Math.round(imageWidth * 0.064);
  const expectedTileH = Math.round(imageHeight * 0.160);
  const components = findRawWhiteComponents(regionCanvas)
    .filter((component) => {
      const bottom = component.y + component.height;
      return (
        component.height >= expectedTileH * 0.72 &&
        component.width >= expectedTileW * 0.55 &&
        bottom >= regionCanvas.height * 0.72
      );
    })
    .sort((left, right) => left.x - right.x);

  const captures = [];
  for (const component of components) {
    const estimatedCount = Math.max(1, Math.min(14, Math.round(component.width / expectedTileW)));
    const slotW = component.width / estimatedCount;
    const bottomY = Math.min(regionCanvas.height - 1, component.y + component.height - 1);
    const topY = Math.max(0, bottomY - expectedTileH + 1);

    for (let index = 0; index < estimatedCount; index += 1) {
      const x1 = Math.round(component.x + index * slotW);
      const x2 = Math.round(index === estimatedCount - 1 ? component.x + component.width - 1 : component.x + (index + 1) * slotW - 1);
      const local = refineTileBox(regionCanvas, x1, x2, topY, bottomY);
      if (!local) continue;
      const crop = cropTightTile(regionCanvas, local, 2, 3);
      if (brightRatio(crop.canvas) > 0.22) {
        captures.push({
          url: crop.canvas.toDataURL("image/png"),
          x: offsetX + crop.x,
          y: offsetY + crop.y,
          width: crop.width,
          height: crop.height,
        });
      }
    }
  }

  return captures.sort((left, right) => left.x - right.x).slice(0, 14);
}

function extractHandTilesByProjection(regionCanvas, offsetX, offsetY) {
  const context = regionCanvas.getContext("2d");
  const { width, height } = regionCanvas;
  const data = context.getImageData(0, 0, width, height).data;
  const columnScores = new Array(width).fill(0);
  const rowScores = new Array(height).fill(0);

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const offset = (y * width + x) * 4;
      if (isHandTilePixel(data[offset], data[offset + 1], data[offset + 2])) {
        columnScores[x] += 1;
        rowScores[y] += 1;
      }
    }
  }

  const xRange = activeRange(smoothScores(columnScores, 7), height * 0.12);
  const yRange = activeRange(smoothScores(rowScores, 7), width * 0.10);
  if (!xRange || !yRange) return [];

  const handWidth = xRange.end - xRange.start + 1;
  const estimatedCount = Math.max(1, Math.min(14, Math.round(handWidth / (width * 0.069))));
  const tileStep = handWidth / estimatedCount;
  const captures = [];

  for (let index = 0; index < estimatedCount; index += 1) {
    const slotStart = Math.round(xRange.start + index * tileStep);
    const slotEnd = Math.round(index === estimatedCount - 1 ? xRange.end : xRange.start + (index + 1) * tileStep);
    const local = refineTileBox(regionCanvas, slotStart, slotEnd, yRange.start, yRange.end);
    if (!local) continue;
    const crop = cropTightTile(regionCanvas, local, 2, 3);
    if (brightRatio(crop.canvas) > 0.24) {
      captures.push({
        url: crop.canvas.toDataURL("image/png"),
        x: offsetX + crop.x,
        y: offsetY + crop.y,
        width: crop.width,
        height: crop.height,
      });
    }
  }

  return captures;
}

function isHandTilePixel(red, green, blue) {
  return red > 135 && green > 135 && blue > 125 && Math.max(red, green, blue) - Math.min(red, green, blue) < 95;
}

function smoothScores(scores, radius) {
  return scores.map((_, index) => {
    let total = 0;
    let count = 0;
    for (let delta = -radius; delta <= radius; delta += 1) {
      const at = index + delta;
      if (at >= 0 && at < scores.length) {
        total += scores[at];
        count += 1;
      }
    }
    return total / count;
  });
}

function activeRange(scores, threshold) {
  let start = -1;
  let end = -1;
  for (let index = 0; index < scores.length; index += 1) {
    if (scores[index] >= threshold) {
      if (start < 0) start = index;
      end = index;
    }
  }
  if (start < 0 || end <= start) return null;
  return { start, end };
}

function refineTileBox(regionCanvas, x1, x2, y1, y2) {
  const context = regionCanvas.getContext("2d");
  const data = context.getImageData(0, 0, regionCanvas.width, regionCanvas.height).data;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let pixels = 0;

  for (let y = y1; y <= y2; y += 1) {
    for (let x = x1; x <= x2; x += 1) {
      const offset = (y * regionCanvas.width + x) * 4;
      if (isHandTilePixel(data[offset], data[offset + 1], data[offset + 2])) {
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
        pixels += 1;
      }
    }
  }

  if (pixels < 600 || !Number.isFinite(minX)) return null;
  return { x1: minX, x2: maxX, y1: minY, y2: maxY };
}

function cropTightTile(source, box, padX, padY) {
  const x = Math.max(0, box.x1 - padX);
  const y = Math.max(0, box.y1 - padY);
  const width = Math.min(source.width - x, box.x2 - box.x1 + 1 + padX * 2);
  const height = Math.min(source.height - y, box.y2 - box.y1 + 1 + padY * 2);
  return {
    canvas: cropCanvas(source, x, y, width, height),
    x,
    y,
    width,
    height,
  };
}

function extractHandTilesByGrid(canvas) {
  const captures = [];
  const width = canvas.width;
  const height = canvas.height;
  const tileW = Math.round(width * 0.064);
  const tileH = Math.round(height * 0.16);
  const startX = Math.round(width * 0.022);
  const startY = Math.round(height * 0.825);
  const step = Math.round(width * 0.066);

  for (let index = 0; index < 14; index += 1) {
    const x = startX + index * step;
    const crop = cropCanvas(canvas, x, startY, tileW, tileH);
    if (brightRatio(crop) > 0.26) {
      captures.push({ url: crop.toDataURL("image/png"), x, y: startY });
    }
  }
  return captures;
}

function extractDiscardTiles(image) {
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d");
  context.drawImage(image, 0, 0);

  const width = canvas.width;
  const height = canvas.height;
  const regions = [
    [0.250, 0.115, 0.520, 0.250],
    [0.610, 0.270, 0.170, 0.350],
    [0.380, 0.510, 0.390, 0.180],
    [0.245, 0.300, 0.170, 0.360],
  ];
  const captures = [];
  for (const [rx, ry, rw, rh] of regions) {
    const region = cropCanvas(
      canvas,
      Math.round(width * rx),
      Math.round(height * ry),
      Math.round(width * rw),
      Math.round(height * rh),
    );
    captures.push(
      ...findWhiteTileComponents(region, Math.round(width * rx), Math.round(height * ry), {
        minPixels: 320,
        minWidth: Math.round(width * 0.018),
        minHeight: Math.round(height * 0.030),
        maxWidth: Math.round(width * 0.095),
        maxHeight: Math.round(height * 0.150),
        pad: 6,
        merge: true,
      }),
    );
  }
  return dedupeCaptures(captures).slice(0, 48);
}

function cropCanvas(source, x, y, width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(source, x, y, width, height, 0, 0, width, height);
  return canvas;
}

function brightRatio(canvas) {
  const data = canvas.getContext("2d").getImageData(0, 0, canvas.width, canvas.height).data;
  let bright = 0;
  for (let index = 0; index < data.length; index += 4) {
    if (data[index] > 185 && data[index + 1] > 185 && data[index + 2] > 175) bright += 1;
  }
  return bright / (data.length / 4);
}

function findWhiteTileComponents(regionCanvas, offsetX, offsetY, options = {}) {
  const minPixels = options.minPixels ?? 500;
  const minWidth = options.minWidth ?? 34;
  const minHeight = options.minHeight ?? 34;
  const maxWidth = options.maxWidth ?? 150;
  const maxHeight = options.maxHeight ?? 160;
  const pad = options.pad ?? 8;
  const context = regionCanvas.getContext("2d");
  const imageData = context.getImageData(0, 0, regionCanvas.width, regionCanvas.height);
  const data = imageData.data;
  const width = regionCanvas.width;
  const height = regionCanvas.height;
  const visited = new Uint8Array(width * height);
  const captures = [];

  function isTilePixel(index) {
    const offset = index * 4;
    return data[offset] > 185 && data[offset + 1] > 185 && data[offset + 2] > 170;
  }

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = y * width + x;
      if (visited[start] || !isTilePixel(start)) continue;
      const queue = [start];
      visited[start] = 1;
      let minX = x;
      let maxX = x;
      let minY = y;
      let maxY = y;
      let pixels = 0;

      while (queue.length) {
        const current = queue.pop();
        const cx = current % width;
        const cy = Math.floor(current / width);
        pixels += 1;
        minX = Math.min(minX, cx);
        maxX = Math.max(maxX, cx);
        minY = Math.min(minY, cy);
        maxY = Math.max(maxY, cy);

        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = cx + dx;
          const ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
          const next = ny * width + nx;
          if (!visited[next] && isTilePixel(next)) {
            visited[next] = 1;
            queue.push(next);
          }
        }
      }

      const boxW = maxX - minX + 1;
      const boxH = maxY - minY + 1;
      if (pixels > minPixels && boxW >= minWidth && boxH >= minHeight && boxW <= maxWidth && boxH <= maxHeight) {
        const crop = cropCanvas(
          regionCanvas,
          Math.max(0, minX - pad),
          Math.max(0, minY - pad),
          Math.min(regionCanvas.width - minX + pad, boxW + pad * 2),
          Math.min(regionCanvas.height - minY + pad, boxH + pad * 2),
        );
        captures.push({
          url: crop.toDataURL("image/png"),
          x: offsetX + minX,
          y: offsetY + minY,
          width: boxW,
          height: boxH,
        });
      }
    }
  }
  const sorted = captures.sort((left, right) => left.y - right.y || left.x - right.x);
  return options.merge ? mergeNearbyCaptures(sorted) : sorted;
}

function findRawWhiteComponents(regionCanvas) {
  const context = regionCanvas.getContext("2d");
  const imageData = context.getImageData(0, 0, regionCanvas.width, regionCanvas.height);
  const data = imageData.data;
  const width = regionCanvas.width;
  const height = regionCanvas.height;
  const visited = new Uint8Array(width * height);
  const components = [];

  function isTilePixel(index) {
    const offset = index * 4;
    return isHandTilePixel(data[offset], data[offset + 1], data[offset + 2]);
  }

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const start = y * width + x;
      if (visited[start] || !isTilePixel(start)) continue;
      const queue = [start];
      visited[start] = 1;
      let minX = x;
      let maxX = x;
      let minY = y;
      let maxY = y;
      let pixels = 0;

      while (queue.length) {
        const current = queue.pop();
        const cx = current % width;
        const cy = Math.floor(current / width);
        pixels += 1;
        minX = Math.min(minX, cx);
        maxX = Math.max(maxX, cx);
        minY = Math.min(minY, cy);
        maxY = Math.max(maxY, cy);

        for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nx = cx + dx;
          const ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
          const next = ny * width + nx;
          if (!visited[next] && isTilePixel(next)) {
            visited[next] = 1;
            queue.push(next);
          }
        }
      }

      if (pixels >= 900) {
        components.push({
          x: minX,
          y: minY,
          width: maxX - minX + 1,
          height: maxY - minY + 1,
          pixels,
        });
      }
    }
  }

  return components;
}

function mergeNearbyCaptures(captures) {
  const merged = [];
  for (const capture of captures) {
    const previous = merged[merged.length - 1];
    if (previous && Math.abs(capture.x - previous.x) < Math.max(capture.width, previous.width) * 0.45) {
      if (capture.width * capture.height > previous.width * previous.height) {
        merged[merged.length - 1] = capture;
      }
    } else {
      merged.push(capture);
    }
  }
  return merged;
}

function dedupeCaptures(captures) {
  const sorted = captures.sort((left, right) => left.y - right.y || left.x - right.x);
  const deduped = [];
  for (const capture of sorted) {
    const duplicate = deduped.find((item) => {
      const dx = Math.abs(item.x - capture.x);
      const dy = Math.abs(item.y - capture.y);
      return dx < Math.max(item.width, capture.width) * 0.35 && dy < Math.max(item.height, capture.height) * 0.35;
    });
    if (!duplicate) {
      deduped.push(capture);
    }
  }
  return deduped;
}

populateIncomingTileSelect();
render();
