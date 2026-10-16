# LibrePods M51: evidencias fisicas HCI e candidato p9 — 16/10/2026

## Resultado e limite

O APK existente v9+p0-p8 mostrou as tres baterias no M51 apos um replay de
configuracao BLE por lotes e uma solicitacao explicita de entrega
(`flushPendingScanResults`). A tela capturada mostrou **esquerda80%, direita70%,
estojo50%**, com os dois fones carregando. Isso comprova uma leitura no teste
controlado; nao comprova estabilidade do APK distribuido, nem instala p9.

O candidato de fonte p9 implementa entrega periodica de lotes para M51/API31.
Compilacao Android/CI e validacao de um futuro candidato no aparelho devem ser
conferidas separadamente. Nao tratar o teste do p8 modificado em memoria como
teste do binario p9. Nenhum APK novo foi instalado ou publicado nesta etapa.

## Ambiente e artefato

- Samsung Galaxy M51, Android12/API31, sem root, ADB autorizado.
- REA MCP6.5.0, JADX headless0.7.1, JDK17.0.20.1, Kotlin2.1.10.
- APK instalado: versionCode19, `0.1.0-rc.4-m51-v9-ble-recovery`.
- SHA256 APK: `e9af4b1aa5bea0f67a090144d743aa909c2853b464cae0fc212382227d91d5a9`.
- Conferido com o candidato p8 existente e metodos decompilados; o versionName
  sozinho nao foi usado como prova. Manifesto instalado targetSdk35, sem
  `neverForLocation`. SCAN/CONNECT/FINE/COARSE estavam concedidas.
- Relatorios brutos, imagens e logs completos permanecem locais. Este documento
  nao inclui MACs, seriais, chaves, nomes de dispositivos ou caudas criptografadas.

## Evidencias e testes fisicos

| Condicao observada | Resultado | Interpretacao permitida |
|---|---|---|
| p8 regular/fallback, repetidas aberturas | Apple >0, proximidade0, baterias desconhecidas | Nao prova defeito nos offsets do parser |
| CAPod, leitura atual apos reinicio Bluetooth | 70/80/50, carregamento e tampa aberta | Controle positivo BLE, nao AACP |
| HCI do M51 | 0x07/len25, prefixo01, modelo0x2720 | Controlador recebeu o formato aceito pelo parser |
| Novo scan p8 em primeiro plano, localizacao allow | Proximidade continuou0 | Localizacao/reinicio isolados nao resolveram |
| Replay filtro Apple data00/mask00, entrega imediata | BLE453/Apple385/proximidade0 | Mascara isolada nao resolveu |
| Replay com reportDelay5000 | Proximidade28, 11 atualizacoes automaticas registradas | Houve tambem rotacao/reinicio; nao isola causalidade |
| Replay de lotes estavel + um flush explicito | Proximidade28->34, tela80/70/50 | Evidencia funcional da estrategia de entrega de lote |

Na ultima etapa foram guardados60 frames privados, a cada2s durante120s.
O processo confirmou pareamento, ausencia de fonte manual e11 atualizacoes
automaticas. A leitura posterior ocorreu apos a expiracao de15s da previa;
isso nao deve ser confundido com ausencia de processamento das baterias.

As leituras atuais CAPod70/80/50 e LibrePods80/70/50 ocorreram em janelas
diferentes. **Nao ha comparacao simultanea conclusiva de esquerda/direita.**
Os cabecalhos tambem variaram; proxima validacao deve correlacionar cada quadro
com a tela e verificar ordem dos lados sem alterar nibbles por suposicao.

Identificadores REA para rastreio local:
- Captura CAPod atual: `ev_7e92d26a94966b541c8786a291bbbd32208f6af34a786d5d9cee31a142929a67`.
- Bugreport01: `ev_26c4501e9e11559abcdc9178bc42188ced25fd6a9229905cb9a02e8d5c7fd704`.
- Bugreport02-retry: `ev_7b6908b0ec6ba93e989feab8b030e79d1e561727af7ed816bc80d3d54fd4ef35`.
- Proximidade28: `ev_38cdea18710f702716488df1f10bbbfe782a254fb6e1c6e9f2abddbee015a424`.
- Tela com tres baterias apos flush: `ev_51b8d8f04797aeaff70edf0771c26ac42175b048ce6d076a4d24588cd0374464`.

## Capturas HCI e interpretacao

Bugreport01: SHA256
`2e46af4989adf8db3434403839ef7659a8305f228b687f778270efb15956b3b6`.
Arquivo HCI437018bytes, SHA256
`7c80dc0131ff05ec9efe07707eba7d85bed133455a99c65b98ff4bb500686803`.
3088 registros,1390 anuncios LE,281 TLVs0x07/len25 do modelo0x2720.

