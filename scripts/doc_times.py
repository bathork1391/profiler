import subprocess
import argparse
import os
import time
import json

SOURCE_DIR = "/root/profiler/compiled"
RESULTS_DIR = "/root/profiler/results/doc_times"

DOCKER_IMAGE_MAP = {
    "wasmer": "bathork1391/wasmer-runtime:from-scratch",
    "wasmtime": "bathork1391/wasmtime-runtime:from-scratch",
    "wavm": "bathork1391/wavm-runtime:from-scratch",
    "iwasm": "bathork1391/iwasm-full:from-scratch",
    "native": "bathork1391/clang-wasi:clang_with_wasi"
}

def run_command(command):
    start = time.time()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    end = time.time()
    return stdout.decode().strip(), stderr.decode().strip(), end - start

def convert_time_to_seconds(time_str):
    minutes, seconds = time_str.split('m')
    seconds = seconds.rstrip('s')
    return int(minutes) * 60 + float(seconds)

def measure_execution(runtime, binary_file):
    app_path = f"/app/{binary_file}"
    cmd = f"docker run --rm -v {SOURCE_DIR}:/app {DOCKER_IMAGE_MAP[runtime]} "
    
    if runtime == "wavm":
        cmd += f"/bin/bash -c 'time wavm run {app_path}'"
    elif runtime in ["wasmer", "wasmtime", "iwasm"]:
        cmd += f"/bin/bash -c 'time {runtime} {app_path}'"
    else:
        cmd += f"/bin/bash -c 'time ./{binary_file}'"  # for native

    stdout, stderr, external_time = run_command(cmd)
    internal_time = None

    for line in stderr.splitlines():
        if 'real' in line:
            internal_time = convert_time_to_seconds(line.split()[1])

    return internal_time, external_time

def main(file_name, opt_level):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    results = []
    for runtime in DOCKER_IMAGE_MAP:
        binary_file = f"{file_name}_{opt_level}_native" if runtime == "native" else f"{file_name}_{opt_level}.wasm"
        if not os.path.exists(os.path.join(SOURCE_DIR, binary_file)):
            print(f"File {binary_file} does not exist in {SOURCE_DIR}")
            continue
        print(f"Running {binary_file} on {runtime}...")
        internal_time, external_time = measure_execution(runtime, binary_file)
        results.append({
            "binary": f"{binary_file} ({runtime})",
            "internal_time": internal_time,
            "external_time": external_time
        })
        print(f"{binary_file} ({runtime}): Internal Time = {internal_time}s, External Time = {external_time}s")

    # Save results to JSON file
    json_output_file = os.path.join(RESULTS_DIR, f"{file_name}_{opt_level}_doc_times.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print(f"Execution times saved to {json_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure runtime for native and WASM binaries.")
    parser.add_argument("file_name", type=str, help="Name of the file to execute")
    parser.add_argument("opt_level", type=int, help="Optimization level of the binaries")
    args = parser.parse_args()
    main(args.file_name, args.opt_level)

