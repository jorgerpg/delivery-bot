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
  Gera gráficos comparativos a partir dos dados coletados, usando apenas seeds
  que foram executadas em todos os scripts para garantir comparação justa.
  """
  try:
      # Lê os dados do arquivo CSV
    df = pd.read_csv(csv_file)

    if df.empty:
      print("No data found in CSV. Skipping plotting.")
      return

    # Encontra as seeds completas (que foram executadas em todos os scripts)
    script_counts = df.groupby('Seed')['Script'].nunique()
    num_scripts = df['Script'].nunique()
    complete_seeds = script_counts[script_counts == num_scripts].index.tolist()

    if not complete_seeds:
      print("No seeds were completed for all scripts. Skipping plotting.")
      return

    print(f"Using only seeds completed for all scripts: {complete_seeds}")

    # Filtra o dataframe para manter apenas seeds completas
    filtered_df = df[df['Seed'].isin(complete_seeds)].copy()

    # Cria subdiretório para os gráficos
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # Agrupa os dados por Script e Seed, calculando médias
    grouped = filtered_df.groupby(['Script', 'Seed']).mean().reset_index()

    # 1. Gráfico de Scores (pontuações)
    scores = grouped.pivot(index='Seed', columns='Script', values='Score')
    fig, ax = plt.subplots(figsize=(12, 6))
    scores.plot(kind='bar', ax=ax)
    ax.set_title(
        'Comparison of Scores by Script\n(Only seeds completed for all scripts)')
    ax.set_ylabel('Score')
    ax.legend(title='Script')
    plt.tight_layout()
    score_path = os.path.join(plots_dir, "score.png")
    plt.savefig(score_path)
    plt.close()
    print(f"Score graph saved at {score_path}")

    # 2. Gráfico de Steps (passos/etapas)
    steps = grouped.pivot(index='Seed', columns='Script', values='Steps')
    fig, ax = plt.subplots(figsize=(12, 6))
    steps.plot(kind='bar', ax=ax)
    ax.set_title(
        'Comparison of Steps by Script\n(Only seeds completed for all scripts)')
    ax.set_ylabel('Steps')
    ax.legend(title='Script')
    plt.tight_layout()
    steps_path = os.path.join(plots_dir, "steps.png")
    plt.savefig(steps_path)
    plt.close()
    print(f"Steps graph saved at {steps_path}")

    # 3. Gráfico de Score/Steps Ratio (eficiência)
    grouped['Score/Steps'] = grouped['Score'] / grouped['Steps']
    ratio = grouped.pivot(index='Seed', columns='Script', values='Score/Steps')
    fig, ax = plt.subplots(figsize=(12, 6))
    ratio.plot(kind='bar', ax=ax)
    ax.set_title(
        'Comparison of Score/Steps Ratio by Script\n(Only seeds completed for all scripts)')
    ax.set_ylabel('Score/Steps Ratio')
    ax.legend(title='Script')
    plt.tight_layout()
    ratio_path = os.path.join(plots_dir, "score_steps_ratio.png")
    plt.savefig(ratio_path)
    plt.close()
    print(f"Score/Steps Ratio graph saved at {ratio_path}")

    # 4. Gráfico de Média do Score/Steps Ratio por Script
    avg_ratio = grouped.groupby('Script')['Score/Steps'].mean()
    fig, ax = plt.subplots(figsize=(12, 6))
    avg_ratio.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title(
        'Average Score/Steps Ratio by Script\n(Only seeds completed for all scripts)')
    ax.set_ylabel('Average Score/Steps Ratio')
    ax.set_xlabel('Script')
    plt.tight_layout()
    avg_ratio_path = os.path.join(plots_dir, "average_score_steps_ratio.png")
    plt.savefig(avg_ratio_path)
    plt.close()
    print(f"Average Score/Steps Ratio graph saved at {avg_ratio_path}")

    # Salva os dados processados para referência
    processed_data_path = os.path.join(results_dir, "processed_data.csv")
    grouped.to_csv(processed_data_path, index=False)
    print(f"Processed data saved at {processed_data_path}")

    # Salva também as seeds completas usadas
    complete_seeds_path = os.path.join(results_dir, "complete_seeds_used.txt")
    with open(complete_seeds_path, 'w') as f:
      f.write("\n".join(map(str, complete_seeds)) + "\n")
    print(f"Complete seeds list saved at {complete_seeds_path}")

  except Exception as e:
    print(f"Error while plotting results: {e}")


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
