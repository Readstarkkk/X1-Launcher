#!/usr/bin/env python3
"""Replace X1 Performance diagnostics with native Frame Generation controls.

Run in Termux:
  python X1_FrameGeneration_panel_patch.py

Optional project override:
  X1_PROJECT="$HOME/downloads/X1-Launcher" python X1_FrameGeneration_panel_patch.py

The patch creates timestamped backups and refuses to write if source anchors
are missing or duplicated. It does not modify the existing ADB pairing code.
"""
from __future__ import annotations

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path

DEFAULT_PROJECT = Path(os.environ.get("X1_PROJECT", "~/downloads/X1-Launcher")).expanduser()

NEW_CSS = r'''/* X1 Frame Generation: módulo de ativação e teste nativo */
.performance-hero{position:relative;overflow:hidden;margin:0 0 16px;padding:19px;border:1px solid rgba(124,58,237,.55);border-radius:20px;background:radial-gradient(ellipse at 92% 0%,rgba(37,99,235,.22),transparent 42%),linear-gradient(140deg,rgba(28,16,48,.98),rgba(5,8,20,.98));box-shadow:0 0 28px rgba(91,33,182,.13)}
.performance-hero:after{content:"";position:absolute;right:-34px;top:18px;width:120px;height:120px;border:1px solid rgba(96,165,250,.2);border-radius:50%;box-shadow:0 0 0 13px rgba(96,165,250,.035),0 0 0 28px rgba(168,85,247,.035);pointer-events:none}
.performance-kicker{font:800 9px/1.4 ui-monospace,SFMono-Regular,monospace;letter-spacing:.24em;color:#60a5fa;text-transform:uppercase}
.performance-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;position:relative;z-index:1;margin-top:8px}
.performance-heading h2{font-size:clamp(21px,4vw,29px);line-height:1.1;letter-spacing:.04em;margin:0;color:#f6f1ff}
.performance-heading p{max-width:560px;margin:8px 0 0;font-size:11px;line-height:1.55;color:#aca9c4}
.performance-badge{flex-shrink:0;border:1px solid rgba(96,165,250,.5);border-radius:999px;padding:7px 9px;background:rgba(30,64,175,.18);color:#93c5fd;font:800 9px ui-monospace,SFMono-Regular,monospace;letter-spacing:.08em}
.performance-state{display:flex;align-items:center;gap:9px;padding:11px 13px;border:1px solid rgba(96,165,250,.25);border-radius:12px;background:rgba(5,10,22,.7);color:#bfdbfe;font:700 11px ui-monospace,SFMono-Regular,monospace}
.performance-state-dot{width:7px;height:7px;border-radius:50%;background:#60a5fa;box-shadow:0 0 10px rgba(96,165,250,.8)}
.framegen-panel{padding:15px;border:1px solid rgba(96,165,250,.26);border-radius:17px;background:linear-gradient(145deg,rgba(17,13,32,.97),rgba(5,8,18,.98))}
.framegen-setting-row{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:17px 2px;border-bottom:1px solid rgba(168,85,247,.18)}
.framegen-setting-row strong{display:block;font-size:15px;color:#f3e8ff}
.framegen-setting-row p{margin:5px 0 0;color:#a8a2bd;font-size:11px;line-height:1.5}
.framegen-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:14px 0}
.framegen-metric{min-width:0;padding:13px;border:1px solid rgba(96,165,250,.2);border-radius:13px;background:rgba(8,10,22,.72)}
.framegen-metric small{display:block;color:#8e9ebd;font:700 9px ui-monospace,SFMono-Regular,monospace;letter-spacing:.08em}
.framegen-metric strong{display:block;margin-top:7px;font-size:13px;color:#f0eaff;overflow-wrap:anywhere}
.framegen-actions button{width:100%;min-height:46px;border:1px solid rgba(96,165,250,.5);border-radius:12px;background:linear-gradient(110deg,#6d28d9,#1747a6);box-shadow:0 0 20px rgba(37,99,235,.12);font-size:12px;font-weight:800}
.framegen-actions button:disabled{opacity:.55;cursor:default}
.framegen-footnote{margin:13px 1px 0;color:#9692aa;font-size:10px;line-height:1.6}
@media(max-width:390px){.x1-tab{font-size:11px}.performance-hero{padding:15px}.performance-heading{display:block}.performance-badge{display:inline-block;margin-top:10px}.framegen-grid{gap:8px}.framegen-metric{padding:10px}}'''

