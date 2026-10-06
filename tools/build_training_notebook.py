"""Bundle the tested Python pipeline into a standalone Kaggle/Colab notebook."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def cell(kind, text):
    result = {"cell_type": kind, "metadata": {}, "source": text.splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


helpers = (ROOT / "ai_model/tinyml_pipeline.py").read_text(encoding="utf-8")
trainer = (ROOT / "ai_model/train_keras_tflite.py").read_text(encoding="utf-8")
trainer = trainer[:trainer.index("\ndef main()")]
trainer = "\n".join(line for line in trainer.splitlines() if not line.startswith("from ai_model.tinyml_pipeline import"))
cells = [
    cell("markdown", "# ESP32: huấn luyện và đánh giá theo recording\n\n"
         "Notebook độc lập, được đóng gói từ pipeline đã kiểm thử trong project. Dùng 3 feature đúng firmware: "
         "distance_cm, distance_delta_3, distance_std_5. Train/validation/test tách recording và luôn đủ 3 lớp. "
         "Chọn model bằng validation; test chỉ đánh giá sau khi chọn. Không đổi seed để tìm điểm đẹp.\n\n"
         "Chỉ có 3 recording APPROACHING và 3 EMERGENCY: một split chưa chứng minh khả năng tổng quát. "
         "Cần thu thêm phiên độc lập và khớp chu kỳ lấy mẫu trước khi nạp thiết bị.\n"),
    cell("code", "# Kaggle thường đã có TensorFlow. Bỏ comment nếu môi trường thiếu thư viện.\n# %pip install tensorflow pandas numpy scikit-learn\n"),
    cell("code", helpers),
    cell("code", trainer),
    cell("code", "# Thay None bằng Path('đường/dẫn/dataset_3class.csv') nếu có nhiều dataset.\n"
         "DATASET_PATH = None\n"
         "candidates = []\n"
         "for root in [Path.cwd()] + list(Path.cwd().parents)[:3]:\n"
         "    candidates.extend([root / 'ai_model/data/single_sensor/processed_3class/dataset_3class.csv', root / 'data/single_sensor/processed_3class/dataset_3class.csv'])\n"
         "for root in [Path('/kaggle/input'), Path('/content')]:\n"
         "    if root.exists(): candidates.extend(sorted(root.rglob('dataset_3class.csv')))\n"
         "available = sorted(set(path.resolve() for path in candidates if path.exists()))\n"
         "if DATASET_PATH is None:\n"
         "    if len(available) != 1: raise ValueError(f'Cần chỉ định đúng một dataset; tìm thấy: {available}')\n"
         "    DATASET_PATH = available[0]\n"
         "OUTPUT_DIR = Path('/kaggle/working/esp32_candidate') if Path('/kaggle/working').exists() else Path('esp32_candidate')\n"
         "data = prepare_data(DATASET_PATH, seed=42)\n"
         "print(json.dumps(split_manifest(data), indent=2, ensure_ascii=False))\n"
         "print('Median dt:', data['raw'].groupby('source_file')['elapsed_s'].diff().median())\n"),
    cell("code", "report = train_and_export(data, OUTPUT_DIR, epochs=150, seed=42)\n"
         "print(json.dumps({key: report[key] for key in ['selected','test_float','test_int8','test_firmware_policy','float_int8_agreement']}, indent=2))\n"),
    cell("code", "# Đường cong learning; test không được dùng cho early stopping.\n"
         "import matplotlib.pyplot as plt\n"
         "histories = json.loads((OUTPUT_DIR / 'history.json').read_text())\n"
         "history = histories[report['selected']]\n"
         "plt.plot(history['accuracy'], label='train accuracy')\n"
         "plt.plot(history['val_accuracy'], label='validation accuracy')\n"
         "plt.xlabel('Epoch'); plt.ylabel('Accuracy'); plt.legend(); plt.show()\n"),
    cell("code", "import shutil\n"
         "print(shutil.make_archive(str(OUTPUT_DIR), 'zip', root_dir=OUTPUT_DIR))\n"),
    cell("markdown", "## Trước khi nạp ESP32\n\n"
         "Kiểm tra model_metadata.json: input [1,3], output [1,3], feature order và mean/scale. "
         "Các file model_data.cc/h được copy cùng nhau. Đối chiếu parity_vectors.json trên thiết bị, "
         "đo thời gian Invoke và arena thực tế. Chỉ tin test_int8 là metric của AI; test_firmware_policy "
         "đo thêm luật firmware (<=30 cm luôn EMERGENCY; AI có thể nâng mức ở phía ngoài). "
         "Nếu hai metric khác nhau, kiểm tra nhãn ở vùng biên 30 cm.\n"),
]
notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
           "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
target = ROOT / "ai_model/notebooks/esp32_grouped_training.ipynb"
target.write_text(json.dumps(notebook, indent=1, ensure_ascii=False), encoding="utf-8")
print(target)
