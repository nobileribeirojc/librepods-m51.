> Continuacao fisica de 16/10/2026: veja [HCI e candidato p9](M51-PHYSICAL-HCI-2026-10-16.md). Houve leitura das tres baterias em replay controlado; 41 testes e CI Android passaram no commit608fddf. O binario p9 ainda nao foi instalado no aparelho. O historico abaixo foi preservado.

# REA + Codex: investigação reprodutível do LibrePods M51

**Alvo:** Samsung Galaxy M51 (SM-M515F), Android 12/API 31, AirPods Pro 3, sem root.
**Repositório existente:** `nobileribeirojc/librepods-m51.` (o ponto final faz parte do nome do repo).
**Branch de trabalho:** `m51-root-cause-audit`; **PR:** #4. Não modificar `main` e não fazer merge automático.

## Status verificável (15/out/2026)

- O CI da PR #4, run `38479204666`, passou compilação e testes JVM após aplicar os scripts p0-p6.
- O CAPod já mostrou esquerda/direita/estojo no MESMO M51; isso prova que o caminho BLE público merece prioridade, **não** que o canal AACP funciona.
- A v8 originalmente exigia selecionar um endereço BLE manualmente antes de a bateria chegar à tela principal. p0 corrige o roteamento usando uma heurística **não autenticada** de proximidade.
- A comunicação L2CAP clássica/AACP falhou no aparelho com `read ret: -1`; esse erro sozinho não identifica a causa física ou prova timeout.
- **Nova hipótese de falha encontrada por revisão estática:** ao acionar fallback do filtro Apple para busca sem filtro, `startScanning()` poderia registrar outro `ScanCallback` sem remover o anterior. `scripts/m51-p7-single-scanner.py` impede isso; conferir a compilação/CI e validar no aparelho.
- Ainda **não existe** evidência física de que a PR #4 mostre as três baterias ou pausa por retirada.

## Configuração do REA, no ambiente que executa o Codex

Use exclusivamente o [REA oficial](https://rea.tools/) / [morluto/rea](https://github.com/morluto/rea). Exige Node.js 22.19+ (ou versão oficial suportada), npm e, para APK, JADX headless + JDK; para usar o celular, ADB. No terminal do ambiente Codex:

```bash
node --version
npx rea-agents@latest setup
```

O setup é interativo: **mostrar o plano e obter aprovação antes de alterar configuração**, escolher Codex como cliente, reiniciar o agente e verificar a conexão MCP/REA. Não executar downloads ou um APK de origem desconhecida às cegas; não remover proteções do sistema. A instalação REA + Codex **não foi realizada pelo autor deste guia**. Só declarar ferramentas conectadas após confirmação real do agente.

## Investigação solicitada ao Codex com REA

1. **Preserve e reconstrua o código que já existe.** Inspecione `README.md`, `docs/M51-ROOT-CAUSE-AUDIT.md`, `scripts/m51-v7.patch`, `scripts/m51-v9-ble-recovery.py` e p0-p7. Reproduza a ordem dos scripts no workflow `.github/workflows/audit-v8-source.yml`. Não criar outro aplicativo.
2. **Inspecione o APK do próprio LibrePods** que foi produzido por esta branch, se estiver disponível no ambiente do agente, usando os recursos Android/JADX do REA. Confirme `AndroidManifest.xml`, permissões API 31, serviço foreground, callbacks `startScan/stopScan`, fluxo `ScanCallback -> BLEManager -> AirPodsService -> BatteryView`, e estados de ciclo de vida. A análise do fonte reconstruído é a linha de base; REA deve conferir o binário efetivamente construído e apresentar métodos/linhas/artefato correspondentes.
3. **Compare com código público autorizado** do CAPod (`d4rken-org/capod`), OpenPods (`adolfintel/OpenPods`) e LibrePods upstream. Procure lógica de anúncios Continuity 0x07/0x19, modelo AirPods Pro 3 `0x2720`, rotação de endereços, inversão dos nibbles, validade das baterias, scanner e janela do estojo. Não atribuir uma leitura BLE não autenticada a uma identidade criptograficamente verificada.
4. **Instrumente o BLE sem dados sensíveis.** No Galaxy M51 autorizado, usar ADB/REA para observar início/fim do scan, erros de `onScanFailed`, número de callbacks ativos, contadores BLE/Apple/proximidade, latência de atualização, anúncio de estojo aberto/fechado e comportamento em segundo plano. Nunca postar MACs completos ou dumps pessoais em issues públicos.
5. **Separe transportes.** A2DP/HFP é áudio, fabricante BLE fornece porcentagens aproximadas, AACP exige transporte clássico L2CAP. PSM `0x1001` de BR/EDR não equivale a LE CoC; não tentar substituir por APIs públicas LE. Não declarar ANC/Transparência/Adaptive operantes sem handshake e resposta verificável.
6. **Teste correções mínimas.** Evitar callbacks órfãos e retry infinito; permitir fallback filtrado -> sem filtro sem scanner duplicado; não apagar a bateria AACP válida; evitar valores falsos para caso/earbuds. Acrescentar testes de regressão de política e, onde possível, de start/stop scan via fake/adapter.
7. **Executar CI antes de APK.** `./gradlew :app:testDebugUnitTest :app:assembleDebug --no-daemon`, listar testes e status, sem publicar uma nova versão como pronta antes da validação física.

## Evidências que precisam acompanhar cada hipótese

| Hipótese | Observação/artefato esperado | Decisão |
|---|---|---|
| Scanner não inicia | `Anúncios BLE = 0`, permissões, `onScanFailed`, registro do serviço | Corrigir lifecycle/permissões |
| Filtro de fabricante não entrega | BLE > 0, Apple = 0, diferenças filtrado/sem filtro | Revisar hardware filter |
| Decoder rejeita AirPods | Apple > 0 e proximidade = 0, bytes ofuscados e formato válido | Corrigir parser, adicionar fixture autorizada |
| Bateria não chega à UI | proximidade > 0 e contadores auto/UI = 0 | Corrigir roteamento e estado Compose |
| Baterias não conferem | Captura autorizada e comparação simultânea com CAPod | Revisar nibble/modelo/cache/expiração |
| Janela não abre | Lid state, RSSI, cooldown, permissão de sobreposição | Corrigir somente após captura |
| AACP falha | `read ret:-1`, sem resposta ao handshake clássico | Tratar limite Android 12 como bloqueio, não fingir controle |

## Critérios de aceitação

- Três baterias e estado de carregamento corretamente identificados contra CAPod em **múltiplos testes físicos**, com valores desconhecidos explicitamente ausentes.
- Popup opt-in consistente com abertura real do estojo; sem exibição atribuída a um dispositivo próximo não autenticado como se fosse certeza.
- Audio A2DP/HFP corretamente exibido sem depender de AACP.
- Pausa/retomada apenas se houver evidência de eventos em-orelha interpretados com confiança; registrar eventual indisponibilidade.
- Nenhuma tentativa automática repetitiva de L2CAP no Android 12; testes manuais permanecem explícitos.
- CI verde, relatório de evidências e **somente depois** candidato único de APK para teste no M51.

**Importante:** engenharia reversa deve focar artefatos próprios, software de código aberto e dispositivos sob autorização. Analisar a pilha Android não dá permissões de sistema a um APK comum.
