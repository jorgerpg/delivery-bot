# README - Sistema de Entrega Autônoma com Pathfinding

**Equipe:** Daniel Januário, Jorge Ricarte e Ruan Utah

---

## Visão Geral
Este projeto simula um robô autônomo de entrega em um ambiente grid-based, com múltiplas versões de algoritmos de pathfinding e estratégias de decisão. Inclui comparações entre diferentes abordagens de otimização de rotas, gestão de bateria e tratamento de terrenos irregulares.

---

## Dependências:

- Python 3, pip
- Bibliotecas: pygame, numpy, pandas, matplotlib, seaborn

Instale todas as bibliotecas com:

```bash
pip install -r requirements.txt
```

## Exemplo de Execução

Para comparar diferentes versões do código, utilize os seguintes comandos:

### Rodando `compare_script`
O script `compare_script.py` deve ser executado dentro da pasta `headless_versions`, garantindo que todas as dependências estejam corretamente configuradas.

### Usando seeds aleatórias (padrão)
```bash
cd headless_versions

# Comparação geral dos codigos com terreno irregular (100 execuções com seeds aleatórias)
python3 compare_script.py with_rough/janu_rough.py with_rough/rough_integrated.py with_rough/rough_terrain.py --runs 100

# Comparação com seeds específicas sem terreno irregular
python3 compare_script.py without_rough/janu.py without_rough/integrated.py without_rough/original.py --seeds 8192736887241304,3770486853704386 --output results_seeded.csv
```

### Execução com Interface Gráfica
Da pasta raiz do projeto
```bash
python3 normal_versions/rough_integrated.py
```

---

## Estrutura do Projeto

### Diretórios Principais
| Diretório           | Descrição                                                                 |
|---------------------|---------------------------------------------------------------------------|
| `normal_versions/`  | Versões com interface gráfica (PyGame)                                   |
| `headless_versions/`| Versões otimizadas para execução em batch sem GUI                        |
| `with_rough/`       | Versões que incluem lógica para terreno irregular                        |
| `without_rough/`    | Versões base sem tratamento de terreno irregular                         |

---

## Principais Arquivos

### Versões Base
| Arquivo               | Descrição                                                                 |
|-----------------------|---------------------------------------------------------------------------|
| `original.py`         | Implementação original do professor sem modificações                     |
| `rough_terrain.py`    | Versão base + suporte a terreno irregular (custo 2 por movimento)        |

### Versões Aprimoradas
| Arquivo               | Destaques                                                                 |
|-----------------------|---------------------------------------------------------------------------|
| `rough_integrated.py` | - Algoritmo A* com custo variável<br>- Lógica de decisão de Janu<br>- Otimização para terrenos irregulares |
| `janu_rough.py`       | - Pathfinding A* com custos dinâmicos<br>- Validação de rotas seguras (+5 energia de margem)<br>- Retorno obrigatório ao carregador |

---