from flask import Flask, render_template, request, jsonify
from models import db, Terrain
from sqlalchemy import func
from geoalchemy2.shape import from_shape
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from shapely.geometry import shape as shapely_shape
import os
import json
import math

app = Flask(__name__)

_geo_cache = {
    'quartier_polygons': None,
    'routes_nationales': None,
    'routes_principales': None,
}

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

@app.route('/api/quartiers', methods=['GET'])
def get_quartiers():
    """Retourne la liste des quartiers/communes disponibles."""
    q = (request.args.get('q') or '').strip().lower()
    rows = Terrain.query.with_entities(Terrain.quartier, Terrain.commune).all()

    valeurs = set()
    for quartier, commune in rows:
        if quartier:
            valeurs.add(quartier)
        if commune:
            valeurs.add(commune)

    # Ajoute aussi les quartiers du GeoJSON (meme s'ils n'ont pas encore de transactions en base)
    geojson_paths = [
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana.geojson'),
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana_ville.geojson'),
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana_full.geojson'),
    ]
    for p in geojson_paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p, 'r', encoding='utf-8') as f:
                gj = json.load(f)
            for feat in gj.get('features', []):
                props = feat.get('properties', {})
                name = props.get('quartier') or props.get('name') or props.get('fokontany')
                if name:
                    valeurs.add(str(name).strip())
        except Exception:
            # Ne bloque pas l'API si un fichier geojson est invalide
            continue

    quartiers = sorted(
        [v for v in valeurs if not q or q in v.lower()],
        key=lambda x: x.lower()
    )
    return jsonify(quartiers)


@app.route('/api/quartiers/stats', methods=['GET'])
def get_quartiers_stats():
    """Statistiques geographiques et de prix par quartier pour la carte."""
    terrains = Terrain.query.filter(Terrain.geom.isnot(None)).all()

    agg = {}
    for t in terrains:
        zone = (t.quartier or t.commune or '').strip()
        if not zone:
            continue

        point = to_shape(t.geom)
        lat, lon = point.y, point.x
        prix = float(t.prix_proprietaire) if t.prix_proprietaire is not None else None

        if zone not in agg:
            agg[zone] = {
                'quartier': zone,
                'count': 0,
                'lat_sum': 0.0,
                'lon_sum': 0.0,
                'min_lat': lat,
                'max_lat': lat,
                'min_lon': lon,
                'max_lon': lon,
                'prices': []
            }

        a = agg[zone]
        a['count'] += 1
        a['lat_sum'] += lat
        a['lon_sum'] += lon
        a['min_lat'] = min(a['min_lat'], lat)
        a['max_lat'] = max(a['max_lat'], lat)
        a['min_lon'] = min(a['min_lon'], lon)
        a['max_lon'] = max(a['max_lon'], lon)
        if prix is not None:
            a['prices'].append(prix)

    resultats = []
    for zone, a in agg.items():
        avg_price_m2 = round(sum(a['prices']) / len(a['prices']), 2) if a['prices'] else None
        resultats.append({
            'quartier': zone,
            'count': a['count'],
            'center': {
                'lat': a['lat_sum'] / a['count'],
                'lon': a['lon_sum'] / a['count']
            },
            'bbox': {
                'south': a['min_lat'],
                'west': a['min_lon'],
                'north': a['max_lat'],
                'east': a['max_lon']
            },
            'avg_price_m2': avg_price_m2
        })

    resultats.sort(key=lambda x: x['quartier'].lower())
    return jsonify(resultats)


