# Pipeline implementation notes

1. **IoT**: `firmware/ultrasonic_esp32/ultrasonic_esp32.ino` measures sensors sequentially to reduce crosstalk and emits a stable text protocol.
2. **Gateway**: `gateway/serial_reader.py` parses the protocol. `gateway/pipeline.py` is also replayable from CSV, which makes the demo deterministic and testable without hardware.
3. **Feature layer**: `ai/feature_engineering.py` is shared by notebook, training script, and inference. This prevents train/live feature drift.
4. **Decision layer**: distance thresholds run before the model. The model adds an anomaly warning but cannot suppress a danger threshold.
5. **Blockchain**: `gateway/blockchain_client.py` submits only the event commitment and safety state to `HRCSafetyLog.sol`.
6. **Audit**: transaction hash, event hash, source CSV row, and model metrics are the evidence bundle for the report.
