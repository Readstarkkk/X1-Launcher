#!/usr/bin/env python3
"""Add persistent ADB pairing status UI to a local X1-Launcher checkout.

Run from the repository root or pass the repository path as the first argument.
The script validates every expected source snippet before writing any file and
creates timestamped backups for each file it changes.
"""
from __future__ import annotations

import datetime as _dt
import pathlib
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one occurrence for {label}; found {count}. No files were changed.")
    return text.replace(old, new, 1)


def main() -> int:
    root = pathlib.Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else pathlib.Path.cwd()
    root = root.resolve()

    files = {
        "main": root / "app/src/main/java/com/x1launcher/app/MainActivity.kt",
        "receiver": root / "app/src/main/java/com/x1launcher/app/AdbPairingReceiver.kt",
        "html": root / "app/src/main/assets/index.html",
    }
    for path in files.values():
        if not path.is_file():
            print(f"ERRO: não encontrei {path}", file=sys.stderr)
            print("Execute o script na raiz do repositório X1-Launcher.", file=sys.stderr)
            return 2

    main_text = files["main"].read_text(encoding="utf-8")
    receiver_text = files["receiver"].read_text(encoding="utf-8")
    html_text = files["html"].read_text(encoding="utf-8")

    # MainActivity: persistent state shared with the notification receiver.
    main_text = replace_once(
        main_text,
        '''    private fun adbKeyProvider(): FileKeyProvider {
        val keyDirectory = File(filesDir, "adb").apply { mkdirs() }
        return FileKeyProvider(File(keyDirectory, "adbkey"))
    }
''',
        '''    private fun adbKeyProvider(): FileKeyProvider {
        val keyDirectory = File(filesDir, "adb").apply { mkdirs() }
        return FileKeyProvider(File(keyDirectory, "adbkey"))
    }

    private fun adbPairingPreferences(): android.content.SharedPreferences =
        getSharedPreferences("x1_adb_pairing_state", MODE_PRIVATE)

    private fun saveAdbPairingState(host: String) {
        adbPairingPreferences().edit()
            .putBoolean("paired", true)
            .putString("host", host)
            .putLong("pairedAt", System.currentTimeMillis())
            .apply()
    }

    private fun adbPairingStateJson(): String {
        val prefs = adbPairingPreferences()
        return JSONObject()
            .put("paired", prefs.getBoolean("paired", false))
            .put("host", prefs.getString("host", "") ?: "")
            .put("pairedAt", prefs.getLong("pairedAt", 0L))
            .toString()
    }

    private fun clearAdbPairingState() {
        adbPairingPreferences().edit()
            .putBoolean("paired", false)
            .remove("host")
            .remove("pairedAt")
            .apply()
    }
''',
        "MainActivity ADB preferences helpers",
    )

    main_text = replace_once(
        main_text,
        '''        @JavascriptInterface
        fun startAutomaticAdbPairing() {
            runOnUiThread { startAutomaticAdbPairingNotification() }
        }
''',
        '''        @JavascriptInterface
        fun getAdbPairingState(): String = adbPairingStateJson()

        @JavascriptInterface
        fun forgetAdbPairingState(): Boolean {
            clearAdbPairingState()
            return true
        }

        @JavascriptInterface
        fun startAutomaticAdbPairing() {
            runOnUiThread { startAutomaticAdbPairingNotification() }
        }
''',
        "MainActivity JavaScript bridge methods",
    )

    main_text = replace_once(
        main_text,
        '''                }

                var message = "Pareamento ADB concluído."
''',
        '''                }

                // Persist only the pairing state. A successful pairing does not mean
                // that an active ADB shell connection will survive leaving the screen.
                saveAdbPairingState(host)
                var message = "Pareamento ADB concluído."
''',
        "persist manual pairing success",
    )

    main_text = replace_once(
        main_text,
        '''                } else {
                    val model = shellResult.stdoutText.trim()
                    AdbUiResult(
                        true,
                        if (model.isNotBlank()) "Conectado por ADB: $model." else "Conexão ADB confirmada.",
                        true
                    )
                }
            }
        }
''',
        '''                } else {
                    saveAdbPairingState(host)
                    val model = shellResult.stdoutText.trim()
                    AdbUiResult(
                        true,
                        if (model.isNotBlank()) "Conectado por ADB: $model." else "Conexão ADB confirmada.",
                        true
                    )
                }
            }
        }
''',
        "persist successful connect state",
    )

    main_text = replace_once(
        main_text,
        '''    override fun onResume() {
        super.onResume()
        if (::webView.isInitialized) {
            webView.evaluateJavascript("window.x1RefreshAdvanced && window.x1RefreshAdvanced();", null)
        }
    }
''',
        '''    override fun onResume() {
        super.onResume()
        if (::webView.isInitialized) {
            webView.evaluateJavascript("window.x1RefreshAdvanced && window.x1RefreshAdvanced();", null)
            webView.evaluateJavascript("window.x1RefreshAdbPairingState && window.x1RefreshAdbPairingState();", null)
        }
    }
''',
        "refresh pairing status on resume",
    )

    # Automatic pairing from Android's notification must save the same state.
    receiver_text = replace_once(
        receiver_text,
        '''        showStatus(context, "Pareamento concluído", "Código aceito. Procurando a porta de conexão ADB…", false)
''',
        '''        // Keep the UI state after the app is closed/reopened. This marks pairing,
        // not a continuously active shell connection.
        context.getSharedPreferences("x1_adb_pairing_state", Context.MODE_PRIVATE).edit()
            .putBoolean("paired", true)
            .putString("host", pairHost)
            .putLong("pairedAt", System.currentTimeMillis())
            .apply()

        showStatus(context, "Pareamento concluído", "Código aceito. Procurando a porta de conexão ADB…", false)
''',
        "persist automatic notification pairing",
    )

    # HTML: green card replacing the manual pairing form after pairing is saved.
    html_text = replace_once(
        html_text,
        '''.adb-pair-panel{margin-top:12px;padding:13px;border:1px solid rgba(168,85,247,.32);border-radius:14px;background:rgba(7,5,13,.72)}
''',
        '''.adb-pair-panel{margin-top:12px;padding:13px;border:1px solid rgba(168,85,247,.32);border-radius:14px;background:rgba(7,5,13,.72)}
.adb-paired-banner{margin-top:12px;padding:15px;border:1px solid rgba(34,197,94,.65);border-radius:14px;background:linear-gradient(125deg,rgba(20,83,45,.42),rgba(6,25,17,.92));color:#dcfce7;box-shadow:0 0 18px rgba(34,197,94,.10)}
.adb-paired-banner[hidden],.adb-pair-panel[hidden]{display:none!important}
.adb-paired-banner strong{display:block;font-size:15px;color:#86efac}
.adb-paired-banner p{font-size:12px;line-height:1.5;margin:8px 0 12px;color:#d1fae5}
.adb-paired-banner button{width:100%;min-height:42px;border:1px solid rgba(74,222,128,.42);border-radius:10px;background:rgba(20,83,45,.35);color:#dcfce7;font-weight:700}
''',
        "green ADB pairing banner CSS",
    )

    html_text = replace_once(
        html_text,
        '''    <div class="adb-pair-panel" id="adbPairPanel">
''',
        '''    <div class="adb-paired-banner" id="adbPairedBanner" hidden role="status" aria-live="polite">
      <strong>✓ Pareamento ADB ativado</strong>
      <p id="adbPairedDescription">O X1 salvou o estado do pareamento neste aplicativo.</p>
      <button type="button" id="adbForgetPairingButton">Configurar pareamento novamente</button>
    </div>
    <div class="adb-pair-panel" id="adbPairPanel">
''',
        "green ADB pairing banner markup",
    )

    html_text = replace_once(
        html_text,
        '''function setAdbBusy(busy){$('adbPairButton').disabled=busy;$('adbConnectButton').disabled=busy;}
window.onX1AdbPairResult=function(success,message,connected){setAdbBusy(false);const el=$('wirelessStatus');el.textContent=(success?'✓ ':'✕ ')+message+(connected?' Estado: conectado.':'');el.style.color=success?'#d7ffd9':'#ffd0dc';if(!success)toast(message)};
''',
        '''function setAdbBusy(busy){$('adbPairButton').disabled=busy;$('adbConnectButton').disabled=busy;}
function renderAdbPairingState(state){
 const paired=!!(state&&state.paired);
 $('adbPairedBanner').hidden=!paired;
 $('adbPairPanel').hidden=paired;
 if(!paired){$('wirelessStatus').style.color='';return;}
 const host=String(state.host||'').trim();
 $('adbPairedDescription').textContent=(host?'O pareamento deste dispositivo ('+host+') foi salvo no X1. ':'O pareamento foi salvo no X1. ')+ 'Esse estado permanece ao sair e voltar ao aplicativo. A conexão ADB ativa pode precisar ser refeita se a Depuração sem fio for desligada ou o Android reiniciar.';
 $('wirelessStatus').textContent='✓ Pareamento ADB salvo neste aplicativo.'+(host?' Dispositivo: '+host+'.':'')+' O estado da conexão ativa é separado.';
 $('wirelessStatus').style.color='#86efac';
}
window.x1RefreshAdbPairingState=function(){
 try{if(!window.X1||!window.X1.getAdbPairingState)return;renderAdbPairingState(JSON.parse(window.X1.getAdbPairingState()||'{}'));}
 catch(e){console.warn('Não foi possível consultar o estado do pareamento ADB.',e);}
};
function adbForgetPairingState(){
 try{
  if(!window.X1||!window.X1.forgetAdbPairingState){toast('Atualize o APK para alterar o estado do pareamento.');return;}
  window.X1.forgetAdbPairingState();
  renderAdbPairingState({paired:false});
  $('wirelessStatus').textContent='Estado local do pareamento removido. Isso não revoga a autorização ADB nas configurações do Android.';
  toast('Estado salvo removido.');
 }catch(e){toast('Não foi possível alterar o estado salvo.');}
}
window.onX1AdbPairResult=function(success,message,connected){setAdbBusy(false);const el=$('wirelessStatus');el.textContent=(success?'✓ ':'✕ ')+message+(connected?' Estado: conectado.':'');el.style.color=success?'#d7ffd9':'#ffd0dc';if(success&&window.x1RefreshAdbPairingState)window.x1RefreshAdbPairingState();if(!success)toast(message)};
''',
        "persistent pairing JavaScript functions",
    )

    html_text = replace_once(
        html_text,
        '''$("adbPairButton").addEventListener("click",adbPairRequest);$("adbConnectButton").addEventListener("click",adbConnectRequest);
''',
        '''$("adbPairButton").addEventListener("click",adbPairRequest);$("adbConnectButton").addEventListener("click",adbConnectRequest);$("adbForgetPairingButton").addEventListener("click",adbForgetPairingState);
''',
        "bind reset button",
    )

    html_text = replace_once(
        html_text,
        '''function initialize(){try{renderPorts();renderRail('recentRail',safeRead('x1RecentApps',[]));loadSettings();refreshInstalled()}catch(e){console.error('X1 initialization failed',e);toast('A interface carregou com limitações.')}}
''',
        '''function initialize(){try{renderPorts();renderRail('recentRail',safeRead('x1RecentApps',[]));loadSettings();refreshInstalled();if(window.x1RefreshAdbPairingState)window.x1RefreshAdbPairingState()}catch(e){console.error('X1 initialization failed',e);toast('A interface carregou com limitações.')}}
''',
        "load saved pairing status at startup",
    )

    updated = {
        "main": main_text,
        "receiver": receiver_text,
        "html": html_text,
    }
    # All transformations were validated before this point; now create backups and write.
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for key, content in updated.items():
        path = files[key]
        backup = path.with_name(path.name + f".bak-adb-pairing-{stamp}")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Atualizado: {path.relative_to(root)}")
        print(f"Backup:    {backup.relative_to(root)}")

    print("\nCorreção aplicada. O estado salvo indica PAREAMENTO, não uma conexão ADB continuamente ativa.")
    print("Agora execute: git diff --check && git diff --stat && gradle assembleDebug")
    print("Só faça commit/push após revisar o diff e confirmar que o build passou.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