def _load_geojson(path):
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _get_quartier_polygons():
    if _geo_cache['quartier_polygons'] is not None:
        return _geo_cache['quartier_polygons']

    geojson_candidates = [
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana.geojson'),
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana_ville.geojson'),
        os.path.join(app.static_folder or 'static', 'data', 'quartiers_tana_full.geojson'),
    ]

    polygons = []
    for path in geojson_candidates:
        gj = _load_geojson(path)
        if not gj:
            continue
        for feat in gj.get('features', []):
            props = feat.get('properties', {})
            geom = feat.get('geometry')
            if not geom:
                continue
            name = props.get('quartier') or props.get('name') or props.get('fokontany')
            commune = props.get('commune')
            if not name:
                continue
            polygons.append({
                'quartier': str(name).strip(),
                'commune': str(commune).strip() if commune else None,
                'geometry': shapely_shape(geom),
            })
        if polygons:
            break

    _geo_cache['quartier_polygons'] = polygons
    return polygons


def _get_routes():
    if _geo_cache['routes_nationales'] is not None and _geo_cache['routes_principales'] is not None:
        return _geo_cache['routes_nationales'], _geo_cache['routes_principales']

    path = os.path.join(app.static_folder or 'static', 'data', 'routes_tana.geojson')
    gj = _load_geojson(path)
    routes_nationales, routes_principales = [], []
    if gj:
        for feat in gj.get('features', []):
            props = feat.get('properties', {})
            geom = feat.get('geometry')
            if not geom:
                continue
            g = shapely_shape(geom)
            rt = (props.get('type_route') or '').lower()
            if rt == 'nationale':
                routes_nationales.append(g)
            elif rt == 'principale':
                routes_principales.append(g)

    _geo_cache['routes_nationales'] = routes_nationales
    _geo_cache['routes_principales'] = routes_principales
    return routes_nationales, routes_principales


def _geometry_distance_meters(point, line, lat_ref=-18.88):
    # Approximation locale suffisante pour l'UX de saisie.
    meters_per_deg_lat = 110540.0
    meters_per_deg_lon = 111320.0 * math.cos(math.radians(abs(lat_ref)))

    p = Point(point.x * meters_per_deg_lon, point.y * meters_per_deg_lat)

    if line.geom_type == 'MultiLineString':
        dists = [_geometry_distance_meters(point, sub, lat_ref=lat_ref) for sub in line.geoms]
        return min(dists) if dists else float('inf')

    line_coords = [(x * meters_per_deg_lon, y * meters_per_deg_lat) for x, y in line.coords]
    line_metric = shapely_shape({'type': 'LineString', 'coordinates': line_coords})
    return p.distance(line_metric)


