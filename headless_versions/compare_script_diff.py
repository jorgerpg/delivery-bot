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
  Gera visualizações completas com tratamento de erros robusto e estilos atualizados
  """
  try:
      # Configuração inicial com estilo moderno
    plt.style.use('seaborn-v0_8')  # Estilo compatível com versões recentes
    sns.set_theme(style="whitegrid")  # Configuração visual do Seaborn

    # Leitura e preparação dos dados
    df = pd.read_csv(csv_file)

    if df.empty:
      print("No data found in CSV. Skipping plotting.")
      return

    # Verificação de colunas obrigatórias
    required_columns = ['Script', 'Seed', 'Score', 'Steps']
    if not all(col in df.columns for col in required_columns):
      missing = [col for col in required_columns if col not in df.columns]
      print(f"Missing required columns: {missing}. Skipping plotting.")
      return

    # Filtra apenas seeds completas
    script_counts = df.groupby('Seed')['Script'].nunique()
    num_scripts = df['Script'].nunique()
    complete_seeds = script_counts[script_counts == num_scripts].index.tolist()

    if not complete_seeds:
      print("No seeds were completed for all scripts. Skipping plotting.")
      return

    print(f"Using {len(complete_seeds)} complete seeds for analysis")
    filtered_df = df[df['Seed'].isin(complete_seeds)].copy()

    # Cálculo de métricas adicionais
    filtered_df['Score/Steps'] = filtered_df['Score'] / filtered_df['Steps']
    grouped = filtered_df.groupby(['Script', 'Seed']).mean(
        numeric_only=True).reset_index()

    # Configurações de visualização
    plots_dir = os.path.join(results_dir, "analysis_plots")
    os.makedirs(plots_dir, exist_ok=True)
    palette = sns.color_palette("husl", num_scripts)

    # =====================================================================
    # VISUALIZAÇÕES PRINCIPAIS (com tratamento de erro individual)
    # =====================================================================

    def safe_plot(func, filename, **kwargs):
      """Helper function to make each plot safely"""
      try:
        func(**kwargs)
        plt.tight_layout()
        plt.savefig(os.path.join(plots_dir, filename), dpi=150)
        plt.close()
        print(f"Generated {filename}")
      except Exception as e:
        print(f"Failed to generate {filename}: {str(e)}")

    # 1. Boxplot de scores
    safe_plot(
        func=lambda: sns.boxplot(
            data=filtered_df, x='Script', y='Score', palette=palette),
        filename="1_score_distribution.png",
    )

    # 2. Violin plot de eficiência
    safe_plot(
        func=lambda: sns.violinplot(
            data=filtered_df, x='Script', y='Score/Steps', palette=palette),
        filename="2_efficiency_distribution.png",
    )

    # 3. Scatter plot com regressão
    safe_plot(
        func=lambda: sns.lmplot(
            data=filtered_df,
            x='Steps',
            y='Score',
            hue='Script',
            palette=palette,
            height=6,
            aspect=1.3,
            ci=None
        ),
        filename="3_steps_vs_score.png",
    )

    # 4. Heatmap de métricas
    safe_plot(
        func=lambda: (
            metrics := filtered_df.groupby('Script')[['Score', 'Steps', 'Score/Steps']].mean(),
            sns.heatmap(
                metrics.T,
                annot=True,
                fmt=".1f",
                cmap="Blues",
                linewidths=.5
            ),
            plt.title("Métricas Comparativas")
        ),
        filename="4_metrics_comparison.png",
    )

    # 5. Gráfico de barras agrupadas
    safe_plot(
        func=lambda: sns.barplot(
            data=grouped,
            x='Seed',
            y='Score',
            hue='Script',
            palette=palette
        ),
        filename="5_scores_by_seed.png",
    )

    print(f"All generated plots saved to: {plots_dir}")

  except Exception as e:
    print(f"Critical error in plot generation: {str(e)}")
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
