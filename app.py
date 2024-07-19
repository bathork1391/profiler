from flask import Flask, request, jsonify, Response, stream_with_context
import subprocess
import json
import time
import os

app = Flask(__name__)

LOCAL_SCRIPT_DIR = "/root/profiler/scripts"
RESULTS_DIR = "/root/profiler/results"

def run_local_script(script_name, application_name, opt_level):
    try:
        command = ['python3', f'{LOCAL_SCRIPT_DIR}/{script_name}', application_name, str(opt_level)]
        print(f"Executing local command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip(), None
    except subprocess.CalledProcessError as e:
        return None, f"Error: {e}"

def read_json_file(filepath):
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

@app.route('/run_profiling', methods=['POST'])
def run_profiling():
    @stream_with_context
    def generate():
        data = request.json
        application_name = data.get('application_name')
        opt_levels = data.get('opt_levels')
        config_file = data.get('config_file', 'config.json')
        
        with open(config_file, 'r') as file:
            config = json.load(file)
        
        local_tests = [t for t in config.get('local_tests', []) if t['active']]
        if not opt_levels:
            opt_levels = config.get('optimization_levels', [0, 1, 2, 3])
        
        results = {}
        start_time = time.time()

        # Run local tests
        for opt_level in opt_levels:
            level_key = f"optimization_level_{opt_level}"
            if level_key not in results:
                results[level_key] = {}
            yield f"\nOptimization Level: {opt_level}\n"
            for test in local_tests:
                test_name = test["name"]
                yield f"\nRunning {test_name} locally...\n"
                
                result, error = run_local_script(test_name, application_name, opt_level)
                
                if error:
                    results[level_key][f"{test_name}_local"] = {"error": error}
                    yield error + "\n"
                else:
                    yield result + "\n"
                    try:
                        last_line = result.strip().split('\n')[-1]
                        file_path = last_line.split()[-1]
                        test_results = read_json_file(file_path)
                        results[level_key][f"{test_name}_local"] = test_results
                    except Exception as e:
                        results[level_key][f"{test_name}_local"] = {"error": str(e)}

        total_time = time.time() - start_time

        # Create a directory for this profiling run
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        profile_dir = os.path.join(RESULTS_DIR, f'{application_name}_{timestamp}')
        os.makedirs(profile_dir, exist_ok=True)
        
        # Save results to a JSON file
        results_file = os.path.join(profile_dir, f'{application_name}_results.json')
        json_results = {"application": application_name, "profiling_results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        
        yield "\nFinal Results:\n"
        yield json.dumps(json_results, indent=4)

        # Indicate that the server is ready for the next command
        print("Server is running and waiting for the next command...")

    try:
        response = Response(generate(), mimetype='application/json')
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.debug = True  # Enable debug mode
    print("Server is running and waiting for the next command...")
    app.run(host='0.0.0.0', port=5000)

