from flask import Flask, request, jsonify, Response, stream_with_context
import subprocess
import json
import time
import os
import paramiko
import psutil

app = Flask(__name__)

VPC_HOST = "192.168.17.64"
VPC_USERNAME = "imran"
VPC_PASSWORD = "3RDGzQ7nQWKi"
VPC_SCRIPT_DIR = "/root/vpc-rest/rest-api/scripts"
LOCAL_SCRIPT_DIR = "/root/profiler/scripts"
RESULTS_DIR = "/root/profiler/results"
VPN_CONFIG_PATH = "/etc/openvpn/pfSense-UDP4-2871-imran.ovpn"
VPN_USERNAME = "imran"
VPN_PASSWORD = "3RDGzQ7nQWKi"

ssh_client = None

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
        # Change to the correct directory
        os.chdir("/root/profiler/pfSense-UDP4-2871-imran")
        
        vpn_command = f"sudo openvpn --config {VPN_CONFIG_PATH}"
        print(f"Starting VPN connection with command: {vpn_command}")
        process = subprocess.Popen(vpn_command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Provide VPN username and password
        process.stdin.write(f"{VPN_USERNAME}\n".encode())
        process.stdin.flush()
        process.stdin.write(f"{VPN_PASSWORD}\n".encode())
        process.stdin.flush()

        # Wait for the connection to establish
        time.sleep(10)
        
        # Check if the VPN connection is successful
        output, error = process.communicate()
        if error:
            raise Exception(f"VPN connection error: {error.decode()}")
        print("VPN connection established.")
    except Exception as e:
        print(f"Failed to establish VPN connection: {e}")
        raise e
    finally:
        # Change back to the original directory
        os.chdir("/root/new-profiler/rest-api")

def initialize_ssh_connection():
    global ssh_client
    if ssh_client is None:
        try:
            print(f"Attempting to connect to VPC at {VPC_HOST} with username {VPC_USERNAME}")
            initialize_vpn_connection()
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(VPC_HOST, username=VPC_USERNAME, password=VPC_PASSWORD, timeout=30)
            stdin, stdout, stderr = ssh_client.exec_command('echo Connection Established')
            connection_message = stdout.read().decode().strip()
            if connection_message == 'Connection Established':
                print("Connection to the VPC is successful.")
            else:
                ssh_client.close()
                ssh_client = None
                raise Exception(f"Error: Unable to establish connection, got message: {connection_message}")
        except Exception as e:
            print(f"Failed to connect to VPC: {e}")
            ssh_client = None
            raise e

def close_ssh_connection():
    global ssh_client
    if ssh_client is not None:
        ssh_client.close()
        ssh_client = None

def run_local_script(script_name, argument):
    try:
        command = ['python3', f'{LOCAL_SCRIPT_DIR}/{script_name}', str(argument)]
        print(f"Executing local command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def run_remote_script(script_name, argument):
    try:
        initialize_ssh_connection()
        command = f'sudo python3 {VPC_SCRIPT_DIR}/{script_name} {argument}'
        stdin, stdout, stderr = ssh_client.exec_command(command)
        result = ''
        yield f"Executing command: {command}\n"
        print(f"Executing remote command: {command}")
        while True:
            line = stdout.readline()
            if not line:
                break
            result += line
            yield f"{line}\n"  # Stream each line back to the client
        error = stderr.read().decode().strip()
        
        if error:
            yield f"Error: {error}, Command: {command}, Result: {result}\n"
        else:
            yield f"Finished executing command: {command}\n"
            print(f"Finished executing remote command: {command}")
        
        yield result
    except Exception as e:
        yield f"Error: {e}\n"

def generate_results(script_name, arguments, run_script_func, result_identifier):
    results = {}
    start_time = time.time()

    for arg in arguments:
        results[arg] = ''
        for line in run_script_func(script_name, arg):
            results[arg] += line
            yield line

        yield f"\nFinished executing {script_name} with argument {arg}.\n"

    total_time = time.time() - start_time

    # Save results to a JSON file with result identifier
    os.makedirs(RESULTS_DIR, exist_ok=True)
    results_file = os.path.join(RESULTS_DIR, f'{script_name}_{result_identifier}.json')
    json_results = {"results": results, "total_time": total_time}
    with open(results_file, 'w') as json_file:
        json.dump(json_results, json_file, indent=4)

    yield f"Total time taken: {total_time} seconds\n"
    yield f"Results saved to {results_file}\n"

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
        for line in generate_results(script_name, arguments, run_script_func, result_identifier):
            yield line
        
        # Close SSH connection after the script execution is completed
        if location == 'vpc':
            close_ssh_connection()

    try:
        response = Response(generate(), mimetype='application/json')
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.debug = True  # Enable debug mode
    print("Server is running and waiting for the next command...")
    app.run(host='0.0.0.0', port=5000)

