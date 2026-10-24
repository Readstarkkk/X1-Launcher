package com.x1launcher.app

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.view.View
import android.graphics.Color
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var webView: WebView

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
        webView.webChromeClient = WebChromeClient()
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
            Toast.makeText(this, "Não foi possível abrir o link.", Toast.LENGTH_LONG).show()
            false
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
            val launchIntent = pm.getLaunchIntentForPackage(pkg) ?: return@mapNotNull null
            // O launcher lista apps iniciáveis instalados pelo usuário; assim, jogos com categoria incorreta também aparecem.
            if ((info.flags and ApplicationInfo.FLAG_SYSTEM) != 0 && (info.flags and ApplicationInfo.FLAG_UPDATED_SYSTEM_APP) == 0) return@mapNotNull null
            val label = runCatching { pm.getApplicationLabel(info).toString() }.getOrDefault(pkg)
            val isGame = (Build.VERSION.SDK_INT >= 26 && info.category == ApplicationInfo.CATEGORY_GAME) ||
                (label + " " + pkg).contains(Regex("roblox|minecraft|free.?fire|pubg|fortnite|genshin|asphalt|call.?of.?duty|codm|brawl|clash|stumble|among.?us|game|jogo", RegexOption.IGNORE_CASE))
            JSONObject().put("name", label).put("packageName", pkg).put("isGame", isGame)
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
}
