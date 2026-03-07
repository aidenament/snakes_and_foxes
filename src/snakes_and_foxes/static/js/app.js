const STORAGE_KEY = "snakes-and-foxes-state-v1";
const API = {
  newGame: "/api/game/new",
  action: "/api/game/action",
};

const canvas = document.getElementById("board-canvas");
const ctx = canvas.getContext("2d");
const overlay = document.getElementById("overlay");
const helpDialog = document.getElementById("help-dialog");

const els = {
  activePiece: document.getElementById("active-piece-text"),
  eventLog: document.getElementById("event-log"),
  foxes: document.getElementById("foxes-text"),
  moves: document.getElementById("moves-text"),
  phase: document.getElementById("phase-text"),
  piecesList: document.getElementById("pieces-list"),
  resume: document.getElementById("resume-btn"),
  roll: document.getElementById("roll-btn"),
  seed: document.getElementById("seed-text"),
  snakes: document.getElementById("snakes-text"),
  start: document.getElementById("start-btn"),
  status: document.getElementById("status-text"),
  turn: document.getElementById("turn-text"),
};

const state = {
  game: null,
  animating: false,
  animations: [],
  hoverNode: null,
};

const layout = {
  centerX: canvas.width / 2,
  centerY: canvas.height / 2,
  ringGap: 72,
};

function symbolForFace(face) {
  if (face === "black_pip") return "●";
  if (face === "red_triangle") return "▼";
  return "≈";
}

function pieceColor(pieceId) {
  return pieceId === "sun" ? "#f2c96d" : "#7aa6b2";
}

function loadSavedState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveState() {
  if (state.game) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state.game));
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

async function createNewGame(seed = null) {
  const response = await postJson(API.newGame, { seed, board: { circle_count: 6, nodes_per_circle: 10 } });
  applyServerState(response.state, response.result);
  overlay.classList.add("hidden");
}

async function submitAction(action) {
  if (!state.game || state.animating) return;
  const response = await postJson(API.action, { state: state.game, action });
  applyServerState(response.state, response.result);
}

function applyServerState(nextState, result) {
  state.game = nextState;
  state.animations = buildAnimations(result.resolved_events);
  state.animating = state.animations.length > 0;
  saveState();
  renderHud(result);
  if (state.animating) {
    runAnimations();
  } else {
    drawBoard();
  }
}

function buildAnimations(events) {
  return events
    .filter((event) => event.source && event.destination)
    .map((event) => ({
      event,
      progress: 0,
      duration: event.kind === "player_move" ? 360 : 280,
    }));
}

