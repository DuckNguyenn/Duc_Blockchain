// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Work Permit and Human–Robot Handoff
/// @notice On-chain authorization and audit trail for a collaborative workspace.
/// @dev The gateway/ESP32 remains responsible for real-time safety decisions.
contract WorkPermitHandoff {
    enum PermitStatus { NONE, PENDING, APPROVED, ACTIVE, COMPLETED, REVOKED }

    struct Permit {
        bytes32 permitId;
        bytes32 workerIdHash;
        bytes32 zoneIdHash;
        bytes32 taskIdHash;
        address worker;
        address requester;
        address approver;
        uint64 validFrom;
        uint64 validUntil;
        PermitStatus status;
    }

    struct Handoff {
        bytes32 handoffId;
        bytes32 permitId;
        bytes32 robotIdHash;
        bytes32 taskIdHash;
        uint64 recordedAt;
        address confirmedBy;
    }

    address public immutable owner;
    mapping(address => bool) public supervisors;
    mapping(address => bool) public gateways;
    mapping(bytes32 => Permit) private permits;
    mapping(bytes32 => Handoff) private handoffs;
    mapping(bytes32 => bool) public permitExists;
    mapping(bytes32 => bool) public handoffExists;

    event SupervisorUpdated(address indexed account, bool allowed);
    event GatewayUpdated(address indexed account, bool allowed);
    event PermitCreated(bytes32 indexed permitId, bytes32 indexed zoneIdHash, bytes32 indexed taskIdHash, address worker, address requester, uint64 validFrom, uint64 validUntil);
    event PermitApproved(bytes32 indexed permitId, address indexed approver);
    event ZoneEntryRecorded(bytes32 indexed permitId, bytes32 indexed telemetryEventHash, uint64 recordedAt, address indexed recorder);
    event HandoffConfirmed(bytes32 indexed handoffId, bytes32 indexed permitId, bytes32 indexed robotIdHash, bytes32 taskIdHash, address confirmer, uint64 recordedAt);
    event PermitCompleted(bytes32 indexed permitId, address indexed completer);
    event PermitRevoked(bytes32 indexed permitId, address indexed revoker);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlySupervisor() {
        require(msg.sender == owner || supervisors[msg.sender], "not supervisor");
        _;
    }

    modifier onlyGateway() {
        require(msg.sender == owner || gateways[msg.sender], "not gateway");
        _;
    }

    constructor() {
        owner = msg.sender;
        supervisors[msg.sender] = true;
        gateways[msg.sender] = true;
    }

    function setSupervisor(address account, bool allowed) external onlyOwner {
        supervisors[account] = allowed;
        emit SupervisorUpdated(account, allowed);
    }

    function setGateway(address account, bool allowed) external onlyOwner {
        gateways[account] = allowed;
        emit GatewayUpdated(account, allowed);
    }

    function createPermit(
        bytes32 permitId,
        bytes32 workerIdHash,
        bytes32 zoneIdHash,
        bytes32 taskIdHash,
        address worker,
        uint64 validFrom,
        uint64 validUntil
    ) external {
        require(permitId != bytes32(0), "empty permit id");
        require(!permitExists[permitId], "permit already exists");
        require(worker != address(0), "empty worker");
        require(validUntil > validFrom, "invalid permit window");
        permits[permitId] = Permit({
            permitId: permitId,
            workerIdHash: workerIdHash,
            zoneIdHash: zoneIdHash,
            taskIdHash: taskIdHash,
            worker: worker,
            requester: msg.sender,
            approver: address(0),
            validFrom: validFrom,
            validUntil: validUntil,
            status: PermitStatus.PENDING
        });
        permitExists[permitId] = true;
        emit PermitCreated(permitId, zoneIdHash, taskIdHash, worker, msg.sender, validFrom, validUntil);
    }

    function approvePermit(bytes32 permitId) external onlySupervisor {
        require(permitExists[permitId], "permit not found");
        Permit storage permit = permits[permitId];
        require(permit.status == PermitStatus.PENDING, "permit not pending");
        permit.status = PermitStatus.APPROVED;
        permit.approver = msg.sender;
        emit PermitApproved(permitId, msg.sender);
    }

    function recordZoneEntry(bytes32 permitId, bytes32 telemetryEventHash) external onlyGateway {
        require(permitExists[permitId], "permit not found");
        Permit storage permit = permits[permitId];
        require(permit.status == PermitStatus.APPROVED, "permit not approved");
        require(telemetryEventHash != bytes32(0), "empty telemetry hash");
        require(block.timestamp >= permit.validFrom, "permit not started");
        require(block.timestamp <= permit.validUntil, "permit expired");
        permit.status = PermitStatus.ACTIVE;
        emit ZoneEntryRecorded(permitId, telemetryEventHash, uint64(block.timestamp), msg.sender);
    }

    function confirmHandoff(bytes32 handoffId, bytes32 permitId, bytes32 robotIdHash) external {
        require(handoffId != bytes32(0), "empty handoff id");
        require(!handoffExists[handoffId], "handoff already exists");
        require(robotIdHash != bytes32(0), "empty robot id");
        require(permitExists[permitId], "permit not found");
        Permit storage permit = permits[permitId];
        require(permit.status == PermitStatus.ACTIVE, "permit not active");
        require(msg.sender == permit.worker || msg.sender == permit.requester || supervisors[msg.sender], "not handoff participant");
        handoffs[handoffId] = Handoff({
            handoffId: handoffId,
            permitId: permitId,
            robotIdHash: robotIdHash,
            taskIdHash: permit.taskIdHash,
            recordedAt: uint64(block.timestamp),
            confirmedBy: msg.sender
        });
        handoffExists[handoffId] = true;
        emit HandoffConfirmed(handoffId, permitId, robotIdHash, permit.taskIdHash, msg.sender, uint64(block.timestamp));
    }

    function completePermit(bytes32 permitId) external {
        require(permitExists[permitId], "permit not found");
        Permit storage permit = permits[permitId];
        require(permit.status == PermitStatus.ACTIVE, "permit not active");
        require(msg.sender == permit.worker || msg.sender == permit.requester || msg.sender == owner, "not permit participant");
        permit.status = PermitStatus.COMPLETED;
        emit PermitCompleted(permitId, msg.sender);
    }

    function revokePermit(bytes32 permitId) external onlySupervisor {
        require(permitExists[permitId], "permit not found");
        Permit storage permit = permits[permitId];
        require(permit.status == PermitStatus.PENDING || permit.status == PermitStatus.APPROVED || permit.status == PermitStatus.ACTIVE, "permit not revocable");
        permit.status = PermitStatus.REVOKED;
        emit PermitRevoked(permitId, msg.sender);
    }

    function getPermit(bytes32 permitId) external view returns (Permit memory) {
        require(permitExists[permitId], "permit not found");
        return permits[permitId];
    }

    function getHandoff(bytes32 handoffId) external view returns (Handoff memory) {
        require(handoffExists[handoffId], "handoff not found");
        return handoffs[handoffId];
    }
}
