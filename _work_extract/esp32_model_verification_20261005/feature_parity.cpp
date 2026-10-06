#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <cstdint>
#include "model_data.h"
constexpr int WINDOW_SIZE=5, FEATURE_COUNT=3, CLASS_COUNT=3;
static float distance_history[WINDOW_SIZE] = {};
static int history_count = 0;
static int write_index = 0;

static float history_distance_back(int back)
{
    if (history_count == 0) return 0.0f;
    const int newest = (write_index - 1 + WINDOW_SIZE) % WINDOW_SIZE;
    const int index = (newest - std::min(back, history_count - 1) + WINDOW_SIZE) % WINDOW_SIZE;
    return distance_history[index];
}

static void update_feature_history(float distance_cm, float features[FEATURE_COUNT])
{
    distance_history[write_index] = distance_cm;
    write_index = (write_index + 1) % WINDOW_SIZE;
    history_count = std::min(history_count + 1, WINDOW_SIZE);

    float distance_sum = 0.0f;
    for (int i = 0; i < history_count; ++i) {
        distance_sum += history_distance_back(i);
    }
    const float distance_mean = distance_sum / history_count;

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
    features[1] = history_count >= 4
        ? distance_cm - history_distance_back(3)
        : 0.0f;
    features[2] = distance_std;
}

struct Input {struct {float scale; int zero_point;} params; struct {int8_t* int8;} data;};
int8_t values[3]; Input input={{0.06372566521167755f,-18},{values}}; Input* model_input=&input;
void quantize(const float features[3]) {
    for (int i = 0; i < FEATURE_COUNT; ++i) {
        const float normalized =
            (features[i] - g_feature_mean[i]) / g_feature_scale[i];
        const int quantized = static_cast<int>(std::lround(
            normalized / model_input->params.scale)) + model_input->params.zero_point;
        model_input->data.int8[i] = static_cast<int8_t>(
            std::max(-128, std::min(127, quantized)));
    }

}
constexpr float DANGER_DISTANCE_CM=30; bool model_ready=true; int mocked_prediction=0;
const char* LABELS[]={"SAFE","APPROACHING","EMERGENCY"}; int run_model(const float*){return mocked_prediction;}
static const char *predict_state(float distance_cm, const float features[FEATURE_COUNT])
{
    // Hard safety rule cannot be downgraded by AI or model initialization failure.
    if (distance_cm <= DANGER_DISTANCE_CM) {
        return "EMERGENCY";
    }
    if (!model_ready) {
        return "AI_FAULT";
    }

    const int predicted = run_model(features);
    if (predicted < 0 || predicted >= CLASS_COUNT) {
        return "AI_FAULT";
    }

    // Keep an AI EMERGENCY above the hard boundary: sensor noise around 30 cm
    // must not silently turn a predicted stop request into APPROACHING.
    return LABELS[predicted];
}

int main(){float features[3]={}; assert(std::strcmp(predict_state(30,features),"EMERGENCY")==0);
mocked_prediction=2; assert(std::strcmp(predict_state(31.5,features),"EMERGENCY")==0);
mocked_prediction=-1; assert(std::strcmp(predict_state(100,features),"AI_FAULT")==0);
mocked_prediction=3; assert(std::strcmp(predict_state(100,features),"AI_FAULT")==0);
model_ready=false; assert(std::strcmp(predict_state(20,features),"EMERGENCY")==0); assert(std::strcmp(predict_state(100,features),"AI_FAULT")==0);
float samples[]={241.300003f,240.899994f,240.899994f,240.800003f,204.899994f,204.899994f,203.600006f,204.0f,204.899994f,216.399994f,214.199997f,205.899994f,207.399994f,203.800003f,195.300003f,193.0f,190.5f,191.100006f,183.399994f,187.0f};
for(float distance:samples){update_feature_history(distance,features); quantize(features); std::printf("%.9g %.9g %.9g %d %d %d\n",features[0],features[1],features[2],values[0],values[1],values[2]);}
history_count=0;write_index=0;update_feature_history(100,features);assert(features[1]==0 && features[2]==0);}
