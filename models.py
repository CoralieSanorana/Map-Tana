from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
from datetime import datetime

db = SQLAlchemy()

class Terrain(db.Model):
    __tablename__ = 'terrains'
    
    id = db.Column(db.Integer, primary_key=True)
    commune = db.Column(db.String(100), nullable=False)
    quartier = db.Column(db.String(120))
    type_bien = db.Column(db.String(30), nullable=False, default='terrain')  # terrain, maison, appartement
    surface_m2 = db.Column(db.Float)
    accessibilite = db.Column(db.String(20), nullable=False)  # aucun, moto, voiture
    is_batissable = db.Column(db.Boolean, default=True, nullable=False)
    distance_route_nationale = db.Column(db.Float)  # distance route nationale en mètres
    distance_route_principale = db.Column(db.Float)  # distance route principale en mètres
    distance_jirama = db.Column(db.Float)  # distance poteau JIRAMA en mètres
    type_papier = db.Column(db.String(50), nullable=False)  # titre_borne, kadasitra, fanolorana
    source_annonce = db.Column(db.String(255))
    date_reference = db.Column(db.Date)
    devise = db.Column(db.String(10), default='Ar')
    prix_total = db.Column(db.Numeric(14, 2))
    prix_proprietaire = db.Column(db.Numeric(12, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Position géographique (Point GPS avec SRID 4326 - WGS84)
    geom = db.Column(Geometry('POINT', srid=4326), nullable=False, unique=True) 

    def __repr__(self):
        return f'<Terrain {self.id} à {self.commune} ({self.accessibilite})>'
    
    def to_dict(self):
        """Convertit le terrain en dictionnaire pour JSON"""
        # Extraire les coordonnées de la géométrie
        point = to_shape(self.geom) if self.geom else None
        return {
            'id': self.id,
            'commune': self.commune,
            'quartier': self.quartier,
            'type_bien': self.type_bien,
            'surface_m2': self.surface_m2,
            'accessibilite': self.accessibilite,
            'is_batissable': self.is_batissable,
            'distance_route_nationale': self.distance_route_nationale,
            'distance_route_principale': self.distance_route_principale,
            'distance_jirama': self.distance_jirama,
            'type_papier': self.type_papier,
            'source_annonce': self.source_annonce,
            'date_reference': self.date_reference.isoformat() if self.date_reference else None,
            'devise': self.devise,
            'prix_total': float(self.prix_total) if self.prix_total else None,
            'prix_proprietaire': float(self.prix_proprietaire) if self.prix_proprietaire else None,
            'latitude': point.y if point else None,
            'longitude': point.x if point else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def from_dict(data):
        """Crée un objet Terrain depuis un dictionnaire"""
        date_reference = data.get('date_reference')
        if isinstance(date_reference, str):
            try:
                date_reference = datetime.fromisoformat(date_reference).date()
            except ValueError:
                date_reference = None

        terrain = Terrain(
            commune=data.get('commune'),
            quartier=data.get('quartier'),
            type_bien=data.get('type_bien', 'terrain'),
            surface_m2=data.get('surface_m2'),
            accessibilite=data.get('accessibilite'),
            is_batissable=data.get('is_batissable', True),
            distance_route_nationale=data.get('distance_route_nationale'),
            distance_route_principale=data.get('distance_route_principale'),
            distance_jirama=data.get('distance_jirama'),
            type_papier=data.get('type_papier'),
            source_annonce=data.get('source_annonce'),
            date_reference=date_reference,
            devise=data.get('devise', 'Ar'),
            prix_total=data.get('prix_total'),
            prix_proprietaire=data.get('prix_proprietaire')
        )
        
        # Créer la géométrie Point à partir des coordonnées
        lat = data.get('latitude')
        lon = data.get('longitude')
        if lat is not None and lon is not None:
            point = Point(lon, lat)  # Point(x=longitude, y=latitude)
            terrain.geom = from_shape(point, srid=4326)
        
        return terrain