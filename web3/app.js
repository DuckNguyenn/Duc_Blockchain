/* SonarChain browser workflow: simulation, safety evidence and HRC permits. */
const SAFETY_ABI = [
  "function recordEvent(bytes32 eventHash, bytes32 deviceIdHash, uint64 timestamp, uint8 severity, bool emergencyStop)",
  "function setReporter(address reporter, bool allowed)",
  "function clearEmergencyStop(bytes32 deviceIdHash)"
];
const PERMIT_ABI = [
  "function createPermit(bytes32 permitId, bytes32 workerIdHash, bytes32 zoneIdHash, bytes32 taskIdHash, address worker, uint64 validFrom, uint64 validUntil)",
  "function approvePermit(bytes32 permitId)",
  "function recordZoneEntry(bytes32 permitId, bytes32 telemetryEventHash)",
  "function confirmHandoff(bytes32 handoffId, bytes32 permitId, bytes32 robotIdHash)",
  "function completePermit(bytes32 permitId)",
  "function setSupervisor(address account, bool allowed)",
  "function setGateway(address account, bool allowed)"
];
const SEVERITY = { SAFE: 0, WARNING: 1, DANGER: 2, EMERGENCY: 3 };
const state = { distance: 86.4, events: [], provider: null, signer: null, currentAddress: null, safety: null, permit: null, permitId: null, permitStatus: 0, estopActive: false, estopOnChain: false, estopPending: false };
const $ = (id) => document.getElementById(id);

function classify(distance) { return distance <= 30 ? "EMERGENCY" : distance <= 60 ? "WARNING" : "SAFE"; }
function hashText(value) { return window.ethers.keccak256(ethers.toUtf8Bytes(value)); }
function shortAddress(address) { return `${address.slice(0, 6)}…${address.slice(-4)}`; }
function now() { return new Date().toLocaleTimeString("vi-VN", { hour12: false }); }
function toast(message) { const node = $("toast"); node.textContent = message; node.classList.add("show"); clearTimeout(window.__toast); window.__toast = setTimeout(() => node.classList.remove("show"), 4200); }
async function copyText(value, label) {
  const text = String(value || "").trim();
  if (!text || text.startsWith("Chưa") || text === "0x…") return toast(`Chưa có ${label} để sao chép.`);
  try { await navigator.clipboard.writeText(text); toast(`Đã sao chép ${label}.`); }
  catch (error) { window.prompt(`Sao chép ${label}:`, text); }
}
function copyInputValue(inputId, label) { copyText($(inputId)?.value, label); }

