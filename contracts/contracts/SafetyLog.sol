// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Audit log for warnings emitted by one distance sensor node.
/// @dev This contract records evidence only; it does not control the ESP32.
contract SafetyLog {
    bytes32 public constant GATEWAY_ROLE = keccak256("GATEWAY_ROLE");
    bytes32 public constant DEFAULT_ADMIN_ROLE = bytes32(0);
    mapping(bytes32 => mapping(address => bool)) private roleMembers;

    modifier onlyRole(bytes32 role) {
        require(roleMembers[role][msg.sender], "missing role");
        _;
    }

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
        roleMembers[DEFAULT_ADMIN_ROLE][admin] = true;
        roleMembers[GATEWAY_ROLE][admin] = true;
    }

    function grantGatewayRole(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        roleMembers[GATEWAY_ROLE][account] = true;
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
