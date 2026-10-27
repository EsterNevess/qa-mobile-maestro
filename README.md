# Automação mobile com Maestro — My Demo App

[![Testes mobile (Maestro)](https://github.com/EsterNevess/qa-mobile-maestro/actions/workflows/ci.yml/badge.svg)](https://github.com/EsterNevess/qa-mobile-maestro/actions/workflows/ci.yml)
[![Relatório Allure](https://img.shields.io/badge/Relat%C3%B3rio-Allure-FF5722?logo=qase&logoColor=white)](https://esternevess.github.io/qa-mobile-maestro/)

📊 **[Relatório Allure da última execução](https://esternevess.github.io/qa-mobile-maestro/)** — com os prints de cada passo anexados, publicado a cada push.

Automação de testes de um aplicativo Android com **Maestro**, rodando em emulador dentro do CI.

Fecha a última camada que faltava no meu portfólio de automação: já tinha
[API e Web](https://github.com/EsterNevess/qa-automation-serverest),
[BDD](https://github.com/EsterNevess/qa-bdd-saucedemo) e
[performance](https://github.com/EsterNevess/qa-performance-serverest) — faltava mobile.

## O app em teste

O [My Demo App](https://github.com/saucelabs/my-demo-app-rn) da Sauce Labs, um e-commerce em React
Native publicado justamente para prática de automação. As credenciais usadas são as de
demonstração, exibidas na própria tela de login do app — não há dado real envolvido.

A escolha tem continuidade com o resto do portfólio: o Saucedemo que eu testei na web é da mesma
empresa, então o domínio é o mesmo e o que muda é a plataforma.

## Os cenários

| Fluxo | O que verifica |
|---|---|
| `01-login-valido.yaml` | autentica com credenciais válidas e volta para a lista de produtos |
| `02-login-invalido.yaml` | recusa senha incorreta e exibe a mensagem de erro |
| `03-adicionar-ao-carrinho.yaml` | adiciona um produto e confirma o contador do carrinho |

Todos começam pelo subfluxo `comum/abrir-app.yaml`, que abre o app com `clearState: true`.

**Por que o `clearState` importa:** sem ele, o cenário de login deixa a sessão ativa e o seguinte
começa de um estado diferente do esperado. A suíte passa a depender da ordem de execução — e
quebra no dia em que alguém roda um fluxo isolado. Teste precisa ser independente, não ordenado.

## Por que Maestro, e não Appium

| | Maestro | Appium |
|---|---|---|
| Escrita do teste | YAML declarativo | código, em várias linguagens |
| Espera por elemento | automática | geralmente explícita, no código |
| Configuração inicial | um binário | servidor, drivers e capabilities |
| Ecossistema | mais novo, menor | maduro, padrão de mercado |

O Appium continua sendo o padrão em empresa grande, e é ele que aparece na maioria das vagas. Mas
para começar em mobile o Maestro tem uma vantagem concreta: **a espera é automática**.

Isso resolve de saída a maior fonte de instabilidade em teste mobile, que é o elemento ainda não
renderizado quando o passo executa. Foi exatamente o defeito que eu já tinha enfrentado no meu
projeto web, onde `locator.count()` contava antes de a lista existir.

## Execução no CI

Teste mobile precisa de um dispositivo, e é aí que a maioria dos projetos para no "rodei na minha
máquina". Aqui o CI sobe um **emulador Android (API 30, Pixel 5)** no runner, instala o APK e
executa os fluxos.

Dois detalhes que fazem diferença:

**KVM habilitado.** Sem virtualização por hardware o emulador sobe por software e fica tão lento
que estoura o tempo limite. O passo que ajusta as regras do `udev` existe por isso.

**Runner com versão fixa (`ubuntu-24.04`).** O rótulo `latest` migrou de distribuição em outubro de
2026 e levou junto o suporte de ferramentas que dependiam da anterior. Em CI, reprodutibilidade
vale mais que estar na última versão.

Ao fim, o resultado sai em **JUnit XML** e as evidências de depuração (prints e logs de cada passo)
ficam disponíveis como artefato da execução.

## Relatório com evidências

O Maestro entrega duas coisas separadas: **JUnit XML** (nome, status e duração de cada cenário) e
uma pasta de depuração com **prints de cada passo**. O XML sozinho vira um relatório magro — diz o
que falhou, não mostra.

O script `scripts/junit_para_allure.py` junta as duas: para cada cenário do XML, procura os prints
correspondentes pelo nome e os anexa ao resultado do Allure. Print que não casa com nenhum cenário
não é descartado — vira um item próprio, porque evidência que ninguém encontra não serve para nada.

O [relatório](https://esternevess.github.io/qa-mobile-maestro/) é publicado no GitHub Pages a cada
execução, com histórico de tendência.

## Como rodar localmente

Requer um emulador Android ou um aparelho conectado via USB com depuração ativada.

```bash
# instalar o Maestro
curl -Ls "https://get.maestro.mobile.dev" | bash

# baixar e instalar o app
curl -L -o app.apk https://github.com/saucelabs/my-demo-app-rn/releases/download/v1.3.0/Android-MyDemoAppRN.1.3.0.build-244.apk
adb install -r app.apk

# rodar tudo
maestro test flows/

# rodar só um grupo
maestro test flows/ --include-tags smoke
```

Para acompanhar passo a passo e inspecionar a árvore de elementos:

```bash
maestro studio
```

## Estrutura

```
flows/
  comum/abrir-app.yaml      subfluxo de preparação, reaproveitado
  01-login-valido.yaml
  02-login-invalido.yaml
  03-adicionar-ao-carrinho.yaml
.github/workflows/ci.yml    emulador + execução a cada push
```

As etiquetas (`smoke`, `login`, `carrinho`) permitem rodar um subconjunto sem mexer nos arquivos —
útil quando a suíte cresce e nem tudo precisa rodar a cada mudança.
