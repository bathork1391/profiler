import subprocess
import argparse
import os
import time
import json

# Docker images for WASM runtimes
DOCKER_IMAGE_MAP = {
    "wasmer": "bathork1391/wasmer-runtime:from-scratch",
    "wasmtime": "bathork1391/wasmtime-runtime:from-scratch",
    "wavm": "bathork1391/wavm-runtime:from-scratch",
    "iwasm": "bathork1391/iwasm-full:from-scratch"
}

NATIVE_IMAGE = "bathork1391/clang-wasi:clang_with_wasi"

SOURCE_DIR = "/root/profiler/compiled"
RESULTS_DIR = "/root/profiler/results/doc_rss"
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

    return parse_results(stdout, file_path)

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

    return parse_results(stdout, f"{runtime} {wasm_file}")

def parse_results(stdout, file_desc):
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

    print(f"Intermediate results for file: {file_desc}")
    print(f"Sum of RSS: {sum_rss} KB")
    print(f"Average RSS: {avg_rss} KB")
    print(f"Maximum RSS: {max_rss} KB")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Sum of RSS divided by total time: {rss_rate:.2f} KB/s")
    print(f"Average RSS divided by total time: {avg_rss / total_time:.2f} KB/s")
    print("\n")

    return {
        "sum_rss": sum_rss,
        "avg_rss": avg_rss,
        "max_rss": max_rss,
        "total_time": total_time,
        "rss_rate": rss_rate,
        "avg_rss_rate": avg_rss / total_time if total_time > 0 else 0
    }

def main(file_name, opt_level):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    native_file = f"{file_name}_{opt_level}_native"
    wasm_file = f"{file_name}_{opt_level}.wasm"
    
    results = {
        "native": run_and_monitor_native(native_file, SOURCE_DIR, NATIVE_IMAGE, INTERVAL),
        "wasm": {}
    }

    for runtime in DOCKER_IMAGE_MAP.keys():
        results["wasm"][runtime] = run_and_monitor_wasm(runtime, wasm_file, SOURCE_DIR, INTERVAL)
    
    json_output_file = os.path.join(RESULTS_DIR, f"{file_name}_{opt_level}_doc_rss.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(results, json_file, indent=4)
    
    print(f"RSS results saved to {json_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file_name', type=str, help='Name of the file to run')
    parser.add_argument('opt_level', type=int, help='Optimization level of the file')
    args = parser.parse_args()

    main(args.file_name, args.opt_level)

