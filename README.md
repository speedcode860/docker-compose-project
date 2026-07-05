# 🚀 Reaction Game - Architecture Docker Compose Sécurisée

Ce projet est une application web de jeu de réaction en temps réel (**Reaction Game**) conçue selon une architecture microservices hautement sécurisée et compartimentée grâce à Docker Compose.

L'application utilise un proxy inverse (**Nginx**), une API de gestion de logique métier (**Python / Flask**), un magasin de données en mémoire à faible latence (**Redis**) pour la gestion des états de jeu en temps réel, et une base de données relationnelle (**PostgreSQL**) pour la persistance des scores et des données utilisateurs.

---

## 🎯 Problématique & Objectifs Architecturels

Dans le développement d'applications web modernes et de jeux en ligne, deux défis majeurs apparaissent :
1. **Performance et Temps Réel :** Un jeu de réaction nécessite une latence minimale pour capturer l'état des sessions de jeu.L'utilisation d'une base de données sur disque classique pour stocker les états volatiles ralentirait l'application.
2. **Sécurité et Isolation des Données :** Exposer directement une base de données (PostgreSQL) ou un cache (Redis) sur Internet est une faille de sécurité critique.

### La Solution : Le Cloisonnement Réseau (Network Bridging)
Pour résoudre ce problème, ce projet implémente un **cloisonnement réseau strict** via Docker à l'aide de deux réseaux virtuels isolés :
* **`frontend` (Réseau Public/Exposé) :** Contient uniquement **Nginx** et l'**API**. Nginx reçoit le trafic public (Port 80) et le redirige vers l'API.Les bases de données sont totalement invisibles ici.
* **`backend` (Réseau Privé/Isolé) :** Contient l'**API**, **Redis** et **PostgreSQL**.Ce réseau n'a aucune ouverture sur l'extérieur.

**Le rôle de l'API (Le Pont) :** L'API Python/Flask est le seul composant rattaché aux **deux réseaux simultanément**.Elle agit comme une passerelle sécurisée (bridge), acceptant les requêtes du proxy Nginx côté frontend, tout en étant capable de requêter Redis et PostgreSQL côté backend.

---

## 🏗️ Architecture des Fichiers du Projet

Voici la structure exacte des fichiers requise pour le bon fonctionnement de l'infrastructure :

```text
reaction-game/
├── docker-compose.yml     # Configuration et orchestration des 4 conteneurs
├── Dockerfile             # Instructions de build pour l'API Python/Flask
├── README.md              # Documentation du projet (ce fichier)
├── api/
│   ├── app.py             # Code source de l'application Flask
│   └── requirements.txt   # Dépendances Python (Flask, redis, psycopg2-binary, etc.)
├── db/
│   └── init.sql           # Script SQL d'initialisation de la base de données
└── nginx/
    └── nginx.conf         # Configuration du proxy inverse et routage
```

---

## 🧩 Description des Services (Microservices)

### 1. Nginx Reverse Proxy (`nginx`)
* **Rôle :** Point d'entrée unique de l'application.Il intercepte les requêtes HTTP externes et les transmet proprement au service API.
* **Réseau :** Connecté uniquement au réseau `frontend`.
* **Port Exposé :** `80:80` (accessible depuis votre navigateur).

### 2. API Service (`api`)
* **Rôle :** Contient la logique métier du jeu de réaction.Traite les actions des joueurs, valide les scores et communique avec les systèmes de données.
* **Technologie :** Python 3 / Flask.
* **Réseau :** Connecté à **`frontend`** et **`backend`**.
* **Sécurité :** Son port interne (5000) n'est pas exposé vers la machine hôte ; il n'est accessible que via Nginx.

### 3. Redis Cache (`redis`)
* **Rôle :** Stockage en mémoire ultra-rapide des sessions de jeu actives, des salons de matchmaking ou des états intermédiaires de réaction des joueurs.
* **Réseau :** Connecté uniquement au réseau `backend`.
* **Port Interne :** `6379`.

### 4. PostgreSQL Database (`db`)
* **Rôle :** Stockage persistant à long terme (historique des parties, classements généraux/Leaderboard, comptes utilisateurs).
* **Réseau :** Connecté uniquement au réseau `backend`.
* **Persistance :** Utilise un volume Docker nommé `db_data` pour éviter de perdre les données lors de l'arrêt des conteneurs.
* **Initialisation :** Exécute automatiquement `init.sql` au premier lancement pour créer les tables.

---

## 🚀 Guide de Lancement et Déploiement

### 1. Prérequis
Assurez-vous d'avoir installé sur votre machine :
* [Docker](https://docs.docker.com/get-docker/) (Version 20.10+)
* [Docker Compose](https://docs.docker.com/compose/install/) (intégré nativement dans Docker Desktop)

### 2. Préparation des fichiers locaux
Avant de lancer, assurez-vous que vos fichiers de configuration locaux contiennent les bases nécessaires.

*Exemple minimal pour `api/requirements.txt` :
```text
Flask==3.0.0
redis==5.0.1
psycopg2-binary==2.9.9
```

*Exemple minimal pour `nginx/nginx.conf` :
```nginx
events {}
http {
    server {
        listen 80;
        location / {
            proxy_pass http://api:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 3. Commande de démarrage
Placez-vous à la racine du projet (`~/reaction-game`) et exécutez la commande suivante pour compiler l'image de l'API et démarrer toute l'infrastructure en arrière-plan :

```bash
docker-compose up --build -d
```

* `--build` : Force Docker à reconstruire l'image de l'API à partir du `Dockerfile` (indispensable si vous modifiez le code Python).
* `-d` : Mode "detached" (arrière-plan), libère votre terminal.

### 4. Vérification du statut des services
Pour vous assurer que tous les conteneurs fonctionnent correctement (statut `Up`) :

```bash
docker-compose ps
```

Pour consulter les journaux applicatifs (logs) en temps réel (pratique pour le débogage de l'API ou de la base de données) :

```bash
docker-compose logs -f
```

### 5. Accès à l'application
Ouvrez votre navigateur web et rendez-vous sur :
👉 **`http://localhost`** (ou `http://127.0.0.1`)

Le trafic passera par Nginx (port 80) -> transmettra à l'API Flask -> qui interagira avec Redis et PostgreSQL en toute sécurité.

### 6. Arrêt et Nettoyage
Pour arrêter proprement l'ensemble des microservices sans supprimer vos données :

```bash
docker-compose down
```

Pour arrêter les services **et détruire définitivement** le volume de la base de données (remise à zéro complète) :

```bash
docker-compose down -v
```

---

## 🔒 Bonnes Pratiques de Sécurité Appliquées
* **Principe du moindre privilège réseau :** Si un attaquant parvient par compromission extrême à s'introduire dans le conteneur Nginx, il se retrouve bloqué sur le réseau `frontend`. Il lui est impossible de scanner, pinguer ou attaquer directement la base de données PostgreSQL ou le cache Redis car aucune route réseau n'existe entre eux.
* **Isolation des ports :** Seul le port 80 est mappé sur la machine hôte.Vos ports de base de données (`5432`) et de cache (`6379`) restent hermétiques aux scans de ports extérieurs.
* **Volumes nommés :** La séparation claire entre le conteneur jetable (`postgres:16`) et les données physiques (`db_data`) garantit la résilience de l'application face aux pannes ou aux mises à jour d'images.