function updateSensor(value) {
  const severity = classify(value); const kind = severity.toLowerCase();
  const card = $("sensorCard"); card.className = `sensor-card ${kind}`;
  $("distanceValue").textContent = value.toFixed(1);
  $("distanceBar").style.width = `${Math.min(100, Math.max(3, value / 1.2))}%`;
  $("distanceBar").style.background = kind === "emergency" ? "var(--red)" : kind === "warning" ? "var(--amber)" : "var(--mint)";
  const tag = $("sensorState"); tag.textContent = severity; tag.className = `tag tag-${kind === "emergency" ? "danger" : kind}`;
  $("distanceEcho").textContent = `echo ${(value * 0.058).toFixed(1)} ms`;
}
function renderSensors() {
  updateSensor(state.distance);
  const severity = classify(state.distance);
  $("minDistance").textContent = state.distance.toFixed(1); $("sampleTime").textContent = now(); $("zoneDistance").textContent = `${state.distance.toFixed(1)} cm`;
  const node = $("overallState"); node.textContent = severity; node.className = severity === "EMERGENCY" ? "state-danger" : severity === "WARNING" ? "state-warning" : "state-safe";
  $("overallHint").textContent = severity === "EMERGENCY" ? "Emergency stop được kích hoạt" : severity === "WARNING" ? "Vật thể trong vùng cảnh báo" : "Không có cảnh báo";
  const tone = severity === "EMERGENCY" ? "danger" : severity === "WARNING" ? "warning" : "safe"; $("safetyBanner").className = `safety-banner ${tone}`;
  $("bannerTitle").textContent = severity === "EMERGENCY" ? "Nguy hiểm — E-stop" : severity === "WARNING" ? "Cảnh báo khoảng cách" : "Hệ thống an toàn";
  $("bannerText").textContent = severity === "EMERGENCY" ? "Vật thể ≤ 30 cm: E-stop cục bộ đã được kích hoạt" : severity === "WARNING" ? "Vật thể trong khoảng 31–60 cm, cần theo dõi" : "Không có vật thể trong vùng cảnh báo";
  $("workerZoneState").textContent = severity;
  if (severity === "EMERGENCY" && !state.estopActive && !state.estopPending) void triggerEstop();
  if (state.estopActive) showEstopState();
}
function showEstopState() {
  $("safetyBanner").className = "safety-banner danger";
  $("bannerTitle").textContent = "E-STOP ACTIVE";
  $("bannerText").textContent = "Khóa dừng khẩn cấp — kiểm tra vùng làm việc trước khi gỡ";
  $("overallState").textContent = "E-STOP"; $("overallState").className = "state-danger";
  $("overallHint").textContent = "Dừng khẩn cấp đang bật";
  $("workerZoneState").textContent = "LOCKED";
}
function setEstopUi(active, message = "") {
  state.estopActive = active;
  if (active) showEstopState(); else renderSensors();
  const badge = $("estopBadge"); if (badge) { badge.textContent = active ? "ACTIVE" : "READY"; badge.className = `estop-badge ${active ? "" : "ready"}`; }
  const stateLabel = $("estopState"); if (stateLabel) stateLabel.textContent = active ? "E-STOP ACTIVE" : "E-STOP ARMED";
  const trigger = $("triggerEstopButton"); const panelTrigger = $("estopPanelTrigger"); const clear = $("clearEstopButton"); const panelClear = $("estopPanelClear");
  if (trigger) trigger.disabled = active || state.estopPending; if (panelTrigger) panelTrigger.disabled = active || state.estopPending;
  const canClear = active && !state.estopPending && classify(state.distance) !== "EMERGENCY";
  if (clear) clear.disabled = !canClear; if (panelClear) panelClear.disabled = !canClear;
  if (message) { $("estopMessage").textContent = message; }
}
function deviceHash() { return hashText($("estopDevice").value.trim() || "HRC-ESP32-01"); }
async function triggerEstop() {
  if (state.estopActive) return;
  const event = makeEvent("EMERGENCY");
  setEstopUi(true, "E-STOP mô phỏng đã bật. Blockchain chỉ lưu bằng chứng, không điều khiển phần cứng.");
  toast("E-STOP mô phỏng đã tự kích hoạt.");
  await recordEstopEvidence(event);
}
async function recordEstopEvidence(event) {
  const address = $("contractAddress").value.trim();
  if (!state.signer || !ethers.isAddress(address)) return;
  state.estopPending = true; setEstopUi(true, "Đang chờ MetaMask xác nhận bằng chứng E-STOP; trạng thái local vẫn khóa.");
  try {
    const contract = new ethers.Contract(address, SAFETY_ABI, state.signer);
    const tx = await contract.recordEvent(event.id, deviceHash(), Math.floor(new Date(event.timestamp).getTime() / 1000), SEVERITY.EMERGENCY, true);
    await tx.wait(); event.tx = tx.hash; state.estopOnChain = true; renderEvents();
    $("estopMessage").textContent = `E-STOP đã ghi on-chain · ${tx.hash.slice(0, 12)}…`;
  } catch (error) { $("estopMessage").textContent = `E-STOP local vẫn bật; ghi chain thất bại: ${error.shortMessage || error.message}`; }
  finally { state.estopPending = false; setEstopUi(true); }
}
async function clearEstop() {
  if (classify(state.distance) === "EMERGENCY" || state.estopPending) return toast("Chưa thể gỡ: cảm biến vẫn ở vùng nguy hiểm hoặc giao dịch đang chờ.");
  if (state.estopOnChain) {
    const address = $("contractAddress").value.trim(); if (!state.signer || !ethers.isAddress(address)) return toast("Kết nối owner và nhập HRCSafetyLog để gỡ khóa on-chain.");
    try { state.estopPending = true; setEstopUi(true, "Đang chờ owner gỡ E-STOP on-chain…"); const tx = await new ethers.Contract(address, SAFETY_ABI, state.signer).clearEmergencyStop(deviceHash()); await tx.wait(); state.estopOnChain = false; setEstopUi(false, `Đã gỡ E-STOP · tx ${tx.hash.slice(0, 12)}…`); toast("E-STOP đã được gỡ."); }
    catch (error) { $("estopMessage").textContent = error.shortMessage || error.message || "Chỉ owner được gỡ E-STOP."; }
    finally { state.estopPending = false; setEstopUi(state.estopActive); }
  } else { setEstopUi(false, "Đã gỡ E-STOP mô phỏng sau khi khoảng cách an toàn."); toast("Đã gỡ E-STOP mô phỏng."); }
}
function makeEvent(forceSeverity = null) {
  const severity = forceSeverity || classify(state.distance); const timestamp = new Date().toISOString(); const device = "HRC-ESP32-01";
  const id = hashText(`${device}|${timestamp}|${state.distance.toFixed(2)}|${severity}`);
  const event = { id, device, timestamp, severity, minimum: state.distance, distance: state.distance, emergency: severity === "EMERGENCY", tx: null }; state.events.unshift(event); $("eventCount").textContent = state.events.length; renderEvents(); return event;
}
function renderEvents() {
  if (!state.events.length) return;
  $("eventList").innerHTML = state.events.slice(0, 8).map((event) => {
    const type = event.severity === "EMERGENCY" ? "emergency" : event.severity === "WARNING" ? "warning" : "";
    return `<div class="event-row"><span class="event-marker ${type}"></span><div class="event-main"><strong>${event.severity} · ${event.minimum.toFixed(1)} cm${event.emergency ? " · LOCKED" : ""}</strong><small>${new Date(event.timestamp).toLocaleString("vi-VN")} · ${event.device}</small></div><div class="event-meta">${event.id.slice(0, 10)}…${event.tx ? `<a href="${event.tx}" target="_blank" rel="noreferrer">view tx ↗</a>` : "<span>local proof</span>"}</div></div>`;
  }).join("");
}
function simulate() {
  const sample = [86.4, 48.2, 24.6, 76.5][Math.floor(Math.random() * 4)]; state.distance = sample; renderSensors();
  if (classify(sample) === "EMERGENCY") return;
  const event = makeEvent(); setEstopUi(state.estopActive); toast(`${event.severity}: event hash đã tạo ở local.`);
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
    $("walletAddress").textContent = "Chưa kết nối";
    $("networkLabel").textContent = "Simulation mode";
    $("connectButton").textContent = "Kết nối ví";
    $("recordButton").disabled = true;
    if ($("copyWalletButton")) $("copyWalletButton").disabled = true;
    updatePermitButtons();
    updateRoleButtons();
    return false;
  }
  state.signer = await state.provider.getSigner();
  const address = await state.signer.getAddress();
  state.currentAddress = address;
  const network = await state.provider.getNetwork();
  $("walletAddress").textContent = shortAddress(address);
  $("networkLabel").textContent = `Wallet · chain ${network.chainId}`;
  $("connectButton").textContent = "Đã kết nối";
  $("recordButton").disabled = false;
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
    else { const contractAddress = $("permitContractAddress").value.trim(); if (!ethers.isAddress(contractAddress)) throw new Error("Nhập WorkPermitHandoff trước."); state.permit = new ethers.Contract(contractAddress, PERMIT_ABI, state.signer); tx = role === "supervisor" ? await state.permit.setSupervisor(address, allowed) : await state.permit.setGateway(address, allowed); }
    roleMessage(`Đang chờ xác nhận ${allowed ? "cấp" : "thu hồi"} role…`); await tx.wait(); roleMessage(`${allowed ? "Đã cấp" : "Đã thu hồi"} ${role} · tx ${tx.hash.slice(0, 12)}…`); toast(`${allowed ? "Đã cấp" : "Đã thu hồi"} role ${role}.`);
  } catch (error) { roleMessage(error.shortMessage || error.message || "Không thể cập nhật role. Hãy dùng owner của contract."); }
}
async function recordOnChain() {
  if (!state.signer) return toast("Hãy kết nối MetaMask trước."); const address = $("contractAddress").value.trim(); if (!ethers.isAddress(address)) return toast("Địa chỉ HRCSafetyLog chưa hợp lệ."); const event = state.events[0] || makeEvent();
  try { state.safety = new ethers.Contract(address, SAFETY_ABI, state.signer); $("chainMessage").textContent = "Đang chờ xác nhận giao dịch…"; const tx = await state.safety.recordEvent(event.id, hashText(event.device), Math.floor(new Date(event.timestamp).getTime() / 1000), SEVERITY[event.severity], event.emergency); await tx.wait(); event.tx = tx.hash; renderEvents(); $("chainMessage").textContent = `Đã ghi on-chain · ${tx.hash.slice(0, 12)}…`; toast("Safety event đã được ghi lên blockchain."); }
  catch (error) { $("chainMessage").textContent = "Giao dịch chưa được ghi."; toast(error.shortMessage || error.message || "Giao dịch thất bại."); }
}

