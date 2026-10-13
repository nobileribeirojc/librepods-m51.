# Auditoria de causa-raiz — AirPods Pro 3 / Galaxy M51 (sem root)

**Objetivo:** parar de produzir APKs sucessivos sem evidência. Esta branch é **código e testes**, não uma versão para instalar. O aplicativo base v8 na branch `main` continua intacto. O usuário já testou oito versões e o CAPod exibe as três baterias no mesmo aparelho.

## Evidências do código reconstruído, não apenas suposições

Fonte: v4 original em ZIP + scripts v5, v6, patch v7 e script v8, reconstruídos no run [38454271084](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38454271084) (sem APK).

1. **O fluxo BLE público da v8 quase nunca chegava à tela principal.** `BLEManager.processScanResult` obtém dados do anúncio Apple, executa `PublicProximity.frame/decode` e notifica `onNearbyProximityAdvertisement` quando não tem IRK para autenticar o endereço. Entretanto, `AirPodsService.onNearbyProximityAdvertisement` só enviava bateria para `receiveManuallySelectedBleBattery`: sem escolher um endereço no diagnóstico (`manualBleAddress`), nada chegava ao `BatteryView`. Os caminhos `onBatteryChanged` / `onBroadcastFromNewAddress` eram usados para endereços autenticados e dependiam de IRK. Isto é um bloqueio real de lógica, **não** uma prova de que o rádio BLE falha.

2. **O indicador de áudio estava sujeito a estado desatualizado.** `M51ConnectionStatus.kt` exigia correspondência com `settings.mac_address` quando existisse; um valor salvo antigo mascarava um AirPods identificado e conectado por A2DP/HFP. A consulta a perfis também era assíncrona e atualizava em momentos limitados. A ação de marcar a caixa `Alternativa experimental CAPod` é apenas uma variável Compose até clicar em **Testar conexão dos AirPods**. A alteração visual ao retornar à tela inicial não demonstrava que o socket L2CAP havia sido trocado.

3. **O app tentava BR/EDR L2CAP automaticamente no Android 12.** `AirPodsService` contém chamadas automáticas de `connectToSocket` durante a inicialização, evento de conexão ou atualização BLE autenticada. Na ausência de comunicação AACP, isso gera avisos `Unable to Connect` e atrapalha o diagnóstico da bateria, que funciona por anúncios públicos BLE. O novo guard impede essas tentativas **automáticas** em API 31/32; o teste L2CAP iniciado pelo usuário segue disponível.

4. **O decodificador por si só não é prova de sucesso físico.** `PublicProximity` reconhece Continuity `0x07/25`, prefixo `0x01`, modelo `0x2720` (AirPods Pro 3), baterias em nibbles esquerdo/direito/estojo e descarte dos códigos desconhecidos. Os testes de v7 usam quadros **sintéticos**, não anúncios capturados no M51. Os três valores ainda dependem da efetiva entrega de anúncios e da atualização da tela.

5. **O scanner pode ter problema específico no Samsung.** `BLEManager` usa `ScanCallback`, `setReportDelay(0L)` e filtro manufacturer Apple; há um botão para testar busca sem filtro. Porém, sem os contadores reais do M51 não é correto culpar exclusivamente hardware offload, filtro, permissões, ou formato de pacote.

## Comparação concreta com três fontes públicas

