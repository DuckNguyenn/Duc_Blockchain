# Dataset single-sensor HC-SR04

Đây là bản dataset dùng cho bốn notebook mới trong `ai_model/notebooks/`.

Schema mỗi file CSV:

```text
timestamp,elapsed_s,distance_cm,label,nguoi,kichban,vat
```

Trong đó:

- `distance_cm`: khoảng cách từ một cảm biến HC-SR04 tới vật thể.
- `label`: `SAFE`, `APPROACHING`, `DANGER`, `RETREATING` hoặc `EMPTY`.
- Không còn các cột `left_cm` và `right_cm`.

Các file CSV trong thư mục này là bản single-sensor đã chuẩn hóa từ bộ recording cũ; cột `distance_cm` lấy từ giá trị cảm biến gần hơn trong mỗi dòng cũ để giữ lại mẫu nguy hiểm bảo thủ.
