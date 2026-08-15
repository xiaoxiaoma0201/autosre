import time
import os
import random
import redis
import mysql.connector
from flask import Flask, jsonify, request, Response, g
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'Request duration in seconds', ['endpoint'])

r = redis.Redis(host='redis', port=6379, decode_responses=True)

def get_db():
    return mysql.connector.connect(
        host='mysql',
        user=os.environ.get('MYSQL_USER', 'testuser'),
        password=os.environ.get('MYSQL_PASSWORD', 'testpass'),
        database=os.environ.get('MYSQL_DATABASE', 'testdb')
    )

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - g.start_time
    endpoint = request.endpoint or 'unknown'
    REQUEST_COUNT.labels(request.method, endpoint, response.status_code).inc()
    REQUEST_DURATION.labels(endpoint).observe(duration)
    return response

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/api/users')
def get_users():
    return jsonify({"users": ["user1", "user2", "user3"]})

@app.route('/api/slow')
def slow_endpoint():
    time.sleep(random.uniform(2, 4))
    return jsonify({"result": "slow response"})

@app.route('/api/cache')
def cache_test():
    try:
        key = 'test_key'
        if not r.get(key):
            r.set(key, 'cached_value', ex=60)
        return jsonify({"cache": r.get(key)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/db')
def db_test():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        db.close()
        return jsonify({"db": result[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
