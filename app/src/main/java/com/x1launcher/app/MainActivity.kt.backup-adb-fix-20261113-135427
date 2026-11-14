package com.x1launcher.app

import android.Manifest
import android.app.Activity
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.RemoteInput
import android.app.ActivityManager
import android.app.AppOpsManager
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Environment
import android.os.Process
import android.os.StatFs
import android.provider.Settings
import android.os.Build
import android.os.BatteryManager
import android.os.Bundle
import android.util.Base64
import android.webkit.JavascriptInterface
import io.github.rhythmcache.adb.AdbClient
import io.github.rhythmcache.adb.FileKeyProvider
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.withTimeout
import java.io.File
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.app.usage.UsageStatsManager
import android.view.View
import android.graphics.Color
import android.widget.Toast
import android.graphics.drawable.Drawable
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.util.concurrent.TimeUnit

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null
    private val imagePickerRequest = 4317
    private val adbOperationActive = java.util.concurrent.atomic.AtomicBoolean(false)
    private var pendingAdbNotificationAfterPermission = false
    private val adbNotificationPermissionRequest = 7901

    private data class AdbUiResult(
        val success: Boolean,
        val message: String,
        val connected: Boolean = false
    )

    private fun adbKeyProvider(): FileKeyProvider {
        val keyDirectory = File(filesDir, "adb").apply { mkdirs() }
        return FileKeyProvider(File(keyDirectory, "adbkey"))
    }

    private fun adbPairingPreferences(): android.content.SharedPreferences =
        getSharedPreferences("x1_adb_pairing_state", MODE_PRIVATE)

    private fun saveAdbPairingState(host: String, connectPort: Int? = null) {
        val editor = adbPairingPreferences().edit()
            .putBoolean("paired", true)
            .putString("host", host)
            .putLong("pairedAt", System.currentTimeMillis())
        if (connectPort != null && connectPort in 1..65535) {
            editor.putInt("connectPort", connectPort)
        } else {
            editor.remove("connectPort")
        }
        editor.apply()
    }

    private fun adbPairingStateJson(): String {
        val prefs = adbPairingPreferences()
        return JSONObject()
            .put("paired", prefs.getBoolean("paired", false))
            .put("host", prefs.getString("host", "") ?: "")
            .put("connectPort", prefs.getInt("connectPort", 0))
            .put("pairedAt", prefs.getLong("pairedAt", 0L))
            .toString()
    }

    private fun clearAdbPairingState() {
        adbPairingPreferences().edit()
            .putBoolean("paired", false)
            .remove("host")
            .remove("connectPort")
            .remove("pairedAt")
            .apply()
    }

    // X1_RESOLUTION_CONTROLLER_V1
    private data class WmSizeState(val physical: String, val override: String?) {
        val effective: String get() = override ?: physical
    }

    private fun resolutionStatePreferences(): android.content.SharedPreferences =
        getSharedPreferences("x1_resolution_state", MODE_PRIVATE)

    private fun currentAdbConnection(): Pair<String, Int> {
        val prefs = adbPairingPreferences()
        if (!prefs.getBoolean("paired", false)) {
            throw IllegalStateException("Pareie o X1 em Depuração sem fio primeiro.")
        }
        val host = prefs.getString("host", "")?.trim().orEmpty()
        val port = prefs.getInt("connectPort", 0)
        if (host.isBlank() || port !in 1..65535) {
            throw IllegalStateException("A porta de conexão ADB não está salva. Conecte manualmente usando a porta da tela Depuração sem fio.")
        }
        return host to port
    }

    private fun resolutionAdbShell(host: String, port: Int, command: String): String {
        val result = runBlocking {
            withTimeout(20_000L) {
                AdbClient.connectTls(
                    host = host,
                    port = port,
                    keyProvider = adbKeyProvider(),
                    handshakeTimeoutMs = 15_000L
                ).use { client -> client.shell(command) }
            }
        }
        if (!result.isSuccess) {
            val detail = result.stderrText.trim().take(160).ifBlank { "comando ADB recusado" }
            throw IllegalStateException(detail)
        }
        return result.stdoutText.trim()
    }

    private fun parseWmSize(output: String): WmSizeState {
        val physical = Regex("Physical size:\\s*(\\d+x\\d+)", RegexOption.IGNORE_CASE)
            .find(output)?.groupValues?.get(1)
            ?: throw IllegalStateException("O Android não informou a resolução física: ${output.take(160)}")
        val override = Regex("Override size:\\s*(\\d+x\\d+)", RegexOption.IGNORE_CASE)
            .find(output)?.groupValues?.get(1)
        return WmSizeState(physical, override)
    }

    @Synchronized
    private fun applyResolutionForLaunch(packageName: String, preset: String): String {
        val allowedPresets = setOf("520p", "720p", "900p", "1080p", "1440p", "2160p")
        if (preset !in allowedPresets) throw IllegalArgumentException("perfil de resolução inválido")
        val (host, port) = currentAdbConnection()
        val statePrefs = resolutionStatePreferences()

        // If a previous session was interrupted, restore its saved baseline before taking a new one.
        if (statePrefs.getBoolean("active", false)) restoreOriginalResolutionWithConnection(host, port)

        val before = parseWmSize(resolutionAdbShell(host, port, "wm size"))
        val parts = before.physical.split("x")
        val physicalWidth = parts.getOrNull(0)?.toIntOrNull()
            ?: throw IllegalStateException("Largura física inválida")
        val physicalHeight = parts.getOrNull(1)?.toIntOrNull()
            ?: throw IllegalStateException("Altura física inválida")
        if (physicalWidth <= 0 || physicalHeight <= 0) throw IllegalStateException("Dimensões físicas inválidas")

        // The preset denotes the shorter edge (e.g. 720p -> 720x1600 on a 9:20 screen).
        val requestedShortEdge = preset.removeSuffix("p").toInt()
        val shortPhysical = minOf(physicalWidth, physicalHeight)
        val longPhysical = maxOf(physicalWidth, physicalHeight)
        val calculatedLong = (longPhysical.toDouble() * requestedShortEdge / shortPhysical).toInt()
        val evenLong = if (calculatedLong % 2 == 0) calculatedLong else calculatedLong + 1
        val target = if (physicalWidth <= physicalHeight) {
            "${requestedShortEdge}x${evenLong}"
        } else {
            "${evenLong}x${requestedShortEdge}"
        }

        val saved = statePrefs.edit()
            .putBoolean("active", true)
            .putBoolean("originalHadOverride", before.override != null)
            .putString("originalOverride", before.override ?: "")
            .putString("originalPhysical", before.physical)
            .putString("targetSize", target)
            .putString("packageName", packageName)
            .putLong("appliedAt", System.currentTimeMillis())
            .commit()
        if (!saved) throw IllegalStateException("Não foi possível salvar o estado original antes da alteração")

        try {
            resolutionAdbShell(host, port, "wm size $target")
            val after = parseWmSize(resolutionAdbShell(host, port, "wm size"))
            if (after.effective != target) {
                throw IllegalStateException("O Android não confirmou a resolução solicitada (atual: ${after.effective})")
            }
        } catch (e: Exception) {
            try { restoreOriginalResolutionWithConnection(host, port) } catch (_: Exception) { }
            throw e
        }
        return "Resolução global aplicada: $target. Ao voltar ao X1, tentaremos restaurar a configuração anterior."
    }

    @Synchronized
    private fun restoreOriginalResolutionBlocking(): String {
        val statePrefs = resolutionStatePreferences()
        if (!statePrefs.getBoolean("active", false)) return "Não há alteração de resolução do X1 pendente para restaurar."
        val (host, port) = currentAdbConnection()
        return restoreOriginalResolutionWithConnection(host, port)
    }

    private fun restoreOriginalResolutionWithConnection(host: String, port: Int): String {
        val statePrefs = resolutionStatePreferences()
        if (!statePrefs.getBoolean("active", false)) return "Não há alteração de resolução do X1 pendente para restaurar."
        val hadOverride = statePrefs.getBoolean("originalHadOverride", false)
        val originalOverride = statePrefs.getString("originalOverride", "")?.trim().orEmpty()
        if (hadOverride && !Regex("^\\d+x\\d+$").matches(originalOverride)) {
            throw IllegalStateException("A resolução anterior salva está inválida; o estado foi mantido para recuperação manual.")
        }
        val command = if (hadOverride) "wm size $originalOverride" else "wm size reset"
        resolutionAdbShell(host, port, command)
        val after = parseWmSize(resolutionAdbShell(host, port, "wm size"))
        val restored = if (hadOverride) after.override == originalOverride else after.override == null
        if (!restored) throw IllegalStateException("O Android não confirmou a restauração. A tentativa será mantida para repetir depois.")
        statePrefs.edit().clear().commit()
        return "Resolução anterior restaurada."
    }

    private fun showResolutionToast(message: String) {
        runOnUiThread {
            if (!::webView.isInitialized || isFinishing || isDestroyed) return@runOnUiThread
            val quoted = org.json.JSONObject.quote(message)
            webView.evaluateJavascript("window.toast && window.toast($quoted);", null)
        }
    }

    private fun restoreResolutionAfterReturnIfNeeded() {
        if (!resolutionStatePreferences().getBoolean("active", false)) return
        Thread({
            try {
                showResolutionToast(restoreOriginalResolutionBlocking())
            } catch (e: Exception) {
                showResolutionToast("A restauração automática falhou: ${e.message?.take(150) ?: "ADB indisponível"}. Reconecte a Depuração sem fio e use Restaurar resolução original no perfil.")
            }
        }, "X1-resolution-restore").start()
    }


    private fun startAdbOperation(task: suspend () -> AdbUiResult) {
        if (!adbOperationActive.compareAndSet(false, true)) {
            reportAdbPairResult(false, "Uma operação ADB já está em andamento. Aguarde terminar.", false)
            return
        }

        Thread({
            val result = try {
                runBlocking {
                    withTimeout(45_000L) { task() }
                }
            } catch (_: TimeoutCancellationException) {
                AdbUiResult(false, "Tempo esgotado após 45 segundos. Confira IP, portas, Wi-Fi e se a Depuração sem fio continua ativa.")
            } catch (e: Exception) {
                val detail = e.message?.take(160)?.takeIf { it.isNotBlank() }
                AdbUiResult(
                    false,
                    "Falha ADB: ${detail ?: e.javaClass.simpleName}. Confira a rede, a porta e o pareamento."
                )
            } finally {
                adbOperationActive.set(false)
            }
            runOnUiThread {
                reportAdbPairResult(result.success, result.message, result.connected)
            }
        }, "X1-ADB-operation").start()
    }

    private fun startAutomaticAdbPairingNotification() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            pendingAdbNotificationAfterPermission = true
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), adbNotificationPermissionRequest)
            return
        }
        postAdbPairingNotification()
    }

    private fun postAdbPairingNotification() {
        val manager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        val channelId = AdbPairingReceiver.NOTIFICATION_CHANNEL_ID
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Pareamento ADB do X1",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Solicita o código temporário da Depuração sem fio do Android."
                lockscreenVisibility = Notification.VISIBILITY_PRIVATE
            }
            manager.createNotificationChannel(channel)
        }

        val replyIntent = Intent(this, AdbPairingReceiver::class.java).apply {
            action = AdbPairingReceiver.ACTION_PAIR_WITH_CODE
        }
        val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0
        val replyPendingIntent = PendingIntent.getBroadcast(
            this,
            AdbPairingReceiver.REPLY_REQUEST_CODE,
            replyIntent,
            pendingFlags
        )
        val remoteInput = RemoteInput.Builder(AdbPairingReceiver.KEY_PAIRING_CODE)
            .setLabel("Código de 6 dígitos")
            .build()
        val action = Notification.Action.Builder(
            android.R.drawable.ic_menu_send,
            "Parear",
            replyPendingIntent
        ).addRemoteInput(remoteInput).build()

        val openAppIntent = PendingIntent.getActivity(
            this,
            7903,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or
                (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, channelId)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        val notification = builder
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle("X1 · Pareamento ADB")
            .setContentText("Abra a janela de pareamento do Android e responda com o código de 6 dígitos.")
            .setContentIntent(openAppIntent)
            .setAutoCancel(false)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_STATUS)
            .setPriority(Notification.PRIORITY_HIGH)
            .addAction(action)
            .build()
        manager.notify(AdbPairingReceiver.NOTIFICATION_ID, notification)
        reportAdbPairResult(
            true,
            "Notificação pronta. Abra Depuração sem fio → Parear dispositivo com código e responda à notificação do X1 com os 6 dígitos. O X1 tentará descobrir o IP e as portas automaticamente.",
            false
        )
    }

    @Suppress("DEPRECATION")
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != adbNotificationPermissionRequest) return
        val wasPending = pendingAdbNotificationAfterPermission
        pendingAdbNotificationAfterPermission = false
        if (!wasPending) return
        if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            postAdbPairingNotification()
        } else {
            reportAdbPairResult(
                false,
                "O Android bloqueou as notificações. Permita notificações para o X1 nas configurações do aplicativo e tente novamente.",
                false
            )
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = Color.rgb(8, 6, 15)
        window.navigationBarColor = Color.rgb(8, 6, 15)
        window.decorView.systemUiVisibility = 0

        webView = WebView(this)
        webView.setBackgroundColor(Color.rgb(8, 6, 15))
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                filePathCallback: ValueCallback<Array<Uri>>?,
                fileChooserParams: FileChooserParams?
            ): Boolean {
                this@MainActivity.fileChooserCallback?.onReceiveValue(null)
                this@MainActivity.fileChooserCallback = filePathCallback
                return try {
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        type = "image/*"
                        addCategory(Intent.CATEGORY_OPENABLE)
                    }
                    startActivityForResult(Intent.createChooser(intent, "Escolher papel de parede"), imagePickerRequest)
                    true
                } catch (_: Exception) {
                    this@MainActivity.fileChooserCallback?.onReceiveValue(null)
                    this@MainActivity.fileChooserCallback = null
                    false
                }
            }
        }
        webView.addJavascriptInterface(X1Bridge(), "X1")
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val url = request.url.toString()
                if (url.startsWith("https://", true) || url.startsWith("http://", true)) {
                    openExternal(url)
                    return true
                }
                return false
            }
        }
        webView.setDownloadListener { url, _, _, _, _ -> openExternal(url) }
        setContentView(webView)
        webView.loadUrl("file:///android_asset/index.html")
    }

    private fun openExternal(url: String): Boolean {
        return try {
            val uri = Uri.parse(url)
            if (uri.scheme != "https" && uri.scheme != "http") return false
            startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            true
        } catch (_: ActivityNotFoundException) {
            Toast.makeText(this, "Nenhum navegador pode abrir este link.", Toast.LENGTH_LONG).show()
            false
        } catch (_: Exception) {
            Toast.makeText(this, "Não foi possível abrir este link.", Toast.LENGTH_LONG).show()
            false
        }
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != imagePickerRequest) return
        val result = if (resultCode == RESULT_OK && data?.data != null) arrayOf(data.data!!) else null
        fileChooserCallback?.onReceiveValue(result)
        fileChooserCallback = null
    }

    private fun iconData(drawable: Drawable): String? {
        return try {
            val size = 96
            val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(bitmap)
            drawable.setBounds(0, 0, size, size)
            drawable.draw(canvas)
            val stream = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
            bitmap.recycle()
            "data:image/png;base64," + Base64.encodeToString(stream.toByteArray(), Base64.NO_WRAP)
        } catch (_: Exception) {
            null
        }
    }

    @Suppress("DEPRECATION")
    private fun installedAppsJson(): String {
        val result = JSONArray()
        val pm = packageManager
        val apps = if (Build.VERSION.SDK_INT >= 33) {
            pm.getInstalledApplications(PackageManager.ApplicationInfoFlags.of(PackageManager.GET_META_DATA.toLong()))
        } else {
            pm.getInstalledApplications(PackageManager.GET_META_DATA)
        }
        val entries = apps.mapNotNull { info ->
            val pkg = info.packageName
            if (pkg == packageName) return@mapNotNull null
            if (pm.getLaunchIntentForPackage(pkg) == null) return@mapNotNull null
            if ((info.flags and ApplicationInfo.FLAG_SYSTEM) != 0 && (info.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) == 0) return@mapNotNull null
            val label = runCatching { pm.getApplicationLabel(info).toString() }.getOrDefault(pkg)
            val isGame = (Build.VERSION.SDK_INT >= 26 && info.category == ApplicationInfo.CATEGORY_GAME) ||
                (label + " " + pkg).contains(Regex("roblox|minecraft|free.?fire|pubg|fortnite|genshin|asphalt|call.?of.?duty|codm|brawl|clash|stumble|among.?us|game|jogo", RegexOption.IGNORE_CASE))
            val icon = runCatching { iconData(pm.getApplicationIcon(info)) }.getOrNull()
            val item = JSONObject().put("name", label).put("packageName", pkg).put("isGame", isGame)
            if (icon != null) item.put("iconData", icon)
            item
        }.sortedBy { it.optString("name").lowercase() }
        entries.forEach { result.put(it) }
        return result.toString()
    }

    private fun deviceStatsJson(): String {
        return try {
            val activityManager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
            val memory = ActivityManager.MemoryInfo()
            activityManager.getMemoryInfo(memory)
            val storage = StatFs(Environment.getDataDirectory().absolutePath)
            val storageTotal = storage.totalBytes
            val storageAvailable = storage.availableBytes
            JSONObject()
                .put("ok", true)
                .put("ramTotal", memory.totalMem)
                .put("ramAvailable", memory.availMem)
                .put("ramUsed", (memory.totalMem - memory.availMem).coerceAtLeast(0L))
                .put("storageTotal", storageTotal)
                .put("storageAvailable", storageAvailable)
                .toString()
        } catch (_: Exception) {
            JSONObject().put("ok", false).toString()
        }
    }

    @Suppress("DEPRECATION")
    private fun hasUsageAccessNow(): Boolean {
        return try {
            val appOps = getSystemService(APP_OPS_SERVICE) as AppOpsManager
            appOps.checkOpNoThrow(
                AppOpsManager.OPSTR_GET_USAGE_STATS,
                Process.myUid(),
                packageName
            ) == AppOpsManager.MODE_ALLOWED
        } catch (_: Exception) {
            false
        }
    }

    private fun usageStatsJson(): String {
        if (!hasUsageAccessNow()) {
            return JSONObject().put("authorized", false).put("apps", JSONArray()).toString()
        }
        return try {
            val usageManager = getSystemService(USAGE_STATS_SERVICE) as UsageStatsManager
            val endTime = System.currentTimeMillis()
            val startTime = endTime - 7L * 24L * 60L * 60L * 1000L
            val totals = HashMap<String, Long>()
            usageManager.queryUsageStats(UsageStatsManager.INTERVAL_DAILY, startTime, endTime)
                .forEach { stat ->
                    if (stat.packageName != packageName && stat.totalTimeInForeground > 0L) {
                        totals[stat.packageName] = (totals[stat.packageName] ?: 0L) + stat.totalTimeInForeground
                    }
                }

            val apps = JSONArray()
            totals.entries
                .filter { it.value >= 60_000L }
                .sortedByDescending { it.value }
                .take(20)
                .forEach { entry ->
                    val launchIntent = packageManager.getLaunchIntentForPackage(entry.key)
                    if (launchIntent != null) {
                        val label = try {
                            packageManager.getApplicationLabel(packageManager.getApplicationInfo(entry.key, 0)).toString()
                        } catch (_: Exception) {
                            entry.key
                        }
                        apps.put(
                            JSONObject()
                                .put("packageName", entry.key)
                                .put("name", label)
                                .put("millis", entry.value)
                        )
                    }
                }
            JSONObject()
                .put("authorized", true)
                .put("periodDays", 7)
                .put("apps", apps)
                .toString()
        } catch (_: Exception) {
            JSONObject().put("authorized", false).put("apps", JSONArray()).toString()
        }
    }


    private fun systemInfoJson(): String {
        val cpu = try {
            if (Build.VERSION.SDK_INT >= 31 && Build.SOC_MODEL.isNotBlank()) Build.SOC_MODEL
            else java.io.File("/proc/cpuinfo").useLines { lines ->
                lines.firstOrNull { it.startsWith("model name", true) || it.startsWith("Hardware", true) || it.startsWith("Processor", true) }
                    ?.substringAfter(":")?.trim()
            } ?: Build.HARDWARE
        } catch (_: Exception) { Build.HARDWARE }
        val temperature = try {
            val battery = registerReceiver(null, android.content.IntentFilter(Intent.ACTION_BATTERY_CHANGED))
            val raw = battery?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, -1) ?: -1
            if (raw >= 0) raw / 10.0 else null
        } catch (_: Exception) { null }
        return JSONObject()
            .put("manufacturer", Build.MANUFACTURER)
            .put("model", Build.MODEL)
            .put("device", Build.DEVICE)
            .put("android", Build.VERSION.RELEASE)
            .put("sdk", Build.VERSION.SDK_INT)
            .put("cpu", cpu)
            .put("hardware", Build.HARDWARE)
            .put("abi", Build.SUPPORTED_ABIS.firstOrNull() ?: "desconhecida")
            .put("batteryTempC", temperature ?: JSONObject.NULL)
            .toString()
    }

    private fun probeRootAccess(): Pair<Boolean, String> {
        var process: java.lang.Process? = null
        return try {
            process = ProcessBuilder("su", "-c", "id")
                .redirectErrorStream(true)
                .start()
            val completed = process.waitFor(5, TimeUnit.SECONDS)
            if (!completed) {
                process.destroyForcibly()
                false to "O teste de root não respondeu em 5 segundos. Verifique o gerenciador de root."
            } else {
                val output = process.inputStream.bufferedReader().use { it.readText() }.trim()
                val allowed = process.exitValue() == 0 && output.contains("uid=0")
                if (allowed) true to "Acesso root confirmado. O comando de diagnóstico retornou uid=0."
                else false to "Root não autorizado ou indisponível. Detalhe: ${output.take(180).ifBlank { "sem saída" }}"
            }
        } catch (_: Exception) {
            process?.destroyForcibly()
            false to "Não foi possível executar su. Root pode não estar instalado neste dispositivo."
        }
    }

    private inner class X1Bridge {
        @JavascriptInterface
        fun openExternal(url: String): Boolean = this@MainActivity.openExternal(url)

        @JavascriptInterface
        fun getInstalledApps(): String = installedAppsJson()

        @JavascriptInterface
        fun launchApp(packageName: String): Boolean {
            val launch = try {
                packageManager.getLaunchIntentForPackage(packageName) ?: return false
            } catch (_: Exception) {
                return false
            }
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

            runOnUiThread {
                if (!::webView.isInitialized || isFinishing || isDestroyed) {
                    try { startActivity(launch) } catch (_: Exception) { }
                    return@runOnUiThread
                }
                val script = "(function(){try{var a=JSON.parse(localStorage.getItem('x1Profiles')||'{}');var p=a[${org.json.JSONObject.quote(packageName)}]||{};return {resolution:String(p.resolution||'1080p'),autoResolution:p.autoResolution===true};}catch(e){return {resolution:'1080p',autoResolution:false};}})()"
                webView.evaluateJavascript(script) { rawProfile ->
                    val profile = try { org.json.JSONObject(rawProfile ?: "{}") } catch (_: Exception) { org.json.JSONObject() }
                    val auto = profile.optBoolean("autoResolution", false)
                    val resolution = profile.optString("resolution", "1080p")
                    if (!auto) {
                        try { startActivity(launch) } catch (_: Exception) {
                            showResolutionToast("Não foi possível abrir este aplicativo.")
                        }
                    } else {
                        showResolutionToast("Verificando ADB e preparando a resolução…")
                        Thread({
                            val resultMessage = try {
                                applyResolutionForLaunch(packageName, resolution)
                            } catch (e: Exception) {
                                "Não foi possível aplicar a resolução: ${e.message?.take(180) ?: "falha na conexão ADB"}. O app será aberto sem essa alteração."
                            }
                            runOnUiThread {
                                try {
                                    startActivity(launch)
                                    showResolutionToast(resultMessage)
                                } catch (_: Exception) {
                                    Thread({
                                        try { restoreOriginalResolutionBlocking() } catch (_: Exception) { }
                                    }, "X1-resolution-launch-rollback").start()
                                    showResolutionToast("Não foi possível abrir o aplicativo; a restauração será tentada.")
                                }
                            }
                        }, "X1-resolution-launch").start()
                    }
                }
            }
            return true
        }

        @JavascriptInterface
        fun getDeviceStats(): String = deviceStatsJson()

        @JavascriptInterface
        fun getSystemInfo(): String = systemInfoJson()

        @JavascriptInterface
        fun getAdbPairingState(): String = adbPairingStateJson()

        @JavascriptInterface
        fun forgetAdbPairingState(): Boolean {
            clearAdbPairingState()
            return true
        }

        @JavascriptInterface
        fun restoreOriginalResolution() {
            Thread({
                try {
                    showResolutionToast(restoreOriginalResolutionBlocking())
                } catch (e: Exception) {
                    showResolutionToast("Não foi possível restaurar a resolução: ${e.message?.take(160) ?: "ADB indisponível"}.")
                }
            }, "X1-resolution-manual-restore").start()
        }

        @JavascriptInterface
        fun startAutomaticAdbPairing() {
            runOnUiThread { startAutomaticAdbPairingNotification() }
        }

        @JavascriptInterface
        fun pairWirelessDebugging(hostInput: String, pairPort: Int, pairingCode: String, connectPort: Int) {
            val host = hostInput.trim()
            if (!host.matches(Regex("^[0-9a-fA-F:.]+$")) || host.length > 64 ||
                pairPort !in 1..65535 ||
                !pairingCode.matches(Regex("^[0-9]{6}$")) ||
                (connectPort != 0 && connectPort !in 1..65535)
            ) {
                reportAdbPairResult(false, "Confira o IP, a porta de pareamento (1–65535) e o código de 6 dígitos.", false)
                return
            }

            startAdbOperation {
                val keyProvider = adbKeyProvider()
                val pairing = AdbClient.pairTls(
                    host = host,
                    port = pairPort,
                    pairingCode = pairingCode,
                    keyProvider = keyProvider,
                    connectTimeoutMs = 10_000
                )

                if (pairing.isFailure) {
                    val detail = pairing.exceptionOrNull()?.message?.take(120)
                    return@startAdbOperation AdbUiResult(
                        false,
                        "Pareamento recusado ou expirado. Confira o código e a porta de pareamento.${detail?.let { " Detalhe: $it" } ?: ""}"
                    )
                }

                // Persist only the pairing state. A successful pairing does not mean
                // that an active ADB shell connection will survive leaving the screen.
                saveAdbPairingState(host)
                var message = "Pareamento ADB concluído."
                var connected = false

                if (connectPort in 1..65535) {
                    try {
                        val shellResult = AdbClient.connectTls(
                            host = host,
                            port = connectPort,
                            keyProvider = keyProvider,
                            handshakeTimeoutMs = 20_000L
                        ).use { client ->
                            client.shell("getprop ro.product.model")
                        }

                        if (shellResult.isSuccess) {
                            connected = true
                            val model = shellResult.stdoutText.trim()
                            message += if (model.isNotBlank()) " Conexão confirmada: $model." else " Conexão confirmada."
                        } else {
                            message += " O pareamento foi feito, mas o teste ADB falhou: ${shellResult.stderrText.trim().take(100).ifBlank { "comando recusado" }}."
                        }
                    } catch (e: Exception) {
                        message += " O pareamento foi feito, mas não conectou na porta informada. Use a porta de conexão da tela principal de Depuração sem fio. ${e.message?.take(100) ?: ""}"
                    }
                } else {
                    message += " Agora informe a porta de conexão mostrada na tela principal de Depuração sem fio e toque em Conectar."
                }

                AdbUiResult(true, message, connected)
            }
        }

        @JavascriptInterface
        fun connectWirelessDebugging(hostInput: String, connectPort: Int) {
            val host = hostInput.trim()
            if (!host.matches(Regex("^[0-9a-fA-F:.]+$")) || host.length > 64 || connectPort !in 1..65535) {
                reportAdbPairResult(false, "Informe um IP válido e a porta de conexão (1–65535).", false)
                return
            }

            startAdbOperation {
                val shellResult = AdbClient.connectTls(
                    host = host,
                    port = connectPort,
                    keyProvider = adbKeyProvider(),
                    handshakeTimeoutMs = 20_000L
                ).use { client ->
                    client.shell("getprop ro.product.model")
                }

                if (!shellResult.isSuccess) {
                    AdbUiResult(
                        false,
                        "A conexão foi aberta, mas o teste ADB falhou: ${shellResult.stderrText.trim().take(120).ifBlank { "comando recusado" }}."
                    )
                } else {
                    saveAdbPairingState(host, connectPort)
                    val model = shellResult.stdoutText.trim()
                    AdbUiResult(
                        true,
                        if (model.isNotBlank()) "Conectado por ADB: $model." else "Conexão ADB confirmada.",
                        true
                    )
                }
            }
        }

        @JavascriptInterface
        fun openDeveloperSettings(): Boolean {
            return try {
                startActivity(Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                true
            } catch (_: Exception) {
                false
            }
        }

        @JavascriptInterface
        fun hasUsageAccess(): Boolean = hasUsageAccessNow()

        @JavascriptInterface
        fun openUsageAccessSettings(): Boolean {
            return try {
                startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                true
            } catch (_: Exception) {
                false
            }
        }

        @JavascriptInterface
        fun getUsageStats(): String = usageStatsJson()

        @JavascriptInterface
        fun openSystemSettings(section: String): Boolean {
            val intent = when (section) {
                "battery" -> Intent(Settings.ACTION_BATTERY_SAVER_SETTINGS)
                "wifi" -> Intent(Settings.ACTION_WIFI_SETTINGS)
                "storage" -> Intent(Settings.ACTION_INTERNAL_STORAGE_SETTINGS)
                "app" -> Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
                else -> return false
            }.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            return try {
                startActivity(intent)
                true
            } catch (_: Exception) {
                try {
                    startActivity(Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    true
                } catch (_: Exception) {
                    false
                }
            }
        }

        @JavascriptInterface
        fun checkRoot() {
            Thread {
                val (hasRoot, message) = probeRootAccess()
                runOnUiThread {
                    if (::webView.isInitialized) {
                        val js = "window.onX1RootCheck && window.onX1RootCheck($hasRoot, ${JSONObject.quote(message)});"
                        webView.evaluateJavascript(js, null)
                    }
                }
            }.start()
        }
    }

    private fun reportAdbPairResult(success: Boolean, message: String, connected: Boolean) {
        runOnUiThread {
            if (!::webView.isInitialized || isFinishing || isDestroyed) return@runOnUiThread
            val js = "window.onX1AdbPairResult && window.onX1AdbPairResult($success, ${JSONObject.quote(message)}, $connected);"
            webView.evaluateJavascript(js, null)
        }
    }

    override fun onResume() {
        super.onResume()
        if (::webView.isInitialized) {
            webView.evaluateJavascript("window.x1RefreshAdvanced && window.x1RefreshAdvanced();", null)
            webView.evaluateJavascript("window.x1RefreshAdbPairingState && window.x1RefreshAdbPairingState();", null)
        }
        restoreResolutionAfterReturnIfNeeded()
    }

    @Deprecated("Deprecated in Android API")
    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        fileChooserCallback?.onReceiveValue(null)
        fileChooserCallback = null
        if (::webView.isInitialized) webView.destroy()
        super.onDestroy()
    }
}
