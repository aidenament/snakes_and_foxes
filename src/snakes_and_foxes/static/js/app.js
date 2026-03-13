const VIEW_SIZE = 900;
const BOARD_CENTER = VIEW_SIZE / 2;
const RING_GAP = 52;
const DIE_REVEAL_STAGGER_MS = 40;
const DIE_REEL_BASE_DURATION_MS = 520;
const DIE_REEL_STEP_DURATION_MS = 50;
const DIE_REVEAL_CLEANUP_MS = 24;
const DIE_SEQUENCE_BASE_LENGTH = 8;
const API = {
  current: "/api/game/current",
  newGame: "/api/game/new",
  action: "/api/game/action",
};

const refs = {
  activePiece: document.getElementById("active-piece-text"),
  boardShell: document.getElementById("board-shell"),
  boardSvg: document.getElementById("board-svg"),
  diceTray: document.getElementById("dice-tray"),
  help: document.getElementById("help-btn"),
  helpDialog: document.getElementById("help-dialog"),
  newGame: document.getElementById("new-game-btn"),
  overlay: document.getElementById("overlay"),
  overlayBody: document.getElementById("overlay-body"),
  overlayEyebrow: document.getElementById("overlay-eyebrow"),
  overlayHelp: document.getElementById("overlay-help-btn"),
  overlayResume: document.getElementById("overlay-resume-btn"),
  overlayTitle: document.getElementById("overlay-title"),
  phase: document.getElementById("phase-text"),
  resume: document.getElementById("resume-btn"),
  roll: document.getElementById("roll-btn"),
  start: document.getElementById("start-btn"),
  status: document.getElementById("status-text"),
  tokenLayer: document.getElementById("token-layer"),
  turnSummary: document.getElementById("turn-summary-text"),
};

const runtime = {
  animating: false,
  csrfToken: null,
  diceCleanupTimer: null,
  diceRenderVersion: 0,
  game: null,
  hoverNodeKey: null,
  motion: null,
  pendingRequest: false,
  reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)"),
  savedGame: null,
  resumeAvailable: false,
  visualEntities: null,
};

function pipSvg(className = "") {
  return `
    <svg class="${className}" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="5.25" fill="currentColor"></circle>
    </svg>
  `;
}

function foxSvg(className = "") {
  return `
    <svg class="${className}" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 20.2 4.9 6.2h14.2Z" fill="currentColor"></path>
    </svg>
  `;
}

function snakeSvg(className = "") {
  return `
    <svg class="${className}" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M3.6 15.8c2.1-4.8 4.3-7.2 6.4-7.2 2.2 0 2.7 2.9 4.8 2.9 2.1 0 3.1-2.1 5.6-5.3"
        fill="none"
        stroke="currentColor"
        stroke-width="3.6"
        stroke-linecap="round"
        stroke-linejoin="round"
      ></path>
    </svg>
  `;
}

function dieFaceInnerMarkup(face) {
  if (face === "preview") {
    return `<span class="die-face-preview" aria-hidden="true"></span>`;
  }
  if (face === "black_pip") {
    return `<span class="die-face-pip" aria-hidden="true">${pipSvg("die-icon")}</span>`;
  }
  if (face === "red_triangle") {
    return `<span class="die-face-fox" aria-hidden="true">${foxSvg("die-icon")}</span>`;
  }
  if (face === "green_squiggle") {
    return `<span class="die-face-snake" aria-hidden="true">${snakeSvg("die-icon")}</span>`;
  }
  return "";
}

function dieFaceMarkup(face) {
  return `<span class="die-face" aria-hidden="true">${dieFaceInnerMarkup(face)}</span>`;
}

function dieRevealDelay(index) {
  return index * DIE_REVEAL_STAGGER_MS;
}

function dieReelDuration(index) {
  return DIE_REEL_BASE_DURATION_MS + index * DIE_REEL_STEP_DURATION_MS;
}

function diceRevealCleanupDelay(faceCount) {
  const finalIndex = Math.max(0, faceCount - 1);
  return dieRevealDelay(finalIndex) + dieReelDuration(finalIndex) + DIE_REVEAL_CLEANUP_MS;
}

function clearDiceCleanupTimer() {
  if (runtime.diceCleanupTimer !== null) {
    clearTimeout(runtime.diceCleanupTimer);
    runtime.diceCleanupTimer = null;
  }
}

function finalizeDiceFaces(faces, renderVersion) {
  if (renderVersion !== runtime.diceRenderVersion) return;
  refs.diceTray.classList.remove("is-revealing");
  [...refs.diceTray.children].forEach((die, index) => {
    const face = faces[index];
    if (!face) return;
    die.classList.remove("is-revealing");
    die.innerHTML = dieFaceMarkup(face);
  });
  runtime.diceCleanupTimer = null;
}

