from flask import Flask, request, jsonify, Response, stream_with_context
import subprocess
import json
import time
import os
import ansible_runner
import psutil

app = Flask(__name__)

LOCAL_SCRIPT_DIR = "/root/profiler/scripts"
RESULTS_DIR = "/root/profiler/results"
LOCAL_BINARY_PATH = "/root/profiler/compiled"
LOCAL_RESULTS_PATH = "/root/profiler/results"
VPN_SCRIPT_PATH = "/root/vpn_con/vpn.sh"

def is_vpn_connected():
    """Check if the VPN connection is active by looking for the VPN interface."""
    for interface, addrs in psutil.net_if_addrs().items():
        if "tun" in interface or "tap" in interface:
            return True
    return False

def initialize_vpn_connection():
    if is_vpn_connected():
        print("VPN connection is already established.")
        return

    try:
        vpn_command = f"sudo {VPN_SCRIPT_PATH}"
        process = subprocess.Popen(vpn_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)  # Allow some time for the VPN to establish

        retries = 5
        while not is_vpn_connected() and retries > 0:
            time.sleep(1)
            retries -= 1
        
        if not is_vpn_connected():
            raise Exception("VPN connection failed to establish.")
        print("VPN connection established.")
    except Exception as e:
        print(f"Failed to establish VPN connection: {e}")
        raise e

def run_ansible_playbook(application_name, opt_levels, tests, vm_config):
    extra_vars = {
        'application_name': application_name,
        'opt_levels': opt_levels,
        'tests': tests,
        'binary_path': vm_config['binary_path'],
        'script_path': vm_config['script_path'],
        'results_path': vm_config['results_path'],
        'local_binary_path': LOCAL_BINARY_PATH,
        'local_scripts': [f"{LOCAL_SCRIPT_DIR}/{script['name']}" for script in tests],
        'local_results_path': LOCAL_RESULTS_PATH,
        'binary_copy_required': True
    }
    
    r = ansible_runner.run(private_data_dir='/root/profiler/ansible', playbook='playbook.yml', extravars=extra_vars, cmdline="-i inventory", quiet=False)
    
    for event in r.events:
        if 'event_data' in event and 'stdout' in event['event_data']:
            yield event['event_data']['stdout'] + '\n'
    
    if r.rc != 0:
        raise Exception(f"Ansible playbook failed")

def run_vm_tests(application_name, opt_levels, vm_tests, vm_config):
    initialize_vpn_connection()
    try:
        for line in run_ansible_playbook(application_name, opt_levels, vm_tests, vm_config):
            yield line
        yield f"Completed running tests on VM {vm_config['hostname']}...\n"
    except Exception as e:
        yield f"Failed to run Ansible playbook: {str(e)}\n"

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

def collect_vm_results(application_name, opt_levels, vm_tests, results):
    for opt_level in opt_levels:
        level_key = f"optimization_level_{opt_level}"
        if level_key not in results:
            results[level_key] = {}
        for test in vm_tests:
            test_name = test["name"]
            test_name_without_py = test_name.replace('.py', '')
            try:
                # Define the new path to which the VM result files are fetched
                vm_result_file_path = f"{LOCAL_RESULTS_PATH}/vm_results/{test_name_without_py}/{application_name}_{opt_level}_{test_name_without_py}.json"
                if os.path.exists(vm_result_file_path):
                    test_results = read_json_file(vm_result_file_path)
                    results[level_key][f"{test_name}_vm"] = test_results
                else:
                    results[level_key][f"{test_name}_vm"] = {"error": "Result file not found"}
            except Exception as e:
                results[level_key][f"{test_name}_vm"] = {"error": str(e)}

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
        vm_tests = [t for t in config.get('vm_tests', []) if t['active']]
        vm_config = config.get('vm')
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

        # Run VM tests
        if vm_config and any(test['active'] for test in vm_tests):
            yield f"\nRunning VM tests...\n"
            try:
                for line in run_vm_tests(application_name, opt_levels, vm_tests, vm_config):
                    yield line
                collect_vm_results(application_name, opt_levels, vm_tests, results)
                yield f"\nDisconnected from VM {vm_config['hostname']}...\n"
            except Exception as e:
                yield f"\nFailed to run VM tests: {str(e)}\n"

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

