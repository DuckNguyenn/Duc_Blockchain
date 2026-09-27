// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title HRC Safety Log
/// @notice Stores tamper-evident hashes of robot safety events and controls an emergency-stop state.
contract HRCSafetyLog {
    enum Severity { SAFE, WARNING, DANGER, EMERGENCY }

    struct SafetyEvent {
        bytes32 eventHash;
        bytes32 deviceIdHash;
        uint64 timestamp;
        Severity severity;
        bool emergencyStop;
        address reporter;
    }

    address public immutable owner;
    mapping(address => bool) public reporters;
    mapping(bytes32 => SafetyEvent) private eventsByHash;
    mapping(bytes32 => bool) public eventExists;
    mapping(bytes32 => bool) public deviceLocked;
    mapping(bytes32 => bool) public emergencyStopByDevice;

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
        require(eventHash != bytes32(0), "empty event hash");
        require(!eventExists[eventHash], "event already recorded");

        eventsByHash[eventHash] = SafetyEvent({
            eventHash: eventHash,
            deviceIdHash: deviceIdHash,
            timestamp: timestamp,
            severity: severity,
            emergencyStop: emergencyStop,
            reporter: msg.sender
        });
        eventExists[eventHash] = true;

        if (emergencyStop) {
            emergencyStopByDevice[deviceIdHash] = true;
            deviceLocked[deviceIdHash] = true;
            emit EmergencyStopChanged(deviceIdHash, true, eventHash);
            emit DeviceAccessChanged(deviceIdHash, true, eventHash);
        }

        emit SafetyEventRecorded(eventHash, deviceIdHash, severity, emergencyStop, msg.sender, timestamp);
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
