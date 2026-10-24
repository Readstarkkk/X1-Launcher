package com.x1launcher.app

import android.app.Activity
import android.os.Bundle
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import android.view.View
import android.graphics.Color

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        window.statusBarColor = Color.rgb(8, 6, 15)
        window.navigationBarColor = Color.rgb(8, 6, 15)
        window.decorView.systemUiVisibility = 0

        val webView = WebView(this)
        webView.setBackgroundColor(Color.rgb(8, 6, 15))
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()

        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.allowFileAccess = true
        webView.settings.allowContentAccess = true

        setContentView(webView)
        webView.loadUrl("file:///android_asset/index.html")
    }
}
