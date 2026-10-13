# LibrePods M51 — v7 experimental

Adaptação do **código original do LibrePods** para Samsung Galaxy M51, Android 12,
AirPods Pro 3, sem root. Mesmo applicationId das versões M51 anteriores.

- Três baterias separadas e atualização da interface em Android 12.
- Leitura BLE pública aproximada, independente da conexão AACP.
- Estado de áudio A2DP/HFP separado dos controles avançados.
- Janela automática opcional, interpretação de anúncios testável e validade limitada.
- Teste opcional de socket BR/EDR usado como alternativa no CAPod.

**Não há correção comprovada do L2CAP no M51.** ANC, Transparência e outros controles
não são declarados funcionais sem comunicação AACP e teste do recurso no aparelho.
A leitura BLE e a janela também precisam de validação física; testes de unidade
não substituem esse teste.

## APK e validação

[Compilação v7 no GitHub Actions](https://github.com/nobileribeirojc/librepods-m51./actions/runs/38414814243)

O artefato `LibrePods-M51-v7-BLE-APK` contém APK, SHA-256, relatório de assinatura,
patch e documentação. Os testes ficam em `M51-v7-test-reports`.

[Alterações, investigação L2CAP, fontes e roteiro de teste](docs/M51-V7.md).

## Código e reprodução

A base original está em `LibrePods-M51-v4-pronto-para-compilar.zip`.
O workflow extrai a base e aplica, nessa ordem:

1. `scripts/fix-m51-unknown-battery.py`
2. `scripts/m51-v5-public-ble-preview.py`
3. `scripts/m51-v6-ble-continuo.py`
4. `scripts/m51-v7.patch` (diff dos arquivos Kotlin/Gradle originais e novos testes).

Compilação: JDK 17, SDK 35 e wrapper Gradle da base;
`:app:testDebugUnitTest :app:assembleDebug`. Mantida licença AGPL-3.0-or-later da base.

APK de depuração: a chave usada nas versões anteriores não está disponível no
repositório. Se o Android recusar atualização por assinatura, exporte o diagnóstico
e remova apenas a versão experimental anterior antes de instalar. Isso apaga suas
preferências locais. A assinatura de produção persistente ainda não foi configurada.
