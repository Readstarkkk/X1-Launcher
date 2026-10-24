package com.x1launcher.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.view.View
import android.graphics.Color
import android.widget.Toast
import android.graphics.drawable.Drawable
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

class MainActivity : Activity() {
    private lateinit var webView: WebView
    private var fileChooserCallback: ValueCallback<Array<Uri>>? = null
    private val imagePickerRequest = 4317

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

    private inner class X1Bridge {
        @JavascriptInterface
        fun openExternal(url: String): Boolean = this@MainActivity.openExternal(url)

        @JavascriptInterface
        fun getInstalledApps(): String = installedAppsJson()

        @JavascriptInterface
        fun launchApp(packageName: String): Boolean {
            return try {
                val launch = packageManager.getLaunchIntentForPackage(packageName) ?: return false
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                startActivity(launch)
                true
            } catch (_: Exception) {
                false
            }
        }
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