NEW_PAGE = '''<section id="performancePage" class="page" aria-label="X1 Frame Generation">
  <div class="performance-hero">
    <div class="performance-kicker">X1 / NATIVE MODULE 03</div>
    <div class="performance-heading"><div><h2>X1 FRAME GENERATION</h2><p>Ativação e configuração do núcleo nativo de interpolação do X1.</p></div><span class="performance-badge" id="frameGenBadge">NATIVE / CHECKING</span></div>
  </div>
  <div class="framegen-panel">
    <div class="performance-state"><span class="performance-state-dot" aria-hidden="true"></span><span id="frameGenStatus">Verificando biblioteca nativa…</span></div>
    <div class="framegen-setting-row">
      <div><strong>Ativar X1 Frame Generation</strong><p>Habilita o módulo experimental no X1 depois que a biblioteca ARM64 passa no teste interno.</p></div>
      <input class="switch" id="frameGenToggle" type="checkbox" disabled aria-label="Ativar X1 Frame Generation">
    </div>
    <div class="framegen-grid">
      <div class="framegen-metric"><small>BIBLIOTECA NATIVA</small><strong id="frameGenVersion">Verificando…</strong></div>
      <div class="framegen-metric"><small>TESTE DO NÚCLEO</small><strong id="frameGenTestResult">Não executado</strong></div>
    </div>
    <div class="framegen-actions"><button type="button" class="primary" id="frameGenRunTest">Executar teste do motor nativo</button></div>
    <p class="framegen-footnote">Limite técnico desta versão: o núcleo C++ faz mistura linear entre dois buffers RGBA de teste. Esta ativação valida e habilita o módulo no X1, mas ainda não captura a tela nem injeta frames em jogos. Captura, fluxo óptico e apresentação dos frames ainda precisam ser implementados. O ADB permanece independente, na aba X1 System.</p>
  </div>
</section>'''

NEW_JS = '''function renderFrameGenerationStatus(data){
  const available=!!(data&&data.available===true);
  const tested=!!(data&&data.selfTestPassed===true);
  const ready=available&&tested;
  const enabled=ready&&data.enabled===true;
  $('frameGenToggle').disabled=!ready;
  $('frameGenToggle').checked=enabled;
  $('frameGenBadge').textContent=ready?(enabled?'NATIVE / ACTIVE':'NATIVE / READY'):'NATIVE / UNAVAILABLE';
  $('frameGenStatus').textContent=ready?(enabled?'Núcleo nativo carregado e ativado.':'Núcleo nativo carregado; módulo desativado.'):'Biblioteca nativa ausente ou teste interno reprovado.';
  $('frameGenVersion').textContent=(data&&data.version)||'Indisponível';
  $('frameGenTestResult').textContent=tested?'PASS':(available?'FAIL':'NÃO DISPONÍVEL');
}
function refreshFrameGeneration(){
  try{
    if(!window.X1||typeof window.X1.getFrameGenerationStatus!=='function')throw new Error('bridge');
    renderFrameGenerationStatus(JSON.parse(window.X1.getFrameGenerationStatus()||'{}'));
  }catch(_){
    renderFrameGenerationStatus({available:false,selfTestPassed:false,enabled:false,version:'APK sem biblioteca nativa'});
  }
}
function setFrameGenerationEnabled(){
  const toggle=$('frameGenToggle'),requested=toggle.checked;
  try{
    if(!window.X1||typeof window.X1.setFrameGenerationEnabled!=='function')throw new Error('bridge');
    const result=JSON.parse(window.X1.setFrameGenerationEnabled(requested)||'{}');
    renderFrameGenerationStatus(result);
    if(!result.ok){toggle.checked=false;toast(result.message||'Não foi possível ativar o núcleo nativo.');return;}
    toast(requested?'Módulo X1 Frame Generation ativado.':'Módulo X1 Frame Generation desativado.');
  }catch(_){toggle.checked=false;toast('A ponte nativa do X1 não está disponível neste APK.');}
}
function runFrameGenerationTest(){
  const button=$('frameGenRunTest');
  button.disabled=true;
  button.textContent='Testando núcleo…';
  try{
    if(!window.X1||typeof window.X1.testFrameGenerationEngine!=='function')throw new Error('bridge');
    const result=JSON.parse(window.X1.testFrameGenerationEngine()||'{}');
    $('frameGenTestResult').textContent=result.ok?'PASS':(result.available?'FAIL':'NÃO DISPONÍVEL');
    $('frameGenVersion').textContent=result.version||'Indisponível';
    $('frameGenStatus').textContent=result.ok?'Teste nativo concluído com sucesso.':'Falha no teste do núcleo nativo.';
    refreshFrameGeneration();
    toast(result.message||(result.ok?'Teste do núcleo concluído.':'O núcleo nativo não passou no teste.'));
  }catch(_){
    $('frameGenTestResult').textContent='ERRO';
    $('frameGenStatus').textContent='Não foi possível acessar a biblioteca nativa.';
    toast('Ponte nativa indisponível. Gere e instale o APK atualizado.');
  }finally{
    button.disabled=false;
    button.textContent='Executar teste do motor nativo';
  }
}
function x1PageChange(pageId){'''

