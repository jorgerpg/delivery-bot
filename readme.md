# README - Descrição dos Arquivos do Projeto

Equipe: Daniel Januario, Jorge Ricarte e Ruan Utah.

Este projeto contém diversas versões do código original, cada uma com diferentes modificações e melhorias implementadas ao longo do tempo. Abaixo, detalhamos o propósito e as mudanças realizadas em cada arquivo:

## Arquivos e suas funcionalidades:

### 1. `original.py`
**Descrição:** Versão original do código base enviado pelo professor, sem alterações. Este arquivo serve como referência inicial para as modificações posteriores.

### 2. `janu.py`
**Descrição:** Versão modificada por Januário, contendo suas adições e melhorias específicas. Entre as mudanças, destacam-se:
- Capacidade de pegar mais de uma carga.
- Nunca permitir a bateria descarregar completamente.
- Sempre retornar ao carregador ao final da execução.

### 3. `rough_terrain.py`
**Descrição:** Versão original com a adição do conceito de `rough_terrain`. Mantém a heurística da versão original.

### 4. `janu_rough.py`
**Descrição:** Implementa uma nova lógica de escolha baseada no `rough_terrain`, combinando a heurística de Janu com o cálculo de `rough_terrain` no algoritmo A*.
- Retorna ao carregador ao final da execução.
- Valida qual é o melhor processo para otimização do caminho.

### 5. `rough_integrated.py`
**Descrição:** Implementa uma nova lógica de escolha baseada no `rough_terrain`.
- Utiliza a lógica de decisão de Janu, mas emprega o algoritmo A* para calcular a distância e o caminho ideal.

### 6. `headless_versions`
**Descrição:** Versões otimizadas para rodar o script comparativo de forma mais rápida, sem a necessidade de interface gráfica. Os gráficos comparativos gerados incluem:
  - **Score:** Pontuação obtida em cada execução.
  - **Steps:** Número de passos realizados.
  - **Ratio Step/Score:** Relação entre o número de passos e a pontuação.

## Exemplo de Execução

Para comparar diferentes versões do código, utilize os seguintes comandos:

### Rodando `compare_script`
O script `compare_script.py` deve ser executado dentro da pasta `headless_versions`, garantindo que todas as dependências estejam corretamente configuradas.

### Usando seeds aleatórias (padrão)
```bash
cd headless_versions
python3 compare_script.py with_rough/janu_rough.py with_rough/rough_integrated.py with_rough/rough_terrain.py --runs 100

python3 compare_script.py without_rough/janu.py without_rough/integrated.py without_rough/original.py --runs 100
```

### Usando seeds específicas
```bash
cd headless_versions
python3 compare_script.py with_rough/janu_rough.py with_rough/rough_integrated.py with_rough/rough_terrain.py --seeds 8192736887241304,3770486853704386 --output results_seeded.csv
```

### Rodando versões com gráficos
As versões que geram gráficos estão na pasta `normal_versions` e devem ser executadas a partir da pasta raiz do projeto. Exemplo:
```bash
python3 normal_versions/integrated.py
```