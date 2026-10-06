const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');

function harness({ initialMode = 'simulation', savedMode = null } = {}) {
  const nodes = new Map(); let intervals = 0;
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, { value: id === 'dataMode' ? initialMode : '', textContent: '', innerHTML: '', style: {}, children: [],
      classList: { add() {}, remove() {}, toggle() {} }, addEventListener() {} });
    return nodes.get(id);
  };
  const ethers = { isAddress: x => /^0x[0-9a-f]{40}$/i.test(x || ''), toUtf8Bytes: x => x,
    keccak256: x => '0x' + crypto.createHash('sha256').update(x).digest('hex') };
  const context = vm.createContext({ document: { getElementById: node }, navigator: {},
    window: { ethers, events: {}, addEventListener(name, callback) { this.events[name] = callback; },
      localStorage: { getItem: () => savedMode, setItem: (_key, value) => { savedMode = value; } },
      setInterval: () => ++intervals, setTimeout: () => 1 },
    setTimeout: () => 1, clearTimeout() {}, Date, Number, Boolean, String, Math, Promise, AbortSignal,
    fetch: async () => { throw Error('offline'); }, WebSocket: class { constructor() { this.readyState = 0; } },
    ethers });
  vm.runInContext(fs.readFileSync('web3/app.js', 'utf8'), context);
  return { run: code => vm.runInContext(code, context), node, intervals: () => intervals };
}

test('fault telemetry clears old distance and does not submit a transaction', () => {
  const h = harness(); h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  h.run(`addGatewayTelemetry({id:1,event_id:'fault',device_id:'esp32',distance_cm:null,severity:'SENSOR_FAULT',received_at:new Date().toISOString(),emergency_stop:false})`);
  assert.equal(h.node('distanceValue').textContent, '—');
  assert.equal(h.node('overallState').textContent, 'SENSOR_FAULT');
  assert.equal(h.run('state.events.length'), 0);
});
test('simulation is isolated from gateway, rendering has no transaction effects', () => {
  const h = harness(); h.run(`addGatewayTelemetry({id:1,event_id:'gateway-emergency',device_id:'esp32',distance_cm:20,severity:'EMERGENCY',received_at:new Date().toISOString(),emergency_stop:true})`);
  assert.equal(h.run('state.distance'), 86.4);
  assert.equal(h.run('activeEvents().length'), 0);
  h.run('state.distance=20; renderSensors(); renderSensors()');
  assert.equal(h.run('state.events.length'), 1);
});
test('reconnect keeps one poll interval and history does not replace live reading', () => {
  const h = harness(); h.run('startGatewayLive(); startGatewayLive()');
  assert.equal(h.intervals(), 1);
  h.run(`addGatewayTelemetry({id:2,event_id:'new',device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:new Date().toISOString()}); rememberGatewayEvent({id:1,event_id:'old',device_id:'esp32',distance_cm:20,severity:'EMERGENCY'})`);
  assert.equal(h.run('state.latest.id'), 2);
});
test('event rendering escapes device names and gateway SHA256 becomes bytes32', () => {
  const h = harness(); h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  h.run(`rememberGatewayEvent({id:1,event_id:'a'.repeat(64),device_id:'<img onerror=alert(1)>',distance_cm:20,severity:'EMERGENCY'}); renderEvents()`);
  assert.ok(!h.node('eventList').innerHTML.includes('<img'));
  assert.equal(h.run("bytes32('a'.repeat(64))"), '0x' + 'a'.repeat(64));
});
test('stale samples do not display SAFE', () => {
  const h = harness(); h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  h.run(`addGatewayTelemetry({id:1,event_id:'old-safe',device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:'2020-01-01T00:00:00Z'})`);
  assert.equal(h.node('overallState').textContent, 'NO DATA');
});
test('zone entry requires a fresh SAFE sample and no stop request', () => {
  const h = harness(); h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  h.run(`addGatewayTelemetry({id:1,event_id:'a'.repeat(64),device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:new Date().toISOString(),emergency_stop:false})`);
  assert.equal(h.run('entryAllowed()'), true);
  h.run('state.estopActive=true'); assert.equal(h.run('entryAllowed()'), false);
  h.run('state.estopActive=false; state.latest.severity="SENSOR_FAULT"'); assert.equal(h.run('entryAllowed()'), false);
});

