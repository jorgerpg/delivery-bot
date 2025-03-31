import pygame
import random
import heapq
import sys
import argparse
from abc import ABC, abstractmethod

# ==========================
# CLASSES DE PLAYER
# ==========================

# Custo para passar por terreno irregular (rough terrain)
ROUGH_TERRAIN_COST = 2
RECHARGE_VALUE = 60  # Valor de recarga da bateria


class BasePlayer(ABC):
  """
  Classe base para o jogador (robô).
  Para criar uma nova estratégia de jogador, basta herdar dessa classe e implementar o método escolher_alvo.
  """

  def __init__(self, position):
    self.position = position  # Posição no grid [x, y]
    self.cargo = 0            # Número de pacotes atualmente carregados
    self.battery = 70         # Nível da bateria

  @abstractmethod
  def escolher_alvo(self, world):
    """
    Retorna o alvo (posição) que o jogador deseja ir.
    Recebe o objeto world para acesso a pacotes e metas.
    """
    pass


class DefaultPlayer(BasePlayer):
  """
  Implementação padrão do jogador.
  Se não estiver carregando pacotes (cargo == 0), escolhe o pacote mais próximo.
  Caso contrário, escolhe a meta (entrega) mais próxima.
  """

  def escolher_alvo(self, world):
    recharge_pos = world.recharger
    current_battery = self.battery
    current_pos = self.position

    # 1. Prioridade máxima para recarga se bateria < 10
    # if current_battery < 10:
    #   path, cost = world.astar(current_pos, recharge_pos)
    #   return (recharge_pos, path, cost)

    # 2. Se tem carga, verifica pacotes no caminho das metas
    if self.cargo > 0:
      # Loop sobre metas para verificar pacotes intermediários
      for goal in world.goals.copy():
        path_to_goal, _ = world.astar(current_pos, goal)
        for pos in path_to_goal:
          if pos in world.packages:
            # Coleta pacote no caminho
            pkg_path, pkg_cost = world.astar(current_pos, pos)
            return (pos, pkg_path, pkg_cost)

    # 3. Se ainda tem carga, escolhe a meta mais eficiente
    if self.cargo > 0:
      best_goal = None
      min_total_cost = float('inf')
      for goal in world.goals.copy():
        # Custo para meta + recarga pós-entrega
        path_to_goal, cost_to_goal = world.astar(current_pos, goal)
        path_to_recharge, cost_to_recharge = world.astar(goal, recharge_pos)
        total_cost = cost_to_goal + cost_to_recharge

        if total_cost <= current_battery and total_cost < min_total_cost:
          min_total_cost = total_cost
          best_goal = (goal, path_to_goal, cost_to_goal)

      if best_goal:
        return best_goal
      else:  # Bateria insuficiente → recarrega
        path, cost = world.astar(current_pos, recharge_pos)
        return (recharge_pos, path, cost)

    # 4. Sem carga: escolhe pacote + entrega + recarga
    else:
      best_pkg = None
      min_total = float('inf')
      for pkg in world.packages.copy():
        path_to_pkg, cost_to_pkg = world.astar(current_pos, pkg)
        best_goal_cost = float('inf')
        # Encontra o melhor custo pacote → meta → recarga
        for goal in world.goals.copy():
          path_pkg_to_goal, cost_pkg_to_goal = world.astar(pkg, goal)
          path_to_recharge, cost_to_recharge = world.astar(goal, recharge_pos)
          total = cost_to_pkg + cost_pkg_to_goal + cost_to_recharge
          best_goal_cost = min(best_goal_cost, total)

        if best_goal_cost <= current_battery and best_goal_cost < min_total:
          min_total = best_goal_cost
          best_pkg = (pkg, path_to_pkg, cost_to_pkg)

      # 5. Se nenhum pacote viável, tenta recarregar
      if best_pkg:
        return best_pkg
      else:
        if current_pos == recharge_pos:
          # Tenta pacotes a partir da recarga
          min_total = float('inf')
          for pkg in world.packages.copy():
            path_to_pkg, cost_to_pkg = world.astar(current_pos, pkg)
            path_pkg_to_recharge, cost_pkg_to_recharge = world.astar(
                pkg, recharge_pos)
            total_cost = cost_to_pkg + cost_pkg_to_recharge
            if total_cost <= current_battery and total_cost < min_total:
              min_total = total_cost
              best_pkg = (pkg, path_to_pkg, cost_to_pkg)
          if best_pkg:
            return best_pkg
        # Recarrega como última opção
        path, cost = world.astar(current_pos, recharge_pos)
        return (recharge_pos, path, cost)