NATIVE_SELF_TEST = '''    fun interpolate(
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
}'''

BRIDGE_REPLACEMENT = '''        // O motor nativo é local ao processo do X1; não depende de ADB.
        private fun frameGenerationStatusJson(): JSONObject {
            val available = FrameGenerationNative.isAvailable()
            val selfTestPassed = available && FrameGenerationNative.runSelfTest()
            val preferences = this@MainActivity.getSharedPreferences(
                "x1_frame_generation",
                android.content.Context.MODE_PRIVATE
            )
            val storedEnabled = preferences.getBoolean("enabled", false)
            val enabled = storedEnabled && selfTestPassed
            if (storedEnabled && !enabled) {
                preferences.edit().putBoolean("enabled", false).apply()
            }
            return JSONObject()
                .put("ok", selfTestPassed)
                .put("available", available)
                .put("selfTestPassed", selfTestPassed)
                .put("enabled", enabled)
                .put("version", FrameGenerationNative.getVersion())
        }

        @JavascriptInterface
        fun getFrameGenerationStatus(): String = frameGenerationStatusJson().toString()

        @JavascriptInterface
        fun setFrameGenerationEnabled(enabled: Boolean): String {
            val status = frameGenerationStatusJson()
            if (enabled && !status.optBoolean("selfTestPassed", false)) {
                return status
                    .put("ok", false)
                    .put("message", "A biblioteca nativa não está disponível ou não passou no teste.")
                    .toString()
            }
            this@MainActivity.getSharedPreferences(
                "x1_frame_generation",
                android.content.Context.MODE_PRIVATE
            ).edit().putBoolean("enabled", enabled).apply()
            return frameGenerationStatusJson()
                .put("ok", true)
                .put("message", if (enabled) "Módulo experimental ativado." else "Módulo experimental desativado.")
                .toString()
        }

        @JavascriptInterface
        fun testFrameGenerationEngine(): String {
            val available = FrameGenerationNative.isAvailable()
            val passed = available && FrameGenerationNative.runSelfTest()
            return JSONObject()
                .put("ok", passed)
                .put("available", available)
                .put("selfTestPassed", passed)
                .put("version", FrameGenerationNative.getVersion())
                .put("message", if (passed) "Mistura RGBA nativa validada." else "Falha ao carregar ou executar o núcleo nativo.")
                .toString()
        }

        // Mantido para as rotinas ADB; não controla o módulo nativo.
        @JavascriptInterface
        fun getConnected(): Boolean = isAdbConnectionFresh()

        @JavascriptInterface
        fun forgetAdbPairingState(): Boolean {'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: esperado 1 ocorrência, encontrado {count}. Nenhum arquivo foi gravado.")
    return text.replace(old, new, 1)


def apply_patch(project: Path, dry_run: bool) -> None:
    html_path = project / "app/src/main/assets/index.html"
    main_path = project / "app/src/main/java/com/x1launcher/app/MainActivity.kt"
    native_path = project / "app/src/main/java/com/x1launcher/app/FrameGenerationNative.kt"
    for path in (html_path, main_path, native_path):
        if not path.is_file():
            raise RuntimeError(f"Arquivo não encontrado: {path}")

    html_original = html_path.read_text(encoding="utf-8")
    main_original = main_path.read_text(encoding="utf-8")
    native_original = native_path.read_text(encoding="utf-8")

    if 'id="frameGenToggle"' in html_original and "fun runSelfTest(): Boolean" in native_original and "fun getFrameGenerationStatus(): String" in main_original:
        print("O patch X1 Frame Generation já está aplicado. Nenhum arquivo alterado.")
        return

    html = html_original
    main = main_original
    native = native_original

    # Navigation tab: Frame Generation is local and no longer locked behind ADB.
    nav_old = '<button class="x1-tab locked" id="performanceTab" type="button" data-x1page="performancePage" aria-pressed="false" aria-label="X1 Performance bloqueado; requer ADB ativo">🔒 X1 Performance</button>'
    nav_new = '<button class="x1-tab" id="performanceTab" type="button" data-x1page="performancePage" aria-pressed="false" aria-label="X1 Frame Generation">⚡ X1 Frame Gen</button>'
    html = replace_once(html, nav_old, nav_new, "Aba X1 Performance")

    # Replace the old diagnostics/lock styling block.
    css_pattern = re.compile(r'/\* X1 Performance: console técnico preto/violeta com sinalização azul \*/[\s\S]*?(?=\n@media\(min-width:650px\))')
    html, css_count = css_pattern.subn(NEW_CSS, html, count=1)
    if css_count != 1:
        raise RuntimeError("Bloco CSS antigo não encontrado. Nenhum arquivo foi gravado.")

    # Replace only the Performance section, leaving X1 System diagnostics and ADB untouched.
    page_pattern = re.compile(r'<section id="performancePage" class="page" aria-label="X1 Performance">[\s\S]*?</section>')
    html, page_count = page_pattern.subn(NEW_PAGE, html, count=1)
    if page_count != 1:
        raise RuntimeError("Seção X1 Performance antiga não encontrada. Nenhum arquivo foi gravado.")

    # Replace ADB-gated diagnostics JavaScript with real native status/activation/test calls.
    js_pattern = re.compile(r'function x1IsAdbConnected\(\)\{[\s\S]*?\nfunction x1PageChange\(pageId\)\{')
    html, js_count = js_pattern.subn(lambda _m: NEW_JS, html, count=1)
    if js_count != 1:
        raise RuntimeError("Bloco JS de diagnóstico não encontrado. Nenhum arquivo foi gravado.")
    html = replace_once(html, "if(pageId==='performancePage')refreshPerformanceAccess();", "if(pageId==='performancePage')refreshFrameGeneration();", "Inicialização da aba")

    old_listeners = '''$("performanceOpenSystem").addEventListener("click",()=>x1PageChange("systemPage"));
