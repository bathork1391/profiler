from flask import Flask, request, jsonify, Response, stream_with_context
import subprocess
import json
import time
import os
import paramiko

app = Flask(__name__)

VPC_HOST = "192.168.17.64"
VPC_USERNAME = "imran"
VPC_PASSWORD = "3RDGzQ7nQWKi"
VPC_SCRIPT_DIR = "/root/vpc-rest/rest-api/scripts"
LOCAL_SCRIPT_DIR = "/root/new-profiler/rest-api/scripts"
RESULTS_DIR = "/root/new-profiler/rest-api/results"

def run_local_script(script_name, argument):
    try:
        result = subprocess.run(['python3', f'{LOCAL_SCRIPT_DIR}/{script_name}', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def run_remote_script(script_name, argument):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPC_HOST, username=VPC_USERNAME, password=VPC_PASSWORD)

        # Verify connection
        command = 'echo Connection Established'
        stdin, stdout, stderr = ssh.exec_command(command)
        connection_message = stdout.read().decode().strip()
        connection_error = stderr.read().decode().strip()
        print(f"Connection message: {connection_message}")
        print(f"Connection error: {connection_error}")

        if connection_message != 'Connection Established':
            ssh.close()
            return f"Error: Unable to establish connection, got message: {connection_message} and error: {connection_error}"

        # Run the script with sudo
        command = f'sudo python3 {VPC_SCRIPT_DIR}/{script_name} {argument}'
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        ssh.close()
        
        if error:
            return f"Error: {error}, Command: {command}, Result: {result}"
        return result
    except Exception as e:
        return f"Error: {e}"

def generate_results(script_name, arguments, run_script_func, result_identifier):
    results = {}
    start_time = time.time()

    for arg in arguments:
        result = run_script_func(script_name, arg)
        results[arg] = result

    total_time = time.time() - start_time

    # Save results to a JSON file with result identifier
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results_file = os.path.join(RESULTS_DIR, f'{script_name}_{result_identifier}_results.json')
    json_results = {"results": results, "total_time": total_time}
    with open(results_file, 'w') as json_file:
        json.dump(json_results, json_file, indent=4)

    return results, total_time, results_file

@app.route('/run_script', methods=['POST'])
def run_script():
    @stream_with_context
    def generate():
        data = request.json
        script_name = data.get('script_name')
        arguments = data.get('arguments', [0, 1, 2, 3])
        location = data.get('location', 'local')  # 'local' or 'vpc'
        
        if location == 'local':
            run_script_func = run_local_script
            result_identifier = 'local'
        else:
            run_script_func = run_remote_script
            result_identifier = 'vpc'

        yield f"Running {script_name} scripts with arguments {arguments} on {location}...\n"
        results, total_time, results_file = generate_results(script_name, arguments, run_script_func, result_identifier)
        
        yield f"Results: {json.dumps(results, indent=4)}\n"
        yield f"Total time taken: {total_time} seconds\n"
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