function runAnimations() {
  if (!state.animations.length) {
    state.animating = false;
    drawBoard();
    return;
  }

  let last = performance.now();
  const step = (timestamp) => {
    const delta = timestamp - last;
    last = timestamp;
    const animation = state.animations[0];
    animation.progress = Math.min(1, animation.progress + delta / animation.duration);
    drawBoard(animation);
    if (animation.progress >= 1) {
      state.animations.shift();
      if (!state.animations.length) {
        state.animating = false;
        drawBoard();
        return;
      }
    }
    requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function renderHud(result) {
  const game = state.game;
  const roll = game.dice_roll;
  const activePiece = game.pieces.find((piece) => piece.piece_id === game.active_piece_id);
  els.activePiece.textContent = activePiece ? activePiece.label : "Captured";
  els.phase.textContent = game.phase.replaceAll("_", " ");
  els.turn.textContent = String(game.turn_number);
  els.seed.textContent = String(game.seed);
  els.moves.textContent = `Moves: ${roll ? roll.black_pips : 0}`;
  els.foxes.textContent = `Foxes: ${roll ? roll.red_triangles : 0}`;
  els.snakes.textContent = `Snakes: ${roll ? roll.green_squiggles : 0}`;
  els.status.textContent = result?.message || "The board is ready.";
  els.roll.disabled = game.phase !== "waiting_for_roll" || state.animating;

  const diceTray = document.getElementById("dice-tray");
  diceTray.innerHTML = "";
  (roll?.faces || Array.from({ length: 6 }, () => "black_pip")).forEach((face) => {
    const die = document.createElement("div");
    die.className = `die ${face}`;
    die.textContent = symbolForFace(face);
    diceTray.appendChild(die);
  });

  els.piecesList.innerHTML = "";
  game.pieces.forEach((piece) => {
    const item = document.createElement("li");
    item.className = "piece-card";
    if (piece.piece_id === game.active_piece_id) item.classList.add("active");
    if (!piece.alive) item.classList.add("dead");
    item.innerHTML = `
      <strong>${piece.label}</strong>
      <div>${piece.alive ? describeNode(piece.node) : "Captured"}</div>
      <div>${piece.reached_outer ? "Has touched the outer ring" : "Has not touched the outer ring yet"}</div>
    `;
    els.piecesList.appendChild(item);
  });

  els.eventLog.innerHTML = "";
  [...game.event_log].reverse().forEach((entry) => {
    const li = document.createElement("li");
    li.textContent = entry.message;
    els.eventLog.appendChild(li);
  });
}

function describeNode(node) {
  if (node.circle_index === 0) return "Center";
  return `Ring ${node.circle_index}, node ${node.node_index}`;
}

function nodePosition(node) {
  if (node.circle_index === 0) {
    return { x: layout.centerX, y: layout.centerY };
  }
  const angle = (Math.PI * 2 * node.node_index) / state.game.board.nodes_per_circle - Math.PI / 2;
  const radius = layout.ringGap * node.circle_index;
  return {
    x: layout.centerX + Math.cos(angle) * radius,
    y: layout.centerY + Math.sin(angle) * radius,
  };
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function animatedPosition(eventAnimation) {
  const start = nodePosition(eventAnimation.event.source);
  const end = nodePosition(eventAnimation.event.destination);
  return {
    x: lerp(start.x, end.x, eventAnimation.progress),
    y: lerp(start.y, end.y, eventAnimation.progress),
  };
}

function drawBoard(activeAnimation = null) {
  if (!state.game) return;
  const { circle_count: circleCount, nodes_per_circle: nodesPerCircle } = state.game.board;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const background = ctx.createRadialGradient(layout.centerX, layout.centerY, 40, layout.centerX, layout.centerY, 540);
  background.addColorStop(0, "rgba(255, 248, 231, 0.98)");
  background.addColorStop(1, "rgba(213, 177, 121, 0.96)");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.strokeStyle = "rgba(61, 37, 26, 0.75)";
  ctx.lineWidth = 6;
  ctx.beginPath();
  ctx.arc(layout.centerX, layout.centerY, 26, 0, Math.PI * 2);
  ctx.stroke();

  for (let ring = 1; ring < circleCount; ring += 1) {
    ctx.strokeStyle = ring === circleCount - 1 ? "rgba(208, 167, 67, 0.95)" : "rgba(73, 43, 30, 0.55)";
    ctx.lineWidth = ring === circleCount - 1 ? 7 : 4;
    ctx.beginPath();
    ctx.arc(layout.centerX, layout.centerY, layout.ringGap * ring, 0, Math.PI * 2);
    ctx.stroke();

    for (let nodeIndex = 0; nodeIndex < nodesPerCircle; nodeIndex += 1) {
      const pos = nodePosition({ circle_index: ring, node_index: nodeIndex });
      ctx.fillStyle = "rgba(105, 69, 51, 0.14)";
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 10, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  drawDirectionalMarks(circleCount, nodesPerCircle);
  drawLegalMoves();
  drawEnemies(activeAnimation);
  drawPieces(activeAnimation);
  drawCenterGlow();
}

function drawDirectionalMarks(circleCount, nodesPerCircle) {
  ctx.save();
  ctx.strokeStyle = "rgba(44, 28, 21, 0.45)";
  ctx.lineWidth = 2;
  for (let ring = 1; ring < circleCount; ring += 1) {
    for (let nodeIndex = 0; nodeIndex < nodesPerCircle; nodeIndex += 2) {
      const node = { circle_index: ring, node_index: nodeIndex };
      const next = {
        circle_index: ring,
        node_index: (nodeIndex + (ring % 2 === 0 ? -1 : 1) + nodesPerCircle) % nodesPerCircle,
      };
      const a = nodePosition(node);
      const b = nodePosition(next);
      const midX = lerp(a.x, b.x, 0.5);
      const midY = lerp(a.y, b.y, 0.5);
      ctx.beginPath();
      ctx.moveTo(midX, midY);
      ctx.lineTo(lerp(midX, b.x, 0.45), lerp(midY, b.y, 0.45));
      ctx.stroke();
    }
  }
  ctx.restore();
}

function drawLegalMoves() {
  if (state.game.phase !== "player_moving") return;
  state.game.legal_moves.forEach((node) => {
    const pos = nodePosition(node);
    ctx.fillStyle = "rgba(208, 167, 67, 0.24)";
    ctx.beginPath();
    ctx.arc(pos.x, pos.y, node.circle_index === 0 ? 30 : 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(208, 167, 67, 0.95)";
    ctx.lineWidth = 3;
    ctx.stroke();
  });
}

function drawEnemies(activeAnimation) {
  state.game.enemies
    .filter((enemy) => enemy.active)
    .forEach((enemy) => {
      let pos = nodePosition(enemy.node);
      if (activeAnimation?.event.actor_id === enemy.enemy_id) {
        pos = animatedPosition(activeAnimation);
      }
      if (enemy.enemy_type === "fox") {
        drawFox(pos.x, pos.y);
      } else {
        drawSnake(pos.x, pos.y);
      }
    });
}

function drawPieces(activeAnimation) {
  state.game.pieces.forEach((piece) => {
    if (!piece.alive) return;
    let pos = nodePosition(piece.node);
    if (activeAnimation?.event.actor_id === piece.piece_id) {
      pos = animatedPosition(activeAnimation);
    }
    const isActive = piece.piece_id === state.game.active_piece_id;
    ctx.beginPath();
    ctx.fillStyle = pieceColor(piece.piece_id);
    ctx.arc(pos.x, pos.y + (piece.piece_id === "moon" ? 14 : -14), 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.lineWidth = isActive ? 4 : 2;
    ctx.strokeStyle = isActive ? "#3c271d" : "rgba(60, 39, 29, 0.45)";
    ctx.stroke();
  });
}

function drawFox(x, y) {
  ctx.save();
  ctx.fillStyle = "#9f3528";
  ctx.beginPath();
  ctx.moveTo(x, y - 18);
  ctx.lineTo(x - 14, y + 12);
  ctx.lineTo(x + 14, y + 12);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

function drawSnake(x, y) {
  ctx.save();
  ctx.strokeStyle = "#4e6b3d";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(x - 16, y + 12);
  ctx.bezierCurveTo(x - 8, y - 18, x + 8, y + 18, x + 16, y - 12);
  ctx.stroke();
  ctx.restore();
}

function drawCenterGlow() {
  ctx.save();
  ctx.fillStyle = "rgba(255, 217, 121, 0.28)";
  ctx.beginPath();
  ctx.arc(layout.centerX, layout.centerY, 30, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function pickNode(clientX, clientY) {
  if (!state.game || state.animating || state.game.phase !== "player_moving") return null;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const x = (clientX - rect.left) * scaleX;
  const y = (clientY - rect.top) * scaleY;
  return state.game.legal_moves.find((node) => {
    const pos = nodePosition(node);
    const radius = node.circle_index === 0 ? 34 : 22;
    return Math.hypot(pos.x - x, pos.y - y) <= radius;
  });
}

canvas.addEventListener("click", async (event) => {
  const node = pickNode(event.clientX, event.clientY);
  if (!node) return;
  await submitAction({ type: "move", destination: node });
});

canvas.addEventListener("touchend", async (event) => {
  const touch = event.changedTouches[0];
  if (!touch) return;
  const node = pickNode(touch.clientX, touch.clientY);
  if (!node) return;
  await submitAction({ type: "move", destination: node });
});

document.getElementById("new-game-btn").addEventListener("click", () => createNewGame());
document.getElementById("overlay-help-btn").addEventListener("click", () => helpDialog.showModal());
document.getElementById("help-btn").addEventListener("click", () => helpDialog.showModal());
els.roll.addEventListener("click", () => submitAction({ type: "roll" }));
els.resume.addEventListener("click", () => {
  const saved = loadSavedState();
  if (!saved) return;
  overlay.classList.add("hidden");
  applyServerState(saved, { message: "Resumed saved game.", resolved_events: [], state: saved });
});
els.start.addEventListener("click", async () => {
  if (state.game) {
    overlay.classList.add("hidden");
    return;
  }
  const saved = loadSavedState();
  if (saved) {
    applyServerState(saved, { message: "Resumed saved game.", resolved_events: [], state: saved });
    overlay.classList.add("hidden");
    return;
  }
  await createNewGame();
});

window.addEventListener("resize", () => drawBoard());

drawBoard();
