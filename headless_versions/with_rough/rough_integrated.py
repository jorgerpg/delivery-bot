# Importações de bibliotecas necessárias
import pygame  # Para renderização gráfica e controle do jogo
import random  # Para geração procedural de conteúdo
import heapq  # Para implementação do algoritmo A* (fila de prioridade)
import sys  # Para funcionalidades do sistema (ex: sair do programa)
import argparse  # Para processar argumentos da linha de comando
from abc import ABC, abstractmethod  # Para criar classes abstratas
import csv  # Para salvar resultados em arquivos CSV
import os  # Para operações com arquivos e diretórios

# ==========================
# CLASSES DE PLAYER (JOGADOR/ROBÔ)
# ==========================

# Constantes globais
ROUGH_TERRAIN_COST = 2  # Custo de movimento em terreno irregular
RECHARGE_VALUE = 60  # Valor de recarga quando chega na estação

# Classe abstrata base para todos os tipos de jogador


class BasePlayer(ABC):
  def __init__(self, position):
    # Inicializa o jogador com:
    self.position = position  # Posição atual no grid [x, y]
    self.cargo = 0  # Quantidade de pacotes carregando
    self.battery = 70  # Nível atual de bateria (0-100)

  # Método abstrato que deve ser implementado pelas subclasses
  @abstractmethod
  def escolher_alvo(self, world):
    """Define a lógica de escolha do próximo alvo pelo jogador"""
    return [], None  # Retorno padrão para evitar erros

# Implementação concreta do jogador padrão


class DefaultPlayer(BasePlayer):
  def escolher_alvo(self, world):
    # Lógica principal de decisão do jogador:
    # 1. Se não tem pacotes, busca o pacote mais próximo
    # 2. Se tem pacotes, busca o destino de entrega mais próximo
    # 3. Sempre verifica se tem bateria suficiente

    current_pos = self.position  # Posição atual do jogador

    # Caso não haja mais metas (deveria recarregar)
    if len(world.goals) == 0:
      recharger_path, recharger_dist = world.astar(
          current_pos, world.recharger)
      return recharger_path, world.recharger

    # Se existem pacotes disponíveis
    if world.packages:
      # Variáveis para armazenar o melhor alvo encontrado
      best = None
      best_path = None
      best_dist = float('inf')  # Inicializa com "infinito"

      # Caso especial: apenas 1 pacote e 1 meta
      if len(world.packages) == 1 and len(world.goals) == 1:
        # Calcula caminho para o pacote
        package_path, d_package = world.astar(current_pos, world.packages[0])
        # Calcula caminho da entrega
        goal_path, d_goal = world.astar(world.packages[0], world.goals[0])

        # Verifica se tem bateria suficiente para todo o percurso
        if (d_package + d_goal) > self.battery:
          # Se não tiver, tenta ir para o recarregador
          recharger_path, recharger_dist = world.astar(
              current_pos, world.recharger)
          if recharger_dist and recharger_dist < self.battery:
            return recharger_path, world.recharger
          return [], None  # Retorna vazio se não conseguir

        return package_path, world.packages[0]  # Retorna o pacote como alvo
      else:
        # Procura o pacote mais próximo
        for pkg in world.packages:
          package_path, d_package = world.astar(current_pos, pkg)
          if d_package < best_dist:  # Se for mais próximo que o atual
            best_path = package_path
            best_dist = d_package
            best = pkg

        # Se estiver carregando pacotes, verifica destinos de entrega
        if world.goals and self.cargo > 0:
          for goal in world.goals:
            goal_path, d_goal = world.astar(current_pos, goal)
            if d_goal < best_dist:
              best_path = goal_path
              best_dist = d_goal
              best = goal

        # Verifica se tem bateria para ir até o alvo E voltar para recarregar
        self_recharger_path, self_recharger_dist = world.astar(
            current_pos, world.recharger)
        best_recharger_path, best_recharger_dist = world.astar(
            best, world.recharger)

        if (best_dist + best_recharger_dist) > self.battery:
          return self_recharger_path, world.recharger

        return best_path, best  # Retorna o melhor alvo encontrado

    # Se estiver carregando pacotes mas não há mais pacotes no mapa
    elif self.cargo > 0:
      # Entrega os pacotes nos destinos
      if world.goals:
        best = None
        best_dist = float('inf')
        for goal in world.goals:
          goal_path, d_goal = world.astar(current_pos, goal)
          if d_goal < best_dist:
            best_path = goal_path
            best_dist = d_goal
            best = goal

        # Verifica bateria para entrega + recarga
        self_recharger_path, self_recharger_dist = world.astar(
            current_pos, world.recharger)
        best_recharger_path, best_recharger_dist = world.astar(
            best, world.recharger)

        if (best_dist + best_recharger_dist) > self.battery:
          return self_recharger_path, world.recharger
        return best_path, best
      else:
        return [], None  # Nada mais a fazer