Bugreport02-retry: SHA256
`d523c5066b90859becb511ebc55c107f010beb08bedd1d566653fd187a966909`.
Arquivo HCI1482788bytes, SHA256
`48e9d8cbe39f03a0daed78d7d8b902e9d1fab305d1f1dcba38013444bbcd31bf`.
10024 registros,4635 anuncios LE,1699 TLVs0x07/len25.
**A segunda captura e cumulativa; nao somar281+1699 como amostras independentes.**

Analise local Python leu H4 e AD/manufacturer TLVs, exportando somente contagens
e primeiros11 bytes publicos do modelo. Nao decodificou eventos vendor de batch
nem conteudo criptografado. Clock do btsnoop apresentou diferenca de3h em relacao
ao UTC do aparelho; nao inferir latencias de usuario/logcat/HCI sem alinhar isso.

Os cinco primeiros cabecalhos distintos passaram no decoder Kotlin p8 real,
resultando70/80/50, ambos carregando e tampa conhecida/aberta. A cauda omitida
foi preenchida para comprimento27, somente para testar os campos publicos.
Nao houve decriptacao. O teste foi adicionado a regressao p9.

## Correcao candidata p9

- Restrita a Samsung SM-M515/API31; outros aparelhos preservam o fluxo p8.
- Filtro fabricante76 com byte00 e mascara00, LOW_LATENCY, ALL_MATCHES,
  reportDelay5000ms: configuracao usada no replay fisico.
- Solicita `flushPendingScanResults` a cada2000ms; nao reinicia o scanner a
  cada flush e nao altera o orcamento de retry p8.
- Pump vinculado ao scanner/callback ativo; cancela ao parar, substituir,
  falhar no registro ou iniciar outra busca. Tarefas atrasadas nao podem
  entregar dados para uma sessao substituta. Erro de flush encerra o pump.
- Descarta resultados em lote com timestamp invalido/futuro ou idade>15s,
  para nao converter cache antigo em abertura/retirada/porcentagem atual.
- Preserva precedencia AACP/manual, previa nao autenticada, expiracao,
  tampa desconhecida, guardas de callbacks e restricoes L2CAP anteriores.

REA conferiu no Bluetooth.apk do proprio M51 que `parseFullResults` calcula
timestamp a partir de `elapsedRealtimeNanos` menos a idade do registro.
Evidence `ev_ef364f35266728aabcd4d01956cecd3eb7e7eeec7b141b05c2f71bab442d1bd6`.
Esse e suporte estatico para a politica de frescor, nao teste fisico do p9.

Referencia de estrategia, sem copia de implementacao:
[CAPod BleScanner](https://github.com/d4rken-org/capod/blob/main/app/src/main/java/eu/darken/capod/common/bluetooth/BleScanner.kt).
CAPod solicita periodicamente entrega do buffer; o p8 tinha reportDelay0 e
nao fazia esse flush. As licencas anteriores foram preservadas.

## Validacao automatizada

- Kotlin/JUnit local: **41 testes aprovados**, incluindo33 anteriores,
  cancelamento/substituicao/falha do pump, seletor do aparelho, frescor e fixture HCI.
- Verificador estrutural p0-p8: **5/5**, incluindo callback unico e retry limitado.
- Evidencia local de41 testes e hashes dos12 fontes testados serao preservados
  junto ao candidato. CI Android ainda deve confirmar compilacao e testes.
- A montagem debug de verificacao deve ocorrer apenas apos os testes no CI;
  nenhum artefato APK sera publicado por esse workflow de auditoria.

## Trabalho restante

1. Conferir CI Android e revisar a integracao do pump; candidato ainda nao foi
   instalado/testado no aparelho. Repetir abertura com captura continua e
   comparar CAPod/esquerda/direita/estojo na mesma janela.
2. Medir atualizacao continua, consumo, segundo plano, reconexao Bluetooth,
   rotacao e rejeicao de lote antigo. Rotacao reiniciou busca e confundiu um
   teste; o layout em paisagem tambem apresentou sobreposicao de textos.
3. Popup: permissao de sobreposicao foi pulada, ainda sem teste conclusivo.
4. Sensores: os testes descritos mantiveram fones no estojo. Nenhum evento
   de retirada/recolocacao confiavel foi validado; pausa/retomada nao foi ativada.
5. L2CAP/AACP: nenhuma nova negociacao manual foi realizada nesta fase. O erro
   anterior `read ret: -1` continua sem causa determinada; audio A2DP nao prova
   AACP. Nao habilitar ANC/Transparencia por essas evidencias BLE.
6. Desativar HCI nas Opcoes do desenvolvedor apos concluir a coleta fisica.
   Os replays de parametros sao volateis; reiniciar o app restaura o APK p8.

A primeira tentativa de bugreport02 nao iniciou porque a revisao automatica
de permissao excedeu prazo. A repeticao permitida concluiu normalmente; nao
houve contorno de recusa de seguranca ou uso de root.