function dieReelMarkup(face, index) {
  const symbols = ["black_pip", "green_squiggle", "red_triangle"];
  const sequence = Array.from({ length: DIE_SEQUENCE_BASE_LENGTH + index }, (_, sequenceIndex) => (
    symbols[(sequenceIndex + index) % symbols.length]
  ));
  sequence.push(face, face, face);
  const faceCount = sequence.length;
  const stopIndex = faceCount - 2;
  const stepPercent = 100 / faceCount;
  const stopPercent = -((stopIndex / faceCount) * 100);
  const preStopPercent = stopPercent * 0.82;
  const overshootPercent = stopPercent - stepPercent * 0.38;
  const reelDuration = dieReelDuration(index);
  return `
    <span class="die-window" aria-hidden="true">
      <span
        class="die-reel"
        style="
          --face-count:${faceCount};
          --stop-pct:${stopPercent}%;
          --pre-stop-pct:${preStopPercent}%;
          --overshoot-pct:${overshootPercent}%;
          --reel-duration:${reelDuration}ms
        "
      >
        ${sequence.map((symbol) => `<span class="die-face die-face-slot">${dieFaceInnerMarkup(symbol)}</span>`).join("")}
      </span>
    </span>
  `;
}

function previewState() {
  return {
    board: { circle_count: 8, nodes_per_circle: 16 },
    turn_number: 1,
    phase: "waiting_for_roll",
    active_piece_id: "white",
    seed: "preview",
    moves_remaining: 0,
    pending_enemy_moves: { foxes: 0, snakes: 0 },
    dice_roll: null,
    legal_moves: [],
    turn_path: [],
    pieces: [
      {
        piece_id: "white",
        label: "White",
        node: { circle_index: 0, node_index: 0 },
        alive: true,
        reached_outer: false,
      },
      {
        piece_id: "black",
        label: "Black",
        node: { circle_index: 0, node_index: 0 },
        alive: true,
        reached_outer: false,
      },
    ],
    enemies: Array.from({ length: 16 }, (_, index) => ({
      enemy_id: `${index % 2 === 0 ? "fox" : "snake"}-${index}`,
      enemy_type: index % 2 === 0 ? "fox" : "snake",
      node: { circle_index: 7, node_index: index },
      active: true,
    })),
    event_log: [
      {
        kind: "intro",
        message:
          "Opening setup: White and Black begin together in the hub while foxes and snakes alternate around the outer ring.",
      },
    ],
  };
}

function presentState() {
  return runtime.game ?? previewState();
}

function boardConfig() {
  return presentState().board;
}

