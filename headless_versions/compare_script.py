import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
from datetime import datetime
import shutil


def create_unique_results_dir(base_dir="results"):
  """Cria um diretório de resultados único com timestamp"""
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  results_dir = os.path.join(base_dir, f"run_{timestamp}")
  os.makedirs(results_dir, exist_ok=True)
  return results_dir


def run_script(script, seed, output_csv):
  subprocess.run([
      "python3", script,
      "--seed", str(seed),
      "--headless",
      "--output", output_csv
  ])


def run_comparison(scripts, num_runs, output_csv, custom_seeds=None):
  # Criar diretório único para esta execução
  results_dir = create_unique_results_dir()
  print(f"All results will be saved in: {results_dir}")

  # Caminho completo para o CSV de saída
  full_output_csv = os.path.join(results_dir, output_csv)

  if custom_seeds:
    seeds = custom_seeds
    print(f"Using custom seeds: {seeds}")
  else:
    seeds = [random.randint(0, 10**16) for _ in range(num_runs)]
    print(f"Generated random seeds: {seeds}")

  # Salvar as seeds usadas para referência futura
  with open(os.path.join(results_dir, "seeds_used.txt"), "w") as f:
    f.write("\n".join(map(str, seeds)) + "\n")

  futures = []
  try:
    with ProcessPoolExecutor() as executor:
      for seed in seeds:
        for script in scripts:
          print(f"Running {script} with seed {seed}")
          futures.append(executor.submit(
              run_script, script, seed, full_output_csv))

      # Aguardar a conclusão das execuções
      for future in as_completed(futures):
        future.result()

  except KeyboardInterrupt:
    print("\nInterruption detected! Stopping remaining executions...")
    executor.shutdown(wait=False, cancel_futures=True)
    raise  # Re-lança a exceção para que o usuário saiba que foi interrompido

  finally:
    if os.path.exists(full_output_csv):
      print("Generating results with collected data...")
      plot_results(full_output_csv, results_dir)

      # Copiar os scripts comparados para referência
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
  try:
    df = pd.read_csv(csv_file)

    if df.empty:
      print("No data found in CSV. Skipping plotting.")
      return

    # Criar subpasta para os gráficos
    plots_dir = os.path.join(results_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    # Agrupa por script e calcula a média
    grouped = df.groupby(['Script', 'Seed']).mean().reset_index()

    # Gráfico de Scores
    scores = grouped.pivot(index='Seed', columns='Script', values='Score')
    fig, ax = plt.subplots(figsize=(12, 6))
    scores.plot(kind='bar', ax=ax)
    ax.set_title('Comparison of Scores by Script')
    ax.set_ylabel('Score')
    ax.legend(title='Script')
    plt.tight_layout()
    score_path = os.path.join(plots_dir, "score.png")
    plt.savefig(score_path)
    plt.close()
    print(f"Score graph saved at {score_path}")

    # Gráfico de Steps
    steps = grouped.pivot(index='Seed', columns='Script', values='Steps')
    fig, ax = plt.subplots(figsize=(12, 6))
    steps.plot(kind='bar', ax=ax)
    ax.set_title('Comparison of Steps by Script')
    ax.set_ylabel('Steps')
    ax.legend(title='Script')
    plt.tight_layout()
    steps_path = os.path.join(plots_dir, "steps.png")
    plt.savefig(steps_path)
    plt.close()
    print(f"Steps graph saved at {steps_path}")

    # Gráfico de Score/Steps Ratio
    grouped['Score/Steps'] = grouped['Score'] / grouped['Steps']
    ratio = grouped.pivot(index='Seed', columns='Script', values='Score/Steps')
    fig, ax = plt.subplots(figsize=(12, 6))
    ratio.plot(kind='bar', ax=ax)
    ax.set_title('Comparison of Score/Steps Ratio by Script')
    ax.set_ylabel('Score/Steps Ratio')
    ax.legend(title='Script')
    plt.tight_layout()
    ratio_path = os.path.join(plots_dir, "score_steps_ratio.png")
    plt.savefig(ratio_path)
    plt.close()
    print(f"Score/Steps Ratio graph saved at {ratio_path}")

    # Gráfico de Média do Score/Steps Ratio por Script
    avg_ratio = grouped.groupby('Script')['Score/Steps'].mean()
    fig, ax = plt.subplots(figsize=(12, 6))
    avg_ratio.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title('Average Score/Steps Ratio by Script')
    ax.set_ylabel('Average Score/Steps Ratio')
    ax.set_xlabel('Script')
    plt.tight_layout()
    avg_ratio_path = os.path.join(plots_dir, "average_score_steps_ratio.png")
    plt.savefig(avg_ratio_path)
    plt.close()
    print(f"Average Score/Steps Ratio graph saved at {avg_ratio_path}")

    # Salvar dados processados para referência
    processed_data_path = os.path.join(results_dir, "processed_data.csv")
    grouped.to_csv(processed_data_path, index=False)
    print(f"Processed data saved at {processed_data_path}")

  except Exception as e:
    print(f"Error while plotting results: {e}")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Compare multiple delivery bot scripts",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument("scripts", nargs='+',
                      help="Scripts to compare (e.g. algo1.py algo2.py)")
  parser.add_argument("--runs", type=int, default=5,
                      help="Number of runs when using random seeds")
  parser.add_argument("--seeds", type=lambda s: [int(item) for item in s.split(',')],
                      help="Comma-separated list of seeds to use (overrides --runs)")
  parser.add_argument("--output", default="comparison.csv",
                      help="Output CSV file name (will be saved in the run folder)")

  args = parser.parse_args()

  try:
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
