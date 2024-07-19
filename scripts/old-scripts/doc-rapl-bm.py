import subprocess
import time
import os
import sys

# Constants
RAPL_PATH = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
ITERATIONS = 2
SOURCE_DIR = "/root/new-profiler/rest-api/source-files"
DOCKER_IMAGE_MAP = {
    "wasmer": "bathork1391/wasmer-runtime:from-scratch",
    "wasmtime": "bathork1391/wasmtime-runtime:from-scratch",
    "wavm": "bathork1391/wavm-runtime:from-scratch",
    "iwasm": "bathork1391/iwasm-full:from-scratch",
    "clang_wasi": "bathork1391/clang-wasi:clang_with_wasi"  # Updated image for native files
}

def read_energy():
    with open(RAPL_PATH, 'r') as f:
        return int(f.read().strip())

def execute_command(image, command, cpu_core='0'):
    start_energy = read_energy()
    start_time = time.time()
    # Execute the command in a Docker container with CPU affinity
    docker_command = f"docker run --rm --cpuset-cpus=\"{cpu_core}\" -v {SOURCE_DIR}:/app {image} /bin/bash -c \"{command}\""
    subprocess.run(docker_command, shell=True, check=True)
    end_time = time.time()
    end_energy = read_energy()
    energy_used = end_energy - start_energy  # Energy in microjoules
    time_taken = end_time - start_time  # Time in seconds
    power_used = (energy_used / 1e6) / time_taken  # Energy in Joules, Power in Watts
    return energy_used, power_used

def average_measurements(measurements):
    average_energy = sum([m[0] for m in measurements]) / len(measurements)
    average_power = sum([m[1] for m in measurements]) / len(measurements)
    return average_energy, average_power

def run_native(file_index):
    native_file = f"2mm_{file_index}_native"
    measurements = []
    for _ in range(ITERATIONS):
        command = f"./{native_file}"
        measurements.append(execute_command(DOCKER_IMAGE_MAP['clang_wasi'], command))
    average_energy, average_power = average_measurements(measurements)
    print(f"{native_file}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")

def run_wasm(file_index):
    wasm_file = f"2mm_{file_index}.wasm"
    for runtime in DOCKER_IMAGE_MAP.keys():
        if runtime == "clang_wasi":
            continue  # Skip native image for WASM processing
        measurements = []
        for _ in range(ITERATIONS):
            if runtime == 'wavm':
                # For wavm, adjust the path to the wasm file
                command = f"wavm run /app/{wasm_file}"
            else:
                # Adjust the path for other runtimes
                command = f"{runtime} /app/{wasm_file}"
            measurements.append(execute_command(DOCKER_IMAGE_MAP[runtime], command))
        average_energy, average_power = average_measurements(measurements)
        print(f"{runtime}_{wasm_file}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 my_script.py <file_index>")
        sys.exit(1)

    file_index = int(sys.argv[1])
    if file_index not in [0, 1, 2, 3]:
        print("Invalid file index. Must be 0, 1, 2, or 3.")
        sys.exit(1)

    run_native(file_index)
    run_wasm(file_index)

if __name__ == "__main__":
    main()