$("performanceRefresh").addEventListener("click",refreshPerformanceAccess);
$("performanceBackSystem").addEventListener("click",()=>x1PageChange("systemPage"));
$("performanceBatterySettings").addEventListener("click",()=>openSystemSetting("battery"));
$("performanceStorageSettings").addEventListener("click",()=>openSystemSetting("storage"));'''
    html = replace_once(html, old_listeners, '''$("frameGenToggle").addEventListener("change",setFrameGenerationEnabled);
$("frameGenRunTest").addEventListener("click",runFrameGenerationTest);''', "Listeners do Performance")
    html = html.replace("if(typeof refreshPerformanceAccess==='function')refreshPerformanceAccess();", "")
    html = re.sub(r"(?m)^\s*setInterval\(\(\)=>\{if\(document\.visibilityState!=='hidden'\)refreshPerformanceAccess\(\)\},3000\);\s*$", "", html)

    # Make getVersion robust if a library loads but a JNI export is missing.
    get_version_old = '''        return try {
            nativeVersion()
        } catch (e: Exception) {
            "Engine error: ${e.message}"
        }'''
    get_version_new = '''        return try {
            nativeVersion()
        } catch (e: LinkageError) {
            "Engine error: ${e.message}"
        } catch (e: RuntimeException) {
            "Engine error: ${e.message}"
        }'''
    native = replace_once(native, get_version_old, get_version_new, "Tratamento de erro de nativeVersion")

    # Add deterministic self-test beside the existing interpolate method.
    native_anchor = '''    fun interpolate(
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
}'''
    native = replace_once(native, native_anchor, NATIVE_SELF_TEST, "Método interpolate")

    # Add the JavaScript bridge endpoints. Existing ADB methods remain unchanged.
    bridge_anchor = '''        // Consumido por x1IsAdbConnected() na interface Performance.
        @JavascriptInterface
        fun getConnected(): Boolean = isAdbConnectionFresh()

        @JavascriptInterface
        fun forgetAdbPairingState(): Boolean {'''
    main = replace_once(main, bridge_anchor, BRIDGE_REPLACEMENT, "Ponte X1Bridge")

    # Hard validation before writing any source.
    stale_tokens = (
        "performanceLocked", "performanceDashboard", "performanceRamValue",
        "performanceStorageValue", "performanceTempValue", "performanceGpuValue",
        "refreshPerformanceAccess", "x1IsAdbConnected", "performanceRefresh",
        "performanceBatterySettings", "performanceStorageSettings"
    )
    leftovers = [token for token in stale_tokens if token in html]
    if leftovers:
        raise RuntimeError("Restaram referências antigas na aba Performance: " + ", ".join(leftovers) + ". Nenhum arquivo foi gravado.")

    for element_id in ("frameGenBadge", "frameGenStatus", "frameGenToggle", "frameGenVersion", "frameGenTestResult", "frameGenRunTest"):
        count = html.count(f'id="{element_id}"')
        if count != 1:
            raise RuntimeError(f'id="{element_id}" aparece {count} vezes. Nenhum arquivo foi gravado.')

    for method in ("getFrameGenerationStatus", "setFrameGenerationEnabled", "testFrameGenerationEngine"):
        if f"fun {method}" not in main:
            raise RuntimeError(f"Método de ponte ausente: {method}. Nenhum arquivo foi gravado.")
    if "fun runSelfTest(): Boolean" not in native:
        raise RuntimeError("Self-test JNI ausente. Nenhum arquivo foi gravado.")
    if "fun getConnected(): Boolean = isAdbConnectionFresh()" not in main:
        raise RuntimeError("A rotina ADB foi alterada inesperadamente. Nenhum arquivo foi gravado.")

    if dry_run:
        print("DRY RUN: validações concluídas; nenhum arquivo foi gravado.")
        print(f"HTML: {len(html_original)} -> {len(html)} bytes")
        print(f"MainActivity.kt: {len(main_original)} -> {len(main)} bytes")
        print(f"FrameGenerationNative.kt: {len(native_original)} -> {len(native)} bytes")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    originals = ((html_path, html_original), (main_path, main_original), (native_path, native_original))
    backups = []
    for path, original in originals:
        backup = path.with_name(path.name + f".backup-framegen-{stamp}")
        backup.write_text(original, encoding="utf-8")
        backups.append(backup)

    # All source transformations were validated before the first source write.
    html_path.write_text(html, encoding="utf-8")
    main_path.write_text(main, encoding="utf-8")
    native_path.write_text(native, encoding="utf-8")

    print("Patch aplicado.")
    print("Arquivos atualizados:")
    print(f"  {html_path}")
    print(f"  {main_path}")
    print(f"  {native_path}")
    print("Backups criados:")
    for path in backups:
        print(f"  {path}")
    print("O pareamento ADB e a tela X1 System foram preservados.")
    print("Próximo passo: git diff --check e compilar pelo GitHub Actions.")
    print("Nota: o teste valida mistura linear RGBA via JNI; não é geração de frames em jogos.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT, help="Pasta raiz do X1-Launcher")
    parser.add_argument("--dry-run", action="store_true", help="Validar sem gravar alterações")
    args = parser.parse_args()
    try:
        apply_patch(args.project.expanduser().resolve(), args.dry_run)
        return 0
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
