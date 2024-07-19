import os
import time
import subprocess
import argparse
import json

# Directory setup
COMPILED_DIR = "/root/profiler/compiled"
RESULTS_DIR = "/root/profiler/results/times"

# Runtimes
RUNTIMES = ["wasmer", "wasmtime", "wavm", "iwasm"]

def check_file_exists(file_path):
    return os.path.isfile(file_path)

def run_native_file(file_path):
    start_time = time.perf_counter()
    process = subprocess.run(file_path, capture_output=True, text=True)
    end_time = time.perf_counter()

    if process.returncode != 0:
        print(f"Error executing native binary {file_path}: {process.stderr}")
    else:
        print(f"Native Execution Time: {end_time - start_time}s")

    return end_time - start_time

def run_wasm_file(runtime, file_path):
    command = {
        "wasmer": ["wasmer", file_path],
        "wasmtime": ["wasmtime", file_path],
        "wavm": ["wavm", "run", file_path],
        "iwasm": ["iwasm", file_path],
    }.get(runtime)

    if not command:
        raise ValueError("Unsupported runtime specified.")

    start_time = time.perf_counter()
    process = subprocess.run(command, capture_output=True, text=True)
    end_time = time.perf_counter()

    if process.returncode != 0:
        print(f"Error executing {file_path} with {runtime}: {process.stderr}")
    else:
        print(f"{runtime} Execution Time: {end_time - start_time}s")

    return end_time - start_time

def main(file_name, opt_level):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    execution_times = {}

    native_file = os.path.join(COMPILED_DIR, f"{file_name}_{opt_level}_native")
    wasm_file = os.path.join(COMPILED_DIR, f"{file_name}_{opt_level}.wasm")

    if check_file_exists(native_file):
        native_exec_time = run_native_file(native_file)
        execution_times[f"{file_name}_native"] = native_exec_time
    else:
        print(f"Native file {native_file} does not exist.")

    if check_file_exists(wasm_file):
        for runtime in RUNTIMES:
            wasm_exec_time = run_wasm_file(runtime, wasm_file)
            execution_times[f"{file_name}_{runtime}"] = wasm_exec_time
    else:
        print(f"WASM file {wasm_file} does not exist.")

    json_output_file = os.path.join(RESULTS_DIR, f"{file_name}_{opt_level}_times.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(execution_times, json_file, indent=4)

    print(f"Execution times saved to {json_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Measure execution times of a native binary and a WASM file.')
    parser.add_argument('file_name', type=str, help='Name of the file to execute')
    parser.add_argument('opt_level', type=int, choices=[0, 1, 2, 3], help='Optimization level (0, 1, 2, 3)')
    args = parser.parse_args()
    main(args.file_name, args.opt_level)

