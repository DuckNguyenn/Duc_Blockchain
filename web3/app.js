/* SonarChain browser workflow: simulation, safety evidence and HRC permits. */
const SAFETY_ABI = [
  "function recordEvent(bytes32 eventHash, bytes32 deviceIdHash, uint64 timestamp, uint8 severity, bool emergencyStop)"
];
const PERMIT_ABI = [
  "function createPermit(bytes32 permitId, bytes32 workerIdHash, bytes32 zoneIdHash, bytes32 taskIdHash, address worker, uint64 validFrom, uint64 validUntil)",
  "function approvePermit(bytes32 permitId)",
  "function recordZoneEntry(bytes32 permitId, bytes32 telemetryEventHash)",
  "function confirmHandoff(bytes32 handoffId, bytes32 permitId, bytes32 robotIdHash)",
  "function completePermit(bytes32 permitId)"
];
const SEVERITY = { SAFE: 0, WARNING: 1, DANGER: 2, EMERGENCY: 3 };
const state = { left: 92.8, right: 86.4, events: [], provider: null, signer: null, safety: null, permit: null, permitId: null, permitStatus: 0 };
const $ = (id) => document.getElementById(id);

function classify(distance) { return distance <= 30 ? "EMERGENCY" : distance <= 60 ? "WARNING" : "SAFE"; }
function hashText(value) { return window.ethers.keccak256(ethers.toUtf8Bytes(value)); }
function shortAddress(address) { return `${address.slice(0, 6)}…${address.slice(-4)}`; }
function now() { return new Date().toLocaleTimeString("vi-VN", { hour12: false }); }
function toast(message) { const node = $("toast"); node.textContent = message; node.classList.add("show"); clearTimeout(window.__toast); window.__toast = setTimeout(() => node.classList.remove("show"), 4200); }

function updateSensor(id, value) {
  const kind = classify(value).toLowerCase();
  $(id + "Distance").textContent = value.toFixed(1);
  $(id + "Bar").style.width = `${Math.min(100, Math.max(3, value / 1.2))}%`;
  $(id + "Bar").style.background = kind === "emergency" ? "var(--red)" : kind === "warning" ? "var(--amber)" : "var(--mint)";
  const tag = $(id + "State"); tag.textContent = kind.toUpperCase(); tag.className = `tag tag-${kind === "emergency" ? "danger" : kind}`;
  $(id + "Echo").textContent = `echo ${(value * 0.058).toFixed(1)} ms`;
}
function renderSensors() {
  updateSensor("left", state.left); updateSensor("right", state.right);
  const minimum = Math.min(state.left, state.right); const severity = classify(minimum);
  $("minDistance").textContent = minimum.toFixed(1); $("sampleTime").textContent = now();
  const node = $("overallState"); node.textContent = severity; node.className = severity === "EMERGENCY" ? "state-danger" : severity === "WARNING" ? "state-warning" : "state-safe";
  $("overallHint").textContent = severity === "EMERGENCY" ? "Emergency stop được kích hoạt" : severity === "WARNING" ? "Vật thể trong vùng cảnh báo" : "Không có cảnh báo";
}
function makeEvent() {
  const minimum = Math.min(state.left, state.right); const severity = classify(minimum); const timestamp = new Date().toISOString(); const device = "HRC-ESP32-01";
  const id = hashText(`${device}|${timestamp}|${state.left.toFixed(2)}|${state.right.toFixed(2)}|${severity}`);
  const event = { id, device, timestamp, severity, minimum, emergency: severity === "EMERGENCY", tx: null }; state.events.unshift(event); $("eventCount").textContent = state.events.length; renderEvents(); return event;
}
function renderEvents() {
  if (!state.events.length) return;
  $("eventList").innerHTML = state.events.slice(0, 8).map((event) => {
    const type = event.severity === "EMERGENCY" ? "emergency" : event.severity === "WARNING" ? "warning" : "";
    return `<div class="event-row"><span class="event-marker ${type}"></span><div class="event-main"><strong>${event.severity} · ${event.minimum.toFixed(1)} cm${event.emergency ? " · LOCKED" : ""}</strong><small>${new Date(event.timestamp).toLocaleString("vi-VN")} · ${event.device}</small></div><div class="event-meta">${event.id.slice(0, 10)}…${event.tx ? `<a href="${event.tx}" target="_blank" rel="noreferrer">view tx ↗</a>` : "<span>local proof</span>"}</div></div>`;
  }).join("");
}
function simulate() {
  const sample = [[86.4, 92.8], [48.2, 54.7], [24.6, 35.2], [76.5, 68.1]][Math.floor(Math.random() * 4)]; state.left = sample[0]; state.right = sample[1]; renderSensors();
  const event = makeEvent(); toast(`${event.severity}: event hash đã tạo ở local.`);
}

