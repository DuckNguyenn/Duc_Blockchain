// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/AccessControl.sol";

/// @notice Audit log for warnings emitted by one distance sensor node.
/// @dev This contract records evidence only; it does not control the ESP32.
contract SafetyLog is AccessControl {
    bytes32 public constant GATEWAY_ROLE = keccak256("GATEWAY_ROLE");

    enum Severity { WARNING, SENSOR_FAULT }

    struct WarningLog {
        bytes32 warningId;
        bytes32 logHash;
        bytes32 deviceId;
        bytes32 sensorId;
        Severity severity;
        uint256 recordedAt;
        address recordedBy;
    }

    mapping(bytes32 => WarningLog) public warnings;

    event WarningRecorded(
        bytes32 indexed warningId,
        bytes32 indexed deviceId,
        bytes32 indexed sensorId,
        bytes32 logHash,
        Severity severity,
        uint256 recordedAt,
        address recordedBy
    );

    constructor(address admin) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
    }

    function recordWarning(
        bytes32 warningId,
        bytes32 logHash,
        bytes32 deviceId,
        bytes32 sensorId,
        Severity severity
    ) external onlyRole(GATEWAY_ROLE) {
        require(warnings[warningId].recordedAt == 0, "Warning already exists");

        warnings[warningId] = WarningLog({
            warningId: warningId,
            logHash: logHash,
            deviceId: deviceId,
            sensorId: sensorId,
            severity: severity,
            recordedAt: block.timestamp,
            recordedBy: msg.sender
        });

        emit WarningRecorded(
            warningId,
            deviceId,
            sensorId,
            logHash,
            severity,
            block.timestamp,
            msg.sender
        );
    }

    function verifyLogHash(bytes32 warningId, bytes32 calculatedHash)
        external
        view
        returns (bool)
    {
        return warnings[warningId].logHash == calculatedHash;
    }
}