@app.route('/api/location/enrich', methods=['GET'])
def enrich_location():
    """Retourne quartier/commune + distances auto aux routes de reference."""
    try:
        lat = float(request.args.get('lat'))
        lon = float(request.args.get('lon'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Paramètres lat/lon invalides'}), 400

    point = Point(lon, lat)
    quartier = None
    commune = None

    polygons = _get_quartier_polygons()
    for poly in polygons:
        geom = poly['geometry']
        if geom.contains(point) or geom.touches(point):
            quartier = poly['quartier']
            commune = poly['commune']
            break

    routes_nationales, routes_principales = _get_routes()

    dist_rn = None
    if routes_nationales:
        dist_rn = min(_geometry_distance_meters(point, line, lat_ref=lat) for line in routes_nationales)

    dist_rp = None
    if routes_principales:
        dist_rp = min(_geometry_distance_meters(point, line, lat_ref=lat) for line in routes_principales)

    return jsonify({
        'success': True,
        'quartier': quartier,
        'commune': commune,
        'distance_route_nationale': round(dist_rn, 1) if dist_rn is not None else None,
        'distance_route_principale': round(dist_rp, 1) if dist_rp is not None else None,
    })

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
            'prix_estime_m2': prix_estime,
            'prix_estime_total': round(prix_estime * float(data.get('surface_m2', 0)), 2) if data.get('surface_m2') else None,
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
    
    type_bien = data.get('type_bien', 'terrain')
    prix_base = get_prix_base_marche(type_bien)
    
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
    
    prix_ajuste = prix_base * coeff_localisation(data)
    prix_comparables = prix_estime_par_comparables(data)
    if prix_comparables:
        prix_ajuste = (prix_ajuste * 0.45) + (prix_comparables * 0.55)

    # Arrondir au millier près
    return round(prix_ajuste / 1000) * 1000


def get_prix_base_marche(type_bien):
    """
    Repères de marché de départ (Ar/m²) basés sur numbeo + calibrage local.
    """
    base = {
        'terrain': 350000.0,
        'appartement': 2700000.0,
        'maison': 2200000.0
    }
    return base.get(type_bien, 350000.0)


def coeff_localisation(data):
    """Ajuste légèrement le prix selon les zones premium connues."""
    zone = (data.get('quartier') or data.get('commune') or '').lower()

    premium = ['ivandry', 'ambatobe', 'ankorondrano', 'faravohitra']
    intermediaire = ['analakely', 'andohalo', 'antsahavola', 'antsakaviro']

    if any(z in zone for z in premium):
        return 1.15
    if any(z in zone for z in intermediaire):
        return 1.05
    return 1.0


def prix_estime_par_comparables(data, limit=12):
    """
    Estimation par comparables pondérés proches (même type + zone similaire).
    """
    q = Terrain.query.filter(Terrain.prix_proprietaire.isnot(None))

    type_bien = data.get('type_bien')
    if type_bien:
        q = q.filter(Terrain.type_bien == type_bien)

    zone = (data.get('quartier') or '').strip()
    if zone:
        q = q.filter(func.lower(Terrain.quartier) == zone.lower())
    elif data.get('commune'):
        q = q.filter(func.lower(Terrain.commune) == str(data.get('commune')).lower())

    comparables = q.order_by(Terrain.date_reference.desc().nullslast(), Terrain.created_at.desc()).limit(40).all()
    if not comparables:
        return None

    dist_rn = to_float(data.get('distance_route_nationale'))
    dist_rp = to_float(data.get('distance_route_principale'))
    surface = to_float(data.get('surface_m2'))

    scored = []
    for c in comparables:
        score = 1.0

        if c.accessibilite == data.get('accessibilite'):
            score += 0.25
        if c.type_papier == data.get('type_papier'):
            score += 0.2
        if c.is_batissable == data.get('is_batissable', True):
            score += 0.1

        if dist_rn is not None and c.distance_route_nationale is not None:
            score += max(0.0, 0.15 - min(abs(c.distance_route_nationale - dist_rn) / 2500, 0.15))
        if dist_rp is not None and c.distance_route_principale is not None:
            score += max(0.0, 0.12 - min(abs(c.distance_route_principale - dist_rp) / 1200, 0.12))
        if surface is not None and c.surface_m2:
            score += max(0.0, 0.18 - min(abs(c.surface_m2 - surface) / 5000, 0.18))

        scored.append((score, float(c.prix_proprietaire)))

    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[:limit]
    poids_total = sum(s for s, _ in best)
    if poids_total == 0:
        return None

    return sum(s * p for s, p in best) / poids_total


def to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_details_calcul(data):
    """Retourne les détails du calcul pour transparence"""
    surface = to_float(data.get('surface_m2'))
    prix_m2 = calculer_prix_estime(data)
    details = {
        'prix_base': get_prix_base_marche(data.get('type_bien', 'terrain')),
        'coefficients': {
            'type_bien': data.get('type_bien', 'terrain'),
            'quartier_commune': data.get('quartier') or data.get('commune'),
            'accessibilite': data.get('accessibilite'),
            'type_papier': data.get('type_papier'),
            'batissable': data.get('is_batissable', True)
        },
        'distances': {
            'route_nationale': data.get('distance_route_nationale'),
            'route_principale': data.get('distance_route_principale'),
            'jirama': data.get('distance_jirama')
        },
        'surface_m2': surface,
        'estimation_m2': prix_m2,
        'estimation_totale': round(prix_m2 * surface, 2) if surface else None
    }
    return details

if __name__ == '__main__':
    app.run(debug=True)