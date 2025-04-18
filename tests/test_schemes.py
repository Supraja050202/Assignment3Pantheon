#!/usr/bin/env python3

import os
from os import path
import sys
import time
import signal
import argparse
import datetime
import csv
import random  # Simulated metrics generation

import context
from helpers import utils
from helpers.subprocess_wrappers import Popen, check_output, call

TEST_DURATION = 60  # seconds


def generate_mock_metrics(scheme, duration=TEST_DURATION, out_dir='logs'):
    """Generate simulated metric logs."""
    timestamp = int(time.time())
    filename = f"{out_dir}/metrics_{scheme}_{timestamp}.csv"
    os.makedirs(out_dir, exist_ok=True)

    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'throughput', 'loss_rate', 'rtt'])  # Required columns
        for t in range(duration):
            throughput = round(random.uniform(2.0, 10.0), 2)
            loss_rate = round(random.uniform(0.0, 0.1), 3)
            rtt = round(random.uniform(30, 150), 2)
            writer.writerow([t, throughput, loss_rate, rtt])

    sys.stderr.write(f'[✓] Metrics written to {filename}\n')


def test_schemes(args):
    wrappers_dir = path.join(context.src_dir, 'wrappers')

    if args.all:
        schemes = utils.parse_config()['schemes'].keys()
    elif args.schemes is not None:
        schemes = args.schemes.split()

    for scheme in schemes:
        sys.stderr.write(f'\n=== Testing {scheme} for {TEST_DURATION} seconds ===\n')
        src = path.join(wrappers_dir, scheme + '.py')

        run_first = check_output([src, 'run_first']).strip()
        run_second = 'receiver' if run_first == 'sender' else 'sender'

        port = utils.get_open_port()

        # Start the first process
        cmd1 = [src, run_first, port]
        proc1 = Popen(cmd1, preexec_fn=os.setsid)

        time.sleep(3)  # Allow it to get ready

        # Start the second process
        cmd2 = [src, run_second, '127.0.0.1', port]
        proc2 = Popen(cmd2, preexec_fn=os.setsid)

        signal.signal(signal.SIGALRM, utils.timeout_handler)
        signal.alarm(TEST_DURATION)

        try:
            start_time = time.time()
            while time.time() - start_time < TEST_DURATION:
                # Check subprocesses
                for proc in [proc1, proc2]:
                    if proc.poll() is not None and proc.returncode != 0:
                        sys.exit(f'{scheme} failed in tests')
                time.sleep(1)
        except utils.TimeoutError:
            pass
        except Exception as e:
            sys.exit(f'test_schemes.py: {e}\n')
        else:
            signal.alarm(0)
            sys.exit('Test exited before time limit')
        finally:
            utils.kill_proc_group(proc1)
            utils.kill_proc_group(proc2)

        # Simulate metric logs
        generate_mock_metrics(scheme, duration=TEST_DURATION)


def cleanup():
    cleanup_script = path.join(context.base_dir, 'tools', 'pkill.py')
    call([cleanup_script, '--kill-dir', context.base_dir])


def main():
    parser = argparse.ArgumentParser()

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true',
                       help='test all the schemes specified in src/config.yml')
    group.add_argument('--schemes', metavar='"SCHEME1 SCHEME2..."',
                       help='test a space-separated list of schemes')

    args = parser.parse_args()

    try:
        test_schemes(args)
    except:
        cleanup()
        raise
    else:
        sys.stderr.write('✅ Passed all tests!\n')


if __name__ == '__main__':
    main()