from flask import Flask, jsonify
import redis
import os

app = Flask(__name__)

# Connexion Redis
redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/cache-test")
def cache_test():
    count = r.incr("hits")
    return jsonify({"redis_hits": count})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
