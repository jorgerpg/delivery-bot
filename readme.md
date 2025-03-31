# README - Descrição dos Arquivos do Projeto

Este projeto contém diversas versões do código original, cada uma com diferentes modificações e melhorias implementadas ao longo do tempo. Abaixo, detalhamos o propósito e as mudanças realizadas em cada arquivo:

## Arquivos e suas funcionalidades:

### 1. `main_original.py`
**Descrição:** Versão original do código base enviado pelo professor, sem alterações. Este arquivo serve como referência inicial para as modificações posteriores.

### 2. `main_janu.py`
**Descrição:** Versão modificada por Januário, contendo suas adições e melhorias específicas. Entre as mudanças, destaca-se a capacidade de pegar mais de uma carga e nunca permitir a bateira descarregar.

### 3. `rough_terrain.py`
**Descrição:** Versão original com a adição do conceito de `rough_terrain`, permitindo lidar melhor com terrenos acidentados. heuristica igual a do original.

### 4. `rough_improved.py`
**Descrição:** Implementação de uma nova lógica de escolha baseada no `rough_terrain`, planejada para futuramente levar em consideração o peso desse fator. No entanto, essa versão ainda apresenta limitações, pois não consegue replicar a funcionalidade de pegar mais de uma carga, como ocorre na versão de Januário.

### 5. `main_full.py`
**Descrição:** Versão planejada para ser a versão final do projeto, contendo todas as modificações realizadas até agora. Ainda não está completa, pois a nova lógica de escolha (`main_escolha_novo.py`) foi integrada parcialmente. No entanto, acredita-se que já seja uma melhoria em relação a `main_rough_terrain.py`.

## Status Atual
Atualmente, o desenvolvimento está focado em:
- Ajustar a lógica de escolha para incluir corretamente o fator `rough_terrain` e permitir a coleta de múltiplas cargas.
- Implementar a possibilidade de pegar duas cargas seguidas no (`rough_improved.py`) para que fique mais otimizado.
- Refinar a versão final (`main_full.py`) para garantir que todas as melhorias estejam funcionando corretamente.


seed de teste:
  8192736887241304
  3770486853704386