# ==========================
# CLASSE WORLD (MUNDO)
# ==========================


class World:
  def __init__(self, seed=None):
    if seed is not None:
      random.seed(seed)

    else:
      # Cria nova seed aleatória
      seed = random.randint(0, 10000000000000000)
      random.seed(seed)

    print("Seed: ", seed)
    # Parâmetros do grid e janela
    self.maze_size = 30
    self.width = 1000
    self.height = 1000
    self.block_size = self.width // self.maze_size

    qnt_recharger = self.maze_size/30

    # Cria uma matriz 2D para planejamento de caminhos:
    # 0 = livre, 1 = obstáculo
    self.map = [[0 for _ in range(self.maze_size)]
                for _ in range(self.maze_size)]
    # Geração de obstáculos com padrão de linha (assembly line)
    self.generate_obstacles()
    # Gera a lista de paredes a partir da matriz
    self.walls = []
    for row in range(self.maze_size):
      for col in range(self.maze_size):
        if self.map[row][col] == 1:
          self.walls.append((col, row))

    # Número total de itens (pacotes) a serem entregues
    self.total_items = random.randint(4, 10)
    print("Itens a serem entregues: ", self.total_items)

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

    # Coloca o recharger (recarga de bateria) próximo ao centro (região 3x3)
    self.recharger = self.generate_recharger()

    # Gera rough terrain após todas as outras entidades para evitar sobreposição
    self.rough_terrains = []
    self.generate_rough_terrain()  # Adicione esta linha após generate_obstacles()

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
    """Gera rough terrain garantindo que não sobreponha pacotes, metas, jogador ou recarregador."""
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

    if len(self.rough_terrains) < max_roughs:
      print(
          f"Aviso: Apenas {len(self.rough_terrains)} rough terrains gerados.")

  def generate_obstacles(self):
    """
    Gera obstáculos com sensação de linha de montagem:
     - Cria vários segmentos horizontais curtos com lacunas.
     - Cria vários segmentos verticais curtos com lacunas.
     - Cria um obstáculo em bloco grande (4x4 ou 6x6) simulando uma estrutura de suporte.
    """
    # Barragens horizontais curtas:
    for _ in range(7):
      row = random.randint(5, self.maze_size - 6)
      start = random.randint(0, self.maze_size - 10)
      length = random.randint(5, 10)
      for col in range(start, start + length):
        if random.random() < 0.7:
          self.map[row][col] = 1

    # Barragens verticais curtas:
    for _ in range(7):
      col = random.randint(5, self.maze_size - 6)
      start = random.randint(0, self.maze_size - 10)
      length = random.randint(5, 10)
      for row in range(start, start + length):
        if random.random() < 0.7:
          self.map[row][col] = 1

    # Obstáculo em bloco grande: bloco de tamanho 4x4 ou 6x6.
    block_size = random.choice([4, 6])
    max_row = self.maze_size - block_size
    max_col = self.maze_size - block_size
    top_row = random.randint(0, max_row)
    top_col = random.randint(0, max_col)
    for r in range(top_row, top_row + block_size):
      for c in range(top_col, top_col + block_size):
        self.map[r][c] = 1

  def generate_player(self):
    # Cria o jogador em uma célula livre que não seja de pacote ou meta.
    while True:
      x = random.randint(0, self.maze_size - 1)
      y = random.randint(0, self.maze_size - 1)
      if self.map[y][x] == 0 and [x, y] not in self.packages and [x, y] not in self.goals:
        return DefaultPlayer([x, y])

  def generate_recharger(self):
    # Coloca o recharger próximo ao centro
    center = self.maze_size // 2
    while True:
      x = random.randint(center - 1, center + 1)
      y = random.randint(center - 1, center + 1)
      if self.map[y][x] == 0 and [x, y] not in self.packages and [x, y] not in self.goals and [x, y] != self.player.position:
        return [x, y]

  def can_move_to(self, pos):
    x, y = pos
    if 0 <= x < self.maze_size and 0 <= y < self.maze_size:
      return self.map[y][x] in (0, 2)  # Permite rough terrain
    return False

  def draw_world(self, path=None):
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

  def heuristic(self, a, b):
    base_cost = abs(a[0] - b[0]) + abs(a[1] - b[1])
    # Prioriza células com pacotes
    if self.map[a[1]][a[0]] == 2:
      return base_cost - 20
    return base_cost

  def astar(self, start, goal):
    maze = self.map
    size = self.maze_size
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
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
        total_cost = gscore[current]
        while current in came_from:
          data.append(list(current))
          current = came_from[current]
        data.reverse()
        return data, total_cost

      close_set.add(current)
      for dx, dy in neighbors:
        neighbor = (current[0] + dx, current[1] + dy)
        # Verifica se está dentro dos limites do grid
        if 0 <= neighbor[0] < size and 0 <= neighbor[1] < size:
          # Pula obstáculos intransponíveis (paredes)
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
        if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [i[1] for i in oheap]:
          came_from[neighbor] = current
          gscore[neighbor] = tentative_g
          fscore[neighbor] = tentative_g + self.heuristic(neighbor, goal)
          heapq.heappush(oheap, (fscore[neighbor], neighbor))

    return [], float('inf')

