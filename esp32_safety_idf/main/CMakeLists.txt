idf_component_register(
    SRCS "main.cpp" "model/model_data.cc"
    INCLUDE_DIRS "."
    REQUIRES esp-tflite-micro esp_driver_gpio esp_timer
)
