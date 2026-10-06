/* SonarChain browser workflow: simulation, safety evidence and HRC permits. */
const SAFETY_ABI = [
  "function recordEvent(bytes32 eventHash, bytes32 deviceIdHash, uint64 timestamp, uint8 severity, bool emergencyStop)",
  "function setReporter(address reporter, bool allowed)",
  "function setSupervisor(address account, bool allowed)",
  "function supervisors(address) view returns (bool)",
  "function clearEmergencyStop(bytes32 deviceIdHash)"
  ,"function owner() view returns (address)"
  ,"function reporters(address) view returns (bool)"
  ,"function emergencyStopByDevice(bytes32) view returns (bool)"
  ,"function evidenceExists(bytes32) view returns (bool)"
  ,"function recordEvidence(bytes32 evidenceHash, bytes32 deviceIdHash, uint64 measuredAt, uint8 severity, bool emergencyStop, bytes32 evidenceSchema)"
];
const PERMIT_ABI = [
  "function createPermit(bytes32 permitId, bytes32 workerIdHash, bytes32 zoneIdHash, bytes32 taskIdHash, address worker, uint64 validFrom, uint64 validUntil)",
  "function approvePermit(bytes32 permitId)",
  "function recordZoneEntry(bytes32 permitId, bytes32 telemetryEventHash)",
  "function confirmHandoff(bytes32 handoffId, bytes32 permitId, bytes32 robotIdHash)",
  "function completePermit(bytes32 permitId)",
  "function setSupervisor(address account, bool allowed)",
  "function setGateway(address account, bool allowed)"
  ,"function owner() view returns (address)"
  ,"function gateways(address) view returns (bool)"
];
const SEVERITY = { SAFE: 0, WARNING: 1, DANGER: 2, EMERGENCY: 3 };
const state = { distance: 86.4, events: [], provider: null, signer: null, currentAddress: null, safety: null, permit: null, permitId: null, permitStatus: 0, estopActive: false, estopOnChain: false, estopPending: false,
  mode: "simulation", latest: null, gatewayOnline: false, gatewayTimer: null, socket: null, reconnectTimer: null,
  chainId: null, reporter: false, supervisor: false, safetyOwner: false, requestPending: false, pollPending: false, permissionsVersion: 0,
  simulationLatest: null, gatewayStops: {}, stopRevision: 0, safetyIssue: "", historyCheckedAt: 0, historyPending: false };
const $ = (id) => document.getElementById(id);

function classify(distance) { return distance === null || !Number.isFinite(distance) || distance < 2 || distance > 450 ? "SENSOR_FAULT" : distance <= 30 ? "EMERGENCY" : distance <= 60 ? "WARNING" : "SAFE"; }
function sampleSeverity(distance) {
  const severity = classify(distance), reported = state.mode === "gateway" ? state.latest?.severity : null;
  if (reported === "SENSOR_FAULT" || reported === "EMERGENCY") return reported;
  return reported === "WARNING" && severity === "SAFE" ? "WARNING" : severity;
}
function activeEvents() { return state.events.filter((event) => event.source === state.mode && event.severity === "EMERGENCY"); }
function stopActive() { return state.estopActive || state.estopOnChain; }
function latestTelemetryEvent() { return state.mode === "gateway" ? { id: state.latest?.event_id } : state.simulationLatest; }
function resetSafe() { return classify(state.distance) === "SAFE" && (state.mode === "simulation" || (liveFresh() && state.latest?.severity === "SAFE" && !state.latest?.emergency_stop)); }
function canResetStop() { return Boolean(state.signer && state.supervisor && !state.estopPending && !state.requestPending && resetSafe()); }
function stopResetReasons() {
  const reasons = [];
  if (state.estopPending || state.requestPending) reasons.push("Đang chờ giao dịch hoàn tất.");
  if (state.mode === "gateway" && !liveFresh()) reasons.push("Cần mẫu mới từ ESP32; dữ liệu quá 5 giây hoặc gateway mất kết nối.");
  else if (!resetSafe()) {
    const distance = state.distance === null ? "" : ` (${state.distance.toFixed(1)} cm)`;
    reasons.push(`Đang ${sampleSeverity(state.distance)}${distance}; cần SAFE > 60 cm và thiết bị hết yêu cầu dừng trước khi gỡ.`);
  }
  if (!state.signer) reasons.push("Kết nối ví Supervisor và nhập đúng HRCSafetyLog.");
  else if (state.safetyIssue) reasons.push(state.safetyIssue);
  else if (!state.supervisor) reasons.push("Ví hiện tại chưa có Supervisor tại HRCSafetyLog; Owner cần cấp quyền ở Ví & vai trò.");
  return reasons;
}
function releaseLocalStop(revision, mode, device) {
  if (revision !== state.stopRevision || mode !== state.mode || device !== $("estopDevice").value || !resetSafe()) return false;
  if (mode === "gateway") state.gatewayStops[device] = false;
  else state.simulationEstop = false;
  state.estopActive = false;
  return true;
}
function liveFresh() { return Boolean(state.gatewayOnline && state.latest && Date.now() - Date.parse(state.latest.received_at) < 5000); }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function bytes32(value) { const text = String(value || ""); return /^0x[0-9a-f]{64}$/i.test(text) ? text : /^[0-9a-f]{64}$/i.test(text) ? `0x${text}` : null; }
function hashText(value) { return window.ethers.keccak256(ethers.toUtf8Bytes(value)); }
function shortAddress(address) { return `${address.slice(0, 6)}…${address.slice(-4)}`; }
function now() { return new Date().toLocaleTimeString("vi-VN", { hour12: false }); }
function toast(message) { const node = $("toast"); node.textContent = message; node.classList.add("show"); clearTimeout(window.__toast); window.__toast = setTimeout(() => node.classList.remove("show"), 4200); }
function transactionError(error, fallback = "Giao dịch thất bại.") {
  const detail = [error?.code, error?.shortMessage, error?.message, error?.info?.error?.message, error?.error?.message].join(" ");
  if (/NONCE_EXPIRED|nonce too low|nonce has already been used/i.test(detail)) {
    return "Nonce đã được dùng. Dừng gateway đang ký bằng cùng ví. Trên mạng Hardhat local, vào MetaMask → Settings → Developer tools → Delete activity and nonce data, rồi thử lại. Dùng ví Reporter riêng cho gateway; ví Owner/Supervisor thao tác trên web.";
  }
  return error?.shortMessage || error?.message || fallback;
}
async function copyText(value, label) {
  const text = String(value || "").trim();
  if (!text || text.startsWith("Chưa") || text === "0x…") return toast(`Chưa có ${label} để sao chép.`);
  try { await navigator.clipboard.writeText(text); toast(`Đã sao chép ${label}.`); }
  catch (error) { window.prompt(`Sao chép ${label}:`, text); }
}
function copyInputValue(inputId, label) { copyText($(inputId)?.value, label); }

