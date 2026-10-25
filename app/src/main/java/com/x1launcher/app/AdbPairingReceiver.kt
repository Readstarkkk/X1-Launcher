package com.x1launcher.app

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