# ==========================
# CLASSE MAZE: Lógica do jogo e planejamento de caminhos (A*)
# ==========================


class Maze:
  def __init__(self, seed=None):
    self.world = World(seed)
    self.running = True
    self.score = 0
    self.steps = 0
    self.delay = 100
    self.path = []
    self.num_deliveries = 0

  def game_loop(self):
    # O jogo termina quando o número de entregas realizadas é igual ao total de itens.
    while self.running:
      if self.num_deliveries >= self.world.total_items:
        self.running = False
        break

      target, path, cost = self.world.player.escolher_alvo(self.world)

      if not path:
        print(
            f"Nenhum caminho encontrado para o alvo {target} custo: {cost}, path: {path}")
        self.running = False
        break

      self.path = path
      path_interrupted = False

      for pos in self.path:
        self.world.player.position = pos
        self.steps += 1

        # Verifica elementos na posição atual
        current_pos = self.world.player.position

        # Coleta dinâmica de pacotes
        if current_pos in self.world.packages:
          self.world.player.cargo += 1
          self.world.packages.remove(current_pos)
          print(f"Pacote coletado! Carga atual: {self.world.player.cargo}")
          path_interrupted = True

        # Entrega dinâmica
        if current_pos in self.world.goals and self.world.player.cargo > 0:
          self.world.player.cargo -= 1
          self.num_deliveries += 1
          self.world.goals.remove(current_pos)
          print(
              f"Entrega realizada! Total: {self.num_deliveries}/{self.world.total_items}")
          self.score += 50
          path_interrupted = True

        # Atualiza bateria
        x, y = current_pos
        cell_value = self.world.map[y][x]
        if cell_value == 2:
          terrain_cost = ROUGH_TERRAIN_COST  # ROUGH_TERRAIN_COST para rough terrain
        elif cell_value == 0:
          terrain_cost = 1

        # Atualiza bateria e pontuação
        self.world.player.battery -= terrain_cost
        if self.world.player.battery >= 0:
          self.score -= terrain_cost  # Penalidade proporcional ao terreno
        else:
          self.score -= 5  # Penalidade maior se bateria negativa

        # Verifica recarga
        if self.world.recharger and pos == self.world.recharger:
          self.world.player.battery = RECHARGE_VALUE
          print("Bateria recarregada!")

        # Atualiza tela
        self.world.draw_world(self.path)
        pygame.time.wait(self.delay)

        if path_interrupted:
          break  # Recalcula novo caminho
      print(f"Passos: {self.steps}, Pontuação: {self.score}, Cargo: {self.world.player.cargo}, Bateria: {self.world.player.battery}, Entregas: {self.num_deliveries}")

    print("Fim de jogo!")
    print(f"Pontuação final: {self.score}")
    print(f"Entregas: {self.num_deliveries}/{self.world.total_items}")
    pygame.quit()


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
  args = parser.parse_args()

  maze = Maze(seed=args.seed)
  maze.game_loop()
