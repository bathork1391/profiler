from flask import Flask, request, jsonify, Response, stream_with_context
import subprocess
import json
import time
import os

app = Flask(__name__)

def run_bare_m_times_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/times-new.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def run_dockers_times_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/doc-times.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"
def run_doc_rss_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/doc-rss.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"
    
def run_doc_rapl_bm_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/doc-rapl-bm.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"


@app.route('/doc_rss', methods=['POST'])
def doc_rss():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running doc-rss script with argument {arg}...\n"
            result = run_doc_rss_script(arg)
            results[arg] = result
            yield f"Completed doc-rss script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'doc_rss_bm.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_rss_bm_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/rss-bm.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

def run_rapl_bm_script(argument):
    try:
        result = subprocess.run(['python3', 'scripts/rapl-bm.py', str(argument)], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"

@app.route('/bare_m_times', methods=['POST'])
def bare_m_times():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running script with argument {arg}...\n"
            result = run_bare_m_times_script(arg)
            results[arg] = result
            yield f"Completed script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'bare_m_times.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/dockers_times', methods=['POST'])
def dockers_times():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running doc-times script with argument {arg}...\n"
            result = run_dockers_times_script(arg)
            results[arg] = result
            yield f"Completed doc-times script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'dockers_times.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/rss_bm', methods=['POST'])
def rss_bm():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running rss-bm script with argument {arg}...\n"
            result = run_rss_bm_script(arg)
            results[arg] = result
            yield f"Completed rss-bm script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'rss_bm.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/rapl_bm', methods=['POST'])
def rapl_bm():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running rapl-bm script with argument {arg}...\n"
            result = run_rapl_bm_script(arg)
            results[arg] = result
            yield f"Completed rapl-bm script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'rapl_bm.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/doc_rapl_bm', methods=['POST'])
def doc_rapl_bm():
    @stream_with_context
    def generate():
        arguments = [0, 1, 2, 3]
        results = {}
        start_time = time.time()

        for arg in arguments:
            yield f"Running doc-rapl-bm script with argument {arg}...\n"
            result = run_doc_rapl_bm_script(arg)
            results[arg] = result
            yield f"Completed doc-rapl-bm script with argument {arg}: {result}\n"

        total_time = time.time() - start_time
        yield f"Total time taken: {total_time} seconds\n"

        # Save results to a JSON file
        results_dir = '/root/new-profiler/rest-api/results'
        os.makedirs(results_dir, exist_ok=True)
        results_file = os.path.join(results_dir, 'doc_rapl_bm.json')
        json_results = {"results": results, "total_time": total_time}
        with open(results_file, 'w') as json_file:
            json.dump(json_results, json_file, indent=4)
        yield f"Results saved to {results_file}\n"

    try:
        return Response(generate(), mimetype='application/json')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