function titleCase(value) {
  if (!value) return "";
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function nodeKey(node) {
  return `${node.circle_index}:${node.node_index}`;
}

function nodesEqual(a, b) {
  return a.circle_index === b.circle_index && a.node_index === b.node_index;
}

function getPieceLabel(pieceId) {
  return pieceId === "black" ? "Black" : "White";
}

function ringType(circleIndex, circleCount = boardConfig().circle_count) {
  if (circleIndex === circleCount - 1) return "blue";
  return circleIndex % 2 === 1 ? "red" : "green";
}

function ringDirection(circleIndex, circleCount = boardConfig().circle_count) {
  if (circleIndex <= 0 || circleIndex === circleCount - 1) return 0;
  return circleIndex % 2 === 1 ? -1 : 1;
}

function nodeAngle(nodeIndex, nodesPerCircle = boardConfig().nodes_per_circle) {
  return (Math.PI * 2 * nodeIndex) / nodesPerCircle - Math.PI / 2;
}

function outerBoardRadius(board = boardConfig()) {
  return RING_GAP * (board.circle_count - 1);
}

function ringRadius(circleIndex, board = boardConfig()) {
  if (circleIndex <= 0) return 0;
  return outerBoardRadius(board) * Math.pow(circleIndex / (board.circle_count - 1), 0.72);
}

function nodePosition(node, board = boardConfig()) {
  if (node.circle_index === 0) {
    return { x: BOARD_CENTER, y: BOARD_CENTER };
  }
  const angle = nodeAngle(node.node_index, board.nodes_per_circle);
  const radius = ringRadius(node.circle_index, board);
  return {
    x: BOARD_CENTER + Math.cos(angle) * radius,
    y: BOARD_CENTER + Math.sin(angle) * radius,
  };
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - ((-2 * t + 2) ** 3) / 2;
}

function inferRingStep(source, destination, nodesPerCircle = boardConfig().nodes_per_circle) {
  const forward = (destination.node_index - source.node_index + nodesPerCircle) % nodesPerCircle;
  if (forward === 1) return 1;
  if (forward === nodesPerCircle - 1) return -1;
  return ringDirection(source.circle_index);
}

function resetSavedSession() {
  runtime.csrfToken = null;
  runtime.savedGame = null;
  runtime.resumeAvailable = false;
}

function requestHeaders() {
  const headers = { "Content-Type": "application/json" };
  if (runtime.csrfToken) {
    headers["X-CSRF-Token"] = runtime.csrfToken;
  }
  return headers;
}

async function requestJson(url, { method = "GET", payload = null, allowMissing = false } = {}) {
  const response = await fetch(url, {
    method,
    credentials: "same-origin",
    headers: payload ? requestHeaders() : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await response.json() : null;
  if (allowMissing && response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(body?.detail ?? `Request failed with status ${response.status}`);
  }
  return body;
}

async function createNewGame(seed = null) {
  if (runtime.pendingRequest) return;
  setStatus("Opening a fresh board.");
  runtime.pendingRequest = true;
  renderMeta({ message: "Opening a fresh board.", resolved_events: [] });
  try {
    const response = await requestJson(API.newGame, {
      method: "POST",
      payload: { seed },
    });
    await applySessionPayload(response);
  } catch (error) {
    handleRequestError(error, "Could not start a new game.");
  } finally {
    runtime.pendingRequest = false;
    renderMeta({ message: refs.status.textContent, resolved_events: [] }, { skipDice: true });
  }
}

async function submitAction(action) {
  if (!runtime.game || runtime.animating || runtime.pendingRequest) return;
  runtime.pendingRequest = true;
  renderMeta({ message: refs.status.textContent, resolved_events: [] });
  try {
    const response = await requestJson(API.action, {
      method: "POST",
      payload: { action },
    });
    await applySessionPayload(response);
  } catch (error) {
    if (error instanceof Error && error.message === "No live game session.") {
      runtime.game = null;
      resetSavedSession();
      renderMeta({ message: "The saved session expired. Start a new game.", resolved_events: [] });
      updateOverlay();
      renderBoard();
      return;
    }
    handleRequestError(error, "Could not apply that action.");
  } finally {
    runtime.pendingRequest = false;
    renderMeta({ message: refs.status.textContent, resolved_events: [] }, { skipDice: true });
  }
}

async function applySessionPayload(payload) {
  runtime.csrfToken = payload.csrf_token ?? runtime.csrfToken;
  runtime.savedGame = payload.state;
  runtime.resumeAvailable = true;
  await applyServerState(payload.state, payload.result);
}

async function loadCurrentGame({ activate = false, silent = false } = {}) {
  if (runtime.pendingRequest) return false;
  runtime.pendingRequest = true;
  const loadingMessage = silent ? refs.status.textContent : "Loading the saved game.";
  if (!silent) {
    setStatus(loadingMessage);
  }
  renderMeta({ message: loadingMessage, resolved_events: [] });
  try {
    const response = await requestJson(API.current, { allowMissing: true });
    if (!response) {
      resetSavedSession();
      if (activate) {
        runtime.game = null;
      }
      renderMeta({ message: silent ? "Preparing the board." : "No saved game was found.", resolved_events: [] });
      updateOverlay();
      renderBoard();
      return false;
    }

    runtime.csrfToken = response.csrf_token;
    runtime.savedGame = response.state;
    runtime.resumeAvailable = true;
    if (activate) {
      runtime.game = response.state;
      runtime.visualEntities = null;
      renderMeta({ message: "Saved game resumed.", resolved_events: [] });
    } else {
      renderMeta({ message: "Saved game available.", resolved_events: [] });
    }
    updateOverlay();
    renderBoard();
    return true;
  } catch (error) {
    handleRequestError(error, "Could not load the saved session.");
    return false;
  } finally {
    runtime.pendingRequest = false;
    renderMeta({ message: refs.status.textContent, resolved_events: [] }, { skipDice: true });
  }
}

async function applyServerState(nextState, result) {
  const previousState = runtime.game;
  runtime.game = nextState;
  renderMeta(result);

  if (shouldAnimate(previousState, result)) {
    runtime.visualEntities = createVisualEntities(previousState);
    refs.overlay.classList.add("hidden");
    renderBoard();
    await playTimeline(result.resolved_events, nextState);
  } else {
    runtime.visualEntities = null;
    renderBoard();
    updateOverlay();
  }
}

function shouldAnimate(previousState, result) {
  if (!previousState) return false;
  if (runtime.reducedMotion.matches) return false;
  return Boolean(result?.resolved_events?.some((event) => event.source && event.destination));
}

function renderMeta(result, { skipDice = false } = {}) {
  const game = presentState();
  const isPreview = runtime.game === null;
  const hasSaved = runtime.resumeAvailable;
  const statusMessage = result?.message ?? (hasSaved ? "Saved game available." : "Opening setup preview.");

  const activePiece = game.pieces.find((piece) => piece.piece_id === game.active_piece_id);
  refs.activePiece.textContent = activePiece ? activePiece.label : "Captured";
  refs.phase.textContent = isPreview ? "Opening setup" : titleCase(game.phase);
  refs.status.textContent = isPreview ? statusMessage : (result?.message ?? "The board is ready.");
  refs.turnSummary.textContent = buildTurnSummary(game, activePiece);
  refs.newGame.disabled = runtime.animating || runtime.pendingRequest;
  refs.roll.disabled = isPreview || game.phase !== "waiting_for_roll" || runtime.animating || runtime.pendingRequest;
  refs.resume.disabled = !hasSaved || runtime.animating || runtime.pendingRequest;
  refs.overlayResume.disabled = !hasSaved || runtime.pendingRequest;
  refs.start.disabled = runtime.pendingRequest;
  refs.resume.classList.toggle("hidden", !hasSaved);
  refs.overlayResume.classList.toggle("hidden", !hasSaved);
  if (!skipDice) {
    renderDice(game, result, isPreview);
  }
}

function buildTurnSummary(game, activePiece) {
  if (!activePiece) return "Both pieces have fallen.";
  if (runtime.game === null) {
    return "White begins. Both pieces are visible in the center before the first roll.";
  }
  if (game.phase === "game_won") {
    return `${activePiece.label} reached the outer ring and made it back to center.`;
  }
  if (game.phase === "game_lost") {
    return "Both pieces were taken before they could complete the route.";
  }
  if (game.phase === "player_moving") {
    return `${activePiece.label} is active. Spend all ${game.moves_remaining} move(s) exactly.`;
  }
  const objective = activePiece.reached_outer ? "return to the center" : "reach the outer ring";
  return `${activePiece.label} is active. Roll next, then ${objective}.`;
}

function entityRenderOrder(entity) {
  if (entity.kind === "enemy") {
    return [0, entity.enemyType === "fox" ? 0 : 1, entity.id];
  }
  return [1, entity.active ? 1 : 0, entity.pieceId === "white" ? 0 : 1, entity.id];
}

function renderDice(game, result, isPreview) {
  clearDiceCleanupTimer();
  runtime.diceRenderVersion += 1;
  const renderVersion = runtime.diceRenderVersion;
  refs.diceTray.innerHTML = "";
  const faces = isPreview ? Array.from({ length: 6 }, () => "preview") : (
    game.dice_roll?.faces ?? Array.from({ length: 6 }, () => "black_pip")
  );
  const shouldReveal = result?.resolved_events?.some((event) => ["roll", "reroll", "skip"].includes(event.kind));
  const revealDice = shouldReveal && !runtime.reducedMotion.matches && !isPreview;
  refs.diceTray.classList.remove("is-revealing");
  if (revealDice) {
    void refs.diceTray.offsetWidth;
    refs.diceTray.classList.add("is-revealing");
  }
  faces.forEach((face, index) => {
    const die = document.createElement("div");
    die.className = `die ${face}`;
    die.setAttribute("aria-label", face === "preview" ? "Pending roll" : titleCase(face));
    if (revealDice) {
      die.classList.add("is-revealing");
      die.style.setProperty("--delay", `${dieRevealDelay(index)}ms`);
    }
    die.innerHTML = revealDice ? dieReelMarkup(face, index) : dieFaceMarkup(face);
    refs.diceTray.appendChild(die);
  });
  if (revealDice) {
    runtime.diceCleanupTimer = window.setTimeout(() => {
      finalizeDiceFaces(faces, renderVersion);
    }, diceRevealCleanupDelay(faces.length));
  }
}

function updateOverlay() {
  const hasSaved = runtime.resumeAvailable;
  refs.overlayResume.disabled = !hasSaved || runtime.pendingRequest;
  refs.overlayResume.classList.toggle("hidden", !hasSaved);

  if (!runtime.game) {
    refs.overlay.classList.remove("hidden");
    refs.overlayEyebrow.textContent = "Opening board";
    refs.overlayTitle.textContent = "Start a clean run from the center.";
    refs.overlayBody.textContent =
      "Both pieces begin together at center. Reach the outer ring, then return to the center.";
    refs.start.classList.remove("hidden");
    return;
  }

  if (runtime.game.phase === "game_won") {
    refs.overlay.classList.remove("hidden");
    refs.overlayEyebrow.textContent = "Victory";
    refs.overlayTitle.textContent = `${getPieceLabel(runtime.game.winner_piece_id)} completed the route.`;
    refs.overlayBody.textContent =
      "The board is beaten. A piece reached the outer ring and made it back to center.";
    refs.start.classList.remove("hidden");
    refs.overlayResume.classList.add("hidden");
    return;
  }

  if (runtime.game.phase === "game_lost") {
    refs.overlay.classList.remove("hidden");
    refs.overlayEyebrow.textContent = "Defeat";
    refs.overlayTitle.textContent = "The hunt closed the board.";
    refs.overlayBody.textContent =
      "Both pieces were taken before either could return to the center. Start again and protect the return route.";
    refs.start.classList.remove("hidden");
    refs.overlayResume.classList.add("hidden");
    return;
  }

  refs.overlay.classList.add("hidden");
}

function renderBoard() {
  refs.boardSvg.innerHTML = buildBoardMarkup();
  bindBoardTargets();
  renderTokens();
}

function buildBoardMarkup() {
  const board = boardConfig();
  const outerRingRadius = outerBoardRadius(board);
  const rings = [];
  const spokes = [];
  const nodes = [];
  const directionMarks = [];
  const legalMoves =
    !runtime.animating && runtime.game?.phase === "player_moving" ? runtime.game.legal_moves : [];

  for (let spoke = 0; spoke < board.nodes_per_circle; spoke += 1) {
    const pos = nodePosition({ circle_index: board.circle_count - 1, node_index: spoke }, board);
    spokes.push(
      `<line class="board-spoke" x1="${BOARD_CENTER}" y1="${BOARD_CENTER}" x2="${pos.x}" y2="${pos.y}"></line>`,
    );
  }

  for (let ring = 1; ring < board.circle_count; ring += 1) {
    const radius = ringRadius(ring, board);
    const type = ringType(ring, board.circle_count);
    rings.push(
      `<circle class="board-ring board-ring-${type}" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="${radius}" stroke-width="${
        type === "blue" ? 6 : 3.5
      }"></circle>`,
    );
    directionMarks.push(...buildDirectionMarks(ring, board));

    for (let nodeIndex = 0; nodeIndex < board.nodes_per_circle; nodeIndex += 1) {
      const pos = nodePosition({ circle_index: ring, node_index: nodeIndex }, board);
      nodes.push(
        `<circle class="board-node board-node-${type}" cx="${pos.x}" cy="${pos.y}" r="${
          type === "blue" ? 7 : 5.6
        }"></circle>`,
      );
    }
  }

  return `
    <defs>
      <radialGradient id="boardWash" cx="50%" cy="42%">
        <stop offset="0%" stop-color="#fdfbf6"></stop>
        <stop offset="58%" stop-color="#f6f2ea"></stop>
        <stop offset="100%" stop-color="#ebe4d7"></stop>
      </radialGradient>
      <clipPath id="hubSymbolClip">
        <circle cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="28"></circle>
      </clipPath>
      ${buildBoardInscriptionPaths()}
    </defs>
    <rect class="board-backdrop" x="0" y="0" width="${VIEW_SIZE}" height="${VIEW_SIZE}" rx="40" fill="url(#boardWash)"></rect>
    ${buildBoardInscriptions()}
    <circle class="board-frame board-frame-outer" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="426"></circle>
    <circle class="board-frame board-frame-inner" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="396"></circle>
    <circle class="board-slot-track" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="${outerRingRadius}"></circle>
    <g>${spokes.join("")}</g>
    <g>${rings.join("")}</g>
    <g>${directionMarks.join("")}</g>
    <g>${nodes.join("")}</g>
    ${buildLegalMoveHalos(legalMoves, board)}
    <g>
      <circle class="board-hub-shadow" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="39"></circle>
      ${buildHubSymbol()}
      <text class="board-center-label" x="${BOARD_CENTER}" y="${BOARD_CENTER + 54}" text-anchor="middle">Hub</text>
    </g>
  `;
}

function boardInscriptions() {
  return [
    {
      quadrant: "nw",
      pathId: "board-inscription-nw",
      text: "Courage to strengthen.",
      centerAngle: degreesToRadians(225),
      spanAngle: degreesToRadians(58),
    },
    {
      quadrant: "ne",
      pathId: "board-inscription-ne",
      text: "Fire to blind.",
      centerAngle: degreesToRadians(315),
      spanAngle: degreesToRadians(40),
    },
    {
      quadrant: "se",
      pathId: "board-inscription-se",
      text: "Music to dazzle.",
      centerAngle: degreesToRadians(45),
      spanAngle: degreesToRadians(42),
    },
    {
      quadrant: "sw",
      pathId: "board-inscription-sw",
      text: "Iron to bind.",
      centerAngle: degreesToRadians(135),
      spanAngle: degreesToRadians(40),
    },
  ];
}

function buildBoardInscriptionPaths() {
  const radius = 446;
  return `
    ${boardInscriptions().map((inscription) => {
      const startAngle = inscription.centerAngle - inscription.spanAngle / 2;
      const endAngle = inscription.centerAngle + inscription.spanAngle / 2;
      return `<path id="${inscription.pathId}" d="${buildInscriptionArcPath(radius, startAngle, endAngle)}"></path>`;
    }).join("")}
  `;
}

function buildBoardInscriptions() {
  return `
    <g>
      ${boardInscriptions().map((inscription) => (
        `<text class="board-inscription" text-anchor="middle">
          <textPath href="#${inscription.pathId}" startOffset="50%">${inscription.text}</textPath>
        </text>`
      )).join("")}
    </g>
  `;
}

function buildInscriptionArcPath(radius, startAngle, endAngle) {
  const start = polarToCartesian(radius, startAngle);
  const end = polarToCartesian(radius, endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
}

function degreesToRadians(degrees) {
  return (degrees * Math.PI) / 180;
}

function buildHubSymbol() {
  const radius = 28;
  const innerRadius = radius / 2;
  return `
    <g clip-path="url(#hubSymbolClip)">
      <circle class="board-hub-symbol-light" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="${radius}"></circle>
      <rect
        class="board-hub-symbol-dark"
        x="${BOARD_CENTER}"
        y="${BOARD_CENTER - radius}"
        width="${radius}"
        height="${radius * 2}"
      ></rect>
      <circle
        class="board-hub-symbol-dark"
        cx="${BOARD_CENTER}"
        cy="${BOARD_CENTER - innerRadius}"
        r="${innerRadius}"
      ></circle>
      <circle
        class="board-hub-symbol-light"
        cx="${BOARD_CENTER}"
        cy="${BOARD_CENTER + innerRadius}"
        r="${innerRadius}"
      ></circle>
    </g>
    <circle class="board-hub" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="29"></circle>
    <circle class="board-hub-symbol-outline" cx="${BOARD_CENTER}" cy="${BOARD_CENTER}" r="${radius}"></circle>
  `;
}

function buildDirectionMarks(ring, board) {
  const marks = [];
  const type = ringType(ring, board.circle_count);
  const directions = type === "blue" ? [-1, 1] : [ringDirection(ring, board.circle_count)];
  for (let nodeIndex = 0; nodeIndex < board.nodes_per_circle; nodeIndex += 4) {
    const anchor = nodePosition({ circle_index: ring, node_index: nodeIndex }, board);
    directions.forEach((direction) => {
      const nextNode = {
        circle_index: ring,
        node_index: (nodeIndex + direction + board.nodes_per_circle) % board.nodes_per_circle,
      };
      const next = nodePosition(nextNode, board);
      const midX = lerp(anchor.x, next.x, 0.52);
      const midY = lerp(anchor.y, next.y, 0.52);
      const angle = Math.atan2(next.y - anchor.y, next.x - anchor.x);
      marks.push(directionMarkMarkup(midX, midY, angle, type));
    });
  }
  return marks;
}

function annularSectorPath(innerRadius, outerRadius, startAngle, endAngle) {
  const startOuter = polarToCartesian(outerRadius, startAngle);
  const endOuter = polarToCartesian(outerRadius, endAngle);
  const endInner = polarToCartesian(innerRadius, endAngle);
  const startInner = polarToCartesian(innerRadius, startAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return [
    `M ${startOuter.x} ${startOuter.y}`,
    `A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${endOuter.x} ${endOuter.y}`,
    `L ${endInner.x} ${endInner.y}`,
    `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${startInner.x} ${startInner.y}`,
    "Z",
  ].join(" ");
}

function polarToCartesian(radius, angle) {
  return {
    x: BOARD_CENTER + Math.cos(angle) * radius,
    y: BOARD_CENTER + Math.sin(angle) * radius,
  };
}

function directionMarkMarkup(x, y, angle, type) {
  return `
    <g transform="translate(${x} ${y}) rotate(${(angle * 180) / Math.PI})">
      <path class="direction-mark direction-mark-${type}" d="M-6 0H5M1-3.5 5 0 1 3.5"></path>
    </g>
  `;
}

function buildLegalMoveHalos(legalMoves, board) {
  if (!legalMoves?.length) return "";
  const halos = legalMoves
    .map((node) => {
      const pos = nodePosition(node, board);
      return `
        <circle
          class="legal-halo"
          cx="${pos.x}"
          cy="${pos.y}"
          r="${node.circle_index === 0 ? 15 : 10}"
        ></circle>
        <circle
          class="legal-hit"
          data-node-key="${nodeKey(node)}"
          cx="${pos.x}"
          cy="${pos.y}"
          r="${node.circle_index === 0 ? 24 : 16}"
        ></circle>
      `;
    })
    .join("");
  return `<g>${halos}</g>`;
}

function bindBoardTargets() {
  refs.boardSvg.querySelectorAll(".legal-hit").forEach((target) => {
    const key = target.dataset.nodeKey;
    target.addEventListener("click", async () => {
      const node = runtime.game.legal_moves.find((candidate) => nodeKey(candidate) === key);
      if (node) {
        await submitAction({ type: "move", destination: node });
      }
    });
  });
}

function createVisualEntities(state) {
  const entities = new Map();
  state.enemies
    .filter((enemy) => enemy.active)
    .forEach((enemy) => {
      entities.set(enemy.enemy_id, {
        id: enemy.enemy_id,
        kind: "enemy",
        enemyType: enemy.enemy_type,
        node: enemy.node,
        visible: true,
      });
    });
  state.pieces
    .filter((piece) => piece.alive)
    .forEach((piece) => {
      entities.set(piece.piece_id, {
        id: piece.piece_id,
        kind: "piece",
        pieceId: piece.piece_id,
        label: piece.label,
        node: piece.node,
        reachedOuter: piece.reached_outer,
        active: piece.piece_id === state.active_piece_id,
        visible: true,
        captured: false,
      });
    });
  return entities;
}

function currentEntities() {
  if (runtime.visualEntities) {
    return [...runtime.visualEntities.values()].filter((entity) => entity.visible !== false);
  }
  const game = presentState();
  return [
    ...game.enemies
      .filter((enemy) => enemy.active)
      .map((enemy) => ({
        id: enemy.enemy_id,
        kind: "enemy",
        enemyType: enemy.enemy_type,
        node: enemy.node,
        visible: true,
      })),
    ...game.pieces
      .filter((piece) => piece.alive)
      .map((piece) => ({
        id: piece.piece_id,
        kind: "piece",
        pieceId: piece.piece_id,
        label: piece.label,
        node: piece.node,
        reachedOuter: piece.reached_outer,
        active: piece.piece_id === game.active_piece_id,
        visible: true,
        captured: false,
      })),
  ];
}

function renderTokens() {
  const entities = currentEntities();
  const positions = computeEntityPositions(entities);
  refs.tokenLayer.innerHTML = entities
    .sort((a, b) => compareTuples(entityRenderOrder(a), entityRenderOrder(b)))
    .map((entity) => {
      const position = positions.get(entity.id);
      return entity.kind === "piece"
        ? pieceTokenMarkup(entity, position)
        : enemyTokenMarkup(entity, position);
    })
    .join("");
}

function computeEntityPositions(entities) {
  const grouped = new Map();
  entities.forEach((entity) => {
    const key = runtime.motion?.entityId === entity.id ? `moving:${entity.id}` : nodeKey(entity.node);
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(entity);
  });

  const positions = new Map();
  grouped.forEach((occupants, key) => {
    if (
      key === "0:0"
      && occupants.length === 2
      && occupants.every((occupant) => occupant.kind === "piece")
    ) {
      const base = nodePosition({ circle_index: 0, node_index: 0 }, boardConfig());
      occupants
        .sort((a, b) => compareTuples(entityRenderOrder(a), entityRenderOrder(b)))
        .forEach((entity) => {
          const direction = entity.pieceId === "white" ? -1 : 1;
          positions.set(entity.id, {
            x: base.x + direction * 24,
            y: base.y,
          });
        });
      return;
    }

    occupants
      .sort((a, b) => compareTuples(entityRenderOrder(a), entityRenderOrder(b)))
      .forEach((entity, index) => {
        const base = animatedOrStaticPosition(entity);
        if (occupants.length === 1) {
          positions.set(entity.id, base);
          return;
        }
        const angle = -Math.PI / 2 + (Math.PI * 2 * index) / occupants.length;
        const radius = entity.node.circle_index === 0
          ? 18
          : entity.node.circle_index === 1
            ? 10
            : entity.node.circle_index === 2
              ? 11
              : 12;
        positions.set(entity.id, {
          x: base.x + Math.cos(angle) * radius,
          y: base.y + Math.sin(angle) * radius,
        });
      });
  });
  return positions;
}

function compareTuples(a, b) {
  for (let index = 0; index < Math.min(a.length, b.length); index += 1) {
    if (a[index] < b[index]) return -1;
    if (a[index] > b[index]) return 1;
  }
  return 0;
}

function animatedOrStaticPosition(entity) {
  if (runtime.motion?.entityId === entity.id) {
    return motionPosition(runtime.motion);
  }
  return nodePosition(entity.node, boardConfig());
}

function motionPosition(motion) {
  const { source, destination, progress, sourcePoint, destinationPoint } = motion;
  if (sourcePoint && destinationPoint && (source.circle_index === 0 || destination.circle_index === 0)) {
    return {
      x: lerp(sourcePoint.x, destinationPoint.x, progress),
      y: lerp(sourcePoint.y, destinationPoint.y, progress),
    };
  }
  if (source.circle_index === destination.circle_index && source.circle_index > 0) {
    const startAngle = nodeAngle(source.node_index, boardConfig().nodes_per_circle);
    const stepAngle =
      (Math.PI * 2 * inferRingStep(source, destination, boardConfig().nodes_per_circle)) /
      boardConfig().nodes_per_circle;
    const angle = startAngle + stepAngle * progress;
    const radius = ringRadius(source.circle_index, boardConfig());
    return {
      x: BOARD_CENTER + Math.cos(angle) * radius,
      y: BOARD_CENTER + Math.sin(angle) * radius,
    };
  }
  const start = nodePosition(source, boardConfig());
  const end = nodePosition(destination, boardConfig());
  return {
    x: lerp(start.x, end.x, progress),
    y: lerp(start.y, end.y, progress),
  };
}

function percent(value) {
  return `${(value / VIEW_SIZE) * 100}%`;
}

function pieceTokenMarkup(entity, position) {
  return `
    <div
      class="token token-piece token-${entity.pieceId}${entity.active ? " is-active" : ""}${entity.reachedOuter ? " reached-outer" : ""}${
        entity.captured ? " is-captured" : ""
      }"
      style="--x:${percent(position.x)};--y:${percent(position.y)};--size:34px"
    ></div>
  `;
}

function enemyTokenMarkup(entity, position) {
  return `
    <div
      class="token token-enemy token-${entity.enemyType}"
      style="--x:${percent(position.x)};--y:${percent(position.y)};--size:${entity.node.circle_index === 0 ? 42 : 34}px"
    >
      ${entity.enemyType === "fox" ? foxSvg("token-icon") : snakeSvg("token-icon")}
    </div>
  `;
}

async function playTimeline(events, finalState) {
  runtime.animating = true;
  renderMeta({ ...runtime.game, resolved_events: events, message: refs.status.textContent }, { skipDice: true });

  for (const event of events) {
    if (["player_move", "enemy_move"].includes(event.kind)) {
      const entity = runtime.visualEntities.get(event.actor_id);
      if (!entity) continue;

      await animateMovement(event.actor_id, event.source, event.destination, movementDuration(event.kind));
      entity.node = event.destination;
      if (entity.kind === "piece") {
        entity.reachedOuter = finalState.pieces.find((piece) => piece.piece_id === entity.id)?.reached_outer ?? false;
      }
      renderTokens();
      continue;
    }

    if (event.kind === "capture") {
      const captured = capturedPiecesForEvent(event);
      if (captured.length) {
        await animateCapturedPieces(captured);
      }
    }
  }

  runtime.motion = null;
  runtime.visualEntities = null;
  runtime.animating = false;
  renderMeta({ state: runtime.game, resolved_events: [], message: refs.status.textContent }, { skipDice: true });
  renderBoard();
  updateOverlay();
}

function movementDuration(kind) {
  return 320;
}

function animateMovement(entityId, source, destination, duration) {
  const sourcePoint = currentRenderedPosition(entityId);
  const destinationPoint = nodePosition(destination, boardConfig());
  return new Promise((resolve) => {
    const start = performance.now();
    const tick = (timestamp) => {
      const elapsed = timestamp - start;
      const progress = Math.min(1, elapsed / duration);
      runtime.motion = {
        entityId,
        source,
        destination,
        sourcePoint,
        destinationPoint,
        progress: easeInOutCubic(progress),
      };
      renderTokens();
      if (progress >= 1) {
        runtime.motion = null;
        resolve();
        return;
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function currentRenderedPosition(entityId) {
  const entities = currentEntities();
  const positions = computeEntityPositions(entities);
  return positions.get(entityId) ?? null;
}

function capturedPiecesForEvent(event) {
  if (!event.destination) return [];
  return [...runtime.visualEntities.values()]
    .filter((entity) => (
      entity.kind === "piece"
      && entity.visible !== false
      && entity.active
      && nodesEqual(entity.node, event.destination)
    ))
    .map((entity) => entity.id);
}

async function animateCapturedPieces(pieceIds) {
  pieceIds.forEach((pieceId) => {
    const entity = runtime.visualEntities.get(pieceId);
    if (entity) {
      entity.captured = true;
    }
  });
  renderTokens();
  await wait(runtime.reducedMotion.matches ? 0 : 240);
  pieceIds.forEach((pieceId) => {
    const entity = runtime.visualEntities.get(pieceId);
    if (entity) {
      entity.visible = false;
    }
  });
  renderTokens();
}

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function setStatus(message) {
  refs.status.textContent = message;
}

function handleRequestError(error, fallbackMessage) {
  const message = error instanceof Error ? error.message : fallbackMessage;
  setStatus(message || fallbackMessage);
  updateOverlay();
  renderBoard();
}

async function resumeSavedGame() {
  if (runtime.savedGame) {
    runtime.game = runtime.savedGame;
    runtime.visualEntities = null;
    renderMeta({ message: "Saved game resumed.", resolved_events: [] });
    updateOverlay();
    renderBoard();
    return;
  }
  await loadCurrentGame({ activate: true });
}

refs.newGame.addEventListener("click", () => {
  void createNewGame();
});

refs.roll.addEventListener("click", () => submitAction({ type: "roll" }));
refs.resume.addEventListener("click", () => {
  void resumeSavedGame();
});
refs.help.addEventListener("click", () => refs.helpDialog.showModal());
refs.overlayHelp.addEventListener("click", () => refs.helpDialog.showModal());
refs.overlayResume.addEventListener("click", () => {
  void resumeSavedGame();
});
refs.start.addEventListener("click", async () => {
  await createNewGame();
});

window.addEventListener("keydown", (event) => {
  if (
    event.key === " "
    && runtime.game?.phase === "waiting_for_roll"
    && !runtime.animating
    && !runtime.pendingRequest
  ) {
    event.preventDefault();
    void submitAction({ type: "roll" });
  }
  if (event.key.toLowerCase() === "n") {
    void createNewGame();
  }
  if (event.key === "Escape") {
    if (refs.helpDialog.open) refs.helpDialog.close();
  }
});

runtime.reducedMotion.addEventListener("change", () => {
  renderBoard();
});

renderMeta({ message: "Preparing the board.", resolved_events: [] });
updateOverlay();
renderBoard();
void loadCurrentGame({ silent: true });
