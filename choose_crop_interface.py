#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
DEFAULT_RECT = {"x": 1500, "y": 1400, "width": 3100, "height": 3900}
DEFAULT_OUTPUT = Path("crop_selection/crop_config.json")


HTML = r"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Cryobloc crop selector</title>
  <style>
    :root {
      --bg: #f5f5f2;
      --panel: #ffffff;
      --line: #d4d4cc;
      --text: #191918;
      --muted: #66665f;
      --accent: #d21f3c;
      --blue: #1769aa;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }
    .app {
      display: grid;
      grid-template-columns: 240px minmax(420px, 1fr) 300px;
      height: 100vh;
      min-height: 640px;
    }
    aside, .tools {
      background: var(--panel);
      border-color: var(--line);
      overflow: auto;
    }
    aside { border-right: 1px solid var(--line); }
    .tools { border-left: 1px solid var(--line); }
    .panel-head {
      position: sticky;
      top: 0;
      z-index: 1;
      padding: 14px;
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      font-weight: 700;
    }
    .sample-list {
      display: grid;
      gap: 6px;
      padding: 10px;
    }
    .sample-btn {
      width: 100%;
      border: 1px solid var(--line);
      background: #fafaf8;
      color: var(--text);
      border-radius: 6px;
      padding: 8px 9px;
      text-align: left;
      cursor: pointer;
      line-height: 1.25;
    }
    .sample-btn.active {
      border-color: var(--blue);
      background: #eef6fd;
    }
    .sample-btn.saved::after {
      content: "saved";
      float: right;
      color: var(--blue);
      font-size: 11px;
      margin-top: 1px;
    }
    main {
      display: grid;
      grid-template-rows: auto 1fr auto;
      min-width: 0;
      min-height: 0;
    }
    .topbar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      background: #ecece6;
      border-bottom: 1px solid var(--line);
    }
    .topbar .title {
      font-weight: 700;
      margin-right: auto;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    button {
      border: 1px solid #bdbdb4;
      background: #fff;
      border-radius: 6px;
      padding: 7px 10px;
      cursor: pointer;
      font: inherit;
    }
    button.primary {
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
      font-weight: 700;
    }
    button:disabled {
      opacity: 0.45;
      cursor: default;
    }
    .stage {
      position: relative;
      min-height: 0;
      overflow: auto;
      padding: 18px;
      background: #deded7;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }
    canvas {
      display: block;
      max-width: 100%;
      height: auto;
      background: #111;
      box-shadow: 0 1px 10px rgba(0,0,0,0.18);
      cursor: crosshair;
    }
    .status {
      padding: 8px 14px;
      color: var(--muted);
      background: #ecece6;
      border-top: 1px solid var(--line);
      min-height: 34px;
    }
    .tool-section {
      padding: 14px;
      border-bottom: 1px solid var(--line);
    }
    .tool-section h2 {
      margin: 0 0 10px;
      font-size: 14px;
    }
    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    label {
      display: grid;
      gap: 4px;
      color: var(--muted);
      font-size: 12px;
    }
    input[type="number"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 5px;
      padding: 7px 8px;
      font: inherit;
      color: var(--text);
      background: #fff;
    }
    .check-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 4px 0 10px;
      color: var(--text);
    }
    .button-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }
    .note {
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    @media (max-width: 1050px) {
      .app { grid-template-columns: 190px minmax(360px, 1fr); }
      .tools { grid-column: 1 / -1; border-left: 0; border-top: 1px solid var(--line); max-height: 280px; }
      main { min-height: 0; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="panel-head">Coupes echantillonnees</div>
      <div id="sampleList" class="sample-list"></div>
    </aside>

    <main>
      <div class="topbar">
        <button id="prevBtn">Precedent</button>
        <button id="nextBtn">Suivant</button>
        <div id="title" class="title">Chargement...</div>
        <button id="saveBtn" class="primary">Sauver JSON</button>
      </div>
      <div class="stage">
        <canvas id="canvas"></canvas>
      </div>
      <div id="status" class="status"></div>
    </main>

    <section class="tools">
      <div class="panel-head">Rectangle crop</div>
      <div class="tool-section">
        <div class="check-row">
          <input id="lockSize" type="checkbox" checked>
          <label for="lockSize" style="display:block;color:var(--text);font-size:14px;">Taille commune</label>
        </div>
        <div class="grid2">
          <label>X<input id="xInput" type="number" step="1"></label>
          <label>Y<input id="yInput" type="number" step="1"></label>
          <label>Largeur<input id="wInput" type="number" step="1" min="50"></label>
          <label>Hauteur<input id="hInput" type="number" step="1" min="50"></label>
        </div>
        <div class="button-row">
          <button id="centerBtn">Centrer</button>
          <button id="copyPosBtn">Copier position</button>
          <button id="resetBtn">Reset</button>
        </div>
        <div class="note">
          Deplace le rectangle a la souris. Les coins permettent de redimensionner.
          Si "Taille commune" est active, la largeur/hauteur sont appliquees a toutes les coupes marquees.
        </div>
      </div>
      <div class="tool-section">
        <h2>Sortie</h2>
        <div id="outputPath" class="mono"></div>
        <div id="summary" class="note"></div>
      </div>
    </section>
  </div>

<script>
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const sampleList = document.getElementById("sampleList");
const titleEl = document.getElementById("title");
const statusEl = document.getElementById("status");
const summaryEl = document.getElementById("summary");
const outputPathEl = document.getElementById("outputPath");
const inputs = {
  x: document.getElementById("xInput"),
  y: document.getElementById("yInput"),
  width: document.getElementById("wInput"),
  height: document.getElementById("hInput")
};
const lockSizeEl = document.getElementById("lockSize");

let state = null;
let current = 0;
let img = new Image();
let drag = null;
let dirty = false;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function cloneRect(rect) {
  return {x: rect.x, y: rect.y, width: rect.width, height: rect.height};
}

function currentImage() {
  return state.images[current];
}

function currentCrop() {
  const item = currentImage();
  if (!state.crops[item.index]) {
    state.crops[item.index] = defaultRectForImage(item);
  }
  return state.crops[item.index];
}

function defaultRectForImage(item) {
  const rect = cloneRect(state.default_rect);
  rect.width = Math.min(rect.width, item.full_width);
  rect.height = Math.min(rect.height, item.full_height);
  rect.x = clamp(rect.x, 0, item.full_width - rect.width);
  rect.y = clamp(rect.y, 0, item.full_height - rect.height);
  return rect;
}

function scaleToCanvas(item) {
  return {
    x: canvas.width / item.full_width,
    y: canvas.height / item.full_height
  };
}

function rectToCanvas(rect, item) {
  const scale = scaleToCanvas(item);
  return {
    x: rect.x * scale.x,
    y: rect.y * scale.y,
    width: rect.width * scale.x,
    height: rect.height * scale.y
  };
}

function pointerToFull(event) {
  const item = currentImage();
  const bounds = canvas.getBoundingClientRect();
  const canvasX = (event.clientX - bounds.left) * (canvas.width / bounds.width);
  const canvasY = (event.clientY - bounds.top) * (canvas.height / bounds.height);
  return {
    x: canvasX * item.full_width / canvas.width,
    y: canvasY * item.full_height / canvas.height,
    canvasX,
    canvasY
  };
}

function normalizeRect(rect, item, minSize=80) {
  rect.width = Math.max(minSize, Math.round(rect.width));
  rect.height = Math.max(minSize, Math.round(rect.height));
  rect.width = Math.min(rect.width, item.full_width);
  rect.height = Math.min(rect.height, item.full_height);
  rect.x = clamp(Math.round(rect.x), 0, item.full_width - rect.width);
  rect.y = clamp(Math.round(rect.y), 0, item.full_height - rect.height);
  return rect;
}

function ensureCommonSizeFrom(rect, sourceIndex) {
  if (!lockSizeEl.checked) return;
  const item = currentImage();
  const width = clamp(Math.round(rect.width), 80, item.full_width);
  const height = clamp(Math.round(rect.height), 80, item.full_height);
  state.common_size = [width, height];

  for (const imageItem of state.images) {
    const old = state.crops[imageItem.index] || defaultRectForImage(imageItem);
    const centerX = old.x + old.width / 2;
    const centerY = old.y + old.height / 2;
    const next = {
      x: centerX - width / 2,
      y: centerY - height / 2,
      width,
      height
    };
    state.crops[imageItem.index] = normalizeRect(next, imageItem);
  }
  state.crops[sourceIndex] = normalizeRect(rect, item);
}

function draw() {
  const item = currentImage();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (img.complete && img.naturalWidth) {
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  }
  const rect = rectToCanvas(currentCrop(), item);
  ctx.save();
  ctx.fillStyle = "rgba(210, 31, 60, 0.10)";
  ctx.strokeStyle = "#d21f3c";
  ctx.lineWidth = 3;
  ctx.fillRect(rect.x, rect.y, rect.width, rect.height);
  ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);

  const handles = handleRects(rect);
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#d21f3c";
  ctx.lineWidth = 2;
  for (const key of Object.keys(handles)) {
    const h = handles[key];
    ctx.fillRect(h.x, h.y, h.size, h.size);
    ctx.strokeRect(h.x, h.y, h.size, h.size);
  }
  ctx.restore();
}

function handleRects(rect) {
  const s = 12;
  const hs = s / 2;
  return {
    nw: {x: rect.x - hs, y: rect.y - hs, size: s},
    ne: {x: rect.x + rect.width - hs, y: rect.y - hs, size: s},
    sw: {x: rect.x - hs, y: rect.y + rect.height - hs, size: s},
    se: {x: rect.x + rect.width - hs, y: rect.y + rect.height - hs, size: s}
  };
}

function hitTest(point) {
  const rect = rectToCanvas(currentCrop(), currentImage());
  const handles = handleRects(rect);
  for (const key of Object.keys(handles)) {
    const h = handles[key];
    if (point.canvasX >= h.x - 3 && point.canvasX <= h.x + h.size + 3 &&
        point.canvasY >= h.y - 3 && point.canvasY <= h.y + h.size + 3) {
      return key;
    }
  }
  if (point.canvasX >= rect.x && point.canvasX <= rect.x + rect.width &&
      point.canvasY >= rect.y && point.canvasY <= rect.y + rect.height) {
    return "move";
  }
  return "move-new";
}

function updateInputs() {
  const rect = currentCrop();
  inputs.x.value = Math.round(rect.x);
  inputs.y.value = Math.round(rect.y);
  inputs.width.value = Math.round(rect.width);
  inputs.height.value = Math.round(rect.height);
  const item = currentImage();
  statusEl.textContent = `Image ${item.number}/${state.total_images} - ${item.name} - ${item.full_width} x ${item.full_height}`;
  summaryEl.textContent = `${state.images.length} coupes echantillonnees. Coordonnees sauvegardees en pixels apres orientation EXIF.`;
}

function setCurrent(index) {
  current = clamp(index, 0, state.images.length - 1);
  const item = currentImage();
  titleEl.textContent = `${item.number.toString().padStart(4, "0")}  ${item.name}`;
  img = new Image();
  img.onload = () => {
    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    draw();
  };
  img.src = item.image_url + "&t=" + Date.now();
  renderSampleList();
  updateInputs();
  draw();
}

function renderSampleList() {
  sampleList.innerHTML = "";
  state.images.forEach((item, idx) => {
    const button = document.createElement("button");
    button.className = "sample-btn";
    if (idx === current) button.classList.add("active");
    if (state.crops[item.index]) button.classList.add("saved");
    button.textContent = `${item.number.toString().padStart(4, "0")}  ${item.name}`;
    button.addEventListener("click", () => setCurrent(idx));
    sampleList.appendChild(button);
  });
}

function markDirty() {
  dirty = true;
  renderSampleList();
  updateInputs();
  draw();
}

canvas.addEventListener("mousedown", (event) => {
  const point = pointerToFull(event);
  const mode = hitTest(point);
  const rect = cloneRect(currentCrop());
  drag = {
    mode,
    start: point,
    rect,
    item: currentImage()
  };
});

window.addEventListener("mousemove", (event) => {
  if (!drag) return;
  const item = drag.item;
  const point = pointerToFull(event);
  const dx = point.x - drag.start.x;
  const dy = point.y - drag.start.y;
  let rect = cloneRect(drag.rect);

  if (drag.mode === "move" || drag.mode === "move-new") {
    rect.x += dx;
    rect.y += dy;
  } else {
    const x2 = rect.x + rect.width;
    const y2 = rect.y + rect.height;
    if (drag.mode.includes("w")) {
      rect.x += dx;
      rect.width = x2 - rect.x;
    }
    if (drag.mode.includes("e")) {
      rect.width += dx;
    }
    if (drag.mode.includes("n")) {
      rect.y += dy;
      rect.height = y2 - rect.y;
    }
    if (drag.mode.includes("s")) {
      rect.height += dy;
    }
  }

  rect = normalizeRect(rect, item);
  ensureCommonSizeFrom(rect, item.index);
  state.crops[item.index] = normalizeRect(rect, item);
  markDirty();
});

window.addEventListener("mouseup", () => {
  drag = null;
});

function applyInputChange() {
  const item = currentImage();
  const rect = {
    x: Number(inputs.x.value),
    y: Number(inputs.y.value),
    width: Number(inputs.width.value),
    height: Number(inputs.height.value)
  };
  const normalized = normalizeRect(rect, item);
  ensureCommonSizeFrom(normalized, item.index);
  state.crops[item.index] = normalized;
  markDirty();
}

for (const input of Object.values(inputs)) {
  input.addEventListener("change", applyInputChange);
}

lockSizeEl.addEventListener("change", () => {
  if (lockSizeEl.checked) {
    const rect = currentCrop();
    ensureCommonSizeFrom(rect, currentImage().index);
  }
  markDirty();
});

document.getElementById("prevBtn").addEventListener("click", () => setCurrent(current - 1));
document.getElementById("nextBtn").addEventListener("click", () => setCurrent(current + 1));
document.getElementById("centerBtn").addEventListener("click", () => {
  const item = currentImage();
  const rect = currentCrop();
  rect.x = Math.round((item.full_width - rect.width) / 2);
  rect.y = Math.round((item.full_height - rect.height) / 2);
  state.crops[item.index] = normalizeRect(rect, item);
  markDirty();
});
document.getElementById("copyPosBtn").addEventListener("click", () => {
  const source = currentCrop();
  for (const item of state.images) {
    const rect = {
      x: source.x,
      y: source.y,
      width: source.width,
      height: source.height
    };
    state.crops[item.index] = normalizeRect(rect, item);
  }
  markDirty();
});
document.getElementById("resetBtn").addEventListener("click", () => {
  const item = currentImage();
  state.crops[item.index] = defaultRectForImage(item);
  markDirty();
});
document.getElementById("saveBtn").addEventListener("click", async () => {
  const payload = {
    common_size: state.common_size,
    lock_size: lockSizeEl.checked,
    crops: state.images.map(item => {
      const rect = state.crops[item.index] || defaultRectForImage(item);
      return {
        index: item.index,
        number: item.number,
        file: item.file,
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        x2: Math.round(rect.x + rect.width),
        y2: Math.round(rect.y + rect.height)
      };
    })
  };
  const response = await fetch("/api/save", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) {
    statusEl.textContent = result.error || "Erreur de sauvegarde";
    return;
  }
  dirty = false;
  statusEl.textContent = `Sauvegarde: ${result.output}`;
});

async function boot() {
  const response = await fetch("/api/state");
  state = await response.json();
  outputPathEl.textContent = state.output;
  for (const item of state.images) {
    if (!state.crops[item.index]) state.crops[item.index] = defaultRectForImage(item);
  }
  setCurrent(0);
}

boot().catch((error) => {
  statusEl.textContent = String(error);
});
</script>
</body>
</html>
"""


def iter_images(root: Path) -> list[Path]:
    return sorted(
        p
        for p in root.rglob("*")
        if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith("._")
    )


def orient_image(image: Image.Image) -> Image.Image:
    orientation = image.getexif().get(274, 1)
    if orientation == 3:
        return image.rotate(180, expand=True)
    if orientation == 6:
        return image.rotate(270, expand=True)
    if orientation == 8:
        return image.rotate(90, expand=True)
    return image.copy()


def sample_indices(n_images: int, n_samples: int) -> list[int]:
    if n_images <= 0:
        return []
    if n_samples >= n_images:
        return list(range(n_images))
    if n_samples <= 1:
        return [n_images // 2]
    return sorted({round(i * (n_images - 1) / (n_samples - 1)) for i in range(n_samples)})


def parse_indices(indices: str | None, n_images: int) -> list[int] | None:
    if not indices:
        return None
    selected = []
    for token in indices.split(","):
        token = token.strip()
        if not token:
            continue
        value = int(token)
        if value < 1 or value > n_images:
            raise ValueError(f"Index {value} is outside 1..{n_images}")
        selected.append(value - 1)
    return sorted(set(selected))


def clamp_rect(rect: dict, width: int, height: int) -> dict:
    crop_width = max(80, min(int(round(rect["width"])), width))
    crop_height = max(80, min(int(round(rect["height"])), height))
    x = max(0, min(int(round(rect["x"])), width - crop_width))
    y = max(0, min(int(round(rect["y"])), height - crop_height))
    return {"x": x, "y": y, "width": crop_width, "height": crop_height}


class CropServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        files: list[Path],
        sample_indexes: list[int],
        root: Path,
        output: Path,
        default_rect: dict,
        max_preview: int,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.files = files
        self.sample_indexes = sample_indexes
        self.root = root
        self.output = output
        self.default_rect = default_rect
        self.max_preview = max_preview
        self.preview_cache: dict[tuple[int, int], bytes] = {}
        self.image_sizes = self._read_oriented_sizes()
        self.saved_crops = self._read_existing_crops()

    def _read_oriented_sizes(self) -> dict[int, tuple[int, int]]:
        sizes = {}
        for image_index in self.sample_indexes:
            with Image.open(self.files[image_index]) as raw:
                oriented = orient_image(raw)
                sizes[image_index] = oriented.size
        return sizes

    def _read_existing_crops(self) -> dict[int, dict]:
        if not self.output.exists():
            return {}
        try:
            data = json.loads(self.output.read_text())
        except (OSError, json.JSONDecodeError):
            return {}
        crops = {}
        for item in data.get("crops", []):
            try:
                image_index = int(item["index"])
                width, height = self.image_sizes.get(image_index, (0, 0))
                if width and height:
                    crops[image_index] = clamp_rect(item, width, height)
            except (KeyError, TypeError, ValueError):
                continue
        return crops

    def make_state(self) -> dict:
        images = []
        for image_index in self.sample_indexes:
            path = self.files[image_index]
            full_width, full_height = self.image_sizes[image_index]
            images.append(
                {
                    "index": image_index,
                    "number": image_index + 1,
                    "name": path.name,
                    "file": str(path),
                    "full_width": full_width,
                    "full_height": full_height,
                    "image_url": f"/api/image?index={image_index}",
                }
            )
        return {
            "total_images": len(self.files),
            "sample_count": len(images),
            "images": images,
            "default_rect": self.default_rect,
            "common_size": [self.default_rect["width"], self.default_rect["height"]],
            "crops": self.saved_crops,
            "output": str(self.output),
        }

    def make_preview(self, image_index: int) -> bytes:
        key = (image_index, self.max_preview)
        if key in self.preview_cache:
            return self.preview_cache[key]
        with Image.open(self.files[image_index]) as raw:
            image = orient_image(raw).convert("RGB")
            image.thumbnail((self.max_preview, self.max_preview), Image.LANCZOS)
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=90)
        data = buffer.getvalue()
        self.preview_cache[key] = data
        return data

    def save_config(self, payload: dict) -> dict:
        crops = []
        by_index = {int(item["index"]): item for item in payload.get("crops", [])}
        for image_index in self.sample_indexes:
            if image_index not in by_index:
                continue
            width, height = self.image_sizes[image_index]
            rect = clamp_rect(by_index[image_index], width, height)
            path = self.files[image_index]
            crops.append(
                {
                    "index": image_index,
                    "number": image_index + 1,
                    "file": str(path),
                    "x": rect["x"],
                    "y": rect["y"],
                    "width": rect["width"],
                    "height": rect["height"],
                    "x2": rect["x"] + rect["width"],
                    "y2": rect["y"] + rect["height"],
                }
            )
            self.saved_crops[image_index] = rect

        config = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "input_dir": str(self.root),
            "total_images": len(self.files),
            "coordinate_space": "pixels_after_exif_orientation",
            "sample_indices": self.sample_indexes,
            "sample_numbers": [idx + 1 for idx in self.sample_indexes],
            "lock_size": bool(payload.get("lock_size", True)),
            "common_size": payload.get("common_size", [self.default_rect["width"], self.default_rect["height"]]),
            "crops": crops,
            "note": "Use these sampled crop placements to choose a common crop or interpolate centers later.",
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text(json.dumps(config, indent=2))
        return {"ok": True, "output": str(self.output), "crops": len(crops)}


class CropHandler(BaseHTTPRequestHandler):
    server: CropServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/state":
            self.send_json(self.server.make_state())
            return
        if parsed.path == "/api/image":
            query = parse_qs(parsed.query)
            try:
                image_index = int(query.get("index", [""])[0])
            except ValueError:
                self.send_json({"error": "invalid image index"}, 400)
                return
            if image_index not in self.server.sample_indexes:
                self.send_json({"error": "image index is not sampled"}, 404)
                return
            self.send_bytes(self.server.make_preview(image_index), "image/jpeg")
            return
        self.send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/save":
            self.send_json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.server.save_config(payload)
        except Exception as exc:
            self.send_json({"error": str(exc)}, 400)
            return
        self.send_json(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local web interface to choose cryobloc crop rectangles.")
    parser.add_argument("--input", type=Path, default=Path("raw_triees_images"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--samples", type=int, default=15)
    parser.add_argument(
        "--indices",
        default=None,
        help="Comma-separated 1-based image numbers to show, for example 1,50,100,150,200,250,325.",
    )
    parser.add_argument("--crop", type=int, nargs=4, default=None, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-preview", type=int, default=1600)
    args = parser.parse_args()

    files = iter_images(args.input)
    if not files:
        raise SystemExit(f"No images found in {args.input}")

    selected = parse_indices(args.indices, len(files))
    sample_indexes = selected if selected is not None else sample_indices(len(files), args.samples)
    if not sample_indexes:
        raise SystemExit("No sample images selected")

    rect_values = args.crop if args.crop is not None else [
        DEFAULT_RECT["x"],
        DEFAULT_RECT["y"],
        DEFAULT_RECT["width"],
        DEFAULT_RECT["height"],
    ]
    default_rect = {
        "x": rect_values[0],
        "y": rect_values[1],
        "width": rect_values[2],
        "height": rect_values[3],
    }

    server = CropServer(
        (args.host, args.port),
        CropHandler,
        files,
        sample_indexes,
        args.input,
        args.output,
        default_rect,
        args.max_preview,
    )
    url = f"http://{args.host}:{server.server_port}/"
    print(f"Images: {len(files)}", flush=True)
    print(f"Samples: {', '.join(str(i + 1) for i in sample_indexes)}", flush=True)
    print(f"Output: {args.output}", flush=True)
    print(f"Open: {url}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