test('simulation logs only EMERGENCY and keeps E-STOP after the next SAFE sample', () => {
  const h = harness();
  h.run('simulate(); simulate()');
  assert.equal(h.run('state.events.length'), 0);
  assert.equal(h.node('sensorState').textContent, 'WARNING');
  h.run('simulate()');
  assert.equal(h.run('state.estopActive'), true);
  assert.equal(h.run('state.events.length'), 1);
  assert.equal(h.node('overallState').textContent, 'E-STOP');
  h.run('simulate()');
  assert.equal(h.node('sensorState').textContent, 'SAFE');
  assert.equal(h.node('overallState').textContent, 'E-STOP');
  assert.equal(h.node('totalEventCount').textContent, '1 EMERGENCY · 0 on-chain');
  assert.equal(h.run('entryAllowed()'), false);
});

test('Owner, Reporter, Worker and disconnected wallets cannot clear the simulation latch', async () => {
  for (const role of ['owner', 'reporter', 'worker', 'disconnected']) {
    const h = harness();
    h.run(`state.signer=${role === 'disconnected' ? 'null' : '{}'}; state.safetyOwner=${role === 'owner'}; state.reporter=${role === 'reporter'}; state.distance=100; setEstopUi(true)`);
    assert.equal(h.node('clearEstopButton').disabled, true);
    await h.run('clearEstop()');
    assert.equal(h.run('state.estopActive'), true);
  }
});

function supervisorHarness({ stopped = false, allowed = true, failClear = false, duringWait } = {}) {
  const h = harness(); let clears = 0;
  const wallet = '0x' + '1'.repeat(40);
  h.node('contractAddress').value = '0x' + '2'.repeat(40);
  h.run(`state.signer={getAddress: async () => '${wallet}'}; state.currentAddress='${wallet}'; state.provider={getCode:async ()=>'0x1234'}; state.supervisor=true; state.distance=100`);
  h.run('ethers').Contract = class {
    async owner() { return '0x' + '3'.repeat(40); }
    async reporters() { return false; }
    async supervisors() { return allowed; }
    async emergencyStopByDevice() { return stopped; }
    async clearEmergencyStop() {
      clears++;
      if (failClear) throw Error('rejected');
      return { hash: '0x' + '4'.repeat(64), wait: async () => { stopped = false; if (duringWait) duringWait(h); } };
    }
  };
  h.run(`state.estopOnChain=${stopped}; setEstopUi(true)`);
  return { h, clears: () => clears };
}

test('Supervisor clears only at SAFE, preserving the EMERGENCY log', async () => {
  const { h } = supervisorHarness();
  h.run('state.distance=20; makeEvent(); setEstopUi(true)');
  assert.equal(h.node('clearEstopButton').disabled, true);
  await h.run('clearEstop()');
  assert.equal(h.run('state.estopActive'), true);
  h.run('state.distance=100; makeEvent(); setEstopUi(true)');
  assert.equal(h.node('clearEstopButton').disabled, false);
  await h.run('clearEstop()');
  assert.equal(h.run('state.estopActive'), false);
  assert.equal(h.run('state.events.length'), 1);
  assert.equal(h.run('entryAllowed()'), true);
});

test('revoked Supervisor cannot clear a local latch using cached permissions', async () => {
  const { h } = supervisorHarness({ allowed: false });
  await h.run('clearEstop()');
  assert.equal(h.run('state.estopActive'), true);
  assert.equal(h.run('state.supervisor'), false);
});

test('Supervisor clears chain and local state together; failed transactions retain the latch', async () => {
  for (const failClear of [false, true]) {
    const { h, clears } = supervisorHarness({ stopped: true, failClear });
    await h.run('clearChainStop()');
    assert.equal(clears(), 1);
    assert.equal(h.run('stopActive()'), failClear);
  }
});

