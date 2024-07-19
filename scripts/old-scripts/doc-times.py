import subprocess
import argparse
import os
import time

SOURCE_DIR = "/root/new-profiler/rest-api/source-files"

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
    # Convert time format `0m4.523s` to seconds
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

def main(opt_level):
    results = []
    for runtime in DOCKER_IMAGE_MAP:
        binary_file = f"2mm_{opt_level}_native" if runtime == "native" else f"2mm_{opt_level}.wasm"
        internal_time, external_time = measure_execution(runtime, binary_file)
        results.append({
            "binary": f"{binary_file} ({runtime})",
            "internal_time": internal_time,
            "external_time": external_time
        })

    # Output results to terminal
    for result in results:
        print(f"{result['binary']}: Internal Time = {result['internal_time']}s, External Time = {result['external_time']}s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure runtime for native and WASM binaries.")
    parser.add_argument("opt_level", type=int, help="Optimization level of the binaries")
    args = parser.parse_args()
    main(args.opt_level)

