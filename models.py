from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry

db = SQLAlchemy()

class Terrain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    commune = db.Column(db.String(100))
    accessibilite = db.Column(db.String(20)) # aucun, moto, voiture
    is_batissable = db.Column(db.Boolean, default=True)
    distance_rn = db.Column(db.Float) # distance route nationale en mètres
    distance_jirama = db.Column(db.Float) # distance poteau en mètres
    type_papier = db.Column(db.String(50)) # titre borne, kadasitra, fifanolorana
    prix_proprietaire = db.Column(db.Float)
    
    # L'élément clé : la position géographique (Point GPS)
    geom = db.Column(Geometry('POINT')) 

    def __repr__(self):
        return f'<Terrain à {self.commune}>'