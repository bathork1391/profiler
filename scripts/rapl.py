import subprocess
import time
import os
import sys
import json

# Constants
RAPL_PATH = "/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"
ITERATIONS = 2
CPU_CORE = '0'
BASE_PATH = "/root/profiler/compiled"
WASM_RUNTIMES = ['wasmer', 'wasmtime', 'wavm', 'iwasm']
RESULTS_DIR = "/root/profiler/results/rapl"

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

def process_native(file_name, opt_level):
    native_file = f"{BASE_PATH}/{file_name}_{opt_level}_native"
    # Ensure the native file is executable
    if not os.access(native_file, os.X_OK):
        os.chmod(native_file, 0o755)
    file_name_base = os.path.basename(native_file)
    print(f"Executing native file: {file_name_base}")
    measurements = []
    for _ in range(ITERATIONS):
        measurements.append(execute_command(f"{native_file}"))
    average_energy, average_power = average_measurements(measurements)
    print(f"Results for {file_name_base}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")
    return {
        "file": file_name_base,
        "average_energy_uJ": average_energy,
        "average_power_W": average_power
    }

def process_wasm(file_name, opt_level):
    wasm_file = f"{BASE_PATH}/{file_name}_{opt_level}.wasm"
    file_name_base = os.path.basename(wasm_file)
    results = {}
    for runtime in WASM_RUNTIMES:
        print(f"Executing {runtime} with file: {file_name_base}")
        measurements = []
        for _ in range(ITERATIONS):
            if runtime == 'wavm':
                command = f"{runtime} run --enable simd {wasm_file}"
            else:
                command = f"{runtime} {wasm_file}"
            measurements.append(execute_command(command))
        average_energy, average_power = average_measurements(measurements)
        print(f"Results for {runtime} with {file_name_base}: Average Energy (uJ): {average_energy}, Average Power (W): {average_power}")
        results[runtime] = {
            "average_energy_uJ": average_energy,
            "average_power_W": average_power
        }
    return results

def main(file_name, opt_level):
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)

    results = {
        "native": process_native(file_name, opt_level),
        "wasm": process_wasm(file_name, opt_level)
    }

    # Save results to JSON file
    json_output_file = os.path.join(RESULTS_DIR, f"{file_name}_{opt_level}_rapl.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(results, json_file, indent=4)
    
    print(f"RAPL results saved to {json_output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <file_name> <opt_level>")
        sys.exit(1)

    file_name = sys.argv[1]
    opt_level = sys.argv[2]

    main(file_name, opt_level)

