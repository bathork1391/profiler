import os
import time
import subprocess
import argparse


#new working script.. updated and optimized... (execution times)it does native and wasm compilation and execution

#The command to run the file is python3 times-new.py opt_level
# Directory setup
SOURCE_DIR = "/root/new-profiler"
UTILITIES_DIR = "/root/new-profiler/utilities"
CLANG_NATIVE_PATH = "/usr/lib/llvm-16/bin/clang"
CLANG_WASI_PATH = "/home/imran/bench/Clang_dir/wasi-sdk-20.0/bin/clang"
WASI_SDK_PATH = "/home/imran/bench/Clang_dir/wasi-sdk-20.0"
NATIVE_OUTPUT_DIR = "/root/new-profiler/rest-api/nat-files"
WASM_OUTPUT_DIR = "/root/new-profiler/rest-api/wsm-files"

# Runtimes
RUNTIMES = ["wasmer", "wasmtime", "wavm", "iwasm"]

def compile_native(opt_level):
    output_file = os.path.join(NATIVE_OUTPUT_DIR, f"2mm_{opt_level}_native")
    command = [
        CLANG_NATIVE_PATH, 
        "-I/usr/include", 
        "-I" + UTILITIES_DIR, 
        "-DPOLYBENCH", 
        f"-O{opt_level}", 
        "2mm.c", 
        "polybench.c", 
        "-o", 
        output_file, 
        "-lm"
    ]

    start_time = time.perf_counter()
    result = subprocess.run(command, cwd=SOURCE_DIR, capture_output=True, text=True)
    end_time = time.perf_counter()

    if result.returncode != 0:
        print(f"Error: Native compilation failed with stderr: {result.stderr}")
    else:
        print(f"Native Compilation Time: {end_time - start_time}s")

    return output_file, end_time - start_time

def run_native_file(file_path):
    start_time = time.perf_counter()
    process = subprocess.run(file_path, capture_output=True, text=True)
    end_time = time.perf_counter()

    if process.returncode != 0:
        print(f"Error executing native binary {file_path}: {process.stderr}")
    else:
        print(f"Native Execution Time: {end_time - start_time}s")

    return end_time - start_time

def compile_wasm(opt_level):
    output_file = os.path.join(WASM_OUTPUT_DIR, f"2mm_{opt_level}.wasm")
    command = [
        CLANG_WASI_PATH,
        "--target=wasm32-unknown-wasi",
        f"--sysroot={WASI_SDK_PATH}/share/wasi-sysroot",
        f"-I{UTILITIES_DIR}",
        "-DPOLYBENCH",
        "-D_WASI_EMULATED_PROCESS_CLOCKS",
        f"-O{opt_level}",
        "2mm.c",
        "polybench.c",
        "-o",
        output_file,
        "-lwasi-emulated-process-clocks",
    ]

    start_time = time.perf_counter()
    result = subprocess.run(command, cwd=SOURCE_DIR, capture_output=True, text=True)
    end_time = time.perf_counter()

    if result.returncode != 0:
        print(f"Error during WASM compilation: {result.stderr}")
    else:
        print(f"WASM Compilation Time: {end_time - start_time}s")

    return output_file, end_time - start_time

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

def main(opt_level):
    native_file, native_compile_time = compile_native(opt_level)
    if native_file:
        run_native_file(native_file)
    
    wasm_file, wasm_compile_time = compile_wasm(opt_level)
    if wasm_file:
        for runtime in RUNTIMES:
            run_wasm_file(runtime, wasm_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compile and measure execution times of a WASM file and a native binary.')
    parser.add_argument('opt_level', type=int, choices=[0, 1, 2, 3], help='Optimization level (0, 1, 2, 3)')
    args = parser.parse_args()
    main(args.opt_level)

