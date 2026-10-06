"""Headless Edge checks with deterministic API responses and screenshots."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "web3")))
threading.Thread(target=server.serve_forever, daemon=True).start()
errors = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        # Keep a running ESP32 gateway from replacing the deterministic API rows.
        page.add_init_script("window.WebSocket = class { constructor() { this.readyState = 0; } };")
        page.on("pageerror", lambda error: errors.append(str(error)))
        history = []
        row = {"id": 1, "event_id": "a" * 64, "device_id": "ESP32-HRC-01", "distance_cm": 110.0,
               "severity": "SAFE", "received_at": datetime.now(timezone.utc).isoformat(), "emergency_stop": False}
        def api(route):
            if "history" not in route.request.url:
                row["received_at"] = datetime.now(timezone.utc).isoformat()
            payload = {"telemetry": history} if "history" in route.request.url else {"telemetry": row}
            route.fulfill(json=payload, headers={"Access-Control-Allow-Origin": "*"})
        page.route("http://127.0.0.1:8000/**", api)
        page.goto(f"http://127.0.0.1:{server.server_port}", wait_until="networkidle")
        page.locator("#simulateButton").click()
        assert page.locator("#totalEventCount").inner_text() == "0 EMERGENCY · 0 on-chain"
        page.locator("#simulateButton").click()
        assert page.locator("#sensorState").inner_text() == "WARNING"
        assert page.locator("#totalEventCount").inner_text() == "0 EMERGENCY · 0 on-chain"
        page.locator("#simulateButton").click()
        assert page.locator("#overallState").inner_text() == "E-STOP"
        assert page.locator("#totalEventCount").inner_text() == "1 EMERGENCY · 0 on-chain"
        page.locator("#simulateButton").click()
        assert page.locator("#sensorState").inner_text() == "SAFE"
        assert page.locator("#overallState").inner_text() == "E-STOP"
        assert page.locator("#clearEstopButton").is_disabled()
        # Exercise DOM controls with deterministic contract permission reads.
        page.evaluate("""async () => {
          const account = '0x' + '1'.repeat(40);
          state.signer = { getAddress: async () => account };
          state.currentAddress = account;
          state.provider = { getCode: async () => '0x1234' };
          document.getElementById('contractAddress').value = '0x' + '2'.repeat(40);
          window.ethers = { ...window.ethers, Contract: class {
            async owner() { return '0x' + '3'.repeat(40); }
            async reporters() { return false; }
            async supervisors() { return true; }
            async emergencyStopByDevice() { return false; }
          } };
          await refreshSafetyPermissions();
        }""")
        assert page.locator("#clearEstopButton").is_enabled()
        page.screenshot(path=str(ROOT / "docs/dashboard_emergency_desktop.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(ROOT / "docs/dashboard_emergency_mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.locator("#clearEstopButton").click()
        page.wait_for_function("!state.estopActive")
        assert page.locator("#overallState").inner_text() == "SAFE"
        assert page.locator("#totalEventCount").inner_text() == "1 EMERGENCY · 0 on-chain"
        page.select_option("#dataMode", "gateway")
        page.wait_for_function("document.getElementById('distanceValue').textContent === '110.0'")
        assert page.locator("#simulateButton").is_disabled()
        page.reload(wait_until="networkidle")
        page.wait_for_function("document.getElementById('distanceValue').textContent === '110.0'")
        assert page.locator("#dataMode").input_value() == "gateway"
        assert page.locator("#gatewayStatus").inner_text() == "GATEWAY · LIVE"
        assert page.locator("#simulateButton").is_disabled()
        history.append({**row, "id": 0, "event_id": "c" * 64, "distance_cm": 20.0,
                        "severity": "EMERGENCY", "evidence_status": "confirmed", "tx_hash": "0x" + "d" * 64})
        page.wait_for_function("document.getElementById('eventCount').textContent === '1'")
        assert page.locator("#distanceValue").inner_text() == "110.0"
        row.update(id=2, event_id="b" * 64, distance_cm=None, severity="SENSOR_FAULT")
        page.wait_for_function("document.getElementById('overallState').textContent === 'SENSOR_FAULT'")
        assert page.locator("#distanceValue").inner_text() == "—"
        assert not errors, errors
        print("Real Edge: EMERGENCY log, automatic E-STOP, Supervisor clear, source reload, delayed confirmation, gateway fault, mobile overflow, JS errors: PASS")
        browser.close()
finally:
    server.shutdown()
    server.server_close()
