# Importação de bibliotecas necessárias
import pygame       # Para interface gráfica
import random       # Para geração aleatória
import heapq        # Para fila de prioridade (usada no A*)
import sys          # Para funcionalidades do sistema
import argparse     # Para tratar argumentos da linha de comando
from abc import ABC, abstractmethod  # Para classes abstratas
import csv          # Para manipulação de arquivos CSV
import os           # Para operações de sistema de arquivos

# ==========================
# CLASSES DE PLAYER (JOGADOR)
# ==========================

# Custo de movimento em terreno irregular
ROUGH_TERRAIN_COST = 2

# Classe base abstrata para o jogador


class BasePlayer(ABC):
  def __init__(self, position):
    self.position = position  # Posição atual (x,y) no grid
    self.cargo = 0            # Quantidade de pacotes carregados
    self.battery = 70         # Nível atual da bateria

  @abstractmethod
  def escolher_alvo(self, world):
    """Método abstrato para definir estratégia de escolha de alvo"""
    pass

# Implementação concreta do jogador padrão


class DefaultPlayer(BasePlayer):
  def escolher_alvo(self, world):
    """Lógica de escolha de alvo baseada em distância Manhattan e bateria"""
    sx, sy = self.position  # Posição atual do jogador

    # Caso não haja metas restantes
    if len(world.goals) == 0:
      return world.recharger

    # Se houver pacotes disponíveis
    if world.packages:
      best = None
      best_dist = float('inf')  # Inicializa com distância infinita

      # Caso especial: único pacote e única meta
      if len(world.packages) == 1 and len(world.goals) == 1:
        # Calcula distâncias usando Manhattan
        d_package = abs(world.packages[0][0] - sx) + \
            abs(world.packages[0][1] - sy)
        d_goal = abs(world.goals[0][0] - world.packages[0][0]) + \
            abs(world.goals[0][1] - world.packages[0][1])

        # Verifica se a bateria é suficiente com margem de segurança
        if (d_package + d_goal + 5) > self.battery:
          # Verifica se é possível chegar ao recarregador
          dist_recharger = abs(
              world.recharger[0] - sx) + abs(world.recharger[1] - sy)
          if dist_recharger != 0 and dist_recharger < self.battery:
            return world.recharger
          return None  # Não há caminho viável
        return world.packages[0]
      else:
        # Encontra o pacote mais próximo
        for pkg in world.packages:
          d = abs(pkg[0] - sx) + abs(pkg[1] - sy)
          if d < best_dist:
            best_dist = d
            best = pkg

        # Se estiver carregando, verifica metas
        if world.goals and self.cargo > 0:
          for goal in world.goals:
            d = abs(goal[0] - sx) + abs(goal[1] - sy)
            if d < best_dist:
              best_dist = d
              best = goal

        # Verifica viabilidade da rota considerando recarga
        d_self_goal = abs(best[0] - sx) + abs(best[1] - sy)
        d_self_recharge = abs(
            world.recharger[0] - sx) + abs(world.recharger[1] - sy)
        d_goal_recharge = abs(
            best[0] - world.recharger[0]) + abs(best[1] - world.recharger[1])

        # Adiciona margem de segurança de 5 unidades
        if (d_self_goal + d_goal_recharge + 5) > self.battery:
          return world.recharger
        return best
    elif self.cargo > 0:
      # Entrega de pacotes
      if world.goals:
        best = None
        best_dist = float('inf')
        for goal in world.goals:
          d = abs(goal[0] - sx) + abs(goal[1] - sy)
          if d < best_dist:
            best_dist = d
            best = goal

        # Verifica viabilidade da rota de entrega
        d_self_goal = abs(best[0] - sx) + abs(best[1] - sy)
        d_goal_recharge = abs(
            best[0] - world.recharger[0]) + abs(best[1] - world.recharger[1])

        if (d_self_goal + d_goal_recharge) > self.battery:
          return world.recharger
        return best
      else:
        return None

# ==========================
# CLASSE WORLD (MUNDO)
# ==========================


