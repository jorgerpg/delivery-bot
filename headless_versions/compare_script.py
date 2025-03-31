import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import random


def run_comparison(scripts, num_runs, output_csv):
  seeds = [random.randint(0, 10**16) for _ in range(num_runs)]

  for seed in seeds:
    for script in scripts:
      subprocess.run([
          "python", script,
          "--seed", str(seed),
          "--headless",
          "--output", output_csv
      ])


def plot_results(csv_file):
  df = pd.read_csv(csv_file)

  # Agrupa por script e calcula a média
  grouped = df.groupby(['Script', 'Seed']).mean().reset_index()

  # Cria gráfico
  fig, ax = plt.subplots(3, 1, figsize=(12, 15))

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

  plt.tight_layout()
  plt.savefig('comparison.png')
  plt.close()


if __name__ == "__main__":
  parser = argparse.ArgumentParser(
      description="Compare multiple delivery bot scripts")
  parser.add_argument("scripts", nargs='+', help="List of scripts to compare")
  parser.add_argument("--runs", type=int, default=5,
                      help="Number of runs per seed")
  parser.add_argument("--output", default="comparison.csv",
                      help="Output CSV file")

  args = parser.parse_args()

  run_comparison(args.scripts, args.runs, args.output)
  plot_results(args.output)
  print(f"Results saved to {args.output} and comparison.png")
