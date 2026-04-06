# Map-Tana

Application web pour l'estimation des prix de terrains à Antananarivo (Madagascar) avec carte interactive.

## Prérequis

- Python 3.8+
- PostgreSQL 12+ avec PostGIS
- pgAdmin 4 (optionnel mais recommandé)

## Installation pour collaborateurs

### 1. Base de données PostgreSQL

#### 1.1 Installer PostGIS (via Stack Builder)
- Ouvrir l'application **Stack Builder** (menu Démarrer)
- Sélectionner le serveur PostgreSQL et cliquer "Next"
- Dérouler la section **Spatial Extensions**
- Cocher la version de PostGIS correspondant à ton PostgreSQL
- Terminer l'installation

#### 1.2 Créer la base de données
- Ouvrir **pgAdmin 4**
- Créer une nouvelle base de données nommée `map_tana`
- Ouvrir l'outil de requête et exécuter :
```sql
CREATE EXTENSION postgis;
```

#### 1.3 Créer la structure et les données
Dans pgAdmin, ouvrir le fichier `data/data.sql` et exécuter tout le script.

Ou en ligne de commande :
```powershell
psql -d map_tana -f data/data.sql
```

### 2. Configuration du projet Python

#### 2.1 Cloner/naviguer dans le projet
```powershell
cd Map-Tana
```

#### 2.2 Créer l'environnement virtuel
```powershell
python -m venv venv
```

#### 2.3 Activer l'environnement virtuel
```powershell
.\venv\Scripts\activate
```

#### 2.4 Installer les dépendances
```powershell
pip install flask flask-sqlalchemy psycopg2 geoalchemy2 shapely
```

#### 2.5 Configurer la connexion à la base de données
Éditer le fichier `app.py` et modifier la ligne 12-14 avec tes paramètres PostgreSQL :
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://UTILISATEUR:MOTDEPASSE@localhost:5432/map_tana'
```

Exemple avec l'utilisateur postgres par défaut :
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/map_tana'
```

### 3. Lancer l'application

```powershell
.\venv\Scripts\activate
python app.py
```

Puis ouvrir le navigateur à l'adresse : **http://127.0.0.1:5000**

## Structure du projet

```
Map-Tana/
├── app.py                 # Backend Flask (routes API)
├── models.py              # Modèles SQLAlchemy (base de données)
├── data/
│   └── data.sql           # Script SQL de création de la DB
├── templates/
│   └── index.html         # Interface web (carte + formulaires)
├── static/
│   ├── css/leaflet.css    # Styles de la carte
│   └── js/leaflet.js      # Bibliothèque carte interactive
└── README.md              # Ce fichier
```

## Fonctionnalités

- **Carte interactive** d'Antananarivo avec les terrains à vendre
- **Cliquer sur un terrain existant** → Voir les détails + Estimer le prix
- **Cliquer sur une zone vide** → Ajouter un nouveau terrain
- **Algorithme d'estimation** basé sur : accessibilité, type de papier, bâtissabilité, distances aux infrastructures

## API Endpoints

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/terrains` | GET | Liste tous les terrains |
| `/api/terrain/near?lat=&lon=&radius=` | GET | Recherche terrain proche |
| `/api/terrain` | POST | Créer un nouveau terrain |
| `/api/terrain/<id>` | GET | Récupérer un terrain par ID |
| `/api/estimer` | POST | Estimer le prix d'un terrain |

## Résolution des problèmes

### Erreur "ModuleNotFoundError: No module named 'shapely'"
L'environnement virtuel est corrompu ou mal configuré. Solution :
```powershell
Remove-Item -Recurse -Force .\venv
python -m venv venv
.\venv\Scripts\activate
.\venv\Scripts\pip install flask flask-sqlalchemy psycopg2 geoalchemy2 shapely
```

### Erreur de connexion PostgreSQL
Vérifier que :
1. PostgreSQL est démarré (services Windows)
2. Les identifiants dans `app.py` sont corrects
3. La base `map_tana` existe et PostGIS est activé (`CREATE EXTENSION postgis;`)
