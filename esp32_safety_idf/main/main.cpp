#include <cmath>
#include <cstdio>
#include <cstring>

#include "driver/gpio.h"
#include "esp_err.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static constexpr gpio_num_t TRIG_PIN = GPIO_NUM_5;
static constexpr gpio_num_t ECHO_PIN = GPIO_NUM_18;
static constexpr gpio_num_t BUZZER_PIN = GPIO_NUM_23;
static constexpr gpio_num_t BUTTON_PIN = GPIO_NUM_27;

static constexpr float WARNING_DISTANCE_CM = 60.0f;
static constexpr float DANGER_DISTANCE_CM = 30.0f;
static constexpr int64_t ECHO_TIMEOUT_US = 30000;
static constexpr int SAMPLE_INTERVAL_MS = 100;
static constexpr int DEBOUNCE_MS = 35;

static uint32_t sequence_number = 0;
static bool buzzer_silenced = false;
static int last_button_reading = 1;
static int64_t button_changed_at_ms = 0;

static const char *state_for(float distance_cm)
{
    if (std::isnan(distance_cm)) return "SENSOR_FAULT";
    if (distance_cm <= DANGER_DISTANCE_CM) return "EMERGENCY";
    if (distance_cm <= WARNING_DISTANCE_CM) return "WARNING";
    return "SAFE";
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
        "{\"device_id\":\"ESP32-HRC-01\","
        "\"sensor_id\":\"HC-SR04\","
        "\"timestamp_ms\":%lld,\"distance_cm\":"
        , static_cast<long long>(esp_timer_get_time() / 1000));

    if (std::isnan(distance_cm)) std::printf("null");
    else std::printf("%.1f", distance_cm);

    std::printf(
        ",\"state\":\"%s\",\"emergency_stop\":%s,"
        "\"buzzer_on\":%s,\"buzzer_silenced\":%s,\"seq\":%lu}\n",
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
    std::printf("HRC Safety Log: native ESP-IDF firmware ready\n");

    while (true) {
        update_button();
        const float distance_cm = read_distance_cm();
        const char *state = state_for(distance_cm);

        if (std::strcmp(state, "SAFE") == 0) buzzer_silenced = false;

        const bool alarm = std::strcmp(state, "EMERGENCY") == 0 ||
                           std::strcmp(state, "SENSOR_FAULT") == 0;
        const bool buzzer_on = alarm && !buzzer_silenced;
        gpio_set_level(BUZZER_PIN, buzzer_on ? 1 : 0);
        emit_telemetry(distance_cm, state, buzzer_on);
        vTaskDelay(pdMS_TO_TICKS(SAMPLE_INTERVAL_MS));
    }
}
