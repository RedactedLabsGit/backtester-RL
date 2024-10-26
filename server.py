from flask import Flask, jsonify, request, send_file
from src.main import (
    process
)
from src.utils import (
    get_config
)

app = Flask(__name__)

@app.route('/compute', methods=['POST'])
def compute():
    global task_counter
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    process(get_config(data));
    return send_file("results/returns_vs_final_price_diff.html"), 200

if __name__ == '__main__':
    app.run(debug=True, threaded=False, host='0.0.0.0', port=3000)