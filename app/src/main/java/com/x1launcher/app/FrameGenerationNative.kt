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
        } catch (e: LinkageError) {
            "Engine error: ${e.message}"
        } catch (e: RuntimeException) {
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
        } catch (e: LinkageError) {
            null
        } catch (e: RuntimeException) {
            null
        }
    }

    /**
     * Verifica o JNI executando uma mistura RGBA pequena e previsível.
     * Isto valida o núcleo nativo; não testa captura nem FPS em jogos.
     */
    fun runSelfTest(): Boolean {
        if (!loaded) return false
        return try {
            val previous = byteArrayOf(0, 32, 64, -1)
            val current = byteArrayOf(100, 96, -64, -1)
            val expected = byteArrayOf(50, 64, -128, -1)
            val output = nativeBlend(previous, current, 0.5f) ?: return false
            output.contentEquals(expected)
        } catch (e: LinkageError) {
            false
        } catch (e: RuntimeException) {
            false
        }
    }
}
