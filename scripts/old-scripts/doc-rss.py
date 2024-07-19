import subprocess
import argparse
import os
import time

# Docker images for WASM runtimes
DOCKER_IMAGE_MAP = {
    "wasmer": "bathork1391/wasmer-runtime:from-scratch",
    "wasmtime": "bathork1391/wasmtime-runtime:from-scratch",
    "wavm": "bathork1391/wavm-runtime:from-scratch",
    "iwasm": "bathork1391/iwasm-full:from-scratch"
}

NATIVE_IMAGE = "bathork1391/clang-wasi:clang_with_wasi"

SOURCE_DIR = "/root/new-profiler/rest-api/source-files"
INTERVAL = 0.05  # RSS monitoring interval in seconds

def run_and_monitor_native(file_path, source_dir, image, interval):
    monitor_command = f"""
    start_time=$(date +%s.%N)
    ./{file_path} &
    app_pid=$!
    sleep {interval}
    while [ -e /proc/$app_pid ]; do 
        rss=$(grep VmRSS /proc/$app_pid/status | awk '{{print $2}}')
        if [[ ! -z "$rss" ]]; then
            echo $rss
        fi
        sleep {interval}
    done
    end_time=$(date +%s.%N)
    echo "start_time:$start_time"
    echo "end_time:$end_time"
    """

    command = [
        "docker", "run", "--rm", "-v", f"{source_dir}:/app", "-w", "/app",
        image, "/bin/bash", "-c", monitor_command
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error executing the container with file {file_path}")
        print(stderr.strip())
        return

    parse_and_display_results(stdout, file_path)

def run_and_monitor_wasm(runtime, wasm_file, source_dir, interval):
    wasm_run_command = f"{runtime} /app/{wasm_file}" if runtime != "wavm" else f"wavm run /app/{wasm_file}"

    monitor_command = f"""
    start_time=$(date +%s.%N)
    {wasm_run_command} &
    app_pid=$!
    while [ -e /proc/$app_pid ]; do 
        rss=$(grep VmRSS /proc/$app_pid/status | awk '{{print $2}}')
        if [[ ! -z "$rss" ]]; then
            echo $rss
        fi
        sleep {interval}
    done
    wait $app_pid
    end_time=$(date +%s.%N)
    echo "start_time:$start_time"
    echo "end_time:$end_time"
    """

    command = [
        "docker", "run", "--rm", "-v", f"{source_dir}:/app", DOCKER_IMAGE_MAP[runtime],
        "/bin/bash", "-c", monitor_command
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()

    if process.returncode != 0:
        print(f"Error executing the container with file {wasm_file} using {runtime}")
        print(stderr.strip())
        return

    parse_and_display_results(stdout, f"{runtime} {wasm_file}")

def parse_and_display_results(stdout, file_desc):
    lines = stdout.strip().split('\n')
    start_time = end_time = None
    rss_values = []

    for line in lines:
        if line.startswith("start_time:"):
            start_time = float(line.split(':')[1])
        elif line.startswith("end_time:"):
            end_time = float(line.split(':')[1])
        else:
            rss_values.append(int(line) if line.isdigit() else 0)

    if not start_time or not end_time or not rss_values:
        print(f"Failed to capture necessary data from container for {file_desc}.")
        return

    total_time = end_time - start_time
    sum_rss = sum(rss_values)
    max_rss = max(rss_values)
    avg_rss = sum_rss / len(rss_values) if rss_values else 0
    rss_rate = sum_rss / total_time if total_time > 0 else 0

    print(f"File: {file_desc}")
    print(f"Sum of RSS: {sum_rss} KB")
    print(f"Average RSS: {avg_rss} KB")
    print(f"Maximum RSS: {max_rss} KB")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Sum of RSS divided by total time: {rss_rate:.2f} KB/s")
    print(f"Average RSS divided by total time: {avg_rss / total_time:.2f} KB/s")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file_index', type=int, choices=range(4), help='Index of the file to run (0-3).')
    args = parser.parse_args()

    native_file = f"2mm_{args.file_index}_native"
    wasm_file = f"2mm_{args.file_index}.wasm"

    run_and_monitor_native(native_file, SOURCE_DIR, NATIVE_IMAGE, INTERVAL)
    for runtime in DOCKER_IMAGE_MAP.keys():
        run_and_monitor_wasm(runtime, wasm_file, SOURCE_DIR, INTERVAL)

if __name__ == "__main__":
    main()

