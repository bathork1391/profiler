import os
import time
import subprocess
import argparse
import json

# Directory setup
SOURCE_DIR = "/root/profiler/PolyBenchC/files"
UTILITIES_DIR = "/root/profiler/PolyBenchC/utilities"
CLANG_NATIVE_PATH = "/usr/lib/llvm-16/bin/clang"
CLANG_WASI_PATH = "/home/imran/bench/Clang_dir/wasi-sdk-20.0/bin/clang"
WASI_SDK_PATH = "/home/imran/bench/Clang_dir/wasi-sdk-20.0"
COMPILED_DIR = "/root/profiler/compiled"
COMPILE_RESULTS_DIR = "/root/profiler/results/comp-times"

def compile_native(filename, opt_level):
    source_file = os.path.join(SOURCE_DIR, filename, f"{filename}.c")
    output_file = os.path.join(COMPILED_DIR, f"{filename}_{opt_level}_native")
    command = [
        CLANG_NATIVE_PATH, 
        "-I/usr/include", 
        "-I" + UTILITIES_DIR, 
        "-DPOLYBENCH", 
        f"-O{opt_level}", 
        source_file, 
        os.path.join(UTILITIES_DIR, "polybench.c"), 
        "-o", 
        output_file, 
        "-lm"
    ]

    start_time = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True)
    end_time = time.perf_counter()

    if result.returncode != 0:
        print(f"Error: Native compilation failed for {filename} with stderr: {result.stderr}")
    else:
        print(f"Native Compilation Time for {filename}: {end_time - start_time}s")

    return output_file, end_time - start_time

def compile_wasm(filename, opt_level):
    source_file = os.path.join(SOURCE_DIR, filename, f"{filename}.c")
    output_file = os.path.join(COMPILED_DIR, f"{filename}_{opt_level}.wasm")
    command = [
        CLANG_WASI_PATH,
        "--target=wasm32-unknown-wasi",
        f"--sysroot={WASI_SDK_PATH}/share/wasi-sysroot",
        f"-I{UTILITIES_DIR}",
        "-DPOLYBENCH",
        "-D_WASI_EMULATED_PROCESS_CLOCKS",
        f"-O{opt_level}",
        source_file,
        os.path.join(UTILITIES_DIR, "polybench.c"),
        "-o",
        output_file,
        "-lwasi-emulated-process-clocks",
    ]

    start_time = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True)
    end_time = time.perf_counter()

    if result.returncode != 0:
        print(f"Error during WASM compilation for {filename}: {result.stderr}")
    else:
        print(f"WASM Compilation Time for {filename}: {end_time - start_time}s")

    return output_file, end_time - start_time

def main(filename, opt_level):
    if not os.path.exists(COMPILED_DIR):
        os.makedirs(COMPILED_DIR)
    if not os.path.exists(COMPILE_RESULTS_DIR):
        os.makedirs(COMPILE_RESULTS_DIR)

    compile_times = {}

    native_file, native_compile_time = compile_native(filename, opt_level)
    compile_times[f"{filename}_native"] = native_compile_time

    wasm_file, wasm_compile_time = compile_wasm(filename, opt_level)
    compile_times[f"{filename}_wasm"] = wasm_compile_time

    json_output_file = os.path.join(COMPILE_RESULTS_DIR, f"{filename}_{opt_level}_com-times.json")
    with open(json_output_file, 'w') as json_file:
        json.dump(compile_times, json_file, indent=4)

    print(f"Compilation times saved to {json_output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compile and measure compilation times of a WASM file and a native binary.')
    parser.add_argument('filename', type=str, help='Name of the file to compile')
    parser.add_argument('opt_level', type=int, choices=[0, 1, 2, 3], help='Optimization level (0, 1, 2, 3)')
    args = parser.parse_args()
    main(args.filename, args.opt_level)

