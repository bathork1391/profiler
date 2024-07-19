import os
import subprocess
import threading
import time
import argparse
import json

def get_current_rss(pid):
    with open(f'/proc/{pid}/statm', 'r') as f:
        return int(f.readline().split()[1]) * (os.sysconf('SC_PAGE_SIZE') / 1024)  # Convert pages to kilobytes

def monitor_rss(process, interval, memory_usage_list, start_time, time_list):
    while True:
        if process.poll() is not None:
            break  # Exit the loop if the process has terminated
        rss = get_current_rss(process.pid)
        memory_usage_list.append(rss)
        time_list.append(time.time() - start_time)
        time.sleep(interval)

def run_and_monitor_wasm(runtime, file_path, interval):
    command_map = {
        "wasmer": ["wasmer", file_path],
        "wasmtime": ["wasmtime", file_path],
        "wavm": ["wavm", "run", file_path],
        "iwasm": ["iwasm", file_path],
    }
    start_time = time.time()
    command = command_map.get(runtime)
    if command is None:
        print(f"Runtime {runtime} is not supported.")
        return None, None, None
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    memory_usage_list, time_list = [], []
    monitor_thread = threading.Thread(target=monitor_rss, args=(process, interval, memory_usage_list, start_time, time_list))
    monitor_thread.start()
    process.wait()
    monitor_thread.join()

    if process.returncode != 0:
        print(f"Error executing {runtime} with file {file_path}")
        return [], [], 0

    return memory_usage_list, time_list, time.time() - start_time

def run_and_monitor_native(file_path, interval):
    # Ensure the command includes './' to execute from the current directory
    command = ["./" + file_path] if '/' not in file_path else [file_path]
    start_time = time.time()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    memory_usage_list, time_list = [], []
    monitor_thread = threading.Thread(target=monitor_rss, args=(process, interval, memory_usage_list, start_time, time_list))
    monitor_thread.start()
    process.wait()
    monitor_thread.join()

    if process.returncode != 0:
        print(f"Error executing native binary with file {file_path}")
        return [], [], 0

    return memory_usage_list, time_list, time.time() - start_time

def main(file_name, opt_level, interval):
    base_path = "/root/profiler/compiled"
    native_file = f"{file_name}_{opt_level}_native"
    wasm_file = f"{file_name}_{opt_level}.wasm"
    
    results = {
        "native": {},
        "wasm": {}
    }

    # Monitor native binary
    print("\nMonitoring native binary...")
    native_path = os.path.join(base_path, native_file)
    rss_usage, time_list, total_time = run_and_monitor_native(native_path, interval)
    if rss_usage:
        sum_rss = sum(rss_usage)
        avg_rss = sum_rss / len(rss_usage)
        max_rss = max(rss_usage)
        total_time = time_list[-1]  # Last recorded time is the total time
        rss_per_time = sum_rss / total_time
        avg_rss_per_time = avg_rss / total_time

        results["native"] = {
            "sum_rss": sum_rss,
            "avg_rss": avg_rss,
            "max_rss": max_rss,
            "total_time": total_time,
            "rss_per_time": rss_per_time,
            "avg_rss_per_time": avg_rss_per_time
        }
        
        print(f"Sum of RSS: {sum_rss} KB")
        print(f"Average RSS: {avg_rss} KB")
        print(f"Maximum RSS: {max_rss} KB")
        print(f"Total time taken: {total_time} seconds")
        print(f"Sum of RSS divided by total time: {rss_per_time} KB/s")
        print(f"Average RSS divided by total time: {avg_rss_per_time} KB/s")
    else:
        print("No RSS data collected for native binary.")

    # Monitor WASM
    print("\nMonitoring WASM binaries...")
    wasm_path = os.path.join(base_path, wasm_file)
    for runtime in ["wasmer", "wasmtime", "wavm", "iwasm"]:
        print(f"\nRuntime: {runtime}")
        rss_usage, time_list, total_time = run_and_monitor_wasm(runtime, wasm_path, interval)
        if rss_usage:
            sum_rss = sum(rss_usage)
            avg_rss = sum_rss / len(rss_usage)
            max_rss = max(rss_usage)
            total_time = time_list[-1]  # Last recorded time is the total time
            rss_per_time = sum_rss / total_time
            avg_rss_per_time = avg_rss / total_time

            results["wasm"][runtime] = {
                "sum_rss": sum_rss,
                "avg_rss": avg_rss,
                "max_rss": max_rss,
                "total_time": total_time,
                "rss_per_time": rss_per_time,
                "avg_rss_per_time": avg_rss_per_time
            }

            print(f"Sum of RSS: {sum_rss} KB")
            print(f"Average RSS: {avg_rss} KB")
            print(f"Maximum RSS: {max_rss} KB")
            print(f"Total time taken: {total_time} seconds")
            print(f"Sum of RSS divided by total time: {rss_per_time} KB/s")
            print(f"Average RSS divided by total time: {avg_rss_per_time} KB/s")
        else:
            print(f"No RSS data collected for {runtime}.")

    # Save results to JSON file
    results_dir = "/root/profiler/results/rss"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    json_output_file = os.path.join(results_dir, f"{file_name}_{opt_level}_rss.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(results, json_file, indent=4)
    
    print(f"RSS results saved to {json_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('file_name', type=str, help='Name of the file to monitor.')
    parser.add_argument('opt_level', type=int, help='Optimization level of the file.')
    parser.add_argument('--interval', type=float, default=0.05, help='Interval for RSS monitoring in seconds.')
    args = parser.parse_args()
    main(args.file_name, args.opt_level, args.interval)