function updateSensor(value) {
  const severity = sampleSeverity(value); const kind = severity.toLowerCase();
  const card = $("sensorCard"); card.className = `sensor-card ${severity === "EMERGENCY" || severity === "SENSOR_FAULT" ? "danger" : kind}`;
  $("distanceValue").textContent = value === null ? "—" : value.toFixed(1);
  $("distanceBar").style.width = `${Math.min(100, Math.max(3, value / 1.2))}%`;
  $("distanceBar").style.background = kind === "emergency" ? "var(--red)" : kind === "warning" ? "var(--amber)" : "var(--mint)";
  const tag = $("sensorState"); tag.textContent = severity; tag.className = `tag tag-${kind === "emergency" ? "danger" : kind}`;
  $("distanceEcho").textContent = value === null ? "Không có echo hợp lệ" : `echo ước tính ${(value * 0.058).toFixed(1)} ms`;
}
function renderSensors() {
  updateSensor(state.distance);
  const stale = state.mode === "gateway" && !liveFresh();
  let severity = sampleSeverity(state.distance);
  if (stale) severity = "NO DATA";
  const distanceText = state.distance === null ? "—" : state.distance.toFixed(1);
  $("minDistance").textContent = distanceText;
  $("sampleTime").textContent = state.mode === "gateway" ? (state.latest ? new Date(state.latest.received_at).toLocaleTimeString("vi-VN") : "Chưa nhận mẫu") : `${now()} · mô phỏng`;
  $("zoneDistance").textContent = `${distanceText} cm`;
  const node = $("overallState"); node.textContent = severity; node.className = severity === "EMERGENCY" ? "state-danger" : severity === "WARNING" ? "state-warning" : "state-safe";
  $("overallHint").textContent = severity === "EMERGENCY" ? "Emergency stop được kích hoạt" : severity === "WARNING" ? "Vật thể trong vùng cảnh báo" : "Không có cảnh báo";
  const tone = severity === "EMERGENCY" ? "danger" : severity === "WARNING" ? "warning" : "safe"; $("safetyBanner").className = `safety-banner ${tone}`;
  $("bannerTitle").textContent = severity === "EMERGENCY" ? "Nguy hiểm — yêu cầu dừng" : severity === "WARNING" ? "Cảnh báo khoảng cách" : "Không có cảnh báo hiện tại";
  $("bannerText").textContent = severity === "EMERGENCY" ? "Đã nhận yêu cầu dừng; kiểm tra trạng thái tại thiết bị" : severity === "WARNING" ? "Cảnh báo khoảng cách hoặc AI phát hiện tiến gần" : "Không có cảnh báo từ mẫu hiện tại";
  $("workerZoneState").textContent = severity;
  if (severity === "SENSOR_FAULT" || stale) {
    $("sensorState").textContent = severity; $("sensorState").className = "tag tag-danger";
    $("safetyBanner").className = "safety-banner warning";
    $("bannerTitle").textContent = stale ? "Chưa có dữ liệu mới" : "Lỗi cảm biến / AI";
    $("bannerText").textContent = stale ? "Mẫu đã quá 5 giây hoặc gateway mất kết nối. Kiểm tra ESP32 và Serial." : "Mẫu lỗi đã được ghi nhận; kiểm tra thiết bị.";
    $("overallState").textContent = severity; $("overallState").className = "state-warning";
    $("overallHint").textContent = "Chưa thể xác nhận trạng thái vùng";
  }
  if (stopActive()) showEstopState();
  $("gatewayStatus").textContent = state.mode === "simulation" ? "MÔ PHỎNG" : liveFresh() ? "GATEWAY · LIVE" : "GATEWAY · CHỜ DỮ LIỆU";
  $("simulateButton").disabled = state.mode !== "simulation";
  updateRecordButton();
  updatePermitButtons();
}
function showEstopState() {
  $("safetyBanner").className = "safety-banner danger";
  $("bannerTitle").textContent = "E-STOP ACTIVE";
  $("bannerText").textContent = "Khóa dừng khẩn cấp — chỉ Supervisor được gỡ sau khi vùng an toàn";
  $("overallState").textContent = "E-STOP"; $("overallState").className = "state-danger";
  $("overallHint").textContent = "Dừng khẩn cấp đang bật";
  $("workerZoneState").textContent = "LOCKED";
}
function setEstopUi(active, message = "") {
  state.estopActive = active;
  active = stopActive();
  renderSensors();
  const badge = $("estopBadge"); if (badge) { badge.textContent = active ? "ACTIVE" : "READY"; badge.className = `estop-badge ${active ? "" : "ready"}`; }
  const stateLabel = $("estopState"); if (stateLabel) stateLabel.textContent = active ? "E-STOP ACTIVE" : "E-STOP ARMED";
  if (state.mode === "gateway") {
    const uncertain = !liveFresh() || state.latest?.severity === "SENSOR_FAULT";
    if (badge) { badge.textContent = active ? "ACTIVE" : uncertain ? "CHECK DEVICE" : "NO REQUEST"; badge.className = `estop-badge ${uncertain || active ? "" : "ready"}`; }
    if (stateLabel) stateLabel.textContent = active ? "E-STOP ACTIVE" : uncertain ? "KIỂM TRA THIẾT BỊ" : "ĐANG GIÁM SÁT";
  }
  const trigger = $("triggerEstopButton"); const panelTrigger = $("estopPanelTrigger"); const clear = $("clearEstopButton"); const panelClear = $("estopPanelClear");
  if (trigger) trigger.disabled = state.mode !== "simulation" || active || state.estopPending; if (panelTrigger) panelTrigger.disabled = state.mode !== "simulation" || active || state.estopPending;
  const canClear = active && canResetStop();
  if (clear) clear.disabled = !canClear; if (panelClear) panelClear.disabled = !canClear;
  $("clearChainButton").disabled = !state.estopOnChain || !canResetStop();
  $("estopDevice").readOnly = state.mode === "gateway" || active || state.estopPending || state.requestPending;
  const reason = stopResetReasons().join(" ");
  const clearHint = active ? reason || "Supervisor có thể gỡ sau khi kiểm tra vùng an toàn." : "Chưa có E-STOP cần gỡ.";
  if (clear) clear.title = clearHint; if (panelClear) panelClear.title = clearHint;
  $("clearChainButton").title = state.estopOnChain ? clearHint : "Chưa có khóa trên chain; E-STOP giám sát vẫn hoạt động độc lập.";
  const triggerHint = active ? "E-STOP đã bật tự động; không cần kích hoạt lại." : state.mode === "gateway" ? "ESP32 tự phát yêu cầu dừng khi EMERGENCY." : "Tạo yêu cầu dừng mô phỏng.";
  if (trigger) trigger.title = triggerHint; if (panelTrigger) panelTrigger.title = triggerHint;
  $("estopMessage").textContent = message || (active ? `E-STOP đã kích hoạt. ${clearHint}` : reason || "Đang giám sát; EMERGENCY sẽ tự kích hoạt E-STOP.");
}
function deviceHash() { return hashText($("estopDevice").value.trim() || "HRC-ESP32-01"); }
async function triggerEstop() {
  if (state.mode !== "simulation") return toast("Đang giám sát ESP32. Nút này chỉ tạo E-STOP mô phỏng.");
  if (state.estopActive) return;
  const event = makeEvent("EMERGENCY");
  setEstopUi(true, "E-STOP mô phỏng đã bật. Blockchain chỉ lưu bằng chứng, không điều khiển phần cứng.");
  toast("E-STOP mô phỏng đã tự kích hoạt.");
  $("chainMessage").textContent = "Event mô phỏng đã tạo. Nhấn ghi EMERGENCY để ký giao dịch.";
}
async function clearEstop() {
  if (!state.supervisor || !state.signer) return toast("Chỉ ví Supervisor của HRCSafetyLog được gỡ E-STOP.");
  if (!stopActive() || !canResetStop()) return toast("Chưa thể gỡ: cần mẫu SAFE mới và giao dịch trước phải hoàn tất.");
  const revision = state.stopRevision, mode = state.mode, device = $("estopDevice").value;
  let failureMessage = "";
  try {
    state.estopPending = true; setEstopUi(state.estopActive, "Supervisor đang kiểm tra và gỡ E-STOP…");
    const contract = new ethers.Contract($("contractAddress").value.trim(), SAFETY_ABI, state.signer);
    if (!await contract.supervisors(await state.signer.getAddress())) throw new Error("Quyền Supervisor đã bị thu hồi hoặc ví chưa được cấp quyền.");
    if (state.estopOnChain) {
      const tx = await contract.clearEmergencyStop(deviceHash());
      await tx.wait(); state.estopOnChain = false;
    }
    const released = releaseLocalStop(revision, mode, device);
    setEstopUi(state.estopActive, released ? (mode === "simulation" ? "Supervisor đã gỡ E-STOP mô phỏng sau khi vùng an toàn." : "Supervisor đã gỡ khóa giám sát. Kiểm tra/reset cơ cấu dừng tại ESP32 riêng.") : "Có yêu cầu dừng mới hoặc nguồn dữ liệu đã thay đổi; E-STOP vẫn được giữ.");
    toast(released ? "Supervisor đã gỡ E-STOP." : "E-STOP vẫn được giữ; cần kiểm tra lại.");
  } catch (error) { failureMessage = transactionError(error, "Không thể gỡ E-STOP."); toast(failureMessage); }
  finally { state.estopPending = false; await refreshSafetyPermissions(); setEstopUi(state.estopActive, failureMessage); }
}
function makeEvent(forceSeverity = null) {
  const severity = forceSeverity || classify(state.distance); const timestamp = new Date().toISOString(); const device = $("estopDevice").value.trim() || "HRC-ESP32-01";
  const id = hashText(`${device}|${timestamp}|${state.distance?.toFixed(2) ?? "null"}|${severity}|${state.simulationStep || 0}`);
  const event = { id, device, timestamp, severity, minimum: state.distance, distance: state.distance, emergency: severity === "EMERGENCY", tx: null, source: "simulation", status: "local" };
  state.simulationLatest = event;
  if (event.emergency) { state.estopActive = true; state.simulationEstop = true; state.stopRevision++; state.events.unshift(event); }
  renderEvents(); return event;
}
function renderEvents() {
  const emergencyEvents = activeEvents();
  $("eventCount").textContent = emergencyEvents.filter((event) => event.tx).length;
  $("totalEventCount").textContent = `${emergencyEvents.length} EMERGENCY · ${emergencyEvents.filter((event) => event.tx).length} on-chain`;
  if (!emergencyEvents.length) {
    $("eventList").innerHTML = `<div class="empty-state"><span>◎</span><p>Chưa có EMERGENCY ở nguồn dữ liệu đang chọn.</p></div>`;
    updateRecordButton(); updatePermitButtons();
    return;
  }
  $("eventList").innerHTML = emergencyEvents.slice(0, 8).map((event) => {
    const type = event.severity === "SENSOR_FAULT" ? "emergency" : event.severity.toLowerCase();
    const tx = /^0x[0-9a-f]{64}$/i.test(event.tx || "") ? event.tx : null;
    const explorer = event.chainId === 11155111 ? "https://sepolia.etherscan.io/tx/" : event.chainId === 1 ? "https://etherscan.io/tx/" : null;
    const txView = tx ? (explorer ? `<a href="${explorer}${tx}" target="_blank" rel="noreferrer">Xem giao dịch ↗</a>` : `<span title="${tx}">tx ${tx.slice(0, 12)}… · local</span>`) : `<span>${escapeHtml(event.status)} · ${event.source === "gateway" ? "SHA-256" : "mô phỏng"}</span>`;
    return `<div class="event-row"><span class="event-marker ${type}"></span><div class="event-main"><strong>${escapeHtml(event.severity)} · ${event.minimum === null ? "—" : event.minimum.toFixed(1)} cm${event.emergency ? " · yêu cầu dừng" : ""}</strong><small>${escapeHtml(new Date(event.timestamp).toLocaleString("vi-VN"))} · ${escapeHtml(event.device)}</small></div><div class="event-meta">${escapeHtml(event.id.slice(0, 10))}…${txView}</div></div>`;
  }).join("");
  updateRecordButton();
  updatePermitButtons();
}

