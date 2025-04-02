import subprocess  # Para executar processos
import pandas as pd  # Para manipulação e análise de dados
import matplotlib.pyplot as plt  # Para criação de gráficos
import argparse  # Para processar argumentos da linha de comando
import os  # Para operações com sistema de arquivos
# Para execução paralela
from concurrent.futures import ProcessPoolExecutor, as_completed
import random  # Para geração de números aleatórios
from datetime import datetime  # Para manipulação de datas/horas
import shutil  # Para operações avançadas com arquivos (como cópia)
import seaborn as sns  # Para visualização de dados (gráficos mais bonitos)


def create_unique_results_dir(base_dir="results"):
  """
  Cria um diretório de resultados único com timestamp para evitar sobrescrita de arquivos.

  Parâmetros:
      base_dir (str): Diretório base onde a pasta será criada (padrão: "results")

  Retorna:
      str: Caminho completo para o diretório criado
  """
  # Gera um timestamp no formato AAAAMMDD_HHMMSS
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  # Cria o caminho completo combinando base_dir com o timestamp
  results_dir = os.path.join(base_dir, f"run_{timestamp}")
  # Cria o diretório (e quaisquer pai necessário)
  os.makedirs(results_dir, exist_ok=True)
  return results_dir


def run_script(script, seed, output_csv):
  """
  Executa um script Python individual com os parâmetros especificados.

  Parâmetros:
      script (str): Caminho para o script Python a ser executado
      seed (int): Semente aleatória para reproduzibilidade
      output_csv (str): Arquivo CSV onde os resultados serão salvos
  """
  # Executa o script como um subprocesso com os parâmetros especificados
  subprocess.run([
      "python3", script,  # Comando para executar o script
      "--seed", str(seed),  # Passa a semente aleatória
      "--headless",  # Flag para modo headless (sem interface gráfica)
      "--output", output_csv  # Arquivo de saída para os resultados
  ])


def run_comparison(scripts, num_runs, output_csv, custom_seeds=None):
  """
  Executa a comparação entre múltiplos scripts em paralelo.

  Parâmetros:
      scripts (list): Lista de caminhos para scripts Python a comparar
      num_runs (int): Número de execuções quando usando seeds aleatórias
      output_csv (str): Nome do arquivo CSV de saída
      custom_seeds (list, opcional): Lista de seeds personalizadas para usar
  """
  # Cria um diretório único para os resultados desta execução
  results_dir = create_unique_results_dir()
  print(f"All results will be saved in: {results_dir}")

  # Cria o caminho completo para o arquivo CSV de saída
  full_output_csv = os.path.join(results_dir, output_csv)

  # Determina as seeds a serem usadas
  if custom_seeds:
    seeds = custom_seeds
    print(f"Using custom seeds: {seeds}")
  else:
    # Gera seeds aleatórias se nenhuma for fornecida
    seeds = [random.randint(0, 10**16) for _ in range(num_runs)]
    print(f"Generated random seeds: {seeds}")

  # Salva as seeds usadas em um arquivo para referência futura
  with open(os.path.join(results_dir, "seeds_used.txt"), "w") as f:
    f.write("\n".join(map(str, seeds)) + "\n")

  futures = []
  try:
    # Cria um pool de processos para execução paralela
    with ProcessPoolExecutor() as executor:
      # Para cada seed e cada script, agenda a execução
      for seed in seeds:
        for script in scripts:
          print(f"Running {script} with seed {seed}")
          futures.append(executor.submit(
              run_script, script, seed, full_output_csv))

      # Aguarda a conclusão de todas as execuções agendadas
      for future in as_completed(futures):
        future.result()

  except KeyboardInterrupt:
    # Trata interrupção do usuário (Ctrl+C)
    print("\nInterruption detected! Stopping remaining executions...")
    executor.shutdown(wait=False, cancel_futures=True)
    raise  # Re-lança a exceção para notificar o usuário

  finally:
    # Após todas execuções (ou interrupção), processa os resultados
    if os.path.exists(full_output_csv):
      print("Generating results with collected data...")
      plot_results(full_output_csv, results_dir)

      # Copia os scripts comparados para referência futura
      scripts_dir = os.path.join(results_dir, "scripts_compared")
      os.makedirs(scripts_dir, exist_ok=True)
      for script in scripts:
        try:
          shutil.copy2(script, scripts_dir)
        except Exception as e:
          print(f"Warning: Could not copy script {script}: {e}")
    else:
      print("No output CSV generated. Skipping results generation.")


