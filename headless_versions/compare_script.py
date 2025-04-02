import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
import random


def run_script(script, seed, output_csv):
  subprocess.run([
      "python3", script,
      "--seed", str(seed),
      "--headless",
      "--output", output_csv
  ])


def run_comparison(scripts, num_runs, output_csv, custom_seeds=None):
  if custom_seeds:
    seeds = custom_seeds
    print(f"Using custom seeds: {seeds}")
  else:
    seeds = [random.randint(0, 10**16) for _ in range(num_runs)]
    print(f"Generated random seeds: {seeds}")

  futures = []
  try:
    with ProcessPoolExecutor() as executor:
      for seed in seeds:
        for script in scripts:
          print(f"Running {script} with seed {seed}")
          futures.append(executor.submit(run_script, script, seed, output_csv))

      # Aguardar a conclusão das execuções
      for future in as_completed(futures):
        future.result()

  except KeyboardInterrupt:
    print("\nInterruption detected! Stopping remaining executions...")
    executor.shutdown(wait=False, cancel_futures=True)

  finally:
    print("Generating results with collected data...")
    plot_results(output_csv)


def plot_results(csv_file):
  try:
    df = pd.read_csv(csv_file)

    if df.empty:
      print("No data found in CSV. Skipping plotting.")
      return

    # Criar pasta results para armazenar os gráficos
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

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
    score_path = os.path.join(results_dir, "score.png")
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
    steps_path = os.path.join(results_dir, "steps.png")
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
    ratio_path = os.path.join(results_dir, "score_steps_ratio.png")
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
    avg_ratio_path = os.path.join(results_dir, "average_score_steps_ratio.png")
    plt.savefig(avg_ratio_path)
    plt.close()
    print(f"Average Score/Steps Ratio graph saved at {avg_ratio_path}")

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
                      help="Output CSV file name")

  args = parser.parse_args()

  run_comparison(
      scripts=args.scripts,
      num_runs=args.runs,
      output_csv=args.output,
      custom_seeds=args.seeds
  )

  print(
      f"\nResults saved to {args.output} and all graphs saved in the 'results' folder.")