test('new EMERGENCY during a clear transaction retains the local latch', async () => {
  const { h } = supervisorHarness({ stopped: true, duringWait(h) {
    h.run('state.distance=20; makeEvent(); state.distance=100; makeEvent()');
  } });
  await h.run('clearEstop()');
  assert.equal(h.run('state.estopActive'), true);
});

test('gateway retains its latch through SAFE, stale data and source switching', async () => {
  const { h } = supervisorHarness();
  h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  await h.run('refreshSafetyPermissions()');
  h.run(`addGatewayTelemetry({id:1,event_id:'a'.repeat(64),device_id:'esp32',distance_cm:20,severity:'EMERGENCY',received_at:new Date().toISOString(),emergency_stop:true});
    addGatewayTelemetry({id:2,event_id:'b'.repeat(64),device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:new Date().toISOString(),emergency_stop:false})`);
  assert.equal(h.run('state.events.length'), 1);
  assert.equal(h.run('state.estopActive'), true);
  h.node('dataMode').value = 'simulation'; h.run('setDataMode()');
  h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  await h.run('refreshSafetyPermissions()');
  assert.equal(h.run('state.estopActive'), true);
  h.run(`state.latest.received_at='2020-01-01T00:00:00Z'; setEstopUi(state.estopActive)`);
  assert.equal(h.node('clearEstopButton').disabled, true);
  assert.equal(h.node('overallState').textContent, 'E-STOP');
  h.run('state.latest.received_at=new Date().toISOString(); setEstopUi(state.estopActive)');
  await h.run('clearEstop()');
  h.run('applyLatestGateway()');
  assert.equal(h.run('state.estopActive'), false);
});

test('history requests filter EMERGENCY before limiting rows', async () => {
  const h = harness(); let url;
  await new Promise(setImmediate);
  h.run('globalThis').fetch = async value => { url = value; return { ok: true, json: async () => ({ telemetry: [] }) }; };
  await h.run('loadGatewayHistory()');
  assert.match(url, /severity=EMERGENCY/);
});

test('edge-reported EMERGENCY triggers a stop even outside the hard distance zone', () => {
  const h = harness(); h.node('dataMode').value = 'gateway'; h.run('setDataMode()');
  h.run(`addGatewayTelemetry({id:1,event_id:'edge-emergency',device_id:'esp32',distance_cm:100,severity:'EMERGENCY',received_at:new Date().toISOString(),emergency_stop:true})`);
  assert.equal(h.node('sensorState').textContent, 'EMERGENCY');
  assert.equal(h.node('overallState').textContent, 'E-STOP');
  assert.equal(h.node('clearEstopButton').disabled, true);
});

test('Supervisor grant and revoke update both contracts with two confirmations', async () => {
  for (const allowed of [true, false]) {
    const { h } = supervisorHarness(); const updates = [];
    const safety = h.node('contractAddress').value, permit = '0x' + '5'.repeat(40), target = '0x' + '6'.repeat(40);
    h.node('permitContractAddress').value = permit;
    h.node('roleAddress').value = target; h.node('roleSelect').value = 'supervisor';
    const Base = h.run('ethers').Contract;
    h.run('ethers').Contract = class extends Base {
      constructor(address) { super(); this.address = address; }
      async owner() { return h.run('state.currentAddress'); }
      async setSupervisor(address, grant) {
        updates.push([this.address, address, grant]);
        return { hash: '0x' + '7'.repeat(64), wait: async () => { updates.push('confirmed'); } };
      }
    };
    await h.run(`assignRole(${allowed})`);
    assert.deepEqual(updates, [[safety, target, allowed], 'confirmed', [permit, target, allowed], 'confirmed']);
  }
});

