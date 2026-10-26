#!/usr/bin/env python3
"""Patch X1-Launcher to add inline-notification wireless ADB pairing."""
from pathlib import Path
from datetime import datetime
import sys

ROOT = Path(sys.argv[1]).expanduser().resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
MAIN = ROOT / "app/src/main/java/com/x1launcher/app/MainActivity.kt"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"
HTML = ROOT / "app/src/main/assets/index.html"
RECEIVER = ROOT / "app/src/main/java/com/x1launcher/app/AdbPairingReceiver.kt"

for p in (MAIN, MANIFEST, HTML):
    if not p.is_file():
        raise SystemExit(f"Arquivo não encontrado: {p}\nExecute o script dentro da pasta X1-Launcher.")
if "fun startAutomaticAdbPairing()" in MAIN.read_text(encoding="utf-8") and RECEIVER.exists() and "adbNotifyPairButton" in HTML.read_text(encoding="utf-8"):
    print("A integração de notificação já parece estar instalada. Nada foi alterado.")
    raise SystemExit(0)

main = MAIN.read_text(encoding="utf-8")
manifest = MANIFEST.read_text(encoding="utf-8")
html = HTML.read_text(encoding="utf-8")

# Android notification imports.
if "import android.app.RemoteInput" not in main:
    anchor = "import android.app.Activity\n"
    if anchor not in main:
        raise SystemExit("Não encontrei o import de Activity em MainActivity.kt; arquivos não foram alterados.")
    main = main.replace(anchor, "import android.Manifest\nimport android.app.Activity\nimport android.app.Notification\nimport android.app.NotificationChannel\nimport android.app.NotificationManager\nimport android.app.PendingIntent\nimport android.app.RemoteInput\n", 1)

# State needed by the Android 13+ notification permission flow.
if "pendingAdbNotificationAfterPermission" not in main:
    anchor = "    private val adbOperationActive = java.util.concurrent.atomic.AtomicBoolean(false)\n"
    if anchor not in main:
        raise SystemExit("Não encontrei o campo adbOperationActive; arquivos não foram alterados.")
    main = main.replace(anchor, anchor + "    private var pendingAdbNotificationAfterPermission = false\n    private val adbNotificationPermissionRequest = 7901\n", 1)

# Native notification / runtime permission flow.
if "private fun postAdbPairingNotification()" not in main:
    anchor = "    override fun onCreate(savedInstanceState: Bundle?) {\n"
    block = r'''    private fun startAutomaticAdbPairingNotification() {
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

'''
    block = block.replace(r'\"', '"')
    if anchor not in main:
        raise SystemExit("Não encontrei onCreate em MainActivity.kt; arquivos não foram alterados.")
    main = main.replace(anchor, block + anchor, 1)

# JavaScript bridge endpoint for the new button.
if "fun startAutomaticAdbPairing()" not in main:
    anchor = "        @JavascriptInterface\n        fun pairWirelessDebugging(hostInput: String, pairPort: Int, pairingCode: String, connectPort: Int) {\n"
    insertion = "        @JavascriptInterface\n        fun startAutomaticAdbPairing() {\n            runOnUiThread { startAutomaticAdbPairingNotification() }\n        }\n\n"
    if anchor not in main:
        raise SystemExit("Não encontrei pairWirelessDebugging na ponte X1; arquivos não foram alterados.")
    main = main.replace(anchor, insertion + anchor, 1)

# Manifest permissions and non-exported notification receiver.
if 'android.permission.POST_NOTIFICATIONS' not in manifest:
    anchor = '    <uses-permission android:name="android.permission.INTERNET"/>'
    if anchor not in manifest:
        raise SystemExit("Não encontrei a permissão INTERNET no Manifest; arquivos não foram alterados.")
    manifest = manifest.replace(anchor, anchor + '\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>\n    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>\n    <uses-permission android:name="android.permission.CHANGE_WIFI_MULTICAST_STATE"/>', 1)
if 'android:name=".AdbPairingReceiver"' not in manifest:
    anchor = '        <activity android:name=".MainActivity"'
    if anchor not in manifest:
        raise SystemExit("Não encontrei MainActivity no Manifest; arquivos não foram alterados.")
    manifest = manifest.replace(anchor, '        <receiver android:name=".AdbPairingReceiver" android:exported="false" />\n' + anchor, 1)