- [CAPod — AirPodsPro3.kt](https://github.com/d4rken-org/capod/blob/main/app/src/main/java/eu/darken/capod/pods/core/apple/ble/devices/airpods/AirPodsPro3.kt) usa o modelo `0x2720`, histórico de anúncios e bateria do estojo. [DualApplePods.kt](https://github.com/d4rken-org/capod/blob/main/app/src/main/java/eu/darken/capod/pods/core/apple/ble/devices/DualApplePods.kt) decodifica nibbles da bateria e estado de carga. [BleScanner.kt](https://github.com/d4rken-org/capod/blob/main/app/src/main/java/eu/darken/capod/common/bluetooth/BleScanner.kt) implementa filtragem offloaded configurável, bateladas e alternativa indireta de callback. [BlePodMonitor.kt](https://github.com/d4rken-org/capod/blob/main/app/src/main/java/eu/darken/capod/monitor/core/ble/BlePodMonitor.kt) lida com cache, expiração e retomada. O fato de CAPod exibir baterias no telefone é uma evidência forte a favor de BLE, **não** de que AACP/L2CAP funcione.
- [OpenPods (Java) — PodsStatusScanCallback.java](https://github.com/adolfintel/OpenPods/blob/master/app/src/main/java/com/dosse/airpods/pods/PodsStatusScanCallback.java) mantém anúncios recentes e seleciona a fonte de RSSI mais forte; relata explicitamente a impossibilidade de provar a identidade dos anúncios sem chaves. [PodsService.java](https://github.com/adolfintel/OpenPods/blob/master/app/src/main/java/com/dosse/airpods/pods/PodsService.java) separa estado de conexão de áudio do scanner BLE. Código Java demonstra que trocar Kotlin por Java não é necessário para usar a abordagem.
- [LibrePods original](https://github.com/librepods-org/librepods) oferece AACP, porém seus ajustes internos da pilha Bluetooth não são aplicáveis a um APK comum no Galaxy M51 sem root.

**Licenças:** os repositórios públicos CAPod/OpenPods divulgam GPL-3.0 e a base do projeto M51 declara AGPL-3.0-or-later. A implementação nesta branch é independente e inspira-se em **ideias e formatos documentados**, não faz cópia direta de arquivos de terceiros. Conservar avisos/licenças dos componentes originais e revisar qualquer futura incorporação literal.

## Correções implementadas nesta branch de pesquisa

- `scripts/m51-p0-source-fixes.py`: implementa recebimento automático **explicitamente não autenticado** da bateria BLE em `AirPodsService`, sem remover o caminho manual nem confundir BLE com AACP. Usa `M51AutoBatteryPolicy.kt`, uma heurística de proximidade inspirada no OpenPods (RSSI recente, histerese de 8 dBm, validade temporal), requer existência de AirPods pareado, e expira dados sem anúncios em 15 s. Nenhuma escolha de endereço por RSSI autentica propriedade do aparelho.
- Ajusta `BatteryView.kt` para rotular corretamente dados de BLE vs AACP; `M51ConnectionStatus.kt` passa a reconhecer conexões A2DP/HFP válidas mesmo com endereço salvo antigo e reconsulta os perfis a cada 3s com a tela aberta.
- `scripts/m51-p1-l2cap-guard.py`: evita tentativas **automáticas** conhecidamente problemáticas de L2CAP no Android 12/12L; mantém os testes manuais e preserva o comportamento original em API 33+.
- Novos testes unitários determinísticos: decisões por RSSI, mudança de endereço, validade e políticas da API Android. Mantém os testes do decodificador preexistentes.

## O que NÃO está comprovado

- Ainda não existe captura BLE real do M51 demonstrando que o novo caminho exibe as três baterias.
- Ainda não se sabe se o modelo/scan filter recebe `0x2720` no dispositivo alvo, nem se a Samsung bloqueia scans em segundo plano.
- Não há evidência de que ANC/Transparência possam ser controlados por AACP neste Android sem root.
- A detecção de AirPods pelo RSSI **pode escolher um AirPods Pro 3 próximo que não é o pareado**, apesar das medidas de proximidade; a interface precisa deixar essa limitação visível. É uma prévia BLE, não identidade verificada.

## Evidência mínima pendente antes de qualquer nova instalação

**Não solicitar outro APK.** Usar o app v9 já instalado, abrir `Bateria BLE e diagnóstico (sem root)` e compartilhar **privadamente**, após aproximar e abrir o estojo, o texto do diagnóstico. Sem necessidade de trocar o socket. Observar estes números:
- `Anúncios BLE = 0`: scanner/permissão/serviço.
- `Anúncios BLE > 0`, `Anúncios Apple = 0`: anúncios Apple não entregues pelo filtro/rádio.
- `Anúncios Apple > 0`, `Mensagens de proximidade = 0`: formato, decodificação ou variação de dados.
- `Mensagens de proximidade > 0` e dispositivo `AirPods Pro 3` aparece: o gargalo provavelmente é roteamento/identificação/UI, exatamente o foco do novo patch.

Depois da inspeção desses dados, decidir se se justificam compatibilidades adicionais de scanner (offload, batelada, callback alternativo). Não fabricar números nem afirmar funcionamento no aparelho.

**Critério de saída:** código e testes aprovados pelo CI, diagnóstico físico verificável e demonstração de esquerda/direita/estojo contra o CAPod, antes de nova versão distribuída.
