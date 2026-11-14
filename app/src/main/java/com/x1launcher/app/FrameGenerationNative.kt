package com.x1launcher.app

object FrameGenerationNative {

    private var loaded = false

    init {
        loaded = try {
            System.loadLibrary("x1framegen")
            true
        } catch (e: UnsatisfiedLinkError) {
            false
        } catch (e: SecurityException) {
            false
        }
    }

    @JvmStatic
    external fun nativeVersion(): String

    @JvmStatic
    external fun nativeBlend(
        previous: ByteArray,
        current: ByteArray,
        factor: Float
    ): ByteArray?

    fun isAvailable(): Boolean = loaded

    fun getVersion(): String {
        if (!loaded) return "Native engine unavailable"

        return try {
            nativeVersion()
        } catch (e: Exception) {
            "Engine error: ${e.message}"
        }
    }

    fun interpolate(
        previous: ByteArray,
        current: ByteArray,
        factor: Float
    ): ByteArray? {
        if (!loaded) return null
        if (previous.size != current.size) return null
        if (previous.size % 4 != 0) return null

        return try {
            nativeBlend(previous, current, factor)
        } catch (e: Exception) {
            null
        }
    }
}
