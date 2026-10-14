# LibrePods M51 — revisão da PR #4 e regressões

## Estado e decisão de entrega

Continuação do aplicativo original, applicationId `me.kavishdevar.librepods.m51test`, minSdk 31. Branch `m51-pr4-regression-audit`, derivada da PR #4 no commit `93c0d748df46303326adee4fa560231cb392ab8e`. A `main` e o trabalho da PR #4 foram preservados. Nenhuma alteração da pilha Samsung, root, troca de aplicativo ou troca de linguagem foi feita.

**Não foi gerado nem publicado APK nesta revisão.** O workflow executa `:app:testDebugUnitTest`, que compila o código Android e os testes JVM, sem `assembleDebug` ou `packageDebug`. O workflow antigo de APK foi impedido de empacotar a v8 em eventos de pull request nesta branch. Uma execução antiga intitulada “Build LibrePods M51 v8 APK” não validava os novos scripts p0–p6: a auditoria separada é a evidência correta.

## O que já estava concluído ao retomar

- PR #4: scripts v9 e p0–p6; bateria automática pública, política por RSSI, proteção contra tentativas automáticas L2CAP no Android 12, diagnóstico visível, recuperação BLE e correções de Compose.
- [Auditoria da PR #4, execução 38479204666](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38479204666): sucesso; aplicou os scripts e executou testes e `assembleDebug`. Era trabalho anterior, não um APK novo desta revisão.
- [Branch de regressões, execução 38480409462](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38480409462), commit `d32ae6b`: **43 testes, 0 falhas, 0 erros**, compilação concluída. A execução anterior `38480325102` falhou; a correção de importação já estava salva no commit seguinte. Não havia necessidade de repetir toda a investigação.
- O log `airpods_log_20261013_132454.txt` é anterior à compilação v8. Mostra falhas de ciclo de vida, início do scanner e seis exceções `read ret: -1`; não contém captura BLE utilizável para provar a leitura das três baterias. Não foi tratado como teste físico da PR #4.

## Resultado final desta retomada

[GitHub Actions 38502849542](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38502849542), código `7d8e1d5b0c86b460aa907b10a11ae1f13b9443f4`: **BUILD SUCCESSFUL; 49 testes, 0 falhas, 0 erros, 0 ignorados**. Compilação Gradle em aproximadamente 2 minutos. Os relatórios XML/HTML estão no artefato `m51-pr4-regression-test-reports` da execução. Nenhuma tarefa de empacotamento APK foi executada.

| Conjunto | Testes aprovados |
|---|---:|
| Decodificador público | 14 |
| Fluxo de bateria, histórico e expiração | 13 |
| Seleção automática | 5 |
| Recuperação do scanner | 4 |
| Política de transporte | 4 |
| Evidências e erros de transporte | 6 |
| Política da janela do estojo | 3 |
| **Total** | **49** |

As seis regressões adicionadas nesta retomada diferenciam fechamento, timeout e permissão, e validam reconhecimento de cabeçalho AACP. O teste de combinações de nibbles exercita 512 combinações de valores/orientação dentro de um teste JUnit. Não equivale a 512 testes físicos.

As correções de serviço, receivers, janela, callbacks do Android e retomada da apresentação foram compiladas; os testes JVM cobrem suas políticas e valores, não executam o ciclo de vida Android completo. Permanecem pendentes testes instrumentais e físicos. A revisão adicional fechou sockets ao destruir o serviço, removeu referências obsoletas e corrigiu a retomada BLE após encerramento do AACP.

## Causa-raiz comprovada no código e limites da conclusão

O caminho original do LibrePods privilegia endereços BLE autenticados por IRK. Sem essa chave, `BLEManager` encaminha os anúncios públicos para `onNearbyProximityAdvertisement`. Na v8 esse caminho só alimentava a tela após seleção manual. Assim, **um anúncio corretamente recebido e decodificado podia não chegar às baterias da tela principal**. A PR #4 p0 removeu esse bloqueio com seleção automática por proximidade.

Isso é uma causa-raiz de software demonstrável por inspeção. Não prova que seja a única causa no M51: entrega de anúncios pelo sistema, permissões, localização, filtros e política de energia ainda precisam de observação física. O CAPod funcionar nesse aparelho demonstra viabilidade do caminho BLE, não sucesso do canal AACP.

## Comparação de implementações efetivamente examinadas

| Aspecto | CAPod | OpenPods | LibrePods M51 revisado |
|---|---|---|---|
| Modelo Pro 3 | `0x2720` | `2720` no identificador hexadecimal | Mesmo modelo, com validação do enquadramento Continuity |
| Bateria pública | Nibbles, orientação pelo fone primário; histórico do estojo | Nibbles, orientação e sinal recente mais forte | Decodificação preservada; histórico independente por componente e endereço |
| Precisão pública | Passos de 10%; caminho privado separado | Passos de 10% | Passos de 10%; desconhecido exibido como travessão |
| Identificação | Histórico e opções de identidade/proximidade | Heurística de RSSI | RSSI com histerese; não é autenticação; seleção manual preservada |
| Busca | Filtros/offload configuráveis, lotes e alternativas de entrega | ScanCallback, filtro Apple e sinais recentes | ScanCallback, filtro Apple, fallback da PR #4 e recuperação pelo serviço |
| Controle avançado | Transporte AAP/L2CAP separado do BLE | Não oferece solução para negociação AACP do M51 | AACP original preservado; tentativa manual, sem promessa de controle |

Revisões fixas consultadas:

- [CAPod `0c209ef`](https://github.com/d4rken-org/capod/tree/0c209ef46e7b54e078e2ad2c39e87d1a78891671): `BleScanner.kt`, `ProximityPairing.kt`, `DualApplePods.kt`, `AirPodsPro3.kt`, `L2capSocketFactory.kt`, manifesto.
- [OpenPods `9cd8008`](https://github.com/adolfintel/OpenPods/tree/9cd800875f594fa6eb7325dd33d9216c476a5782): `PodsStatusScanCallback.java`, `PodsStatus.java`, `PodsService.java`, manifesto.
- [LibrePods `efccc44`](https://github.com/librepods-org/librepods/tree/efccc4499b2c1fd2ac243e975ae1f42d8e828ffd): documentação Android, protocolo e hook `l2c_fcr_hook.cpp`.

CAPod satura certos nibbles reservados acima de 10 em 100%. O M51 conserva a decisão explícita de tratá-los como desconhecidos; não existe captura do aparelho justificando mudar isso. Não se decodificam bytes criptografados como percentuais públicos.

## Correções adicionais implementadas em p7

| Defeito encontrado após a PR #4 | Correção implementada | Verificação / limite |
|---|---|---|
| `onStartCommand` recriava scanner e registros a cada início | Scanner criado uma vez em `onCreate`; início repetido é idempotente | Compilação; comportamento de serviço ainda requer aparelho |
| Bluetooth ON dependia do receptor da Activity | Receptor de Bluetooth/localização/tela pertence ao serviço; eliminado receptor duplicado da Activity | Compilação; testar com Activity fechada |
| Operações BLE vinham de threads diferentes | Início, parada e retomada encaminhados ao looper principal | Compilação; não é teste de concorrência instrumental |
| Fine location solicitado sozinho no Android 12 | Coarse + fine solicitados juntos; preflight de SCAN, CONNECT, FINE e localização ativa | Compilação; testar concessão/revogação real |
| Fallback sem filtro podia permanecer ao apagar tela | Serviço solicita modo filtrado ao apagar tela; watchdog só entra no modo sem filtro com tela interativa | Não garante entrega em segundo plano na Samsung |
| Callbacks antigos podiam atualizar estado depois de parada | Callback validado pela sessão ativa; referência invalidada antes de stopScan | Compilação; confirmar contra sistema real |
| Dados recebidos em lote podiam parecer novos | Uso de `ScanResult.timestampNanos`; rejeição de anúncios com 15 s ou mais, futuros ou fora de ordem | Regressões determinísticas |
| Pacote com bateria ausente apagava leitura recente; validade dependia de novos anúncios | Histórico independente: fones até 15 s, estojo até 30 s; temporizador expira mesmo sem pacotes | Regressões de expiração, valores desconhecidos e zero real |
| Troca de endereço podia incentivar mistura de valores | Snapshot inteiro substituído; cache nunca cruza endereços | Regressão de mudança de emissor |
| Diagnóstico continuava pedindo seleção mesmo com bateria automática | Relatório inclui fonte automática, valores, idade e decisão da política; seleção manual aparece separadamente | Compilação; cópia real pendente |
| RSSI 127 podia vencer como sinal forte | Rejeição de RSSI indisponível; memória de candidatos limitada | Teste de regressão |
| Janela poderia usar emissor diferente da bateria automática | Janela pública limitada ao endereço escolhido pelo fluxo de apresentação | Teste físico de abertura/fechamento pendente |
| Falha/fim do AACP deixava referência de socket e cache de apresentação | Limpeza condicional da conexão; fechamento ao destruir serviço; invalidação da apresentação antes de retomar BLE | Compilação; transporte real não exercitado |
| `socket closed` era classificado como timeout e quaisquer bytes contavam como AACP | Categorias distintas; contador AACP exige cabeçalho reconhecido | Regressões de classificação e cabeçalho |

A bateria BLE continua sem executar comandos de áudio. A2DP/HFP são consultados separadamente; o indicador pode usar nome como heurística se o endereço salvo estiver antigo. Esse indicador não autentica o emissor BLE. Foram preservados os controles originais, a proteção contra notificações repetidas L2CAP da PR #4 e a seleção manual.

## L2CAP: corrigível no aplicativo versus limitação de sistema

O PSM `0x1001` é de L2CAP clássico BR/EDR. `createL2capChannel` e `createInsecureL2capChannel` são APIs LE CoC e não substituem esse transporte. A alternativa interna `createInsecureL2capSocket` permanece disponível apenas para teste manual: mudar autenticação/construtor não altera a negociação feita pela pilha Samsung.

`read ret: -1` informa fechamento/falha na negociação, sem distinguir sozinho recusa do periférico, incompatibilidade de modos ou outra causa. O hook do LibrePods upstream modifica `l2c_fcr_chk_chan_modes` **no processo Bluetooth do sistema**. Um APK comum sem root não instala essa alteração na ROM. Não se atribui a causa exata ao firmware sem captura HCI/bugreport pertinente.

Correções de limpeza de sockets, classificação, interface e separação BLE/AACP foram implementadas. Não existe evidência nesta revisão de conexão AACP real no M51 nem de ANC, Transparência ou Adaptativo pelo aplicativo. O cabeçalho AACP é somente evidência do protocolo recebido, não valida cada função.

## Licenças e reprodução

CAPod e OpenPods incluem GPLv3. O arquivo LICENSE raiz do upstream LibrePods é GPLv3, enquanto arquivos Android da base M51 trazem avisos AGPLv3. Esses avisos foram preservados; não se deve resumir incorretamente toda a árvore como uma única licença sem examinar os componentes. As adições são independentes, sob AGPL-3.0-or-later; não houve cópia literal de módulos CAPod/OpenPods.

A [seção 13 da GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) e a [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html) permitem a combinação indicada sob suas condições. Uma candidata distribuída deverá acompanhar fonte correspondente, scripts e avisos preservados. A chave debug dos runners anteriores é efêmera; continuidade de assinatura ainda precisa de preparação antes de distribuição.

Reprodução: seguir `.github/workflows/audit-v8-source.yml`: extrair v4, aplicar v4.1/v5/v6/v7/v8/v9, p0–p6 e `scripts/m51-p7-battery-lifecycle.patch`; Java 17, SDK 35; executar `./gradlew :app:testDebugUnitTest`. Os fontes extraídos são uma reprodução do aplicativo existente, não um segundo projeto.

Referências Android: [permissões Bluetooth](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions), [scanner BLE](https://developer.android.com/reference/android/bluetooth/le/BluetoothLeScanner), [BLE no AOSP](https://source.android.com/docs/core/connect/bluetooth/ble). `neverForLocation` pode filtrar determinados anúncios; a base atual não o declara e mantém o requisito de localização. CAPod/OpenPods têm escolhas de manifesto diferentes; seu sucesso não justifica atribuir todas as falhas a uma única flag sem comparação física controlada.

## Validação física pendente e decisão sobre candidata

Os testes usam quadros sintéticos e relógios determinísticos. Não houve acesso físico ao M51, captura de rádio, execução instrumental de Activity/Service ou teste de economia de energia Samsung. Compilação e testes JVM não confirmam os percentuais no telefone.

Para validar uma única candidata, quando preparada: abrir o estojo perto do M51, verificar reconhecimento Pro 3 e atualização automática sem seleção manual; comparar três valores com CAPod nas mesmas condições; retirar cada fone separadamente; observar expiração do estojo; alternar Bluetooth e localização; testar tela apagada e retorno; confirmar áudio contínuo e exportação de diagnóstico. Valores não recebidos devem permanecer desconhecidos.

Não se exige uma nova instalação apenas para investigar sintomas já documentados. Se o aplicativo instalado não exporta diagnóstico, uma captura privada do CAPod ou do log de Bluetooth é útil, mas sua ausência não é fingida como teste aprovado. **O relatório antecede qualquer nova geração de APK.** A próxima etapa de dispositivo continua distinta dos testes automatizados concluídos.
