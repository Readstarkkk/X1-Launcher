#include <jni.h>
#include <algorithm>
#include <cstdint>

extern "C"
JNIEXPORT jstring JNICALL
Java_com_x1launcher_app_FrameGenerationNative_nativeVersion(
    JNIEnv* env,
    jclass
) {
    return env->NewStringUTF("X1 Frame Generation Engine 0.1.0");
}

extern "C"
JNIEXPORT jbyteArray JNICALL
Java_com_x1launcher_app_FrameGenerationNative_nativeBlend(
    JNIEnv* env,
    jclass,
    jbyteArray previous,
    jbyteArray current,
    jfloat factor
) {
    if (!previous || !current) return nullptr;

    const jsize size = env->GetArrayLength(previous);

    if (size != env->GetArrayLength(current) || size % 4 != 0) {
        return nullptr;
    }

    factor = std::clamp(factor, 0.0f, 1.0f);

    jbyte* a = env->GetByteArrayElements(previous, nullptr);
    jbyte* b = env->GetByteArrayElements(current, nullptr);

    if (!a || !b) {
        if (a) env->ReleaseByteArrayElements(previous, a, JNI_ABORT);
        if (b) env->ReleaseByteArrayElements(current, b, JNI_ABORT);
        return nullptr;
    }

    jbyteArray output = env->NewByteArray(size);

    if (output) {
        jbyte* result = new jbyte[size];

        for (jsize i = 0; i < size; ++i) {
            const float av = static_cast<uint8_t>(a[i]);
            const float bv = static_cast<uint8_t>(b[i]);

            result[i] = static_cast<jbyte>(
                static_cast<uint8_t>(av + (bv - av) * factor)
            );
        }

        env->SetByteArrayRegion(output, 0, size, result);
        delete[] result;
    }

    env->ReleaseByteArrayElements(previous, a, JNI_ABORT);
    env->ReleaseByteArrayElements(current, b, JNI_ABORT);

    return output;
}
