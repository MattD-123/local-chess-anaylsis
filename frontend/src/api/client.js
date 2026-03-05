const JSON_HEADERS = {
  "Content-Type": "application/json",
};

async function parseResponse(response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

export async function newGame(payload) {
  const response = await fetch("/game/new", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function submitMove(payload) {
  const response = await fetch("/game/move", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function getHint(gameId) {
  const response = await fetch(`/game/hint?game_id=${encodeURIComponent(gameId)}`);
  return parseResponse(response);
}

export async function resignGame(payload) {
  const response = await fetch("/game/resign", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

export async function getGameAnalysis(gameId) {
  const response = await fetch(`/game/analysis?game_id=${encodeURIComponent(gameId)}`);
  return parseResponse(response);
}

export async function getGameHistory() {
  const response = await fetch("/game/history");
  return parseResponse(response);
}

export async function getOpeningStats() {
  const response = await fetch("/openings/stats");
  return parseResponse(response);
}

export async function getConfig() {
  const response = await fetch("/config");
  return parseResponse(response);
}

export async function updateConfig(patch) {
  const response = await fetch("/config", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify({ patch }),
  });
  return parseResponse(response);
}

export async function getHealth() {
  const response = await fetch("/health");
  return parseResponse(response);
}

export function createCommentarySource(gameId) {
  return new EventSource(`/game/commentary?game_id=${encodeURIComponent(gameId)}`);
}
