#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#include "driver/gpio.h"
#include "esp_err.h"
#include "esp_log.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "model/model_data.h"
#include "tensorflow/lite/micro/all_ops_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

static constexpr char TAG[] = "safety_ai";
static constexpr gpio_num_t TRIG_PIN = GPIO_NUM_5;
static constexpr gpio_num_t ECHO_PIN = GPIO_NUM_18;
static constexpr gpio_num_t BUZZER_PIN = GPIO_NUM_23;
static constexpr gpio_num_t BUTTON_PIN = GPIO_NUM_27;

static constexpr float WARNING_DISTANCE_CM = 60.0f;
static constexpr float DANGER_DISTANCE_CM = 30.0f;
static constexpr int64_t ECHO_TIMEOUT_US = 30000;
static constexpr int SAMPLE_INTERVAL_MS = 100;
static constexpr int DEBOUNCE_MS = 35;
static constexpr int WINDOW_SIZE = 5;
static constexpr int FEATURE_COUNT = 6;
static constexpr int CLASS_COUNT = 3;
static constexpr size_t TENSOR_ARENA_SIZE = 24 * 1024;

static uint8_t tensor_arena[TENSOR_ARENA_SIZE] __attribute__((aligned(16)));
static const char *LABELS[CLASS_COUNT] = {"SAFE", "APPROACHING", "EMERGENCY"};

static tflite::MicroInterpreter *interpreter = nullptr;
static TfLiteTensor *model_input = nullptr;
static TfLiteTensor *model_output = nullptr;
static bool model_ready = false;

static float distance_history[WINDOW_SIZE] = {};
static float speed_history[WINDOW_SIZE] = {};
static int history_count = 0;
static int write_index = 0;
static uint64_t previous_measurement_us = 0;

static uint32_t sequence_number = 0;
static bool buzzer_silenced = false;
static int last_button_reading = 1;
static int64_t button_changed_at_ms = 0;

static float clamp_value(float value, float low, float high)
{
    return std::max(low, std::min(value, high));
}

static float history_distance_back(int back)
{
    if (history_count == 0) return 0.0f;
    const int newest = (write_index - 1 + WINDOW_SIZE) % WINDOW_SIZE;
    const int index = (newest - std::min(back, history_count - 1) + WINDOW_SIZE) % WINDOW_SIZE;
    return distance_history[index];
}

static float history_speed_back(int back)
{
    if (history_count == 0) return 0.0f;
    const int newest = (write_index - 1 + WINDOW_SIZE) % WINDOW_SIZE;
    const int index = (newest - std::min(back, history_count - 1) + WINDOW_SIZE) % WINDOW_SIZE;
    return speed_history[index];
}

static void update_feature_history(float distance_cm, float dt_seconds, float features[FEATURE_COUNT])
{
    const float previous_distance = history_count == 0
        ? distance_cm
        : history_distance_back(0);
    const float speed = clamp_value(
        (distance_cm - previous_distance) / std::max(dt_seconds, 0.001f),
        -500.0f, 500.0f);

    distance_history[write_index] = distance_cm;
    speed_history[write_index] = speed;
    write_index = (write_index + 1) % WINDOW_SIZE;
    history_count = std::min(history_count + 1, WINDOW_SIZE);

    float distance_sum = 0.0f;
    float speed_sum = 0.0f;
    for (int i = 0; i < history_count; ++i) {
        distance_sum += history_distance_back(i);
        speed_sum += history_speed_back(i);
    }
    const float distance_mean = distance_sum / history_count;
    const float speed_mean = speed_sum / history_count;

    float variance = 0.0f;
    for (int i = 0; i < history_count; ++i) {
        const float delta = history_distance_back(i) - distance_mean;
        variance += delta * delta;
    }
    // pandas rolling().std() uses sample standard deviation (ddof=1).
    const float distance_std = history_count > 1
        ? std::sqrt(variance / (history_count - 1))
        : 0.0f;

    features[0] = distance_cm;
    features[1] = speed;
    features[2] = history_count >= 4
        ? distance_cm - history_distance_back(3)
        : distance_cm - previous_distance;
    features[3] = distance_std;
    features[4] = distance_mean;
    features[5] = speed_mean;
}