function permitHash(value) { return hashText(`sonarchain-permit|${value}`); }
function permitMessage(message) { $("permitMessage").textContent = message; }
function updatePermitButtons() {
  const ready = Boolean(state.signer && $("permitContractAddress").value.trim()); $("createPermitButton").disabled = !ready; $("approvePermitButton").disabled = !ready || !state.permitId || state.permitStatus !== 1; $("entryButton").disabled = !ready || !state.permitId || state.permitStatus !== 2; $("handoffButton").disabled = !ready || !state.permitId || state.permitStatus !== 3; $("completePermitButton").disabled = !ready || !state.permitId || state.permitStatus !== 3;
}
function updatePermitStepper() { const steps = $("permitStepper").children; const current = state.permitStatus === 0 ? 1 : state.permitStatus === 1 ? 2 : state.permitStatus === 2 ? 3 : 4; [...steps].forEach((step, index) => { step.classList.toggle("active", index + 1 === current); step.classList.toggle("done", index + 1 < current || state.permitStatus === 4); }); }
function setPermitStatus(status) { state.permitStatus = Number(status); const labels = ["NONE", "PENDING", "APPROVED", "ACTIVE", "COMPLETED", "REVOKED"]; const node = $("permitStatus"); node.textContent = labels[state.permitStatus] || "UNKNOWN"; node.className = `tag ${state.permitStatus >= 4 ? "tag-safe" : state.permitStatus === 5 ? "tag-danger" : "tag-warning"}`; updatePermitButtons(); updatePermitStepper(); }
function permitContract() { const address = $("permitContractAddress").value.trim(); if (!state.signer) throw new Error("Kết nối MetaMask trước."); if (!ethers.isAddress(address)) throw new Error("Địa chỉ WorkPermitHandoff chưa hợp lệ."); state.permit = new ethers.Contract(address, PERMIT_ABI, state.signer); return state.permit; }
async function createPermit() {
  try { const contract = permitContract(); const worker = $("workerAddress").value.trim() || await state.signer.getAddress(); if (!ethers.isAddress(worker)) throw new Error("Ví người vận hành chưa hợp lệ."); const zone = $("zoneName").value.trim() || "ASSEMBLY-A"; const task = $("taskName").value.trim() || "HANDOFF-001"; const id = permitHash(`${worker}|${zone}|${task}|${Date.now()}`); const start = Math.floor(Date.now() / 1000); permitMessage("Đang chờ xác nhận tạo permit…"); const tx = await contract.createPermit(id, permitHash(worker), permitHash(zone), permitHash(task), worker, start, start + 3600); await tx.wait(); state.permitId = id; $("permitIdLabel").textContent = id; setPermitStatus(1); permitMessage(`Permit đã tạo · tx ${tx.hash.slice(0, 12)}…`); toast("Work permit đã được tạo."); }
  catch (error) { permitMessage(error.shortMessage || error.message || "Không thể tạo permit."); }
}
async function approvePermit() { try { const tx = await permitContract().approvePermit(state.permitId); await tx.wait(); setPermitStatus(2); permitMessage("Permit đã được supervisor approve."); toast("Permit đã approve."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function recordEntry() { try { const event = state.events[0] || makeEvent(); const tx = await permitContract().recordZoneEntry(state.permitId, event.id); await tx.wait(); setPermitStatus(3); permitMessage("Zone entry đã được ghi từ telemetry event."); toast("Đã ghi nhận người vận hành vào zone."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function confirmHandoff() { try { const handoff = permitHash(`${state.permitId}|handoff|${Date.now()}`); const tx = await permitContract().confirmHandoff(handoff, state.permitId, permitHash("HRC-ROBOT-01")); await tx.wait(); permitMessage("Handoff đã xác nhận: robot và worker đã bàn giao task."); toast("Human–Robot handoff đã ghi on-chain."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function completePermit() { try { const tx = await permitContract().completePermit(state.permitId); await tx.wait(); setPermitStatus(4); permitMessage("Permit đã đóng; phiên làm việc hoàn tất."); toast("Permit đã hoàn tất."); } catch (error) { permitMessage(error.shortMessage || error.message); } }

$("simulateButton").addEventListener("click", simulate); $("connectButton").addEventListener("click", connectWallet); $("recordButton").addEventListener("click", recordOnChain); $("copyWalletButton").addEventListener("click", async () => { if (state.signer) copyText(await state.signer.getAddress(), "địa chỉ ví"); }); $("copyContractButton").addEventListener("click", () => copyInputValue("contractAddress", "địa chỉ HRCSafetyLog")); $("permitContractAddress").addEventListener("input", updatePermitButtons); $("copyPermitButton").addEventListener("click", () => copyInputValue("permitContractAddress", "địa chỉ WorkPermitHandoff")); $("createPermitButton").addEventListener("click", createPermit); $("approvePermitButton").addEventListener("click", approvePermit); $("entryButton").addEventListener("click", recordEntry); $("handoffButton").addEventListener("click", confirmHandoff); $("completePermitButton").addEventListener("click", completePermit);
$("triggerEstopButton").addEventListener("click", triggerEstop); $("clearEstopButton").addEventListener("click", clearEstop); $("estopPanelTrigger").addEventListener("click", triggerEstop); $("estopPanelClear").addEventListener("click", clearEstop); $("roleAddress").addEventListener("input", updateRoleButtons); $("assignRoleButton").addEventListener("click", () => assignRole(true)); $("revokeRoleButton").addEventListener("click", () => assignRole(false));
renderSensors(); updatePermitButtons(); setPermitStatus(0); setEstopUi(false); updateRoleButtons();
watchWallet();
if (window.ethereum) syncWallet().catch(() => {});
