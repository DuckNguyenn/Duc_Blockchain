"""Re-evaluate a candidate and compare Python features with actual firmware C++."""
from pathlib import Path
import json
import subprocess
import numpy as np
import pandas as pd
import tensorflow as tf
from ai_model.tinyml_pipeline import FEATURE_COLUMNS, make_features, metrics, prepare_data, write_json

ROOT = Path(__file__).resolve().parents[1]
candidate = ROOT / "ai_model/artifacts/esp32_candidate"
data = prepare_data(ROOT / "ai_model/data/single_sensor/processed_3class/dataset_3class.csv")
interpreter = tf.lite.Interpreter(model_path=str(candidate / "ultrasonic_safety_int8.tflite"))
interpreter.allocate_tensors()
inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
scaled = data["normalized"]["test"] / inp["quantization"][0]
quantized = np.clip(np.sign(scaled) * np.floor(np.abs(scaled) + 0.5) + inp["quantization"][1], -128, 127).astype(np.int8)
predictions = []
for row in quantized:
    interpreter.set_tensor(inp["index"], row.reshape(1, -1))
    interpreter.invoke()
    predictions.append(int(interpreter.get_tensor(out["index"])[0].argmax()))
report_path = candidate / "metrics.json"
report = json.loads(report_path.read_text(encoding="utf-8"))
keras_model = tf.keras.models.load_model(candidate / "selected_model.keras")
report["train"] = metrics(data["y"]["train"], keras_model.predict(data["normalized"]["train"], verbose=0).argmax(axis=1))
assert metrics(data["y"]["test"], np.array(predictions))["confusion_matrix"] == report["test_int8"]["confusion_matrix"]
old_policy = np.where(data["x"]["test"][:, 0] <= 30, 2, np.where(np.array(predictions) == 2, 1, predictions))
report["test_previous_firmware_policy"] = metrics(data["y"]["test"], old_policy)
policy = np.where(data["x"]["test"][:, 0] <= 30, 2, predictions)
report["test_firmware_policy"] = metrics(data["y"]["test"], policy)
write_json(report_path, report)

firmware = (ROOT / "esp32_safety_idf/main/main.cpp").read_text(encoding="utf-8")
globals_text = firmware[firmware.index("static float distance_history"):firmware.index("static uint32_t sequence_number")]
features_text = firmware[firmware.index("static float history_distance_back"):firmware.index("static bool initialize_model")]
policy_text = firmware[firmware.index("static const char *predict_state"):firmware.index("static float read_distance_cm")]
values = [100., 99., 96., 90., 88., 80., 80.2, 100.1, 102.7, 99.3, 100.]
cpp = '#include <algorithm>\n#include <cmath>\n#include <cstdio>\n#include <cstring>\n#include <cassert>\n'
cpp += 'constexpr int WINDOW_SIZE=5; constexpr int FEATURE_COUNT=3; constexpr int CLASS_COUNT=3;\n' + globals_text + features_text
cpp += 'constexpr float DANGER_DISTANCE_CM=30; bool model_ready=true; int mocked_prediction=0;\n'
cpp += 'const char *LABELS[]={"SAFE","APPROACHING","EMERGENCY"}; int run_model(const float*){return mocked_prediction;}\n' + policy_text
cpp += 'int main(){float samples[]={' + ','.join(f'{value}f' for value in values) + '};\n'
cpp += 'float input[3]={}; assert(std::strcmp(predict_state(24,input),"EMERGENCY")==0);\n'
cpp += 'mocked_prediction=2; assert(std::strcmp(predict_state(31.5,input),"EMERGENCY")==0);\n'
cpp += 'mocked_prediction=0; assert(std::strcmp(predict_state(100,input),"SAFE")==0); model_ready=false;\n'
cpp += 'assert(std::strcmp(predict_state(24,input),"EMERGENCY")==0); assert(std::strcmp(predict_state(100,input),"AI_FAULT")==0);\n'
cpp += 'for(float d:samples){float f[3]; update_feature_history(d,f); std::printf("%.9g %.9g %.9g\\n",f[0],f[1],f[2]);}}\n'
check_dir = candidate / "verification"
check_dir.mkdir(exist_ok=True)
source, binary = check_dir / "feature_parity.cpp", check_dir / "feature_parity.exe"
source.write_text(cpp, encoding="utf-8")
subprocess.run(["g++", str(source), "-o", str(binary)], check=True)
actual = np.array([[float(v) for v in line.split()] for line in subprocess.check_output([str(binary)], text=True).splitlines()])
frame = pd.DataFrame({"source_file": "fixture", "elapsed_s": np.arange(len(values)), "distance_cm": values})
expected = make_features(frame)[FEATURE_COLUMNS].to_numpy()
np.testing.assert_allclose(actual, expected, rtol=1e-5, atol=1e-4)
print("Actual firmware C++ / Python feature parity: PASS")
print("Policy accuracy / emergency recall:", report["test_firmware_policy"]["accuracy"], report["test_firmware_policy"]["emergency_recall"])
print("Training accuracy:", report["train"]["accuracy"])
print("EMERGENCY test distance range:", data["frames"]["test"].query("label == 'EMERGENCY'").distance_cm.agg(["min", "max"]).to_dict())
