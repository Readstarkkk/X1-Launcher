X1-Launcher

Um launcher Android focado em controle, conectividade ADB e otimização de jogos.

O X1-Launcher é um projeto Android em desenvolvimento que busca facilitar o gerenciamento de dispositivos e explorar recursos de controle e otimização por meio do Android Debug Bridge (ADB).

O objetivo é reunir ferramentas úteis em uma interface simples, com foco em jogos, configurações de exibição e automação de tarefas compatíveis com as permissões do Android.

«Status: Em desenvolvimento. Os recursos descritos como planejados ainda precisam ser implementados e testados.»

---

🎯 Visão do projeto

O X1-Launcher pretende evoluir para uma central de ferramentas Android com quatro áreas principais:

- ADB simplificado: facilitar o pareamento e a conexão por depuração sem fio.
- Controle de resolução: permitir selecionar resoluções de exibição e restaurar a configuração original.
- Otimização de jogos: oferecer ferramentas para experimentar ajustes que possam melhorar o desempenho.
- Pesquisa gráfica: investigar técnicas de upscaling e reconstrução de imagem para dispositivos móveis.

O projeto prioriza soluções que possam ser desenvolvidas e testadas diretamente no Android, sem depender obrigatoriamente de um computador.

✨ Funcionalidades e planos

1. Conexão ADB

O projeto possui uma interface para trabalhar com ADB por depuração sem fio.

A interface atual contempla campos para:

- Endereço IP do dispositivo.
- Porta de pareamento.
- Código de pareamento.
- Porta de conexão.

Próximos objetivos:

- Simplificar o fluxo de pareamento.
- Melhorar mensagens de erro e diagnóstico.
- Investigar notificações para orientar o usuário durante a autorização e a conexão.
- Automatizar etapas que sejam permitidas pelo Android.

A conexão ADB depende da configuração do dispositivo, das autorizações e das restrições da versão do Android.

2. Controle de resolução

Uma das próximas funcionalidades planejadas é permitir controlar o tamanho lógico da tela por meio de comandos ADB.

A interface poderá oferecer opções de resolução, por exemplo:

- Original.
- 900p.
- 720p.
- 540p.

As opções finais deverão respeitar a proporção da tela do dispositivo.

Também está planejado um botão para restaurar o tamanho padrão.

Observação: a alteração feita com "adb shell wm size" normalmente afeta a exibição do sistema inteiro. Ela não configura diretamente a resolução interna de renderização de cada jogo.

3. Otimização de jogos

O objetivo é investigar ajustes que possam reduzir a carga gráfica e melhorar a experiência em jogos compatíveis.

As possibilidades incluem:

- Alteração da resolução de exibição.
- Consulta de informações do dispositivo.
- Ferramentas de diagnóstico por ADB.
- Comparação de desempenho antes e depois dos ajustes.

O ganho de FPS depende do jogo, da GPU, da CPU e dos limites térmicos do dispositivo. Nenhuma melhoria é garantida.

4. Pesquisa de upscaling gráfico

O projeto também pretende investigar técnicas de ampliação de imagem e reconstrução de detalhes.

A ideia surgiu da possibilidade de criar uma experiência inspirada em tecnologias como DLSS, mas adaptada às limitações do Android.

As linhas de pesquisa incluem:

- Upscaling espacial.
- Filtros gráficos.
- Técnicas de super-resolução com modelos de IA.
- Avaliação de desempenho em GPUs móveis.

Esses recursos são experimentais e não fazem parte de uma implementação de DLSS da NVIDIA. A aplicação de upscaling em jogos externos também depende de como a imagem pode ser obtida e processada no Android.

---

🛠️ Tecnologias

O projeto utiliza ou prevê utilizar:

Tecnologia| Finalidade
Kotlin| Lógica principal do aplicativo
Android SDK| Integração com o sistema Android
WebView| Interface baseada em tecnologias web
HTML, CSS e JavaScript| Elementos da interface
ADB| Comunicação e execução de operações autorizadas
Gradle| Compilação do aplicativo
GitHub Actions| Automação de builds, conforme configurada

A implementação final de cada recurso dependerá da compatibilidade entre as bibliotecas, o Android e o hardware utilizado.

📱 Compatibilidade

O desenvolvimento e os testes incluem um dispositivo Samsung Galaxy A23 5G com Android 14.

A compatibilidade com outros aparelhos, versões do Android e fabricantes ainda precisa ser verificada.

Algumas operações exigem que a depuração sem fio esteja ativada e que o dispositivo tenha autorizado a conexão ADB.

O X1-Launcher não deve ser considerado um aplicativo com acesso root apenas por utilizar ADB.

🔐 Privacidade e permissões

O X1-Launcher deve solicitar somente as permissões necessárias às funcionalidades utilizadas.

O acesso ADB pode permitir executar comandos com os privilégios da interface de shell do Android, dentro das restrições do sistema. Por isso, o usuário deve autorizar apenas dispositivos e operações confiáveis.

A depuração sem fio deve ser desativada quando não for mais necessária, especialmente em redes públicas.

📦 Compilação

O projeto utiliza Gradle e Kotlin para Android.

Para compilar uma versão de depuração em um ambiente com as ferramentas Android necessárias:

gradle assembleDebug

O APK de depuração costuma ser gerado em:

app/build/outputs/apk/debug/app-debug.apk

O caminho e o resultado devem ser verificados após cada build.

Versões públicas estáveis devem ser testadas e publicadas como Releases no GitHub. Uma versão de depuração não deve ser apresentada como versão estável sem validação.

🗺️ Roadmap

- [x] Criar a estrutura inicial do aplicativo.
- [x] Desenvolver uma interface inicial para conexão ADB.
- [ ] Diagnosticar e estabilizar o pareamento ADB.
- [ ] Simplificar a experiência de autorização e conexão.
- [ ] Implementar seleção de resolução.
- [ ] Implementar restauração da resolução padrão.
- [ ] Criar ferramentas de diagnóstico de desempenho.
- [ ] Pesquisar técnicas de upscaling para Android.
- [ ] Testar as funcionalidades em diferentes dispositivos.
- [ ] Preparar uma Release pública testada.

Os itens marcados como concluídos correspondem à estrutura e à interface inicial do projeto, não necessariamente a um funcionamento validado em todos os cenários.

📄 Licença

O X1-Launcher pretende utilizar uma licença proprietária própria, denominada X1-Launcher Proprietary License (XPL).

A proposta é permitir o uso pessoal e o compartilhamento gratuito do APK original e não modificado, sob condições específicas, enquanto restringe a reutilização do código-fonte, a publicação de versões modificadas e a redistribuição comercial sem autorização.

Consulte o arquivo "LICENSE" para conhecer os termos aplicáveis.

Atenção: a licença deve estar finalizada e incluída no repositório antes de se afirmar que essa versão dos termos está oficialmente em vigor. Bibliotecas e outros componentes de terceiros permanecem sujeitos às respectivas licenças.

---

🤝 Contribuições

Contribuições, relatórios de bugs e sugestões podem ajudar na evolução do projeto.

Antes de reutilizar ou redistribuir o código, consulte a licença vigente e solicite autorização quando necessário.

📌 Aviso

O X1-Launcher é um projeto em desenvolvimento. Recursos planejados podem mudar conforme os testes, as limitações do Android e a disponibilidade de soluções tecnicamente viáveis.

O projeto não é afiliado à NVIDIA e não implementa oficialmente o DLSS.