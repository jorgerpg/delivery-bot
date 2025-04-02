# README - Descrição dos Arquivos do Projeto

Este projeto contém diversas versões do código original, cada uma com diferentes modificações e melhorias implementadas ao longo do tempo. Abaixo, detalhamos o propósito e as mudanças realizadas em cada arquivo:

## Arquivos e suas funcionalidades:

### 1. `main_original.py`
**Descrição:** Versão original do código base enviado pelo professor, sem alterações. Este arquivo serve como referência inicial para as modificações posteriores.

### 2. `main_janu.py`
**Descrição:** Versão modificada por Januário, contendo suas adições e melhorias específicas. Entre as mudanças, destaca-se a capacidade de pegar mais de uma carga e nunca permitir a bateria descarregar. Além de sempre voltar para o carregador no fim.

### 3. `rough_terrain.py`
**Descrição:** Versão original com a adição do conceito de `rough_terrain`, Heurística igual à do original.

### 4. `rough_integrated.py`
**Descrição:** Implementação de uma nova lógica de escolha baseada no `rough_terrain`, logica de decisão igual a do janu mas utilizando o astar para calcular a distancia e o path.

### 5. `main_janu_rough.py`
**Descrição:** Implementação de uma nova lógica de escolha baseada no `rough_terrain`, e heuristica do janu com a adição do calculo do rough_terrain no astar. Volta para o carregador no fim. validar qual o melhor processo.

### 6. `seeds de teste:`
  - 8192736887241304
  - 3770486853704386

### 7. `headless_versions`
**Descrição:** Versões otimizadas para rodar o script comparativo de forma mais rápida, sem a necessidade de interface gráfica. Os gráficos comparativos gerados incluem:
  - **Score:** Pontuação obtida em cada execução.
  - **Steps:** Número de passos realizados.
  - **Ratio Step/Score:** Relação entre o número de passos e a pontuação.
  ### Exemplo de Execução

  Para comparar diferentes versões do código, você pode utilizar o seguinte comando:

  #### Usando seeds aleatórios (padrão)
  python3 .\compare_script.py .\with_rough\janu_rough.py .\with_rough\rough_integrated.py .\with_rough\rough_terrain.py --runs 100

  python3 .\compare_script.py .\without_rough\janu.py .\without_rough\integrated.py .\without_rough\original.py --runs 100 

  #### Usando seeds específicos
  python3 .\compare_script.py .\with_rough\janu_rough.py .\with_rough\rough_integrated.py .\with_rough\rough_terrain.py --seeds 8192736887241304,3770486853704386 --output results_seeded.csv

