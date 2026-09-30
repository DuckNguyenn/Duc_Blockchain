// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title HRC Safety Log
/// @notice Stores tamper-evident hashes of robot safety events and controls an emergency-stop state.
contract HRCSafetyLog {
    enum Severity { SAFE, WARNING, DANGER, EMERGENCY }
    bytes32 public constant EVIDENCE_SCHEMA_V1 = keccak256("sonarchain.evidence.v1");

    struct SafetyEvent {
        bytes32 eventHash;
        bytes32 deviceIdHash;
        uint64 timestamp;
        Severity severity;
        bool emergencyStop;
        address reporter;
        bytes32 evidenceHash;
        bytes32 evidenceSchema;
        uint64 recordedAt;
    }

    address public immutable owner;
    mapping(address => bool) public reporters;
    mapping(bytes32 => SafetyEvent) private eventsByHash;
    mapping(bytes32 => bool) public eventExists;
    mapping(bytes32 => bool) public deviceLocked;
    mapping(bytes32 => bool) public emergencyStopByDevice;
    mapping(bytes32 => bool) public evidenceExists;

    event ReporterUpdated(address indexed reporter, bool allowed);
    event SafetyEventRecorded(
        bytes32 indexed eventHash,
        bytes32 indexed deviceIdHash,
        Severity severity,
        bool emergencyStop,
        address indexed reporter,
        uint64 timestamp
    );
    event EmergencyStopChanged(bytes32 indexed deviceIdHash, bool active, bytes32 indexed eventHash);
    event DeviceAccessChanged(bytes32 indexed deviceIdHash, bool locked, bytes32 indexed eventHash);
    event SafetyEvidenceRecorded(
        bytes32 indexed evidenceHash,
        bytes32 indexed deviceIdHash,
        bytes32 indexed evidenceSchema,
        Severity severity,
        bool emergencyStop,
        uint64 measuredAt,
        uint64 recordedAt,
        address reporter
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    modifier onlyReporter() {
        require(msg.sender == owner || reporters[msg.sender], "not reporter");
        _;
    }

    constructor() {
        owner = msg.sender;
        reporters[msg.sender] = true;
    }

    function setReporter(address reporter, bool allowed) external onlyOwner {
        reporters[reporter] = allowed;
        emit ReporterUpdated(reporter, allowed);
    }

    function recordEvent(
        bytes32 eventHash,
        bytes32 deviceIdHash,
        uint64 timestamp,
        Severity severity,
        bool emergencyStop
    ) external onlyReporter {
        _recordEvidence(eventHash, eventHash, EVIDENCE_SCHEMA_V1, deviceIdHash, timestamp, severity, emergencyStop);
    }

    /// @notice Records the digest of a versioned off-chain evidence envelope.
    /// @dev Raw telemetry, model output and operational metadata stay off-chain.
    function recordEvidence(
        bytes32 evidenceHash,
        bytes32 deviceIdHash,
        uint64 measuredAt,
        Severity severity,
        bool emergencyStop,
        bytes32 evidenceSchema
    ) external onlyReporter {
        require(evidenceSchema == EVIDENCE_SCHEMA_V1, "unsupported evidence schema");
        _recordEvidence(evidenceHash, evidenceHash, evidenceSchema, deviceIdHash, measuredAt, severity, emergencyStop);
    }

    function _recordEvidence(
        bytes32 eventHash,
        bytes32 evidenceHash,
        bytes32 evidenceSchema,
        bytes32 deviceIdHash,
        uint64 timestamp,
        Severity severity,
        bool emergencyStop
    ) internal {
        require(eventHash != bytes32(0), "empty event hash");
        require(deviceIdHash != bytes32(0), "empty device hash");
        require(timestamp > 0, "empty measured timestamp");
        require(!eventExists[eventHash], "event already recorded");
        require(!evidenceExists[evidenceHash], "evidence already recorded");
        require(!emergencyStop || severity >= Severity.DANGER, "stop requires danger severity");
        require(severity != Severity.EMERGENCY || emergencyStop, "emergency requires stop");

        uint64 recordedAt = uint64(block.timestamp);
        eventsByHash[eventHash] = SafetyEvent({
            eventHash: eventHash,
            deviceIdHash: deviceIdHash,
            timestamp: timestamp,
            severity: severity,
            emergencyStop: emergencyStop,
            reporter: msg.sender,
            evidenceHash: evidenceHash,
            evidenceSchema: evidenceSchema,
            recordedAt: recordedAt
        });
        eventExists[eventHash] = true;
        evidenceExists[evidenceHash] = true;

        if (emergencyStop) {
            emergencyStopByDevice[deviceIdHash] = true;
            deviceLocked[deviceIdHash] = true;
            emit EmergencyStopChanged(deviceIdHash, true, eventHash);
            emit DeviceAccessChanged(deviceIdHash, true, eventHash);
        }

        emit SafetyEventRecorded(eventHash, deviceIdHash, severity, emergencyStop, msg.sender, timestamp);
        emit SafetyEvidenceRecorded(evidenceHash, deviceIdHash, evidenceSchema, severity, emergencyStop, timestamp, recordedAt, msg.sender);
    }

    function clearEmergencyStop(bytes32 deviceIdHash) external onlyOwner {
        emergencyStopByDevice[deviceIdHash] = false;
        deviceLocked[deviceIdHash] = false;
        emit EmergencyStopChanged(deviceIdHash, false, bytes32(0));
        emit DeviceAccessChanged(deviceIdHash, false, bytes32(0));
    }

    function getEvent(bytes32 eventHash) external view returns (SafetyEvent memory) {
        require(eventExists[eventHash], "event not found");
        return eventsByHash[eventHash];
    }
}
