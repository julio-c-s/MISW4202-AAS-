import json
import sys
import pika
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST')
RABBITMQ_QUEUE = os.environ.get('RABBITMQ_QUEUE')
RABBITMQ_USER = os.environ.get('RABBITMQ_USER')
RABBITMQ_PASS = os.environ.get('RABBITMQ_PASS')

@app.route('/curso', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        if not data:
            return jsonify(error='Message missing in request body'), 400

        create_curso(data)

        return jsonify(message='Message sent to RabbitMQ successfully')
    except Exception as e:
        return jsonify(error=f'Error: {str(e)}'), 500

def create_curso(data):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            credentials=pika.PlainCredentials(username=RABBITMQ_USER, password=RABBITMQ_PASS),
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)
        channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=json.dumps(data).encode('utf-8'))
        print(f"Sent '{data}' to RabbitMQ")
        sys.stdout.flush()
        connection.close()
    except Exception as e:
        print(f"Error sending message to RabbitMQ: {str(e)}")
        sys.stdout.flush()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
