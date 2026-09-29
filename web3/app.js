/* SonarChain is intentionally dependency-light: the dashboard works in simulation mode,
   and uses ethers only when a browser wallet is available. */
const ABI = [
  "function recordEvent(bytes32 eventHash, bytes32 deviceIdHash, uint64 timestamp, uint8 severity, bool emergencyStop)",
  "function getEvent(bytes32 eventHash) view returns (tuple(bytes32 eventHash, bytes32 deviceIdHash, uint64 timestamp, uint8 severity, bool emergencyStop, address reporter))",
  "function deviceLocked(bytes32 deviceIdHash) view returns (bool)",
  "function emergencyStopByDevice(bytes32 deviceIdHash) view returns (bool)",
  "event SafetyEventRecorded(bytes32 indexed eventHash, bytes32 indexed deviceIdHash, uint8 severity, bool emergencyStop, address indexed reporter, uint64 timestamp)"
];
const SEVERITY = { SAFE: 0, WARNING: 1, DANGER: 2, EMERGENCY: 3 };
const state = { left: 92.8, right: 86.4, events: [], provider: null, signer: null, contract: null };
const $ = (id) => document.getElementById(id);

function classify(distance) { return distance <= 30 ? "EMERGENCY" : distance <= 60 ? "WARNING" : "SAFE"; }
function hashText(value) { return window.ethers ? ethers.keccak256(ethers.toUtf8Bytes(value)) : value; }
function formatAddress(address) { return address ? `${address.slice(0, 6)}…${address.slice(-4)}` : "Chưa kết nối"; }
function toast(message) { const node = $("toast"); node.textContent = message; node.classList.add("show"); clearTimeout(window.__toast); window.__toast = setTimeout(() => node.classList.remove("show"), 4200); }
function now() { return new Date().toLocaleTimeString("vi-VN", { hour12: false }); }

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
  const stateNode = $("overallState"); stateNode.textContent = severity; stateNode.className = severity === "EMERGENCY" ? "state-danger" : severity === "WARNING" ? "state-warning" : "state-safe";
  $("overallHint").textContent = severity === "EMERGENCY" ? "Emergency stop được kích hoạt" : severity === "WARNING" ? "Vật thể trong vùng cảnh báo" : "Không có cảnh báo";
}

function makeEvent() {
  const minimum = Math.min(state.left, state.right); const severity = classify(minimum);
  const timestamp = new Date().toISOString(); const device = "HRC-ESP32-01";
  const raw = `${device}|${timestamp}|${state.left.toFixed(2)}|${state.right.toFixed(2)}|${severity}`;
  const event = { id: hashText(raw), device, timestamp, severity, minimum, emergency: severity === "EMERGENCY", tx: null };
  state.events.unshift(event); $("eventCount").textContent = state.events.length; renderEvents(); return event;
}

function renderEvents() {
  const list = $("eventList"); if (!state.events.length) return;
  list.innerHTML = state.events.slice(0, 8).map((event) => {
    const type = event.severity === "EMERGENCY" ? "emergency" : event.severity === "WARNING" ? "warning" : "";
    const hash = typeof event.id === "string" ? event.id : "";
    return `<div class="event-row"><span class="event-marker ${type}"></span><div class="event-main"><strong>${event.severity} · ${event.minimum.toFixed(1)} cm${event.emergency ? " · LOCKED" : ""}</strong><small>${new Date(event.timestamp).toLocaleString("vi-VN")} · ${event.device}</small></div><div class="event-meta">${hash ? hash.slice(0, 10) + "…" : "pending"}${event.tx ? `<a href="${event.tx}" target="_blank" rel="noreferrer">view tx ↗</a>` : "<span>local proof</span>"}</div></div>`;
  }).join("");
}

function simulate() {
  const scenarios = [[86.4, 92.8], [48.2, 54.7], [24.6, 35.2], [76.5, 68.1]];
  const sample = scenarios[Math.floor(Math.random() * scenarios.length)]; state.left = sample[0]; state.right = sample[1]; renderSensors();
  const event = makeEvent(); toast(`${event.severity}: event hash đã tạo ở local. ${event.emergency ? "Emergency stop cần xử lý tại edge." : ""}`);
}

async function connectWallet() {
  if (!window.ethereum) { toast("Chưa tìm thấy MetaMask — bạn vẫn có thể dùng chế độ mô phỏng."); return; }
  try {
    state.provider = new ethers.BrowserProvider(window.ethereum); await state.provider.send("eth_requestAccounts", []); state.signer = await state.provider.getSigner();
    const address = await state.signer.getAddress(); const network = await state.provider.getNetwork();
    $("walletAddress").textContent = formatAddress(address); $("networkLabel").textContent = `Wallet · chain ${network.chainId}`; $("connectButton").textContent = "Đã kết nối"; $("recordButton").disabled = false;
    toast("Đã kết nối ví. Nhập địa chỉ contract để ghi event.");
  } catch (error) { toast(error.shortMessage || error.message || "Không thể kết nối ví."); }
}

async function recordOnChain() {
  if (!state.signer) return toast("Hãy kết nối MetaMask trước.");
  const address = $("contractAddress").value.trim(); if (!ethers.isAddress(address)) return toast("Địa chỉ contract chưa hợp lệ.");
  const event = state.events[0] || makeEvent();
  try {
    state.contract = new ethers.Contract(address, ABI, state.signer); $("chainMessage").textContent = "Đang chờ bạn xác nhận giao dịch trong ví…";
    const hash = event.id; const deviceHash = hashText(event.device); const tx = await state.contract.recordEvent(hash, deviceHash, Math.floor(new Date(event.timestamp).getTime() / 1000), SEVERITY[event.severity], event.emergency);
    $("chainMessage").textContent = "Đang chờ block xác nhận…"; await tx.wait(); event.tx = `https://sepolia.etherscan.io/tx/${tx.hash}`; renderEvents(); $("chainMessage").textContent = `Đã ghi on-chain · ${tx.hash.slice(0, 12)}…`; $("networkLabel").textContent = "Web3 connected"; toast("Safety event đã được ghi lên blockchain.");
  } catch (error) { $("chainMessage").textContent = "Giao dịch chưa được ghi."; toast(error.shortMessage || error.message || "Giao dịch thất bại."); }
}

$("simulateButton").addEventListener("click", simulate); $("connectButton").addEventListener("click", connectWallet); $("recordButton").addEventListener("click", recordOnChain);
renderSensors();