static bool initialize_model()
{
    const tflite::Model *model = tflite::GetModel(g_model_data);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(TAG, "Model schema mismatch: %lu != %d",
                 static_cast<unsigned long>(model->version()), TFLITE_SCHEMA_VERSION);
        return false;
    }

    static tflite::AllOpsResolver resolver;
    static tflite::MicroInterpreter static_interpreter(
        model, resolver, tensor_arena, TENSOR_ARENA_SIZE);
    interpreter = &static_interpreter;

    if (interpreter->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors failed; increase tensor arena");
        return false;
    }

    model_input = interpreter->input(0);
    model_output = interpreter->output(0);
    if (model_input->type != kTfLiteInt8 || model_output->type != kTfLiteInt8 ||
        model_input->bytes < FEATURE_COUNT || model_output->bytes < CLASS_COUNT) {
        ESP_LOGE(TAG, "Expected int8 model with 6 inputs and 3 outputs");
        return false;
    }

    ESP_LOGI(TAG, "TFLite Micro model ready; input scale=%f zero=%d output scale=%f zero=%d",
             model_input->params.scale, model_input->params.zero_point,
             model_output->params.scale, model_output->params.zero_point);
    return true;
}

static int run_model(const float features[FEATURE_COUNT])
{
    for (int i = 0; i < FEATURE_COUNT; ++i) {
        const float normalized =
            (features[i] - g_feature_mean[i]) / g_feature_scale[i];
        const int quantized = static_cast<int>(std::lround(
            normalized / model_input->params.scale)) + model_input->params.zero_point;
        model_input->data.int8[i] = static_cast<int8_t>(
            std::max(-128, std::min(127, quantized)));
    }

    if (interpreter->Invoke() != kTfLiteOk) {
        ESP_LOGE(TAG, "Inference failed");
        return -1;
    }

    int best_class = 0;
    int best_value = model_output->data.int8[0];
    for (int i = 1; i < CLASS_COUNT; ++i) {
        if (model_output->data.int8[i] > best_value) {
            best_value = model_output->data.int8[i];
            best_class = i;
        }
    }
    return best_class;
}

static const char *predict_state(float distance_cm, const float features[FEATURE_COUNT])
{
    // Safety invariant: the model may not downgrade a very close object.
    if (distance_cm <= DANGER_DISTANCE_CM) return "EMERGENCY";
    if (!model_ready) return "AI_FAULT";

    const int predicted = run_model(features);
    if (predicted < 0 || predicted >= CLASS_COUNT) return "AI_FAULT";
    return LABELS[predicted];
}

static float read_distance_cm()
{
    gpio_set_level(TRIG_PIN, 0);
    esp_rom_delay_us(2);
    gpio_set_level(TRIG_PIN, 1);
    esp_rom_delay_us(10);
    gpio_set_level(TRIG_PIN, 0);

    const int64_t wait_started = esp_timer_get_time();
    while (gpio_get_level(ECHO_PIN) == 0) {
        if (esp_timer_get_time() - wait_started >= ECHO_TIMEOUT_US) return NAN;
    }

    const int64_t pulse_started = esp_timer_get_time();
    while (gpio_get_level(ECHO_PIN) == 1) {
        if (esp_timer_get_time() - pulse_started >= ECHO_TIMEOUT_US) return NAN;
    }

    const int64_t pulse_width = esp_timer_get_time() - pulse_started;
    return static_cast<float>(pulse_width) * 0.0343f / 2.0f;
}

