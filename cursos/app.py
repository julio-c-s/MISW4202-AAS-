from datetime import datetime
import json
import os
import string
import sys
import time
import pika
import requests
import socket
import threading
import sqlite3

from flask import Flask, jsonify

app = Flask(__name__)

INSTANCE_ID = socket.gethostname()

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE')
RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS')
MONITOR_URL = os.environ.get('MONITOR_URL')

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def create_cursos_table():
    try:
        conn = sqlite3.connect('cursos.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cursos (
                id INTEGER PRIMARY KEY,
                name TEXT,
                type TEXT
            );
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating 'cursos' table: {str(e)}")

@app.route('/suffocate', methods=['POST'])
def suffocate():
    garbage_array = []
    for i in range(99999999):
        for j in range(1000):
            garbage_array.append(j+i)
        time.sleep(0.00000000001)

@app.route('/cursos', methods=['GET'])
def get_cursos():
    try:
        conn = sqlite3.connect('cursos.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cursos")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        keys = ['id', 'name', 'type']
        result = [dict(zip(keys, row)) for row in rows]

        return jsonify(result)

    except Exception as e:
        return jsonify(error=str(e)), 500



def send_heartbeat(url: string):
    while True:
        try:
            response = requests.post(url, headers=headers, data=json.dumps({"id": INSTANCE_ID, "timestamp": str(datetime.now().isoformat())}))
            if response.status_code != 201:
                print(f"Failed to send heartbeat. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error sending heartbeat: {str(e)}")
        sys.stdout.flush()
        time.sleep(5) 

def callback(ch, method, properties, body):
    sys.stdout.flush()
    try:    
        message_data = body.decode('utf-8')
        print(f"Received message: {message_data}")
        sys.stdout.flush()
        save_to_database(json.loads(message_data))
    except UnicodeDecodeError:
        print(f"Received binary message: {body}")
        sys.stdout.flush()

def save_to_database(data):
    try:
        conn = sqlite3.connect('cursos.db')
        cursor = conn.cursor()
        query = "INSERT INTO cursos (name, type) VALUES (?, ?)"
        values = (data['name'], data['type'])
        cursor.execute(query, values)
        conn.commit()
        conn.close()

        print(f"Data saved in database {data}")
    except Exception as e:
        print(f"Error saving data to the database: {str(e)}")

def consume_messages():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=pika.PlainCredentials(username=RABBITMQ_USER, password=RABBITMQ_PASS),
        ))
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)
        channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback, auto_ack=True)
        print('Waiting for messages')
        sys.stdout.flush()
        channel.start_consuming()

    except Exception as e:
        print(f"Error consuming messages: {str(e)}")
        sys.stdout.flush()
        time.sleep(5) 
        consume_messages()


if __name__ == '__main__':
    create_cursos_table()
    heartbeat_thread = threading.Thread(target=send_heartbeat, args=(f"{MONITOR_URL}/heartbeat",))
    heartbeat_thread.daemon = True
    heartbeat_thread.start()
    message_thread = threading.Thread(target=consume_messages)
    message_thread.daemon = True
    message_thread.start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5002)))