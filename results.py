#!/usr/bin/env python3

import os
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import shutil
import glob
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Configuration Classes
@dataclass
class NetworkProfile:
    latency: int
    dl_trace: str
    ul_trace: str

@dataclass
class TestResult:
    algorithm: str
    profile: str
    data: pd.DataFrame

class TestConfig:
    ALGORITHMS = ["bbr", "vivace", "vegas"]
    
    PROFILES = {
        "low_latency": NetworkProfile(5, 
                                    "mahimahi/traces/TMobile-LTE-driving.down",
                                    "mahimahi/traces/TMobile-LTE-driving.up"),
        "high_latency": NetworkProfile(200,
                                     "mahimahi/traces/TMobile-LTE-short.down",
                                     "mahimahi/traces/TMobile-LTE-short.up")
    }

class TestRunner:
    def __init__(self):
        self.results_dir = Path("results")
        self.graphs_dir = Path("graphs")
        self.logs_dir = Path("logs")
        self._setup_directories()
    
    def _setup_directories(self):
        self.results_dir.mkdir(exist_ok=True)
        self.graphs_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def _run_single_test(self, algorithm: str, profile: str, config: NetworkProfile):
        result_path = self.results_dir / f"profile_{profile}" / algorithm
        result_path.mkdir(parents=True, exist_ok=True)

        test_command = (
            f"mm-delay {config.latency} "
            f"mm-link {config.dl_trace} {config.ul_trace} -- "
            f"bash -c 'python3 tests/test_schemes.py --schemes \"{algorithm}\" > {result_path}/log.txt 2>&1'"
        )

        try:
            subprocess.run(test_command, shell=True, check=True)
            print(f"[SUCCESS] {algorithm.upper()} test completed for Profile {profile}")
        except subprocess.CalledProcessError as err:
            print(f"[ERROR] Test failed for {algorithm.upper()} (Profile {profile}): {err}")
            return None

        metric_logs = sorted(glob.glob(f"{self.logs_dir}/metrics_{algorithm}_*.csv"), 
                           key=os.path.getmtime, reverse=True)
        if metric_logs:
            newest_log = metric_logs[0]
            shutil.copy(newest_log, result_path / f"{algorithm}_cc_log.csv")
            print(f"[INFO] Metrics file saved for {algorithm.upper()} (Profile {profile})")
            return result_path / f"{algorithm}_cc_log.csv"
        else:
            print(f"[WARNING] No metrics file found for {algorithm.upper()} (Profile {profile})")
            return None

    def run_all_tests(self):
        test_results = []
        
        for profile_id, profile_config in TestConfig.PROFILES.items():
            print(f"\n--- Running tests for Network Profile {profile_id} (latency = {profile_config.latency} ms) ---")
            for algorithm in TestConfig.ALGORITHMS:
                print(f"[INFO] Testing congestion control algorithm: {algorithm.upper()}")
                result_file = self._run_single_test(algorithm, profile_id, profile_config)
                
                if result_file and result_file.exists():
                    df = pd.read_csv(result_file)
                    test_results.append(TestResult(algorithm, profile_id, df))
        
        return test_results

    def _prepare_data(self, test_results: List[TestResult]) -> pd.DataFrame:
        frames = []
        for result in test_results:
            df = result.data.copy()
            df["scheme"] = result.algorithm
            df["profile"] = result.profile
            df["timestamp"] = list(range(len(df)))
            frames.append(df)
        
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def generate_plots(self, combined_data: pd.DataFrame):
        if combined_data.empty:
            print("[ERROR] No data available for plotting")
            return

        self.color_map = {
            "bbr": "#8A2BE2",
            "vivace": "#DC143C",
            "vegas": "#32CD32"
        }

        plt.style.use("seaborn-v0_8-darkgrid")
        plt.rcParams.update({
            "figure.dpi": 150,
            "font.size": 12,
            "axes.labelsize": 14,
            "axes.titlesize": 16,
            "legend.fontsize": 10,
            "lines.linewidth": 2,
            "lines.markersize": 6
        })

        self._plot_throughput(combined_data)
        self._plot_loss_rate(combined_data)
        self._generate_rtt_summary(combined_data)
        self._plot_rtt_vs_throughput(combined_data)

    def _plot_throughput(self, data: pd.DataFrame):
        for profile in data['profile'].unique():
            plt.figure(figsize=(10, 6))
            for algorithm in data['scheme'].unique():
                subset = data[(data['scheme'] == algorithm) & (data['profile'] == profile)]
                plt.plot(subset['timestamp'], subset['throughput'], 
                         label=algorithm.upper(), 
                         color=self.color_map[algorithm], marker='o', linestyle='-', markersize=6)

            plt.title(f'Throughput Over Time - Profile: {profile}')
            plt.xlabel('Time (s)')
            plt.ylabel('Throughput (Mbps)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(self.graphs_dir / f'throughput_profile_{profile}.png')
            plt.close()
            print(f"[INFO] Generated throughput plot for Profile {profile}")

    def _plot_loss_rate(self, data: pd.DataFrame):
        if 'loss_rate' not in data.columns:
            print("[WARNING] No loss rate data available")
            return

        for profile in data['profile'].unique():
            plt.figure(figsize=(10, 6))
            for algorithm in data['scheme'].unique():
                subset = data[(data['scheme'] == algorithm) & (data['profile'] == profile)]
                plt.plot(subset['timestamp'], subset['loss_rate'], 
                         label=algorithm.upper(), 
                         color=self.color_map[algorithm], marker='x', linestyle='-', markersize=6)

            plt.title(f'Loss Rate Over Time - Profile: {profile}')
            plt.xlabel('Time (s)')
            plt.ylabel('Loss Rate')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(self.graphs_dir / f'loss_profile_{profile}.png')
            plt.close()
            print(f"[INFO] Generated loss rate plot for Profile {profile}")

    def _generate_rtt_summary(self, data: pd.DataFrame):
        rtt_records = []
        for profile in data['profile'].unique():
            for algorithm in data['scheme'].unique():
                subset = data[(data['scheme'] == algorithm) & (data['profile'] == profile)]
                if not subset.empty:
                    record = (
                        algorithm,
                        profile,
                        subset['rtt'].mean(),
                        subset['rtt'].quantile(0.95)
                    )
                    rtt_records.append(record)
        
        summary_df = pd.DataFrame(rtt_records, 
                                  columns=["Algorithm", "Profile", "Avg RTT", "95th RTT"])
        summary_df.to_csv(self.graphs_dir / "rtt_summary.csv", index=False)
        print("[INFO] Generated RTT summary statistics")

        # === Integrated Bar Chart for RTT Summary ===
        summary_df['Label'] = summary_df['Algorithm'] + '\n(' + summary_df['Profile'] + ')'
        x = range(len(summary_df))
        width = 0.35

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar([i - width/2 for i in x], summary_df['Avg RTT'], width, label='Avg RTT')
        ax.bar([i + width/2 for i in x], summary_df['95th RTT'], width, label='95th RTT')

        ax.set_ylabel('RTT (ms)')
        ax.set_title('Avg vs 95th-Percentile RTT by Algorithm and Profile')
        ax.set_xticks(list(x))
        ax.set_xticklabels(summary_df['Label'], rotation=45, ha='right')
        ax.legend()
        ax.grid(True, linestyle='--', axis='y', alpha=0.6)

        plt.tight_layout()
        plt.savefig(self.graphs_dir / "rtt_summary_plot.png")
        plt.close()
        print("[INFO] Saved RTT summary bar chart to graphs/rtt_summary_plot.png")

    def _plot_rtt_vs_throughput(self, data: pd.DataFrame):
        plt.figure(figsize=(10, 6))
        for profile in data['profile'].unique():
            for algorithm in data['scheme'].unique():
                subset = data[(data['scheme'] == algorithm) & (data['profile'] == profile)]
                if not subset.empty:
                    avg_rtt = subset['rtt'].mean()
                    avg_throughput = subset['throughput'].mean()
                    plt.plot(avg_rtt, avg_throughput, 
                             label=f'{algorithm.upper()}-{profile}', 
                             color=self.color_map[algorithm], marker='o', linestyle='-', markersize=6)

        plt.title("Avg Throughput vs Avg RTT")
        plt.xlabel("RTT (ms)")
        plt.ylabel("Throughput (Mbps)")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(self.graphs_dir / "rtt_vs_throughput.png")
        plt.close()
        print("[INFO] Generated RTT vs Throughput line plot")

def main():
    print("=== Congestion Control Algorithm Test Framework ===")
    
    runner = TestRunner()
    test_results = runner.run_all_tests()
    combined_data = runner._prepare_data(test_results)
    
    if not combined_data.empty:
        runner.generate_plots(combined_data)
        print("\n[COMPLETE] All tests finished and results saved")
    else:
        print("\n[ERROR] No valid test results were collected")

if __name__ == "__main__":
    main()