class World:
  def __init__(self, seed=None, headless=False):
    self.headless = headless  # Modo sem interface gráfica
    # Configuração do gerador aleatório
    if seed is not None:
      random.seed(seed)
    else:
      # Cria nova seed aleatória
      seed = random.randint(0, 10000000000000000)
      random.seed(seed)

    # Configurações do grid
    self.maze_size = 30       # Tamanho do grid (30x30)
    self.width = 1000         # Largura da janela
    self.height = 1000        # Altura da janela
    self.block_size = self.width // self.maze_size  # Tamanho de cada célula

    # Inicialização do mapa (0 = livre, 1 = obstáculo)
    self.map = [[0 for _ in range(self.maze_size)]
                for _ in range(self.maze_size)]

    # Geração de elementos do ambiente
    self.generate_obstacles()       # Cria obstáculos
    self.walls = []                 # Lista de paredes
    for row in range(self.maze_size):
      for col in range(self.maze_size):
        if self.map[row][col] == 1:
          self.walls.append((col, row))

    # Número total de itens (pacotes) a serem entregues
    self.total_items = random.randint(4, 10)

    # Geração dos locais de coleta (pacotes)
    self.packages = []
    # Aqui geramos 5 locais para coleta, garantindo uma opção extra
    while len(self.packages) < self.total_items:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      if self.map[y][x] == 0 and [x, y] not in self.packages:
        self.packages.append([x, y])

    # Geração dos locais de entrega (metas)
    self.goals = []
    while len(self.goals) < self.total_items:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      if self.map[y][x] == 0 and [x, y] not in self.goals and [x, y] not in self.packages:
        self.goals.append([x, y])

    # Cria o jogador usando a classe DefaultPlayer (pode ser substituído por outra implementação)
    self.player = self.generate_player()
    self.recharger = self.generate_recharger()

    # Geração de terrenos irregulares
    self.rough_terrains = []
    self.generate_rough_terrain()

    # Configuração gráfica se necessário
    if not self.headless:
      # Inicializa a janela do Pygame
      pygame.init()
      self.screen = pygame.display.set_mode((self.width, self.height))
      pygame.display.set_caption("Delivery Bot")

      # Carrega imagens para pacote, meta e recharger a partir de arquivos
      self.package_image = pygame.image.load("images/cargo.png")
      self.package_image = pygame.transform.scale(
          self.package_image, (self.block_size, self.block_size))

      self.goal_image = pygame.image.load("images/operator.png")
      self.goal_image = pygame.transform.scale(
          self.goal_image, (self.block_size, self.block_size))

      self.recharger_image = pygame.image.load("images/charging-station.png")
      self.recharger_image = pygame.transform.scale(
          self.recharger_image, (self.block_size, self.block_size))

    # Cores utilizadas para desenho (caso a imagem não seja usada)
    self.rough_color = (139, 69, 19)  # Cor para rough terrain
    self.wall_color = (100, 100, 100)
    self.ground_color = (255, 255, 255)
    self.player_color = (0, 255, 0)
    self.path_color = (200, 200, 0)

  def generate_rough_terrain(self):
    """Gera terrenos irregulares evitando sobreposições"""
    max_roughs = 50
    attempts = 0
    max_attempts = 1000  # Evita loop infinito

    while len(self.rough_terrains) < max_roughs and attempts < max_attempts:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      # Verifica se a posição está livre e não coincide com outras entidades
      if (self.map[y][x] == 0 and
          [x, y] not in self.packages and
          [x, y] not in self.goals and
          [x, y] != self.player.position and
              [x, y] != self.recharger):
        self.map[y][x] = 2
        self.rough_terrains.append((x, y))
      attempts += 1

  def generate_obstacles(self):
    """
    Gera obstáculos com sensação de linha de montagem:
     - Cria vários segmentos horizontais curtos com lacunas.
     - Cria vários segmentos verticais curtos com lacunas.
     - Cria um obstáculo em bloco grande (4x4 ou 6x6) simulando uma estrutura de suporte.
    """
    # Barragens horizontais curtas:
    for _ in range(7):
      row = random.randint(5, self.maze_size-6)
      start = random.randint(0, self.maze_size-10)
      length = random.randint(5, 10)
      for col in range(start, start+length):
        if random.random() < 0.7:
          self.map[row][col] = 1

    # Obstáculos verticais
    for _ in range(7):
      col = random.randint(5, self.maze_size-6)
      start = random.randint(0, self.maze_size-10)
      length = random.randint(5, 10)
      for row in range(start, start+length):
        if random.random() < 0.7:
          self.map[row][col] = 1

    # Bloco grande de obstáculos
    block_size = random.choice([4, 6])
    max_row = self.maze_size - block_size
    max_col = self.maze_size - block_size
    top_row = random.randint(0, max_row)
    top_col = random.randint(0, max_col)
    for r in range(top_row, top_row+block_size):
      for c in range(top_col, top_col+block_size):
        self.map[r][c] = 1

  def generate_player(self):
    """Gera o jogador em posição válida"""
    while True:
      x = random.randint(0, self.maze_size-1)
      y = random.randint(0, self.maze_size-1)
      if self.map[y][x] == 0 and [x, y] not in self.packages+self.goals:
        return DefaultPlayer([x, y])

  def generate_recharger(self):
    """Posiciona a estação de recarga próximo ao centro"""
    center = self.maze_size // 2
    while True:
      x = random.randint(center - 1, center + 1)
      y = random.randint(center - 1, center + 1)
      if self.map[y][x] == 0 and [x, y] not in self.packages and [x, y] not in self.goals and [x, y] != self.player.position:
        return [x, y]

  def can_move_to(self, pos):
    """Verifica se a posição é válida para movimento"""
    x, y = pos
    if 0 <= x < self.maze_size and 0 <= y < self.maze_size:
      return self.map[y][x] in (0, 2)  # Permite rough terrain
    return False

  def draw_world(self, path=None):
    """Renderiza o ambiente gráfico"""
    self.screen.fill(self.ground_color)
    # Desenha os obstáculos (paredes)
    for (x, y) in self.walls:
      rect = pygame.Rect(x * self.block_size, y *
                         self.block_size, self.block_size, self.block_size)
      pygame.draw.rect(self.screen, self.wall_color, rect)

    # Desenha rough terrains
    for (x, y) in self.rough_terrains:
      rect = pygame.Rect(x * self.block_size, y *
                         self.block_size, self.block_size, self.block_size)
      pygame.draw.rect(self.screen, self.rough_color, rect)

    # Desenha os locais de coleta (pacotes) utilizando a imagem
    for pkg in self.packages:
      x, y = pkg
      self.screen.blit(self.package_image,
                       (x * self.block_size, y * self.block_size))
    # Desenha os locais de entrega (metas) utilizando a imagem
    for goal in self.goals:
      x, y = goal
      self.screen.blit(
          self.goal_image, (x * self.block_size, y * self.block_size))
    # Desenha o recharger utilizando a imagem
    if self.recharger:
      x, y = self.recharger
      self.screen.blit(self.recharger_image,
                       (x * self.block_size, y * self.block_size))
    # Desenha o caminho, se fornecido
    if path:
      for pos in path:
        x, y = pos
        rect = pygame.Rect(x * self.block_size + self.block_size // 4,
                           y * self.block_size + self.block_size // 4,
                           self.block_size // 2, self.block_size // 2)
        pygame.draw.rect(self.screen, self.path_color, rect)
    # Desenha o jogador (retângulo colorido)
    x, y = self.player.position
    rect = pygame.Rect(x * self.block_size, y * self.block_size,
                       self.block_size, self.block_size)
    pygame.draw.rect(self.screen, self.player_color, rect)
    pygame.display.flip()

# ==========================
# CLASSE MAZE (CONTROLE DO JOGO)
# ==========================


class Maze:
  def __init__(self, seed=None, headless=False, output_file="results.csv"):
    self.headless = headless      # Modo sem gráficos
    self.world = World(seed, headless)  # Cria o ambiente
    self.running = True           # Controla o loop do jogo
    self.score = 0                # Pontuação atual
    self.steps = 0                # Passos realizados
    self.delay = 100              # Tempo entre movimentos (ms)
    self.path = []                # Caminho atual
    self.num_deliveries = 0       # Entregas concluídas
    self.output_file = output_file  # Arquivo de saída
    self.seed = seed              # Semente usada

  def heuristic(self, a, b):
    """Distância de Manhattan para o A*"""
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

  def astar(self, start, goal):
    """Implementação do algoritmo A* para pathfinding"""
    maze = self.world.map
    size = self.world.maze_size
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Movimentos possíveis

    # Estruturas para o algoritmo
    close_set = set()
    came_from = {}
    gscore = {tuple(start): 0}
    fscore = {tuple(start): self.heuristic(start, goal)}
    oheap = []
    heapq.heappush(oheap, (fscore[tuple(start)], tuple(start)))
    while oheap:
      current = heapq.heappop(oheap)[1]
      if list(current) == goal:
        data = []
        while current in came_from:
          data.append(list(current))
          current = came_from[current]
        data.reverse()
        return data
      close_set.add(current)
      for dx, dy in neighbors:
        neighbor = (current[0] + dx, current[1] + dy)
        tentative_g = gscore[current] + 1
        if 0 <= neighbor[0] < size and 0 <= neighbor[1] < size:
          # Parede, caminho bloqueado
          if maze[neighbor[1]][neighbor[0]] == 1:
            continue

          # Calcula custo do terreno (ROUGH_TERRAIN_COST para rough terrain, 1 para normal)
          terrain_cost = ROUGH_TERRAIN_COST if maze[neighbor[1]
                                                    ][neighbor[0]] == 2 else 1
        else:
          continue  # Fora dos limites do grid

        tentative_g = gscore[current] + terrain_cost
        if neighbor in close_set and tentative_g >= gscore.get(neighbor, 0):
          continue

        # Melhor caminho até então
        if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [i[1] for i in oheap]:
          came_from[neighbor] = current
          gscore[neighbor] = tentative_g
          fscore[neighbor] = tentative_g + self.heuristic(neighbor, goal)
          heapq.heappush(oheap, (fscore[neighbor], neighbor))
    return []

  def game_loop(self):
    """Loop principal do jogo"""
    while self.running:
      # Condição de vitória
      if (self.num_deliveries >= self.world.total_items and
              self.world.player.position == self.world.recharger):
        self.running = False
        break

      # Escolha do alvo pelo jogador
      target = self.world.player.escolher_alvo(self.world)
      if target is None:
        self.running = False
        break

      # Calcula caminho usando A*
      self.path = self.astar(self.world.player.position, target)
      if not self.path:
        self.running = False
        break

      # Movimentação pelo caminho
      for pos in self.path:
        self.world.player.position = pos
        self.steps += 1

        # Determina o custo do terreno
        x, y = pos
        cell_value = self.world.map[y][x]
        if cell_value == 2:
          terrain_cost = ROUGH_TERRAIN_COST  # ROUGH_TERRAIN_COST para rough terrain
        elif cell_value == 0:
          terrain_cost = 1

        # Atualiza bateria e pontuação
        self.world.player.battery -= terrain_cost
        if self.world.player.battery < 0:
          self.score -= (self.world.total_items - self.num_deliveries) * 25
          self.running = False
          break
        self.score -= terrain_cost

        # Recarrega na estação
        if pos == self.world.recharger:
          self.world.player.battery = 60

        # Atualiza a interface gráfica
        if not self.headless:
          self.world.draw_world(self.path)
          pygame.time.wait(self.delay)

      # Ao chegar ao alvo, processa a coleta ou entrega:
      if self.world.player.position == target:
        # Se for local de coleta, pega o pacote.
        if target in self.world.packages:
          self.world.player.cargo += 1
          self.world.packages.remove(target)
        # Se for local de entrega e o jogador tiver pelo menos um pacote, entrega.
        elif target in self.world.goals and self.world.player.cargo > 0:
          self.world.player.cargo -= 1
          self.num_deliveries += 1
          self.world.goals.remove(target)
          self.score += 50
    # Gravação dos resultados
    self._save_results()
    pygame.quit()

  def _save_results(self):
    """Salva os resultados em arquivo CSV"""
    file_exists = os.path.isfile(self.output_file)
    with open(self.output_file, 'a', newline='') as f:
      writer = csv.writer(f)
      if not file_exists:
        writer.writerow(['Seed', 'Score', 'Steps', 'Deliveries', 'Script'])
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

  maze = Maze(seed=args.seed, headless=args.headless, output_file=args.output)
  maze.game_loop()
