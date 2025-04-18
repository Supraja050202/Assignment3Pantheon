Pantheon Congestion Control Analysis

This project provides tools and scripts for evaluating the performance of various congestion control algorithms using the Pantheon framework combined with MahiMahi for network emulation. The evaluation compares algorithms such as BBR, Vegas, and Vivace under different simulated network conditions to assess their behavior in terms of throughput, latency, and packet loss.


Project Highlights

Leverages Pantheon, a unified platform for congestion control research and testing.

Simulates realistic network conditions using MahiMahi.

Automates end-to-end experiment execution, result collection, and analysis.

Generates raw logs, CSV reports, and visual graphs for easy comparison.


Prerequisites

1. Ubuntu 20.04 or later

2. Python 3.8+

3. Git

4. MahiMahi network emulator


Installation

1. Clone the repository:

git clone https://github.com/Supraja050202/Assignment3Pantheon.git


2. Navigate to the project directory:

cd Assignment3Pantheon/pantheon/


3. Install dependencies:

Install required tools and dependencies.


4. Running Experiments:

To execute the experiments across different congestion control algorithms and profiles, simply run:

python3 results.py


5. Output Structure

Once experiments are completed, the following directories will be generated:

	a. Raw Logs

		Location: pantheon/logs/

		Description: Contains detailed logs of each experimental run.

	b. Graphs

		Location: pantheon/graphs/

		Description: Visual representation of:

				i. Throughput

				ii. Latency (RTT)

				iii. Packet Loss

	c. CSV Results: Contain quantitative experiment outputs for further statistical analysis.

	Network Profile	Output Path:

	High Latency Profile	pantheon/results/profile_high_latency/

	Low Latency Profile	pantheon/results/profile_low_latency/