const GATEWAY_API = "http://127.0.0.1:8000";
function addGatewayTelemetry(row) {
  if (!row || !row.event_id || !row.device_id) return;
  const confirmed = rememberGatewayEvent(row);
  // An HTTP history response or delayed WebSocket must not move the display back.
  if (state.latest && Number(row.id) < Number(state.latest.id)) {
    renderEvents();
    if (confirmed && state.mode === "gateway") void refreshSafetyPermissions();
    return;
  }
  if ((!state.latest || row.event_id !== state.latest.event_id) && (row.severity === "EMERGENCY" || row.emergency_stop || classify(Number(row.distance_cm)) === "EMERGENCY")) {
    state.gatewayStops[row.device_id] = true; state.stopRevision++;
  }
  state.latest = row;
  state.gatewayOnline = true;
  if (state.mode === "gateway") applyLatestGateway();
  renderEvents();
  if (confirmed && state.mode === "gateway") void refreshSafetyPermissions();
}
function rememberGatewayEvent(row) {
  if (row.severity !== "EMERGENCY") return;
  const distance = row.distance_cm === null || row.distance_cm === undefined ? null : Number(row.distance_cm);
  const event = { id: row.event_id, evidenceHash: row.evidence_hash, gatewayId: row.id, device: row.device_id,
    timestamp: row.measured_at || row.received_at, severity: row.severity, minimum: Number.isFinite(distance) ? distance : null,
    emergency: Boolean(row.emergency_stop), tx: bytes32(row.tx_hash), source: "gateway", status: row.evidence_status || "offchain" };
  const existing = state.events.find((item) => item.source === "gateway" && item.id === event.id);
  if (existing) {
    const confirmed = Boolean(event.tx && event.tx !== existing.tx);
    if (!event.tx && existing.tx) { event.tx = existing.tx; event.status = existing.status; }
    Object.assign(existing, event);
    return confirmed;
  } else state.events.unshift(event);
  state.events = state.events.slice(0, 500);
  return Boolean(event.tx);
}
function applyLatestGateway() {
  state.distance = state.latest?.distance_cm == null ? null : Number(state.latest.distance_cm);
  if (!Number.isFinite(state.distance)) state.distance = null;
  // This mirrors a report from the device. It never submits a transaction.
  state.estopActive = Boolean(state.gatewayStops[state.latest?.device_id]);
  $("estopDevice").value = state.latest?.device_id || "HRC-ESP32-01";
  renderSensors(); setEstopUi(state.estopActive);
}
function setDataMode() {
  const mode = $("dataMode").value === "gateway" ? "gateway" : "simulation";
  const changed = mode !== state.mode;
  if (changed && state.mode === "simulation") state.simulationEstop = state.estopActive;
  state.mode = mode;
  $("dataMode").value = mode;
  try { window.localStorage.setItem("sonarchain.dataMode", mode); } catch (_) {}
  $("estopDevice").readOnly = state.mode === "gateway";
  if (state.mode === "gateway") applyLatestGateway();
  else {
    if (changed) { state.distance = 86.4; state.estopActive = Boolean(state.simulationEstop); }
    setEstopUi(state.estopActive);
  }
  renderEvents();
  if (changed) void refreshSafetyPermissions();
}
function restoreDataMode() {
  try {
    const saved = window.localStorage.getItem("sonarchain.dataMode");
    if (saved === "gateway" || saved === "simulation") $("dataMode").value = saved;
  } catch (_) {}
  setDataMode();
}
async function loadGatewayHistory() {
  if (state.historyPending) return;
  state.historyPending = true;
  state.historyCheckedAt = Date.now();
  try {
    const response = await fetch(`${GATEWAY_API}/api/telemetry/history?limit=500&severity=EMERGENCY`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (!response.ok) return;
    const payload = await response.json();
    let confirmed = false;
    [...(payload.telemetry || [])].reverse().forEach((row) => { if (rememberGatewayEvent(row)) confirmed = true; });
    renderEvents();
    if (confirmed && state.mode === "gateway") void refreshSafetyPermissions();
  } catch (_) {
    // The dashboard can still be used in simulation mode when the gateway API is off.
  } finally { state.historyPending = false; }
}
async function pollGatewayLatest() {
  if (state.pollPending) return;
  state.pollPending = true;
  try {
    const response = await fetch(`${GATEWAY_API}/api/telemetry/latest?ts=${Date.now()}`, { cache: "no-store", signal: AbortSignal.timeout(3000) });
    if (!response.ok) throw new Error("Gateway API unavailable");
    const payload = await response.json();
    state.gatewayOnline = true;
    if (payload.telemetry) addGatewayTelemetry(payload.telemetry);
    // A receipt can confirm an older EMERGENCY after newer SAFE/WARNING samples.
    if (Date.now() - state.historyCheckedAt >= 5000) await loadGatewayHistory();
  } catch (_) {
    state.gatewayOnline = false;
  } finally {
    state.pollPending = false;
    if (state.mode === "gateway") { renderSensors(); setEstopUi(state.estopActive); }
  }
}
function startGatewayLive() {
  void loadGatewayHistory();
  if (!state.gatewayTimer) state.gatewayTimer = window.setInterval(pollGatewayLatest, 1000);
  void pollGatewayLatest();
  connectGatewaySocket();
}
function connectGatewaySocket() {
  if (state.socket && state.socket.readyState < 2) return;
  try {
    const socket = new WebSocket("ws://127.0.0.1:8000/ws/telemetry");
    state.socket = socket;
    socket.onmessage = (message) => {
      try { addGatewayTelemetry(JSON.parse(message.data)); } catch (_) {}
    };
    socket.onclose = () => { state.socket = null; clearTimeout(state.reconnectTimer); state.reconnectTimer = window.setTimeout(connectGatewaySocket, 3000); };
    socket.onerror = () => socket.close();
  } catch (_) {}
}
function simulate() {
  if (state.mode !== "simulation") return;
  const samples = [86.4, 48.2, 24.6, 76.5];
  const sample = samples[(state.simulationStep || 0) % samples.length]; state.simulationStep = (state.simulationStep || 0) + 1;
  state.distance = sample;
  const event = makeEvent(); setEstopUi(state.estopActive);
  toast(event.emergency ? "EMERGENCY: E-STOP tự kích hoạt; đã ghi log." : `${event.severity}: telemetry đã cập nhật.`);
}

async function syncWallet({ request = false, notify = false } = {}) {
  if (!window.ethereum) return false;
  state.provider = new ethers.BrowserProvider(window.ethereum);
  const accounts = request
    ? await state.provider.send("eth_requestAccounts", [])
    : await window.ethereum.request({ method: "eth_accounts" });
  if (!accounts.length) {
    state.signer = null;
    state.currentAddress = null;
    state.chainId = null; state.reporter = false; state.supervisor = false; state.safetyOwner = false; state.safetyIssue = "";
    state.permissionsVersion++; state.estopOnChain = false; $("clearChainButton").disabled = true;
    $("chainStopStatus").textContent = "Khóa trên chain: chưa kết nối";
    $("chainName").textContent = "CHƯA KẾT NỐI";
    $("walletAddress").textContent = "Chưa kết nối";
    $("networkLabel").textContent = "Ví chưa kết nối";
    $("connectButton").textContent = "Kết nối ví";
    $("recordButton").disabled = true;
    if ($("copyWalletButton")) $("copyWalletButton").disabled = true;
    updatePermitButtons();
    updateRoleButtons();
    setEstopUi(state.estopActive);
    return false;
  }
  state.signer = await state.provider.getSigner();
  const address = await state.signer.getAddress();
  state.currentAddress = address;
  const network = await state.provider.getNetwork();
  state.chainId = Number(network.chainId);
  $("chainName").textContent = state.chainId === 31337 ? "HARDHAT 31337" : state.chainId === 11155111 ? "SEPOLIA" : `CHAIN ${state.chainId}`;
  $("walletAddress").textContent = shortAddress(address);
  $("networkLabel").textContent = `Wallet · chain ${network.chainId}`;
  $("connectButton").textContent = "Đã kết nối";
  await refreshSafetyPermissions();
  if ($("copyWalletButton")) $("copyWalletButton").disabled = false;
  updatePermitButtons();
  setEstopUi(state.estopActive);
  updateRoleButtons();
  if (notify) toast(`Đã chuyển sang ví ${shortAddress(address)}.`);
  return true;
}
async function connectWallet() {
  if (!window.ethereum) return toast("Chưa tìm thấy MetaMask — hãy cài extension hoặc dùng mô phỏng.");
  try {
    await syncWallet({ request: true });
    toast("Đã kết nối ví.");
  } catch (error) { toast(error.shortMessage || error.message || "Không thể kết nối ví."); }
}
function watchWallet() {
  if (!window.ethereum?.on) return;
  const refresh = (notify = false) => syncWallet({ notify }).catch((error) => toast(error.shortMessage || error.message || "Không thể đồng bộ MetaMask."));
  window.ethereum.on("accountsChanged", () => refresh(true));
  window.ethereum.on("chainChanged", () => refresh(false));
  window.ethereum.on("connect", () => refresh(false));
  window.ethereum.on("disconnect", () => refresh(false));
  // Some MetaMask versions update selectedAddress before emitting accountsChanged.
  window.setInterval(() => {
    if (window.ethereum.selectedAddress && window.ethereum.selectedAddress.toLowerCase() !== (state.currentAddress || "").toLowerCase()) refresh(false);
  }, 1000);
}
function updateRoleButtons() {
  const address = $("roleAddress")?.value.trim(); const ready = Boolean(state.signer && ethers.isAddress(address));
  if ($("assignRoleButton")) $("assignRoleButton").disabled = !ready; if ($("revokeRoleButton")) $("revokeRoleButton").disabled = !ready;
}
function roleMessage(message) { $("roleMessage").textContent = message; }
async function assignRole(allowed) {
  if (!state.signer) return roleMessage("Kết nối owner trước.");
  const address = $("roleAddress").value.trim(); const role = $("roleSelect").value;
  if (!ethers.isAddress(address)) return roleMessage("Địa chỉ account chưa hợp lệ.");
  try {
    let tx; if (role === "reporter") { const contractAddress = $("contractAddress").value.trim(); if (!ethers.isAddress(contractAddress)) throw new Error("Nhập HRCSafetyLog trước."); state.safety = new ethers.Contract(contractAddress, SAFETY_ABI, state.signer); tx = await state.safety.setReporter(address, allowed); }
    else if (role === "supervisor") {
      const safetyAddress = $("contractAddress").value.trim(), permitAddress = $("permitContractAddress").value.trim();
      if (!ethers.isAddress(safetyAddress) || !ethers.isAddress(permitAddress)) throw new Error("Nhập cả HRCSafetyLog và WorkPermitHandoff để cấp/thu hồi Supervisor.");
      const safety = new ethers.Contract(safetyAddress, SAFETY_ABI, state.signer), permit = new ethers.Contract(permitAddress, PERMIT_ABI, state.signer);
      const [safetyOwner, permitOwner] = await Promise.all([safety.owner(), permit.owner()]);
      if ([safetyOwner, permitOwner].some((owner) => owner.toLowerCase() !== state.currentAddress.toLowerCase())) throw new Error("Cần owner của cả hai contract để quản lý Supervisor.");
      roleMessage("Supervisor: xác nhận 1/2 — quyền gỡ E-STOP tại HRCSafetyLog.");
      tx = await safety.setSupervisor(address, allowed); await tx.wait();
      roleMessage("Safety đã cập nhật. Xác nhận 2/2 — quyền duyệt permit tại WorkPermitHandoff.");
      try { tx = await permit.setSupervisor(address, allowed); await tx.wait(); }
      catch (error) { throw new Error(`Safety đã ${allowed ? "cấp" : "thu hồi"} Supervisor; Permit chưa cập nhật. Thử lại để đồng bộ. ${transactionError(error)}`); }
    }
    else { const contractAddress = $("permitContractAddress").value.trim(); if (!ethers.isAddress(contractAddress)) throw new Error("Nhập WorkPermitHandoff trước."); state.permit = new ethers.Contract(contractAddress, PERMIT_ABI, state.signer); tx = await state.permit.setGateway(address, allowed); }
    if (role !== "supervisor") { roleMessage(`Đang chờ xác nhận ${allowed ? "cấp" : "thu hồi"} role…`); await tx.wait(); }
    await refreshSafetyPermissions(); roleMessage(`${allowed ? "Đã cấp" : "Đã thu hồi"} ${role} · tx ${tx.hash.slice(0, 12)}…`); toast(`${allowed ? "Đã cấp" : "Đã thu hồi"} role ${role}.`);
  } catch (error) { roleMessage(transactionError(error, "Không thể cập nhật role. Hãy dùng owner của contract.")); }
}
async function recordOnChain() {
  if (!state.signer || !state.reporter || state.requestPending || state.estopPending) return toast("Cần ví Reporter và chờ giao dịch trước hoàn tất."); const address = $("contractAddress").value.trim(); if (!ethers.isAddress(address)) return toast("Địa chỉ HRCSafetyLog chưa hợp lệ."); const event = activeEvents().find((item) => item.severity === "EMERGENCY" && !item.tx);
  if (!event) return toast("Chưa có EMERGENCY chưa ghi ở nguồn đang chọn.");
  if (event.severity !== "EMERGENCY") {
    $("chainMessage").textContent = "SAFE/WARNING chỉ lưu off-chain; chỉ EMERGENCY được ghi lên chain.";
    return toast("Chỉ event EMERGENCY mới được ghi lên blockchain.");
  }
  try {
    state.requestPending = true; updateRecordButton();
    state.safety = new ethers.Contract(address, SAFETY_ABI, state.signer);
    const digest = bytes32(event.source === "gateway" ? event.evidenceHash : event.id);
    if (!digest) throw new Error("Thiếu commitment 32 byte hợp lệ; không thể ghi bằng chứng.");
    if (await state.safety.evidenceExists(digest)) throw new Error("Commitment này đã tồn tại trên chain. Đồng bộ trạng thái gateway trước khi thử lại.");
    $("chainMessage").textContent = "Đang chờ xác nhận giao dịch EMERGENCY…";
    const timestamp = Math.floor(new Date(event.timestamp).getTime() / 1000);
    if (!Number.isFinite(timestamp) || timestamp <= 0) throw new Error("Timestamp không hợp lệ.");
    const tx = event.source === "gateway"
      ? await state.safety.recordEvidence(digest, hashText(event.device), timestamp, SEVERITY.EMERGENCY, true, hashText("sonarchain.evidence.v1"))
      : await state.safety.recordEvent(digest, hashText(event.device), timestamp, SEVERITY.EMERGENCY, true);
    await tx.wait(); event.tx = tx.hash; event.status = "confirmed"; event.chainId = state.chainId;
    renderEvents(); await refreshSafetyPermissions(); $("chainMessage").textContent = `Đã ghi EMERGENCY on-chain · ${tx.hash}`; toast("EMERGENCY đã được ghi lên blockchain.");
  }
  catch (error) { const message = transactionError(error); $("chainMessage").textContent = message; toast(message); }
  finally { state.requestPending = false; updateRecordButton(); }
}

function updateRecordButton() {
  $("recordButton").disabled = !state.signer || !state.reporter || state.requestPending || state.estopPending || !activeEvents().some((event) => event.severity === "EMERGENCY" && !event.tx);
}
async function refreshSafetyPermissions() {
  const version = ++state.permissionsVersion;
  state.reporter = false; state.supervisor = false; state.safetyOwner = false; state.estopOnChain = false; state.safetyIssue = "";
  setEstopUi(state.estopActive);
  updateRecordButton(); $("clearChainButton").disabled = true;
  const address = $("contractAddress").value.trim();
  if (!state.signer || !ethers.isAddress(address)) return;
  try {
    if (await state.provider.getCode(address) === "0x") throw new Error("Địa chỉ không có contract trên mạng ví đang dùng.");
    const contract = new ethers.Contract(address, SAFETY_ABI, state.signer);
    const account = state.currentAddress;
    const [owner, reporter, supervisor, stopped] = await Promise.all([contract.owner(), contract.reporters(account), contract.supervisors(account), contract.emergencyStopByDevice(deviceHash())]);
    if (version !== state.permissionsVersion) return;
    state.safetyOwner = owner.toLowerCase() === account.toLowerCase();
    state.reporter = state.safetyOwner || reporter;
    state.supervisor = supervisor;
    state.estopOnChain = stopped;
    if (stopped) {
      state.estopActive = true;
      if (state.mode === "simulation") state.simulationEstop = true;
      else if (state.latest) state.gatewayStops[state.latest.device_id] = true;
    }
    $("chainStopStatus").textContent = stopped ? "Khóa trên chain: ACTIVE" : "Khóa trên chain: CLEAR";
    $("clearChainButton").disabled = !state.supervisor || !stopped || !canResetStop();
    if (!state.reporter) $("chainMessage").textContent = "Ví đang dùng chưa có quyền Reporter; owner cần cấp quyền.";
  } catch (error) {
    if (version !== state.permissionsVersion) return;
    let message = error.shortMessage || error.message;
    try {
      // Permit has owner/supervisors too; gateways distinguishes it from Safety.
      await new ethers.Contract(address, PERMIT_ABI, state.signer).gateways(state.currentAddress);
      message = "Ô HRCSafetyLog đang chứa WorkPermitHandoff. Chuyển địa chỉ này sang ô WorkPermitHandoff và nhập HRCSafetyLog (dòng contract= khi deploy).";
    } catch (_) {
      if (error.code === "CALL_EXCEPTION" || error.code === "BAD_DATA") message = "Không đọc được quyền HRCSafetyLog. Kiểm tra đúng địa chỉ contract và mạng ví; bản cũ chưa có Supervisor cần deploy lại.";
    }
    if (version !== state.permissionsVersion) return;
    state.safetyIssue = message;
    $("chainMessage").textContent = message;
    $("chainStopStatus").textContent = "Khóa trên chain: chưa đọc được";
  }
  updateRecordButton();
  setEstopUi(state.estopActive);
}
async function clearChainStop() {
  if (state.estopOnChain) await clearEstop();
}

function permitHash(value) { return hashText(`sonarchain-permit|${value}`); }
function permitMessage(message) { $("permitMessage").textContent = message; }
function updatePermitButtons() {
  const ready = Boolean(state.signer && ethers.isAddress($("permitContractAddress").value.trim())); $("createPermitButton").disabled = !ready; $("approvePermitButton").disabled = !ready || !state.permitId || state.permitStatus !== 1; $("entryButton").disabled = !ready || !state.permitId || state.permitStatus !== 2 || !entryAllowed(); $("handoffButton").disabled = !ready || !state.permitId || state.permitStatus !== 3; $("completePermitButton").disabled = !ready || !state.permitId || state.permitStatus !== 3;
}
function entryAllowed() { return !stopActive() && resetSafe() && Boolean(bytes32(latestTelemetryEvent()?.id)); }
function updatePermitStepper() { const steps = $("permitStepper").children; const current = state.permitStatus === 0 ? 1 : state.permitStatus === 1 ? 2 : state.permitStatus === 2 ? 3 : 4; [...steps].forEach((step, index) => { step.classList.toggle("active", index + 1 === current); step.classList.toggle("done", index + 1 < current || state.permitStatus === 4); }); }
function setPermitStatus(status) { state.permitStatus = Number(status); const labels = ["NONE", "PENDING", "APPROVED", "ACTIVE", "COMPLETED", "REVOKED"]; const node = $("permitStatus"); node.textContent = labels[state.permitStatus] || "UNKNOWN"; node.className = `tag ${state.permitStatus === 5 ? "tag-danger" : state.permitStatus === 4 ? "tag-safe" : "tag-warning"}`; updatePermitButtons(); updatePermitStepper(); }
function permitContract() { const address = $("permitContractAddress").value.trim(); if (!state.signer) throw new Error("Kết nối MetaMask trước."); if (!ethers.isAddress(address)) throw new Error("Địa chỉ WorkPermitHandoff chưa hợp lệ."); state.permit = new ethers.Contract(address, PERMIT_ABI, state.signer); return state.permit; }
async function createPermit() {
  try { const contract = permitContract(); const worker = $("workerAddress").value.trim() || await state.signer.getAddress(); if (!ethers.isAddress(worker)) throw new Error("Ví người vận hành chưa hợp lệ."); const zone = $("zoneName").value.trim() || "ASSEMBLY-A"; const task = $("taskName").value.trim() || "HANDOFF-001"; const id = permitHash(`${worker}|${zone}|${task}|${Date.now()}`); const start = Math.floor(Date.now() / 1000); permitMessage("Đang chờ xác nhận tạo permit…"); const tx = await contract.createPermit(id, permitHash(worker), permitHash(zone), permitHash(task), worker, start, start + 3600); await tx.wait(); state.permitId = id; $("permitIdLabel").textContent = id; setPermitStatus(1); permitMessage(`Permit đã tạo · tx ${tx.hash.slice(0, 12)}…`); toast("Work permit đã được tạo."); }
  catch (error) { permitMessage(transactionError(error, "Không thể tạo permit.")); }
}
async function approvePermit() { try { const tx = await permitContract().approvePermit(state.permitId); await tx.wait(); setPermitStatus(2); permitMessage("Permit đã được supervisor approve."); toast("Permit đã approve."); } catch (error) { permitMessage(transactionError(error)); } }
async function recordEntry() { try { if (!entryAllowed()) throw new Error("Cần mẫu SAFE mới và không có yêu cầu dừng trước khi ghi zone entry."); const event = latestTelemetryEvent(); const digest = bytes32(event?.id); if (!digest) throw new Error("Cần telemetry event hợp lệ từ nguồn đang chọn."); const tx = await permitContract().recordZoneEntry(state.permitId, digest); await tx.wait(); setPermitStatus(3); permitMessage("Đã ghi xác nhận zone entry; không chứng minh vị trí người vận hành."); toast("Đã ghi nhận zone entry."); } catch (error) { permitMessage(transactionError(error)); } }
async function confirmHandoff() { try { const handoff = permitHash(`${state.permitId}|handoff|${Date.now()}`); const tx = await permitContract().confirmHandoff(handoff, state.permitId, permitHash("HRC-ROBOT-01")); await tx.wait(); permitMessage("Đã ghi xác nhận bàn giao của tài khoản tham gia."); toast("Xác nhận handoff đã ghi on-chain."); } catch (error) { permitMessage(transactionError(error)); } }
async function completePermit() { try { const tx = await permitContract().completePermit(state.permitId); await tx.wait(); setPermitStatus(4); permitMessage("Permit đã đóng; phiên làm việc hoàn tất."); toast("Permit đã hoàn tất."); } catch (error) { permitMessage(transactionError(error)); } }

$("simulateButton").addEventListener("click", simulate); $("connectButton").addEventListener("click", connectWallet); $("recordButton").addEventListener("click", recordOnChain); $("copyWalletButton").addEventListener("click", async () => { if (state.signer) copyText(await state.signer.getAddress(), "địa chỉ ví"); }); $("copyContractButton").addEventListener("click", () => copyInputValue("contractAddress", "địa chỉ HRCSafetyLog")); $("permitContractAddress").addEventListener("input", updatePermitButtons); $("copyPermitButton").addEventListener("click", () => copyInputValue("permitContractAddress", "địa chỉ WorkPermitHandoff")); $("createPermitButton").addEventListener("click", createPermit); $("approvePermitButton").addEventListener("click", approvePermit); $("entryButton").addEventListener("click", recordEntry); $("handoffButton").addEventListener("click", confirmHandoff); $("completePermitButton").addEventListener("click", completePermit);
$("triggerEstopButton").addEventListener("click", triggerEstop); $("clearEstopButton").addEventListener("click", clearEstop); $("estopPanelTrigger").addEventListener("click", triggerEstop); $("estopPanelClear").addEventListener("click", clearEstop); $("roleAddress").addEventListener("input", updateRoleButtons); $("assignRoleButton").addEventListener("click", () => assignRole(true)); $("revokeRoleButton").addEventListener("click", () => assignRole(false));
renderSensors(); updatePermitButtons(); setPermitStatus(0); setEstopUi(false); updateRoleButtons();
$("dataMode").addEventListener("change", setDataMode);
$("dataMode").addEventListener("input", setDataMode);
window.addEventListener("pageshow", setDataMode);
restoreDataMode();
$("contractAddress").addEventListener("change", refreshSafetyPermissions);
$("estopDevice").addEventListener("change", refreshSafetyPermissions);
$("clearChainButton").addEventListener("click", clearChainStop);
watchWallet();
if (window.ethereum) syncWallet().catch(() => {});
startGatewayLive();
