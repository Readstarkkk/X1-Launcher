# X1 Launcher — projeto Android WebView

Este projeto transforma a interface HTML/CSS/JavaScript do protótipo Python em um app Android que abre a interface localmente dentro de uma WebView. O servidor Python não é necessário dentro do APK.

## Gerar APK
1. Extraia a pasta `X1Launcher-WebView.zip`.
2. Abra a pasta `X1Launcher-WebView` no Android Studio em um computador, ou importe-a em um serviço de build Android compatível com projetos Gradle.
3. Aguarde a sincronização Gradle com JDK 17.
4. Use **Build > Build APK(s)**.
5. O APK de debug normalmente fica em `app/build/outputs/apk/debug/app-debug.apk`.

## Observações
- Este é um projeto inicial de interface. Os cards de aplicativos e a loja são demonstrativos; ainda não iniciam programas de PC.
- Para gerar APK, o ambiente de compilação precisa baixar o Android Gradle Plugin e o SDK correspondente.
- A WebView carrega `app/src/main/assets/index.html`; edite esse arquivo para mudar a interface.
