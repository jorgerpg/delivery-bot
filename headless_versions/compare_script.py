import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import argparse
from concurrent.futures import ProcessPoolExecutor
import random


def run_script(script, seed, output_csv):
  subprocess.run([
      "python", script,
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

  with ProcessPoolExecutor() as executor:
    futures = []
    for seed in seeds:
      for script in scripts:
        futures.append(executor.submit(run_script, script, seed, output_csv))

    # Wait for all executions
    for future in futures:
      future.result()


def plot_results(csv_file):
  df = pd.read_csv(csv_file)

  # Agrupa por script e calcula a média
  grouped = df.groupby(['Script', 'Seed']).mean().reset_index()

  # Cria gráfico
  fig, ax = plt.subplots(4, 1, figsize=(12, 20))

  # Plot Scores
  scores = grouped.pivot(index='Seed', columns='Script', values='Score')
  scores.plot(kind='bar', ax=ax[0])
  ax[0].set_title('Comparison of Scores by Script')
  ax[0].set_ylabel('Score')
  ax[0].legend(title='Script')

  # Plot Steps
  steps = grouped.pivot(index='Seed', columns='Script', values='Steps')
  steps.plot(kind='bar', ax=ax[1])
  ax[1].set_title('Comparison of Steps by Script')
  ax[1].set_ylabel('Steps')
  ax[1].legend(title='Script')

  # Plot Score/Steps Ratio
  grouped['Score/Steps'] = grouped['Score'] / grouped['Steps']
  ratio = grouped.pivot(index='Seed', columns='Script', values='Score/Steps')
  ratio.plot(kind='bar', ax=ax[2])
  ax[2].set_title('Comparison of Score/Steps Ratio by Script')
  ax[2].set_ylabel('Score/Steps Ratio')
  ax[2].legend(title='Script')

  # Plot Average Score/Steps Ratio per Script
  avg_ratio = grouped.groupby('Script')['Score/Steps'].mean()
  avg_ratio.plot(kind='bar', ax=ax[3], color='skyblue')
  ax[3].set_title('Average Score/Steps Ratio by Script')
  ax[3].set_ylabel('Average Score/Steps Ratio')
  ax[3].set_xlabel('Script')

  plt.tight_layout()
  plt.savefig('comparison.png')
  plt.close()


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

  plot_results(args.output)
  print(f"\nResults saved to {args.output} and comparison.png")