test('an active stop explains why Supervisor cannot clear an EMERGENCY distance', () => {
  const { h } = supervisorHarness();
  h.node('dataMode').value = 'gateway'; h.run('setDataMode(); state.supervisor=true');
  h.run(`addGatewayTelemetry({id:1,event_id:'emergency-4cm',device_id:'esp32',distance_cm:4,severity:'EMERGENCY',received_at:new Date().toISOString(),emergency_stop:true})`);
  assert.equal(h.node('overallState').textContent, 'E-STOP');
  assert.equal(h.node('clearEstopButton').disabled, true);
  assert.match(h.node('estopMessage').textContent, /4\.0.*SAFE|SAFE.*4\.0/);
  assert.match(h.node('clearEstopButton').title, /SAFE/);
});

test('a permit contract in the Safety field gets an actionable diagnosis', async () => {
  const { h } = supervisorHarness();
  const Base = h.run('ethers').Contract;
  h.run('ethers').Contract = class extends Base {
    async reporters() { const error = Error('execution reverted'); error.code = 'CALL_EXCEPTION'; throw error; }
    async gateways() { return true; }
  };
  await h.run('refreshSafetyPermissions()');
  assert.equal(h.run('state.supervisor'), false);
  assert.match(h.node('chainMessage').textContent, /WorkPermitHandoff.*HRCSafetyLog/);
});

test('a restored ESP32 selection initializes the live source instead of simulation', () => {
  const h = harness({ initialMode: 'gateway' });
  h.run(`addGatewayTelemetry({id:1,event_id:'restored',device_id:'esp32',distance_cm:51.1,severity:'WARNING',received_at:new Date().toISOString()})`);
  assert.equal(h.run('state.mode'), 'gateway');
  assert.equal(h.node('distanceValue').textContent, '51.1');
  assert.equal(h.node('gatewayStatus').textContent, 'GATEWAY · LIVE');
  assert.equal(h.node('simulateButton').disabled, true);
});

test('pageshow reconciles a browser-restored source and saved source survives reload', () => {
  const h = harness(); h.node('dataMode').value = 'gateway';
  h.run("window.events.pageshow()");
  assert.equal(h.run('state.mode'), 'gateway');
  const restored = harness({ savedMode: 'gateway' });
  assert.equal(restored.run('state.mode'), 'gateway');
  assert.equal(restored.node('dataMode').value, 'gateway');
});

test('polling refreshes confirmations of older events without replacing the latest distance', async () => {
  const h = harness({ initialMode: 'gateway' });
  h.run(`rememberGatewayEvent({id:1,event_id:'old-emergency',device_id:'esp32',distance_cm:20,severity:'EMERGENCY',evidence_status:'queued'});
    addGatewayTelemetry({id:2,event_id:'current-safe',device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:new Date().toISOString()}); state.historyCheckedAt=0; state.pollPending=false`);
  h.run('globalThis').fetch = async url => ({ ok: true, json: async () => url.includes('history')
    ? { telemetry: [{ id:1,event_id:'old-emergency',device_id:'esp32',distance_cm:20,severity:'EMERGENCY',evidence_status:'confirmed',tx_hash:'0x'+'b'.repeat(64) }] }
    : { telemetry: { id:2,event_id:'current-safe',device_id:'esp32',distance_cm:100,severity:'SAFE',received_at:new Date().toISOString() } } });
  await h.run('pollGatewayLatest()');
  assert.equal(h.node('eventCount').textContent, 1);
  assert.equal(h.node('distanceValue').textContent, '100.0');
});

test('a nonce rejection during role grant gives recovery instructions without retrying', async () => {
  const h = harness(); let submissions = 0;
  h.node('roleAddress').value = '0x' + '1'.repeat(40);
  h.node('roleSelect').value = 'reporter';
  h.node('contractAddress').value = '0x' + '2'.repeat(40);
  h.run('state.signer={}');
  h.run('ethers').Contract = class {
    async setReporter() { submissions++; throw { code:'NONCE_EXPIRED', shortMessage:'nonce has already been used',
      info:{error:{message:'Nonce too low. Expected nonce to be 2587 but got 2586'}} }; }
  };
  await h.run('assignRole(true)');
  assert.equal(submissions, 1);
  assert.match(h.node('roleMessage').textContent, /gateway/);
  assert.match(h.node('roleMessage').textContent, /nonce data/);
  assert.match(h.node('roleMessage').textContent, /Reporter/);
});