def plot_results(csv_file, results_dir):
  """
  Gera um conjunto completo de visualizações para análise comparativa:
  - Gráficos de distribuição (boxplot, violinplot)
  - Gráficos de relação (scatter, regressão)
  - Visualizações agregadas (heatmap, barras)
  - Gráficos de eficiência (score/steps ratio)
  """
  try:
      # Leitura e preparação dos dados
    df = pd.read_csv(csv_file)

    if df.empty:
      print("No data found in CSV. Skipping plotting.")
      return

    # Filtra apenas seeds completas (executadas em todos scripts)
    script_counts = df.groupby('Seed')['Script'].nunique()
    num_scripts = df['Script'].nunique()
    complete_seeds = script_counts[script_counts == num_scripts].index.tolist()

    if not complete_seeds:
      print("No seeds were completed for all scripts. Skipping plotting.")
      return

    print(f"Using {len(complete_seeds)} complete seeds for analysis")
    filtered_df = df[df['Seed'].isin(complete_seeds)].copy()
    grouped = filtered_df.groupby(['Script', 'Seed']).mean().reset_index()
    grouped['Score/Steps'] = grouped['Score'] / grouped['Steps']

    # Configurações comuns
    plt.style.use('seaborn')
    plots_dir = os.path.join(results_dir, "advanced_plots")
    os.makedirs(plots_dir, exist_ok=True)
    colors = sns.color_palette("husl", num_scripts)

    # =====================================================================
    # 1. ANÁLISE DE DISTRIBUIÇÃO
    # =====================================================================

    # Boxplot comparativo
    plt.figure(figsize=(12, 6))
    sns.boxplot(data=grouped, x='Script', y='Score', palette=colors)
    plt.title('Distribuição de Scores por Script\n(Quartis e Outliers)')
    plt.xlabel('Script')
    plt.ylabel('Score')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(
        plots_dir, "1_score_distribution_boxplot.png"), dpi=300)
    plt.close()

    # Violin plot (distribuição de densidade)
    plt.figure(figsize=(12, 6))
    sns.violinplot(data=grouped, x='Script', y='Score', palette=colors,
                   inner='quartile', cut=0)
    plt.title('Densidade de Distribuição de Scores')
    plt.savefig(os.path.join(
        plots_dir, "2_score_density_violinplot.png"), dpi=300)
    plt.close()

    # =====================================================================
    # 2. ANÁLISE DE EFICIÊNCIA (SCORE/STEPS)
    # =====================================================================

    # Comparação de razão Score/Steps
    plt.figure(figsize=(12, 6))
    sns.barplot(data=grouped, x='Seed', y='Score/Steps', hue='Script',
                palette=colors, dodge=True)
    plt.title('Eficiência (Score/Steps) por Seed')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(plots_dir, "3_efficiency_by_seed.png"), dpi=300)
    plt.close()

    # Média de eficiência por script
    plt.figure(figsize=(10, 6))
    sns.pointplot(data=grouped, x='Script', y='Score/Steps',
                  palette=colors, ci=95, join=False)
    plt.title('Eficiência Média com Intervalo de Confiança (95%)')
    plt.savefig(os.path.join(plots_dir, "4_mean_efficiency_ci.png"), dpi=300)
    plt.close()

    # =====================================================================
    # 3. ANÁLISE DE RELAÇÕES ENTRE VARIÁVEIS
    # =====================================================================

    # Scatter plot com regressão linear
    g = sns.lmplot(data=grouped, x='Steps', y='Score', hue='Script',
                   height=6, aspect=1.5, palette=colors, ci=None,
                   scatter_kws={'s': 100, 'alpha': 0.7})
    plt.title('Relação entre Steps e Score\n(com Linhas de Regressão)')
    g.savefig(os.path.join(plots_dir, "5_steps_vs_score_regression.png"), dpi=300)
    plt.close()

    # Pairplot multivariado
    if num_scripts <= 5:  # Evita gráficos muito complexos
      sns.pairplot(grouped, vars=['Score', 'Steps', 'Score/Steps'],
                   hue='Script', palette=colors, height=3)
      plt.suptitle('Relações Multivariadas entre Métricas', y=1.02)
      plt.savefig(os.path.join(
          plots_dir, "6_multivariate_relationships.png"), dpi=300)
      plt.close()

    # =====================================================================
    # 4. VISUALIZAÇÕES AGREGADAS
    # =====================================================================

    # Heatmap de métricas normalizadas
    metrics = grouped.groupby(
        'Script')[['Score', 'Steps', 'Score/Steps']].mean()
    metrics_norm = (metrics - metrics.min()) / (metrics.max() - metrics.min())

    plt.figure(figsize=(10, 6))
    sns.heatmap(metrics_norm.T, annot=True, fmt=".2f", cmap="YlGnBu",
                linewidths=.5, cbar_kws={'label': 'Performance Normalizada'})
    plt.title('Comparação Relativa de Métricas (0-1)')
    plt.savefig(os.path.join(plots_dir, "7_metrics_heatmap.png"), dpi=300)
    plt.close()

    # Radar chart para comparação multivariada
    if num_scripts <= 6:  # Radar charts ficam confusos com muitos scripts
      from math import pi

      categories = metrics_norm.columns.tolist()
      N = len(categories)

      angles = [n / float(N) * 2 * pi for n in range(N)]
      angles += angles[:1]

      plt.figure(figsize=(8, 8))
      ax = plt.subplot(111, polar=True)
      ax.set_theta_offset(pi / 2)
      ax.set_theta_direction(-1)

      for idx, (script, row) in enumerate(metrics_norm.iterrows()):
        values = row.values.flatten().tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, linestyle='solid',
                label=script, color=colors[idx])
        ax.fill(angles, values, alpha=0.1, color=colors[idx])

      plt.xticks(angles[:-1], categories)
      ax.set_rlabel_position(0)
      plt.yticks([0.2, 0.4, 0.6, 0.8], ["20%", "40%",
                 "60%", "80%"], color="grey", size=7)
      plt.ylim(0, 1)
      plt.title('Perfil de Performance Relativa', pad=20)
      plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
      plt.savefig(os.path.join(plots_dir, "8_radar_chart.png"),
                  dpi=300, bbox_inches='tight')
      plt.close()

    # =====================================================================
    # 5. VISUALIZAÇÃO DE TENDÊNCIAS TEMPORAIS (se houver dados temporais)
    # =====================================================================
    if 'ExecutionTime' in grouped.columns:
      plt.figure(figsize=(12, 6))
      sns.lineplot(data=grouped, x='Seed', y='ExecutionTime', hue='Script',
                   palette=colors, marker='o')
      plt.title('Tempo de Execução por Seed')
      plt.xticks(rotation=45)
      plt.tight_layout()
      plt.savefig(os.path.join(
          plots_dir, "9_execution_time_trend.png"), dpi=300)
      plt.close()

    print(f"All advanced plots saved to: {plots_dir}")

  except Exception as e:
    print(f"Error in advanced plotting: {str(e)}")
    import traceback
    traceback.print_exc()


if __name__ == "__main__":
  # Configura o parser de argumentos da linha de comando
  parser = argparse.ArgumentParser(
      description="Compare multiple delivery bot scripts",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  # Argumentos esperados:
  parser.add_argument("scripts", nargs='+',
                      help="Scripts to compare (e.g. algo1.py algo2.py)")
  parser.add_argument("--runs", type=int, default=5,
                      help="Number of runs when using random seeds")
  parser.add_argument("--seeds", type=lambda s: [int(item) for item in s.split(',')],
                      help="Comma-separated list of seeds to use (overrides --runs)")
  parser.add_argument("--output", default="comparison.csv",
                      help="Output CSV file name (will be saved in the run folder)")

  # Processa os argumentos
  args = parser.parse_args()

  try:
    # Executa a comparação principal
    run_comparison(
        scripts=args.scripts,
        num_runs=args.runs,
        output_csv=args.output,
        custom_seeds=args.seeds
    )
  except KeyboardInterrupt:
    print("\nExecution was interrupted by user.")
  except Exception as e:
    print(f"\nAn error occurred: {e}")
