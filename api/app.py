from flask import Flask, jsonify, request, render_template_string
import os
import time
import psycopg2
import redis
import random

app = Flask(__name__)

# -------------------
# Redis
# -------------------
redis_host = os.getenv("REDIS_HOST", "redis")
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

# -------------------
# PostgreSQL
# -------------------
db_conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "game"),
    user=os.getenv("DB_USER", "gameuser"),
    password=os.getenv("DB_PASSWORD", "gamepass")
)
db_conn.autocommit = True

# -------------------
# Routes système & Interface Interactive
# -------------------
@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reaction Game ⚡</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; background: #121212; color: white; margin: 0; padding: 20px; }
            .container { max-width: 600px; margin: 0 auto; }
            .box { width: 100%; height: 250px; margin: 20px 0; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: bold; cursor: pointer; user-select: none; transition: background 0.1s ease; }
            .waiting { background: #e74c3c; cursor: not-allowed; } /* Rouge */
            .ready { background: #2ecc71; animation: pulse 0.5s infinite; } /* Vert */
            .idle { background: #34495e; } /* Gris bleu */
            input, button { padding: 12px; font-size: 16px; border-radius: 8px; border: none; margin: 5px; }
            input { background: #2c3e50; color: white; width: 60%; }
            button { background: #e67e22; color: white; font-weight: bold; cursor: pointer; }
            button:hover { background: #d35400; }
            #leaderboard { text-align: left; background: #1e1e1e; padding: 15px; border-radius: 10px; margin-top: 20px; }
            ol { padding-left: 20px; }
            li { margin: 8px 0; font-size: 18px; }
            @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚡ Réaction Game ⚡</h1>
            
            <div id="setup-zone">
                <input type="text" id="username" placeholder="Entre ton pseudo..." />
                <button onclick="registerPlayer()">Rejoindre</button>
            </div>

            <div id="game-zone" style="display:none;">
                <h3 id="round-title">Manche 1 / 3</h3>
                <p id="instructions">Clique sur la zone ci-dessous pour démarrer la partie.</p>
                <div id="click-box" class="idle" onclick="handleBoxClick()">CLIQUE ICI POUR COMMENCER</div>
                <h2 id="result-message"></h2>
            </div>

            <div id="leaderboard">
                <h3>🏆 Top 10 Meilleurs Temps</h3>
                <ol id="leaderboard-list"><li>Chargement...</li></ol>
            </div>
        </div>

        <script>
            let playerId = null;
            let gameState = "idle"; // idle, waiting, ready, finished
            let nextSignalTime = 0;
            let checkInterval = null;

            updateLeaderboard();

            async function registerPlayer() {
                const name = document.getElementById('username').value;
                if(!name) return alert("Mets un pseudo !");
                
                const res = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name })
                });
                const data = await res.json();
                playerId = data.player_id;
                
                document.getElementById('setup-zone').style.display = 'none';
                document.getElementById('game-zone').style.display = 'block';
            }

            async function startRound() {
                if (checkInterval) clearInterval(checkInterval);
                
                const res = await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ player_id: playerId })
                });
                const data = await res.json();
                
                document.getElementById('round-title').innerText = `Manche ${data.round} / 3`;
                document.getElementById('instructions').innerText = "Attends le VERT... NE CLIQUE PAS AVANT !";
                
                const box = document.getElementById('click-box');
                box.className = "waiting";
                box.innerText = "ATTENDS...";
                gameState = "waiting";

                // Récupération du temps exact du serveur
                const syncRes = await fetch(`/get_signal_time?player_id=${playerId}`);
                const syncData = await syncRes.json();
                nextSignalTime = syncData.signal_time * 1000;

                checkInterval = setInterval(() => {
                    if (Date.now() >= nextSignalTime && gameState === "waiting") {
                        box.className = "ready";
                        box.innerText = "CLIQUE MAINTENANT !";
                        gameState = "ready";
                        clearInterval(checkInterval);
                    }
                }, 10);
            }

            async function handleBoxClick() {
                const box = document.getElementById('click-box');
                
                if (gameState === "idle" || gameState === "finished") {
                    document.getElementById('result-message').innerText = "";
                    startRound();
                    return;
                }

                // Envoi du clic à l'API
                const res = await fetch('/click', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ player_id: playerId })
                });
                const data = await res.json();

                if (data.status === "foul") {
                    document.getElementById('result-message').innerText = "FAUX DÉPART ! Le timer recommence !";
                    // Recalcule du temps suite à la triche
                    const syncRes = await fetch(`/get_signal_time?player_id=${playerId}`);
                    const syncData = await syncRes.json();
                    nextSignalTime = syncData.signal_time * 1000;
                    box.className = "waiting";
                    box.innerText = "ATTENDS...";
                    gameState = "waiting";
                } 
                else if (data.status === "next_round") {
                    document.getElementById('result-message').innerText = `Manche précédente : ${data.round_score_ms} ms`;
                    // On enchaîne automatiquement sur le round suivant côté API
                    document.getElementById('round-title').innerText = `Manche ${data.next_round} / 3`;
                    box.className = "waiting";
                    box.innerText = "ATTENDS LE PROCHAIN SIGNAL...";
                    gameState = "waiting";

                    const syncRes = await fetch(`/get_signal_time?player_id=${playerId}`);
                    const syncData = await syncRes.json();
                    nextSignalTime = syncData.signal_time * 1000;

                    checkInterval = setInterval(() => {
                        if (Date.now() >= nextSignalTime && gameState === "waiting") {
                            box.className = "ready";
                            box.innerText = "CLIQUE !";
                            gameState = "ready";
                            clearInterval(checkInterval);
                        }
                    }, 10);
                } 
                else if (data.status === "finished") {
                    document.getElementById('result-message').innerText = `Dernière manche : ${data.round_score_ms} ms. Score Moyen Final : ${data.average_reaction_time_ms} ms ! 🎉`;
                    gameState = "finished";
                    box.className = "idle";
                    box.innerText = "PARTIE TERMINÉE ! CLIQUE ICI POUR REJOUER";
                    updateLeaderboard();
                }
            }

            async function updateLeaderboard() {
                const res = await fetch('/leaderboard');
                const data = await res.json();
                const list = document.getElementById('leaderboard-list');
                list.innerHTML = "";
                if(data.length === 0) {
                    list.innerHTML = "<li>Aucun score pour le moment.</li>";
                    return;
                }
                data.forEach(player => {
                    const li = document.createElement('li');
                    li.innerText = `${player[0]} — ${player[1]} ms`;
                    list.appendChild(li);
                });
            }
        </script>
    </body>
    </html>
    """)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# -------------------
# Jeu
# -------------------

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")

    cur = db_conn.cursor()
    cur.execute(
        "INSERT INTO players (name) VALUES (%s) RETURNING id;",
        (name,)
    )
    player_id = cur.fetchone()[0]
    cur.close()

    return jsonify({
        "player_id": player_id,
        "name": name
    })


@app.route("/start", methods=["POST"])
def start_game():
    player_id = request.json.get("player_id")

    delay = random.uniform(1.5, 3.5)
    signal_time = time.time() + delay

    r.set(f"game:{player_id}:round", 1)
    r.set(f"game:{player_id}:signal_time", signal_time)
    r.delete(f"game:{player_id}:scores") 

    return jsonify({
        "status": "initialized",
        "round": 1
    })


@app.route("/get_signal_time")
def get_signal_time():
    player_id = request.args.get("player_id")
    signal_time = r.get(f"game:{player_id}:signal_time")
    return jsonify({"signal_time": float(signal_time) if signal_time else 0})


@app.route("/click", methods=["POST"])
def click():
    player_id = request.json.get("player_id")
    now = time.time()

    current_round = r.get(f"game:{player_id}:round")
    signal_time_raw = r.get(f"game:{player_id}:signal_time")

    if not current_round or not signal_time_raw:
        return jsonify({"error": "Aucune partie en cours."}), 400

    current_round = int(current_round)
    signal_time = float(signal_time_raw)

    # 1. FAUX DÉPART
    if now < signal_time:
        delay = random.uniform(1.5, 3.5)
        r.set(f"game:{player_id}:signal_time", now + delay)
        return jsonify({
            "status": "foul",
            "round": current_round
        })

    # 2. CLIC APPRÉCIÉ
    reaction_time = int((now - signal_time) * 1000)
    r.rpush(f"game:{player_id}:scores", reaction_time)

    # 3. PASSAGE AU ROUND SUIVANT OU FIN
    if current_round < 3:
        next_round = current_round + 1
        delay = random.uniform(1.5, 3.5)
        next_signal = now + delay

        r.set(f"game:{player_id}:round", next_round)
        r.set(f"game:{player_id}:signal_time", next_signal)

        return jsonify({
            "status": "next_round",
            "round_score_ms": reaction_time,
            "next_round": next_round
        })
    else:
        scores = [int(s) for s in r.lrange(f"game:{player_id}:scores", 0, -1)]
        avg_reaction_time = sum(scores) // len(scores) if scores else reaction_time

        cur = db_conn.cursor()
        cur.execute(
            "SELECT name FROM players WHERE id = %s;",
            (player_id,)
        )
        player_name = cur.fetchone()[0]

        cur.execute(
            "INSERT INTO scores (player_id, reaction_time_ms) VALUES (%s, %s);",
            (player_id, avg_reaction_time)
        )
        cur.close()

        r.zadd("leaderboard", {player_name: avg_reaction_time})

        r.delete(f"game:{player_id}:round")
        r.delete(f"game:{player_id}:signal_time")
        r.delete(f"game:{player_id}:scores")

        return jsonify({
            "status": "finished",
            "round_score_ms": reaction_time,
            "average_reaction_time_ms": avg_reaction_time
        })


@app.route("/leaderboard")
def leaderboard():
    top = r.zrange("leaderboard", 0, 9, withscores=True)
    return jsonify(top)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
