from datetime import datetime, timedelta
import os
import sys
import threading
import time
import docker
from flask import Flask, jsonify, request

app = Flask(__name__)
heartbeats = {}

docker_client = docker.from_env()

@app.route('/heartbeat', methods=['POST'])
def record_heartbeat():
    data = request.get_json()
    if data:
        id, timestamp = data.get("id"), data.get("timestamp")
        if id not in heartbeats: heartbeats[id] = None
        heartbeats[id] =  timestamp
        return "Heartbeat recorded successfully", 201
    return "Invalid heartbeat data", 400

def check_heartbeats():
     while True:
        try:
            for id, timestamp in heartbeats.items():
                last_call = datetime.fromisoformat(timestamp)
                if datetime.now() - last_call >= timedelta(seconds=10):
                    print(f'ERROR: container {id} has no recent heartbeat, restarting...')
                    sys.stdout.flush()
                    docker_client.containers.get(id).restart()
                    del heartbeats[id]
        except Exception as e:
            print(f'ERROR: checking heartbeats {e}')
            sys.stdout.flush()
            time.sleep(1)

        time.sleep(1)


if __name__ == '__main__':
    heartbeat_thread = threading.Thread(target=check_heartbeats)
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5003)))
