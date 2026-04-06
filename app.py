from flask import Flask, render_template, request, jsonify
from models import db, Terrain
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
import os

app = Flask(__name__)

# Configuration de la base de données PostgreSQL
# Modifie ces paramètres selon ta configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'postgresql://postgres:postgres@localhost:5432/map_tana'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation de la base de données
db.init_app(app)

# Création des tables au démarrage (pour le développement)
with app.app_context():
    db.create_all()

# =====================================================
# ROUTES DE L'INTERFACE WEB
# =====================================================

@app.route('/')
def index():
    """Affiche la page principale avec la carte"""
    return render_template('index.html')

# =====================================================
# ROUTES API - TERRAINS
# =====================================================

@app.route('/api/terrains', methods=['GET'])
def get_terrains():
    """Récupère tous les terrains pour affichage sur la carte"""
    terrains = Terrain.query.all()
    return jsonify([t.to_dict() for t in terrains])

@app.route('/api/terrain/near', methods=['GET'])
def get_terrain_near():
    """
    Recherche un terrain proche des coordonnées données.
    Paramètres query: lat, lon, radius (mètres, défaut: 50)
    """
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
        radius = float(request.args.get('radius', 50))
    except (TypeError, ValueError):
        return jsonify({'error': 'Paramètres lat/lon invalides'}), 400
    
    # Requête pour trouver les terrains dans le rayon donné
    # Utilisation de ST_Distance pour calculer la distance
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    
    terrains = Terrain.query.filter(
        func.ST_DWithin(
            func.ST_GeogFromWKB(Terrain.geom),
            func.ST_GeogFromWKB(point),
            radius
        )
    ).all()
    
    if terrains:
        # Retourne le terrain le plus proche (le premier dans la liste triée par distance)
        return jsonify({
            'found': True,
            'terrain': terrains[0].to_dict()
        })
    else:
        return jsonify({
            'found': False,
            'coordinates': {'lat': lat, 'lon': lon}
        })

@app.route('/api/terrain', methods=['POST'])
def create_terrain():
    """
    Insère un nouveau terrain dans la base de données.
    Données JSON attendues: toutes les caractéristiques du terrain
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Données JSON manquantes'}), 400
    
    # Validation des champs obligatoires
    required_fields = ['commune', 'accessibilite', 'type_papier', 'latitude', 'longitude']
    missing_fields = [f for f in required_fields if f not in data or data[f] is None]
    
    if missing_fields:
        return jsonify({'error': f'Champs obligatoires manquants: {missing_fields}'}), 400
    
    try:
        # Création du terrain depuis les données
        terrain = Terrain.from_dict(data)
        
        # Sauvegarde en base
        db.session.add(terrain)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Terrain enregistré avec succès',
            'terrain': terrain.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erreur lors de l\'enregistrement: {str(e)}'}), 500

@app.route('/api/terrain/<int:terrain_id>', methods=['GET'])
def get_terrain_by_id(terrain_id):
    """Récupère un terrain par son ID"""
    terrain = Terrain.query.get(terrain_id)
    
    if not terrain:
        return jsonify({'error': 'Terrain non trouvé'}), 404
    
    return jsonify(terrain.to_dict())

# =====================================================
# ROUTE D'ESTIMATION DE PRIX
# =====================================================

@app.route('/api/estimer', methods=['POST'])
def estimer():
    """
    Estime le prix d'un terrain basé sur ses caractéristiques.
    Peut recevoir soit un terrain_id (terrain existant), soit les caractéristiques complètes.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Données manquantes'}), 400
    
    # Si un ID est fourni, on récupère le terrain existant
    terrain_id = data.get('terrain_id')
    if terrain_id:
        terrain = Terrain.query.get(terrain_id)
        if not terrain:
            return jsonify({'error': 'Terrain non trouvé'}), 404
        
        # Utilise les données du terrain pour l'estimation
        data = terrain.to_dict()
    
    # Vérification des champs nécessaires pour l'estimation
    required = ['accessibilite', 'type_papier', 'is_batissable']
    if not all(k in data for k in required):
        return jsonify({'error': 'Données insuffisantes pour l\'estimation'}), 400
    
    try:
        prix_estime = calculer_prix_estime(data)
        
        return jsonify({
            'success': True,
            'prix_estime': prix_estime,
            'currency': 'Ar/m²',
            'details': get_details_calcul(data)
        })
        
    except Exception as e:
        return jsonify({'error': f'Erreur lors de l\'estimation: {str(e)}'}), 500


# =====================================================
# ALGORITHME D'ESTIMATION DE PRIX
# =====================================================

def calculer_prix_estime(data):
    """
    Algorithme d'estimation de prix basé sur les caractéristiques du terrain.
    
    Prix de base: 100 000 Ar/m² (prix moyen à Antananarivo)
    Ajustements selon les critères:
    - Accessibilité
    - Type de papier
    - Bâtissabilité
    - Distances aux infrastructures
    """
    
    # Prix de base
    prix_base = 100000.0
    
    # 1. Coefficient d'accessibilité
    coeff_access = {
        'aucun': 0.6,    # -40% (difficile d'accès)
        'moto': 0.85,    # -15% (accès limité)
        'voiture': 1.2   # +20% (accès facile)
    }
    accessibilite = data.get('accessibilite', 'aucun')
    prix_base *= coeff_access.get(accessibilite, 1.0)
    
    # 2. Coefficient de type de papier (sécurité juridique)
    coeff_papier = {
        'fanolorana': 0.7,      # -30% (pas de titre officiel)
        'kadasitra': 0.9,       # -10% (titre local)
        'titre_borne': 1.35     # +35% (titre sécurisé)
    }
    type_papier = data.get('type_papier', 'fanolorana')
    prix_base *= coeff_papier.get(type_papier, 1.0)
    
    # 3. Coefficient de bâtissabilité
    is_batissable = data.get('is_batissable', True)
    if not is_batissable:
        prix_base *= 0.75  # -25% si non bâtissable
    
    # 4. Ajustement selon la distance à la route nationale
    dist_rn = data.get('distance_route_nationale', 1000)
    if dist_rn is not None:
        if dist_rn < 100:
            prix_base *= 1.15  # +15% si très proche (<100m)
        elif dist_rn > 1000:
            prix_base *= 0.9   # -10% si loin (>1km)
    
    # 5. Ajustement selon la distance à la route principale
    dist_rp = data.get('distance_route_principale', 500)
    if dist_rp is not None:
        if dist_rp < 50:
            prix_base *= 1.1   # +10% si très proche (<50m)
        elif dist_rp > 500:
            prix_base *= 0.95  # -5% si loin (>500m)
    
    # 6. Ajustement selon la distance au poteau JIRAMA (électricité)
    dist_jir = data.get('distance_jirama', 200)
    if dist_jir is not None:
        if dist_jir < 50:
            prix_base *= 1.08  # +8% si électricité proche
        elif dist_jir > 300:
            prix_base *= 0.95  # -5% si électricité loin
    
    # Arrondir au millier près
    return round(prix_base / 1000) * 1000


def get_details_calcul(data):
    """Retourne les détails du calcul pour transparence"""
    details = {
        'prix_base': 100000,
        'coefficients': {
            'accessibilite': data.get('accessibilite'),
            'type_papier': data.get('type_papier'),
            'batissable': data.get('is_batissable', True)
        },
        'distances': {
            'route_nationale': data.get('distance_route_nationale'),
            'route_principale': data.get('distance_route_principale'),
            'jirama': data.get('distance_jirama')
        }
    }
    return details

if __name__ == '__main__':
    app.run(debug=True)