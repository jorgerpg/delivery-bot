import pygame
import random
import heapq
import sys
import argparse
from abc import ABC, abstractmethod

# ==========================
# CLASSES DE PLAYER
# ==========================


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
    possible_targets = []
    buffer = 5  # Buffer para ações (pegar/entregar)

    if self.cargo == 0:
      possible_targets = world.packages.copy()
    else:
      possible_targets = world.goals.copy()

    best_target = None
    best_path = None
    min_total_cost = float('inf')
    collected_packages = []

    # Tentar coletar múltiplos pacotes em uma única viagem
    if self.cargo == 0 and world.packages:
      sorted_packages = sorted(
          world.packages, key=lambda p: world.heuristic(self.position, p))
      current_position = self.position
      current_battery = self.battery

      for pkg in sorted_packages:
        path_to_pkg = world.astar(current_position, pkg)
        if not path_to_pkg:
          continue
        cost_to_pkg = self.calculate_path_cost(path_to_pkg)

        # Simula pegar o pacote e continuar a busca
        collected_packages.append(pkg)
        current_position = pkg
        current_battery -= cost_to_pkg + 1  # +1 pelo ato de pegar

        if current_battery <= 0:
          break

      # Escolhe o ponto de entrega após coletar pacotes
      if collected_packages:
        best_delivery = None
        min_delivery_cost = float('inf')

        for goal in world.goals:
          path_to_goal = world.astar(current_position, goal)
          if not path_to_goal:
            continue
          cost_to_goal = self.calculate_path_cost(path_to_goal)

          path_to_recharger = world.astar(goal, world.recharger)
          if not path_to_recharger:
            continue
          cost_to_recharger = self.calculate_path_cost(path_to_recharger)

          total_cost = cost_to_goal + cost_to_recharger + buffer

          if total_cost <= current_battery and total_cost < min_delivery_cost:
            min_delivery_cost = total_cost
            best_delivery = goal
            best_path = path_to_goal

        if best_delivery:
          return (best_delivery, best_path)

    # Se não foi possível pegar múltiplos pacotes, segue lógica normal
    for target in possible_targets:
      path_to_target = world.astar(self.position, target)
      if not path_to_target:
        continue
      cost_to_target = self.calculate_path_cost(path_to_target)

      path_to_recharger = world.astar(target, world.recharger)
      if not path_to_recharger:
        continue
      cost_to_recharger = self.calculate_path_cost(path_to_recharger)

      total_cost = cost_to_target + cost_to_recharger + buffer

      if total_cost <= self.battery and total_cost < min_total_cost:
        min_total_cost = total_cost
        best_target = target
        best_path = path_to_target

    if best_target:
      return (best_target, best_path)
    else:
      path_to_recharger = world.astar(self.position, world.recharger)
      if path_to_recharger:
        cost = self.calculate_path_cost(path_to_recharger)
        if cost <= self.battery:
          return (world.recharger, path_to_recharger)
      return (None, None)

  def calculate_path_cost(self, path):
    """Retorna o custo total de um caminho ou infinito se o caminho for inválido."""
    return len(path) - 1 if path else float('inf')

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
    self.wall_color = (100, 100, 100)
    self.ground_color = (255, 255, 255)
    self.player_color = (0, 255, 0)
    self.path_color = (200, 200, 0)

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
      return self.map[y][x] == 0
    return False

  def draw_world(self, path=None):
    self.screen.fill(self.ground_color)
    # Desenha os obstáculos (paredes)
    for (x, y) in self.walls:
      rect = pygame.Rect(x * self.block_size, y *
                         self.block_size, self.block_size, self.block_size)
      pygame.draw.rect(self.screen, self.wall_color, rect)
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
    # Distância de Manhattan
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

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
        # Evitar sair do mapa
        else:
          continue
        # TODO: Entender
        if neighbor in close_set and tentative_g >= gscore.get(neighbor, 0):
          continue

        # Melhor caminho até então
        if tentative_g < gscore.get(neighbor, float('inf')) or neighbor not in [i[1] for i in oheap]:
          came_from[neighbor] = current
          gscore[neighbor] = tentative_g
          fscore[neighbor] = tentative_g + self.heuristic(neighbor, goal)
          heapq.heappush(oheap, (fscore[neighbor], neighbor))
    return []

# ==========================
# CLASSE MAZE: Lógica do jogo e planejamento de caminhos (A*)
# ==========================


class Maze:
  def __init__(self, seed=None):
    self.world = World(seed)
    self.running = True
    self.score = 0
    self.steps = 0
    self.delay = 100  # milissegundos entre movimentos
    self.path = []
    self.num_deliveries = 0  # contagem de entregas realizadas

  def game_loop(self):
    # O jogo termina quando o número de entregas realizadas é igual ao total de itens.
    while self.running:
      if self.num_deliveries >= self.world.total_items and ((abs(self.world.recharger[0] - self.world.player.position[0]) + abs(self.world.recharger[1] - self.world.player.position[1])) == 0):
        print("Entrou aqui: ", ((abs(self.world.recharger[0] - self.world.player.position[0]) + abs(
            self.world.recharger[1] - self.world.player.position[1]))))
        self.running = False
        break

      # Utiliza a estratégia do jogador para escolher o alvo

      target, path = self.world.player.escolher_alvo(self.world)
      if target is None:
        print("No more target")
        self.running = False
        break

      # Usa o path retornado pelo jogador
      self.path = path  # Não precisa chamar A* novamente!
      if not self.path:
        print("Nenhum caminho encontrado para o alvo", target)
        self.score -= 50
        self.running = False
        break

      # Segue o caminho calculado
      for pos in self.path:
        self.world.player.position = pos
        self.steps += 1
        # Consumo da bateria: -1 por movimento se bateria >= 0, caso contrário -5
        self.world.player.battery -= 1
        if self.world.player.battery >= 0:
          self.score -= 1
        else:
          self.running = False
          print("Bateria descarregada! Entregas faltantes: ",
                (self.world.total_items - self.num_deliveries))

          self.score -= (self.world.total_items - self.num_deliveries) * 25
          self.score -= 25
          break
        # Recarrega a bateria se estiver no recharger
        if self.world.recharger and pos == self.world.recharger:
          print("Chegou na estação de recarga com bateira em: ",
                self.world.player.battery)
          self.world.player.battery = 60
          print("Bateria recarregada!")
        self.world.draw_world(self.path)
        pygame.time.wait(self.delay)

      # Ao chegar ao alvo, processa a coleta ou entrega:
      if self.world.player.position == target:
        # Se for local de coleta, pega o pacote.
        if target in self.world.packages:
          self.world.player.cargo += 1
          self.world.packages.remove(target)
          print("Pacote coletado em", target,
                "Cargo agora:", self.world.player.cargo)
        # Se for local de entrega e o jogador tiver pelo menos um pacote, entrega.
        elif target in self.world.goals and self.world.player.cargo > 0:
          self.world.player.cargo -= 1
          self.num_deliveries += 1
          self.world.goals.remove(target)
          self.score += 50
          print("Pacote entregue em", target,
                "Cargo agora:", self.world.player.cargo)
      print(f"Passos: {self.steps}, Pontuação: {self.score}, Cargo: {self.world.player.cargo}, Bateria: {self.world.player.battery}, Entregas: {self.num_deliveries}")

    print("Fim de jogo!")
    print("Pontuação final:", self.score)
    print("Total de passos:", self.steps)
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