# ==========================
# CLASSE WORLD (MUNDO/AMBIENTE)
# ==========================


class World:
  def __init__(self, seed=None, headless=False):
    # Configurações iniciais do mundo
    self.headless = headless  # Modo sem interface gráfica
    if seed is not None:  # Define uma seed para reproducibilidade
      random.seed(seed)
    else:  # Cria uma seed aleatória se não for fornecida
      seed = random.randint(0, 10000000000000000)
      random.seed(seed)

    # Parâmetros do grid/mapa
    self.maze_size = 30  # Tamanho do grid (30x30)
    self.width = 1000  # Largura da janela em pixels
    self.height = 1000  # Altura da janela em pixels
    self.block_size = self.width // self.maze_size  # Tamanho de cada célula

    # Inicializa o mapa como matriz 2D (0 = livre, 1 = obstáculo)
    self.map = [[0 for _ in range(self.maze_size)]
                for _ in range(self.maze_size)]

    # Gera os obstáculos no mapa
    self.generate_obstacles()

    # Cria lista de paredes a partir da matriz
    self.walls = []
    for row in range(self.maze_size):
      for col in range(self.maze_size):
        if self.map[row][col] == 1:
          self.walls.append((col, row))  # Armazena posições das paredes

    # Define quantidade de itens para entrega (4-10 itens)
    self.total_items = random.randint(4, 10)

    # Gera posições dos pacotes (locais de coleta)
    self.packages = []
    while len(self.packages) < self.total_items:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      # Garante que a posição é válida e não está ocupada
      if self.map[y][x] == 0 and [x, y] not in self.packages:
        self.packages.append([x, y])

    # Gera posições das metas (locais de entrega)
    self.goals = []
    while len(self.goals) < self.total_items:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      # Garante posição válida e não conflitante
      if self.map[y][x] == 0 and [x, y] not in self.goals and [x, y] not in self.packages:
        self.goals.append([x, y])

    # Cria o jogador em uma posição válida
    self.player = self.generate_player()

    # Posiciona a estação de recarga
    self.recharger = self.generate_recharger()

    # Gera terrenos irregulares (custo maior de movimento)
    self.rough_terrains = []
    self.generate_rough_terrain()

    # Configurações gráficas (se não for headless)
    if not self.headless:
      pygame.init()  # Inicializa o pygame
      self.screen = pygame.display.set_mode((self.width, self.height))
      pygame.display.set_caption("Delivery Bot")

      # Carrega imagens para os elementos visuais
      self.package_image = pygame.image.load("images/cargo.png")
      self.package_image = pygame.transform.scale(
          self.package_image, (self.block_size, self.block_size))

      self.goal_image = pygame.image.load("images/operator.png")
      self.goal_image = pygame.transform.scale(
          self.goal_image, (self.block_size, self.block_size))

      self.recharger_image = pygame.image.load("images/charging-station.png")
      self.recharger_image = pygame.transform.scale(
          self.recharger_image, (self.block_size, self.block_size))

    # Define cores para os elementos (usadas se não houver imagens)
    self.rough_color = (139, 69, 19)  # Marrom para terreno irregular
    self.wall_color = (100, 100, 100)  # Cinza para paredes
    self.ground_color = (255, 255, 255)  # Branco para fundo
    self.player_color = (0, 255, 0)  # Verde para o jogador
    self.path_color = (200, 200, 0)  # Amarelo para o caminho

  def generate_rough_terrain(self):
    """Gera terrenos irregulares garantindo que não sobreponham outros elementos"""
    max_roughs = 50  # Número máximo de terrenos irregulares
    attempts = 0
    max_attempts = 1000  # Previne loop infinito

    while len(self.rough_terrains) < max_roughs and attempts < max_attempts:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      # Verifica se a posição é válida
      if (self.map[y][x] == 0 and
          [x, y] not in self.packages and
          [x, y] not in self.goals and
          [x, y] != self.player.position and
              [x, y] != self.recharger):
        self.map[y][x] = 2  # Marca como terreno irregular
        self.rough_terrains.append((x, y))  # Adiciona à lista
      attempts += 1

  def generate_obstacles(self):
    """Gera obstáculos no mapa com padrão de linha de montagem"""
    # Barreiras horizontais
    for _ in range(7):
      row = random.randint(5, self.maze_size - 6)
      start = random.randint(0, self.maze_size - 10)
      length = random.randint(5, 10)
      for col in range(start, start + length):
        if random.random() < 0.7:  # 70% de chance de ter obstáculo
          self.map[row][col] = 1

    # Barreiras verticais
    for _ in range(7):
      col = random.randint(5, self.maze_size - 6)
      start = random.randint(0, self.maze_size - 10)
      length = random.randint(5, 10)
      for row in range(start, start + length):
        if random.random() < 0.7:
          self.map[row][col] = 1

    # Bloco grande de obstáculos (4x4 ou 6x6)
    block_size = random.choice([4, 6])
    max_row = self.maze_size - block_size
    max_col = self.maze_size - block_size
    top_row = random.randint(0, max_row)
    top_col = random.randint(0, max_col)
    for r in range(top_row, top_row + block_size):
      for c in range(top_col, top_col + block_size):
        self.map[r][c] = 1  # Marca como obstáculo

  def generate_player(self):
    """Gera o jogador em uma posição válida"""
    while True:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      # Verifica se a posição é válida
      if self.map[y][x] == 0 and [x, y] not in self.packages and [x, y] not in self.goals:
        return DefaultPlayer([x, y])  # Cria o jogador

  def generate_recharger(self):
    """Posiciona a estação de recarga próxima ao centro"""
    center = self.maze_size // 2
    while True:
      x = random.randint(center - 1, center + 1)
      y = random.randint(center - 1, center + 1)
      # Verifica posição válida
      if self.map[y][x] == 0 and [x, y] not in self.packages and [x, y] not in self.goals and [x, y] != self.player.position:
        return [x, y]

  def can_move_to(self, pos):
    """Verifica se uma posição é válida para movimento"""
    x, y = pos
    # Verifica limites do grid e tipo de terreno
    if 0 <= x < self.maze_size and 0 <= y < self.maze_size:
      return self.map[y][x] in (0, 2)  # 0 = livre, 2 = terreno irregular
    return False

  def draw_world(self, path=None):
    """Renderiza o mundo na tela"""
    self.screen.fill(self.ground_color)  # Fundo branco

    # Desenha paredes
    for (x, y) in self.walls:
      rect = pygame.Rect(x * self.block_size, y *
                         self.block_size, self.block_size, self.block_size)
      pygame.draw.rect(self.screen, self.wall_color, rect)

    # Desenha terrenos irregulares
    for (x, y) in self.rough_terrains:
      rect = pygame.Rect(x * self.block_size, y *
                         self.block_size, self.block_size, self.block_size)
      pygame.draw.rect(self.screen, self.rough_color, rect)

    # Desenha pacotes (usando imagem se disponível)
    for pkg in self.packages:
      x, y = pkg
      self.screen.blit(self.package_image,
                       (x * self.block_size, y * self.block_size))

    # Desenha metas de entrega
    for goal in self.goals:
      x, y = goal
      self.screen.blit(
          self.goal_image, (x * self.block_size, y * self.block_size))

    # Desenha estação de recarga
    if self.recharger:
      x, y = self.recharger
      self.screen.blit(self.recharger_image,
                       (x * self.block_size, y * self.block_size))

    # Desenha caminho calculado (se fornecido)
    if path:
      for pos in path:
        x, y = pos
        rect = pygame.Rect(x * self.block_size + self.block_size // 4,
                           y * self.block_size + self.block_size // 4,
                           self.block_size // 2, self.block_size // 2)
        pygame.draw.rect(self.screen, self.path_color, rect)

    # Desenha o jogador
    x, y = self.player.position
    rect = pygame.Rect(x * self.block_size, y * self.block_size,
                       self.block_size, self.block_size)
    pygame.draw.rect(self.screen, self.player_color, rect)
    pygame.display.flip()  # Atualiza a tela

  def heuristic(self, a, b):
    """Função heurística para A* (distância de Manhattan)"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

  def astar(self, start, goal):
    """Implementação do algoritmo A* para pathfinding"""
    maze = self.map  # Referência para o mapa
    size = self.maze_size  # Tamanho do grid
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Movimentos possíveis

    # Estruturas para o algoritmo A*
    close_set = set()  # Nós já avaliados
    came_from = {}  # Rastreia o caminho
    gscore = {tuple(start): 0}  # Custo do caminho do início até cada nó
    fscore = {tuple(start): self.heuristic(
        start, goal)}  # Custo total estimado
    oheap = []  # Fila de prioridade (heap)
    # Adiciona o nó inicial
    heapq.heappush(oheap, (fscore[tuple(start)], tuple(start)))

    while oheap:
      current = heapq.heappop(oheap)[1]  # Pega o nó com menor custo

      # Se chegou ao destino, reconstrói o caminho
      if list(current) == goal:
        data = []
        total_cost = gscore[current]
        while current in came_from:
          data.append(list(current))
          current = came_from[current]
        data.reverse()  # Inverte para ter do início ao fim
        return data, total_cost  # Retorna caminho e custo total

      close_set.add(current)  # Marca como avaliado

      # Avalia todos os vizinhos
      for dx, dy in neighbors:
        neighbor = (current[0] + dx, current[1] + dy)

        # Verifica se está dentro dos limites do grid
        if 0 <= neighbor[0] < size and 0 <= neighbor[1] < size:
          # Ignora paredes
          if maze[neighbor[1]][neighbor[0]] == 1:
            continue

          # Calcula custo do terreno
          terrain_cost = ROUGH_TERRAIN_COST if maze[neighbor[1]
                                                    ][neighbor[0]] == 2 else 1
        else:
          continue  # Fora dos limites - ignora

        # Calcula custo temporário para o vizinho
        tentative_g = gscore[current] + terrain_cost

        # Se já foi avaliado e o novo custo não é melhor, ignora
        if neighbor in close_set and tentative_g >= gscore.get(neighbor, 0):
          continue

        # Se encontrou um caminho melhor ou é um novo nó
        if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [i[1] for i in oheap]:
          came_from[neighbor] = current  # Atualiza o caminho
          gscore[neighbor] = tentative_g  # Atualiza custo real
          fscore[neighbor] = tentative_g + \
              self.heuristic(neighbor, goal)  # Atualiza custo estimado
          # Adiciona à fila
          heapq.heappush(oheap, (fscore[neighbor], neighbor))

    return [], float('inf')  # Retorna vazio se não encontrar caminho

# ==========================
# CLASSE MAZE: Lógica principal do jogo
# ==========================


class Maze:
  def __init__(self, seed=None, headless=False, output_file="results.csv"):
    """Inicializa o jogo principal"""
    self.headless = headless  # Modo sem gráficos
    self.world = World(seed, headless)  # Cria o mundo
    self.running = True  # Controle do loop principal
    self.score = 0  # Pontuação do jogador
    self.steps = 0  # Número de passos dados
    self.delay = 100  # Tempo entre movimentos (ms)
    self.path = []  # Caminho atual do jogador
    self.num_deliveries = 0  # Entregas realizadas
    self.output_file = output_file  # Arquivo para salvar resultados
    self.seed = seed  # Seed usada para geração

  def game_loop(self):
    """Loop principal do jogo"""
    while self.running:
      # Verifica condição de término (todas entregas e na estação)
      dist_recharger = self.world.heuristic(
          self.world.player.position, self.world.recharger)
      if self.num_deliveries >= self.world.total_items and (dist_recharger == 0):
        self.running = False
        break

      # Obtém próximo movimento do jogador
      self.path, target = self.world.player.escolher_alvo(self.world)

      # Se não houver alvo válido, termina o jogo
      if not self.path or target is None:
        self.running = False
        break

      # Executa cada passo do caminho calculado
      for pos in self.path:
        self.world.player.position = pos  # Atualiza posição
        self.steps += 1  # Incrementa contador de passos

        # Calcula custo do terreno
        x, y = pos
        cell_value = self.world.map[y][x]
        if cell_value == 2:
          terrain_cost = ROUGH_TERRAIN_COST  # Custo maior em terreno irregular
        elif cell_value == 0:
          terrain_cost = 1  # Custo normal

        # Atualiza bateria e pontuação
        self.world.player.battery -= terrain_cost
        if self.world.player.battery >= 0:
          self.score -= terrain_cost  # Penalidade por movimento
        else:
          self.running = False  # Bateria acabou
          # Penalidade por entregas não realizadas
          self.score -= (self.world.total_items - self.num_deliveries) * 25
          break

        # Recarrega bateria se estiver na estação
        if self.world.recharger and pos == self.world.recharger:
          self.world.player.battery = RECHARGE_VALUE

        # Renderiza (se não for headless)
        if not self.headless:
          self.world.draw_world(self.path)
          pygame.time.wait(self.delay)  # Pequena pausa

      # Processa chegada no alvo
      if self.world.player.position == target:
        # Se for pacote, coleta
        if target in self.world.packages:
          self.world.player.cargo += 1
          self.world.packages.remove(target)
        # Se for meta e tiver pacote, entrega
        elif target in self.world.goals and self.world.player.cargo > 0:
          self.world.player.cargo -= 1
          self.num_deliveries += 1
          self.world.goals.remove(target)
          self.score += 50  # Bônus por entrega

    # Salva resultados e finaliza
    self._save_results()
    pygame.quit()

  def _save_results(self):
    """Salva os resultados da simulação em arquivo CSV"""
    file_exists = os.path.isfile(self.output_file)
    with open(self.output_file, 'a', newline='') as f:
      writer = csv.writer(f)
      # Cria cabeçalho se o arquivo não existir
      if not file_exists:
        writer.writerow(['Seed', 'Score', 'Steps', 'Deliveries', 'Script'])
      # Escreve os dados da simulação
      writer.writerow([
          self.seed,
          self.score,
          self.steps,
          self.num_deliveries,
          os.path.basename(__file__)
      ])


# ==========================
# PONTO DE ENTRADA PRINCIPAL
# ==========================
if __name__ == "__main__":
  # Configura parser de argumentos da linha de comando
  parser = argparse.ArgumentParser(
      description="Delivery Bot: Navegue no grid, colete pacotes e realize entregas."
  )
  parser.add_argument(
      "--seed",
      type=int,
      default=None,
      help="Valor do seed para recriar o mesmo mundo (opcional)."
  )
  parser.add_argument(
      "--headless",
      action="store_true",
      help="Executa em modo sem interface gráfica para coleta de dados"
  )
  parser.add_argument("--output", type=str, default="results.csv")
  args = parser.parse_args()

  # Inicializa e executa o jogo
  maze = Maze(seed=args.seed, headless=args.headless, output_file=args.output)
  maze.game_loop()
