import subprocess
import time
import os
import sys

# Constants
RAPL_PATH = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
ITERATIONS = 2
CPU_CORE = '0'
BASE_PATH = "/root/new-profiler/rest-api/source-files"
WASM_RUNTIMES = ['wasmer', 'wasmtime', 'wavm', 'iwasm']

def read_energy():
    with open(RAPL_PATH, 'r') as f:
        return int(f.read().strip())

def execute_command(command):
    start_energy = read_energy()
    start_time = time.time()
    # Execute the command in a new process with CPU affinity set
    subprocess.run(f"taskset -c {CPU_CORE} {command}", shell=True, check=True)
    end_time = time.time()
    end_energy = read_energy()
    energy_used = end_energy - start_energy
    time_taken = end_time - start_time  # Time in seconds
    power_used = (energy_used / 1e6) / time_taken  # Energy in Joules, Power in Watts
    return energy_used, power_used

def average_measurements(measurements):
    average_energy = sum([m[0] for m in measurements]) / ITERATIONS
    average_power = sum([m[1] for m in measurements]) / ITERATIONS
    return average_energy, average_power

def process_native(file_index):
    native_file = f"{BASE_PATH}/2mm_{file_index}_native"
    # Ensure the native file is executable
    if not os.access(native_file, os.X_OK):
        os.chmod(native_file, 0o755)
    file_name = os.path.basename(native_file)
    print(f"Executing native file: {file_name}")
    measurements = []
    for _ in range(ITERATIONS):
        measurements.append(execute_command(f"{native_file}"))
    average_energy, average_power = average_measurements(measurements)
    print(f"Results for {file_name}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")

def process_wasm(file_index):
    wasm_file = f"{BASE_PATH}/2mm_{file_index}.wasm"
    file_name = os.path.basename(wasm_file)
    for runtime in WASM_RUNTIMES:
        print(f"Executing {runtime} with file: {file_name}")
        measurements = []
        for _ in range(ITERATIONS):
            if runtime == 'wavm':
                command = f"{runtime} run --enable simd {wasm_file}"
            else:
                command = f"{runtime} {wasm_file}"
            measurements.append(execute_command(command))
        average_energy, average_power = average_measurements(measurements)
        print(f"Results for {runtime} with {file_name}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")

def main(file_index):
    process_native(file_index)
    process_wasm(file_index)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 rapl-bm.py <file_index>")
        sys.exit(1)

    file_index = int(sys.argv[1])
    if file_index not in [0, 1, 2, 3]:
        print("Invalid file index. Must be 0, 1, 2, or 3.")
        sys.exit(1)

    main(file_index)