# Update the ADB panel while retaining the manual form as an advanced fallback.
if 'adbNotifyPairButton' not in html:
    old_intro = '<p class="note">Ative Depuração sem fio no Android e escolha <b>Parear dispositivo com código</b>. Digite aqui o IP e a porta mostrados nessa janela, junto com o código de 6 dígitos. O aparelho e o X1 precisam estar na mesma rede Wi-Fi.</p>'
    new_intro = '''<p class="note">Ative a Depuração sem fio no Android. O modo automático permite responder ao aviso do X1 com o código de 6 dígitos, sem preencher IP ou portas.</p>
      <button type="button" class="primary" id="adbNotifyPairButton">Parear pela notificação (sem IP/porta)</button>
      <p class="note">Abra “Parear dispositivo com código” no Android. Quando o aviso do X1 aparecer, responda com o código temporário. O X1 tentará descobrir os endereços automaticamente.</p>
      <details class="adb-manual-details"><summary>Configuração manual / avançada</summary>
      <p class="note">Use o modo manual apenas se a descoberta automática não funcionar. O IP e as portas temporárias mudam e devem ser copiados da tela atual do Android.</p>'''
    if old_intro not in html:
        raise SystemExit("Não encontrei o texto inicial do painel ADB na página HTML; arquivos não foram alterados.")
    html = html.replace(old_intro, new_intro, 1)
    close_anchor = '      <button type="button" class="secondary" id="adbConnectButton">Conectar dispositivo já pareado</button>\n    </div>'
    close_replacement = '      <button type="button" class="secondary" id="adbConnectButton">Conectar dispositivo já pareado</button>\n      </details>\n    </div>'
    if close_anchor not in html:
        raise SystemExit("Não encontrei o fechamento do painel ADB na página HTML; arquivos não foram alterados.")
    html = html.replace(close_anchor, close_replacement, 1)
    event_anchor = '$("adbPairButton").addEventListener("click",adbPairRequest);$("adbConnectButton").addEventListener("click",adbConnectRequest);'
    event_replacement = '''$("adbNotifyPairButton").addEventListener("click",()=>{if(!window.X1||!window.X1.startAutomaticAdbPairing){toast("Recurso disponível no APK Android atualizado.");return}try{$("wirelessStatus").textContent="Preparando notificação de pareamento…";window.X1.startAutomaticAdbPairing()}catch(_){toast("Não foi possível preparar a notificação.")}});
'''+event_anchor
    if event_anchor not in html:
        raise SystemExit("Não encontrei os handlers de botões ADB na página HTML; arquivos não foram alterados.")
    html = html.replace(event_anchor, event_replacement, 1)
    html = html.replace(
        'O X1 oferece pareamento e conexão ADB sem fio por TLS em dispositivos Android 11+. Ative Depuração sem fio no Android e informe as portas exibidas pelo sistema.',
        'O X1 pode receber o código pela notificação e descobrir as portas ADB por mDNS, sem preenchê-las manualmente. Ative Depuração sem fio no Android 11+.'
    )
    html = html.replace(
        '1) No Android 11 ou superior, ative Opções do desenvolvedor e Depuração sem fio. 2) Toque em Parear dispositivo com código. 3) Informe aqui o mesmo IP, a porta de pareamento e o código de 6 dígitos da janela. 4) Para conectar automaticamente, informe também a porta de conexão que aparece na tela principal de Depuração sem fio. As portas de pareamento e conexão são diferentes; os dois dispositivos precisam estar na mesma rede.',
        '1) Ative Depuração sem fio. 2) Toque em Parear dispositivo com código e mantenha a janela aberta. 3) No X1, toque em Parear pela notificação. 4) Responda ao aviso do X1 com o código de 6 dígitos. O X1 tentará descobrir automaticamente IP e portas via mDNS. Se o Android não anunciar o serviço, abra Configuração manual / avançada.'
    )

