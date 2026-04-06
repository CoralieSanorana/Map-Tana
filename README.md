# Map-Tana

## Environnements

- Ouvre l'application Stack Builder (cherche-la dans le menu Démarrer)

- Sélectionne ton serveur PostgreSQL dans la liste et clique sur "Next".

- Déroule la section Spatial Extensions et coche la version de PostGIS correspondant à ton PostgreSQL

- Termine l'installation.

- Ouvre pgAdmin 4

- Crée une nouvelle base de données 'map_tana'
```sql
CREATE EXTENSION postgis;
```

- Entre dans le dossier du projet et exécute le script suivant :
```powershell
.\venv\Scripts\activate
```

- Installe les environnements nécessaires :
```powershell
pip install flask flask-sqlalchemy psycopg2 geopy geoalchemy2
```