async function connectWallet() {
  if (!window.ethereum) return toast("Chưa tìm thấy MetaMask — hãy cài extension hoặc dùng mô phỏng.");
  try {
    state.provider = new ethers.BrowserProvider(window.ethereum); await state.provider.send("eth_requestAccounts", []); state.signer = await state.provider.getSigner(); const address = await state.signer.getAddress(); const network = await state.provider.getNetwork();
    $("walletAddress").textContent = shortAddress(address); $("networkLabel").textContent = `Wallet · chain ${network.chainId}`; $("connectButton").textContent = "Đã kết nối"; $("recordButton").disabled = false; updatePermitButtons(); toast("Đã kết nối ví.");
  } catch (error) { toast(error.shortMessage || error.message || "Không thể kết nối ví."); }
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
function setPermitStatus(status) { state.permitStatus = Number(status); const labels = ["NONE", "PENDING", "APPROVED", "ACTIVE", "COMPLETED", "REVOKED"]; const node = $("permitStatus"); node.textContent = labels[state.permitStatus] || "UNKNOWN"; node.className = `tag ${state.permitStatus >= 4 ? "tag-safe" : state.permitStatus === 5 ? "tag-danger" : "tag-warning"}`; updatePermitButtons(); }
function permitContract() { const address = $("permitContractAddress").value.trim(); if (!state.signer) throw new Error("Kết nối MetaMask trước."); if (!ethers.isAddress(address)) throw new Error("Địa chỉ WorkPermitHandoff chưa hợp lệ."); state.permit = new ethers.Contract(address, PERMIT_ABI, state.signer); return state.permit; }
async function createPermit() {
  try { const contract = permitContract(); const worker = $("workerAddress").value.trim() || await state.signer.getAddress(); if (!ethers.isAddress(worker)) throw new Error("Ví người vận hành chưa hợp lệ."); const zone = $("zoneName").value.trim() || "ASSEMBLY-A"; const task = $("taskName").value.trim() || "HANDOFF-001"; const id = permitHash(`${worker}|${zone}|${task}|${Date.now()}`); const start = Math.floor(Date.now() / 1000); permitMessage("Đang chờ xác nhận tạo permit…"); const tx = await contract.createPermit(id, permitHash(worker), permitHash(zone), permitHash(task), worker, start, start + 3600); await tx.wait(); state.permitId = id; $("permitIdLabel").textContent = id; setPermitStatus(1); permitMessage(`Permit đã tạo · tx ${tx.hash.slice(0, 12)}…`); toast("Work permit đã được tạo."); }
  catch (error) { permitMessage(error.shortMessage || error.message || "Không thể tạo permit."); }
}
async function approvePermit() { try { const tx = await permitContract().approvePermit(state.permitId); await tx.wait(); setPermitStatus(2); permitMessage("Permit đã được supervisor approve."); toast("Permit đã approve."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function recordEntry() { try { const event = state.events[0] || makeEvent(); const tx = await permitContract().recordZoneEntry(state.permitId, event.id); await tx.wait(); setPermitStatus(3); permitMessage("Zone entry đã được ghi từ telemetry event."); toast("Đã ghi nhận người vận hành vào zone."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function confirmHandoff() { try { const handoff = permitHash(`${state.permitId}|handoff|${Date.now()}`); const tx = await permitContract().confirmHandoff(handoff, state.permitId, permitHash("HRC-ROBOT-01")); await tx.wait(); permitMessage("Handoff đã xác nhận: robot và worker đã bàn giao task."); toast("Human–Robot handoff đã ghi on-chain."); } catch (error) { permitMessage(error.shortMessage || error.message); } }
async function completePermit() { try { const tx = await permitContract().completePermit(state.permitId); await tx.wait(); setPermitStatus(4); permitMessage("Permit đã đóng; phiên làm việc hoàn tất."); toast("Permit đã hoàn tất."); } catch (error) { permitMessage(error.shortMessage || error.message); } }

$("simulateButton").addEventListener("click", simulate); $("connectButton").addEventListener("click", connectWallet); $("recordButton").addEventListener("click", recordOnChain); $("permitContractAddress").addEventListener("input", updatePermitButtons); $("createPermitButton").addEventListener("click", createPermit); $("approvePermitButton").addEventListener("click", approvePermit); $("entryButton").addEventListener("click", recordEntry); $("handoffButton").addEventListener("click", confirmHandoff); $("completePermitButton").addEventListener("click", completePermit);
renderSensors(); updatePermitButtons();