receiver = r'''package com.x1launcher.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.RemoteInput
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import io.github.rhythmcache.adb.AdbClient
import io.github.rhythmcache.adb.FileKeyProvider
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

class AdbPairingReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_PAIR_WITH_CODE) return
        val code = RemoteInput.getResultsFromIntent(intent)
            ?.getCharSequence(KEY_PAIRING_CODE)
            ?.toString()
            ?.trim()
            .orEmpty()

        if (!code.matches(Regex("^[0-9]{6}$"))) {
            showStatus(context, "Código inválido", "Responda à notificação com o código atual de 6 dígitos.", true)
            return
        }

        val pending = goAsync()
        Thread({
            try {
                performPairing(context.applicationContext, code)
            } catch (e: Exception) {
                showStatus(
                    context,
                    "Falha no pareamento do X1",
                    e.message?.take(180)?.ifBlank { "Não foi possível concluir o pareamento ADB." }
                        ?: "Não foi possível concluir o pareamento ADB.",
                    true
                )
            } finally {
                pending.finish()
            }
        }, "X1-ADB-auto-pair").start()
    }

    private fun performPairing(context: Context, code: String) {
        showStatus(context, "X1 · Pareamento ADB", "Código recebido. Procurando a porta de pareamento via mDNS…", false)

        val pairService = discoverService(context, PAIRING_SERVICE_TYPE, 15_000L)
        val pairHost = pairService?.host?.hostAddress?.substringBefore("%")
        if (pairService == null || pairHost.isNullOrBlank() || pairService.port !in 1..65535) {
            showStatus(
                context,
                "Serviço de pareamento não encontrado",
                "Mantenha aberta a janela “Parear dispositivo com código” do Android, com Depuração sem fio ativa, e tente novamente. Se persistir, use Configuração manual / avançada.",
                true
            )
            return
        }

        val keyDirectory = File(context.filesDir, "adb").apply { mkdirs() }
        val keyProvider = FileKeyProvider(File(keyDirectory, "adbkey"))
        val pairResult = runBlocking {
            withTimeout(20_000L) {
                AdbClient.pairTls(
                    host = pairHost,
                    port = pairService.port,
                    pairingCode = code,
                    keyProvider = keyProvider,
                    connectTimeoutMs = 10_000
                )
            }
        }

        if (pairResult.isFailure) {
            showStatus(
                context,
                "Pareamento recusado",
                "O Android recusou o código ou ele expirou. Abra uma nova janela de pareamento e responda ao aviso do X1 imediatamente. Detalhe: ${pairResult.exceptionOrNull()?.message?.take(100).orEmpty()}",
                true
            )
            return
        }

        showStatus(context, "Pareamento concluído", "Código aceito. Procurando a porta de conexão ADB…", false)
        val connectService = discoverService(context, CONNECT_SERVICE_TYPE, 10_000L)
        val connectHost = connectService?.host?.hostAddress?.substringBefore("%")
        if (connectService == null || connectHost.isNullOrBlank() || connectService.port !in 1..65535) {
            showStatus(
                context,
                "X1 pareado",
                "Pareamento concluído. Não encontrei a porta de conexão por mDNS; o acesso foi pareado, mas talvez seja necessário conectar manualmente.",
                true
            )
            return
        }

        val shellResult = runBlocking {
            withTimeout(25_000L) {
                AdbClient.connectTls(
                    host = connectHost,
                    port = connectService.port,
                    keyProvider = keyProvider,
                    handshakeTimeoutMs = 20_000L
                ).use { client ->
                    client.shell("getprop ro.product.model")
                }
            }
        }

        if (shellResult.isSuccess) {
            val model = shellResult.stdoutText.trim().ifBlank { "dispositivo Android" }
            showStatus(context, "X1 conectado por ADB", "Pareamento e conexão concluídos com $model.", true)
        } else {
            showStatus(
                context,
                "X1 pareado",
                "O código foi aceito, mas o teste de conexão falhou: ${shellResult.stderrText.trim().take(140).ifBlank { "comando recusado" }}",
                true
            )
        }
    }

    private fun discoverService(context: Context, serviceType: String, timeoutMs: Long): NsdServiceInfo? {
        val manager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
        val latch = CountDownLatch(1)
        val found = AtomicReference<NsdServiceInfo?>(null)
        val resolving = AtomicBoolean(false)
        val listener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(serviceType: String) = Unit

            override fun onServiceFound(serviceInfo: NsdServiceInfo) {
                if (!resolving.compareAndSet(false, true)) return
                try {
                    manager.resolveService(serviceInfo, object : NsdManager.ResolveListener {
                        override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                            latch.countDown()
                        }

                        override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                            found.set(serviceInfo)
                            latch.countDown()
                        }
                    })
                } catch (_: Exception) {
                    latch.countDown()
                }
            }

            override fun onServiceLost(serviceInfo: NsdServiceInfo) = Unit
            override fun onDiscoveryStopped(serviceType: String) = Unit

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                try { manager.stopServiceDiscovery(this) } catch (_: Exception) { }
                latch.countDown()
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) = Unit
        }

        return try {
            manager.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, listener)
            latch.await(timeoutMs, TimeUnit.MILLISECONDS)
            found.get()
        } catch (_: Exception) {
            null
        } finally {
            try { manager.stopServiceDiscovery(listener) } catch (_: Exception) { }
        }
    }

    private fun showStatus(context: Context, title: String, message: String, finished: Boolean) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(
                    NOTIFICATION_CHANNEL_ID,
                    "Pareamento ADB do X1",
                    NotificationManager.IMPORTANCE_HIGH
                ).apply {
                    description = "Status do pareamento e conexão ADB do X1."
                    lockscreenVisibility = Notification.VISIBILITY_PRIVATE
                }
            )
        }

        val openIntent = PendingIntent.getActivity(
            context,
            7903,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or
                (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0)
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(context, NOTIFICATION_CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(context)
        }
        val notificationBuilder = builder
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(message)
            .setStyle(Notification.BigTextStyle().bigText(message))
            .setContentIntent(openIntent)
            .setAutoCancel(finished)
            .setOngoing(!finished)
            .setOnlyAlertOnce(true)
            .setCategory(Notification.CATEGORY_STATUS)
            .setPriority(Notification.PRIORITY_HIGH)

        if (!finished) {
            val replyIntent = Intent(context, AdbPairingReceiver::class.java).apply {
                action = ACTION_PAIR_WITH_CODE
            }
            val pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT or
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0
            val replyPendingIntent = PendingIntent.getBroadcast(context, REPLY_REQUEST_CODE, replyIntent, pendingFlags)
            val remoteInput = RemoteInput.Builder(KEY_PAIRING_CODE)
                .setLabel("Código de 6 dígitos")
                .build()
            notificationBuilder.addAction(
                Notification.Action.Builder(
                    android.R.drawable.ic_menu_send,
                    "Parear",
                    replyPendingIntent
                ).addRemoteInput(remoteInput).build()
            )
        }

        manager.notify(NOTIFICATION_ID, notificationBuilder.build())
    }

    companion object {
        const val ACTION_PAIR_WITH_CODE = "com.x1launcher.app.ACTION_PAIR_WITH_CODE"
        const val KEY_PAIRING_CODE = "x1_adb_pairing_code"
        const val NOTIFICATION_CHANNEL_ID = "x1_adb_pairing"
        const val NOTIFICATION_ID = 7107
        const val REPLY_REQUEST_CODE = 7108
        private const val PAIRING_SERVICE_TYPE = "_adb-tls-pairing._tcp."
        private const val CONNECT_SERVICE_TYPE = "_adb-tls-connect._tcp."
    }
}
'''