static void update_button()
{
    const int reading = gpio_get_level(BUTTON_PIN);
    const int64_t now_ms = esp_timer_get_time() / 1000;

    if (reading != last_button_reading) {
        last_button_reading = reading;
        button_changed_at_ms = now_ms;
    }
    if (reading == 0 && now_ms - button_changed_at_ms >= DEBOUNCE_MS) {
        buzzer_silenced = true;
    }
}

static void emit_telemetry(float distance_cm, const char *state, bool buzzer_on)
{
    std::printf(
        "{\"device_id\":\"ESP32-HRC-01\",\"sensor_id\":\"HC-SR04\","
        "\"timestamp_ms\":%lld,\"distance_cm\":",
        static_cast<long long>(esp_timer_get_time() / 1000));

    if (std::isnan(distance_cm)) std::printf("null");
    else std::printf("%.1f", distance_cm);

    std::printf(
        ",\"state\":\"%s\",\"emergency_stop\":%s,\"buzzer_on\":%s,"
        "\"buzzer_silenced\":%s,\"seq\":%lu}\n",
        state,
        std::strcmp(state, "EMERGENCY") == 0 ? "true" : "false",
        buzzer_on ? "true" : "false",
        buzzer_silenced ? "true" : "false",
        static_cast<unsigned long>(++sequence_number));
}

extern "C" void app_main(void)
{
    gpio_config_t outputs = {};
    outputs.pin_bit_mask = (1ULL << TRIG_PIN) | (1ULL << BUZZER_PIN);
    outputs.mode = GPIO_MODE_OUTPUT;
    outputs.pull_up_en = GPIO_PULLUP_DISABLE;
    outputs.pull_down_en = GPIO_PULLDOWN_DISABLE;
    outputs.intr_type = GPIO_INTR_DISABLE;
    ESP_ERROR_CHECK(gpio_config(&outputs));

    gpio_config_t inputs = {};
    inputs.pin_bit_mask = (1ULL << ECHO_PIN) | (1ULL << BUTTON_PIN);
    inputs.mode = GPIO_MODE_INPUT;
    inputs.pull_up_en = GPIO_PULLUP_ENABLE;
    inputs.pull_down_en = GPIO_PULLDOWN_DISABLE;
    inputs.intr_type = GPIO_INTR_DISABLE;
    ESP_ERROR_CHECK(gpio_config(&inputs));

    gpio_set_level(TRIG_PIN, 0);
    gpio_set_level(BUZZER_PIN, 0);
    model_ready = initialize_model();
    std::printf("HRC Safety Log: ESP-IDF + TFLite Micro ready=%s\n",
                model_ready ? "true" : "false");

    while (true) {
        update_button();
        const float distance_cm = read_distance_cm();
        const uint64_t now_us = esp_timer_get_time();
        const float dt_seconds = previous_measurement_us == 0
            ? 0.1f
            : static_cast<float>(now_us - previous_measurement_us) / 1000000.0f;
        previous_measurement_us = now_us;

        float features[FEATURE_COUNT] = {};
        const bool valid_measurement = !std::isnan(distance_cm) &&
                                       distance_cm >= 2.0f && distance_cm <= 450.0f;
        if (valid_measurement) {
            update_feature_history(distance_cm, dt_seconds, features);
        }

        const char *state = valid_measurement
            ? predict_state(distance_cm, features)
            : "SENSOR_FAULT";

        if (std::strcmp(state, "SAFE") == 0) buzzer_silenced = false;
        const bool alarm = std::strcmp(state, "EMERGENCY") == 0 ||
                           std::strcmp(state, "SENSOR_FAULT") == 0 ||
                           std::strcmp(state, "AI_FAULT") == 0;
        const bool buzzer_on = alarm && !buzzer_silenced;
        gpio_set_level(BUZZER_PIN, buzzer_on ? 1 : 0);
        emit_telemetry(distance_cm, state, buzzer_on);
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_INTERVAL_MS));
    }
}