receiver = receiver.replace(r'\"', '"')

# Check all intended replacements before writing anything.
if 'startAutomaticAdbPairing()' not in main:
    raise SystemExit("Erro interno: ponte nativa não foi adicionada.")
if 'android:name=".AdbPairingReceiver"' not in manifest or 'POST_NOTIFICATIONS' not in manifest:
    raise SystemExit("Erro interno: Manifest não foi atualizado corretamente.")
if 'adbNotifyPairButton' not in html:
    raise SystemExit("Erro interno: botão automático não foi adicionado.")

# Back up only files about to be modified.
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
for path in (MAIN, MANIFEST, HTML):
    backup = path.with_name(path.name + f".before-adb-notification-{stamp}")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

MAIN.write_text(main, encoding="utf-8")
MANIFEST.write_text(manifest, encoding="utf-8")
HTML.write_text(html, encoding="utf-8")
RECEIVER.parent.mkdir(parents=True, exist_ok=True)
RECEIVER.write_text(receiver, encoding="utf-8")

print("Integração adicionada localmente:")
print(" - Notificação Android com campo para responder o código de 6 dígitos")
print(" - Descoberta mDNS das portas _adb-tls-pairing e _adb-tls-connect")
print(" - Conexão ADB TLS automática após o pareamento, quando a descoberta funciona")
print(" - Formulário manual preservado em Configuração manual / avançada")
print(" - Backups criados ao lado dos 3 arquivos alterados")
print("\nAgora confira: git diff --check && git status --short")
