-- =====================================================
-- Script de création de la base de données Map-Tana
-- PostgreSQL + PostGIS
-- =====================================================

-- 1. Création de la base de données (à exécuter en dehors de cette base)
-- CREATE DATABASE map_tana WITH ENCODING = 'UTF8';

-- 2. Activation de l'extension PostGIS pour les données géospatiales
CREATE EXTENSION IF NOT EXISTS postgis;

-- Vérification de l'installation PostGIS
SELECT PostGIS_Version();

-- =====================================================
-- Table: terrains
-- Description: Stocke les terrains à vendre avec leurs caractéristiques
-- =====================================================
DROP TABLE IF EXISTS terrains CASCADE;

CREATE TABLE terrains (
    id                      SERIAL PRIMARY KEY,
    commune                 VARCHAR(100) NOT NULL,
    accessibilite           VARCHAR(20) NOT NULL,
    is_batissable           BOOLEAN DEFAULT TRUE NOT NULL,
    distance_route_nationale  FLOAT CHECK (distance_route_nationale >= 0),
    distance_route_principale FLOAT CHECK (distance_route_principale >= 0),
    distance_jirama         FLOAT CHECK (distance_jirama >= 0),
    type_papier             VARCHAR(50) NOT NULL,
    prix_proprietaire       DECIMAL(12,2) CHECK (prix_proprietaire >= 0),
    geom                    GEOMETRY(POINT, 4326) NOT NULL,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Contraintes de validation
    CONSTRAINT chk_accessibilite CHECK (accessibilite IN ('aucun', 'moto', 'voiture')),
    CONSTRAINT chk_type_papier CHECK (type_papier IN ('titre_borne', 'kadasitra', 'fanolorana')),
    -- Chaque position GPS doit être unique (pas deux terrains au même endroit)
    CONSTRAINT uq_geom UNIQUE (geom)
);

-- =====================================================
-- Index pour optimiser les performances
-- =====================================================

-- Index spatial sur la géométrie (très important pour les recherches par coordonnées)
CREATE INDEX idx_terrains_geom ON terrains USING GIST(geom);

-- Index sur la commune pour filtrer par zone
CREATE INDEX idx_terrains_commune ON terrains(commune);

-- Index sur le type d'accessibilité pour les filtres
CREATE INDEX idx_terrains_accessibilite ON terrains(accessibilite);

-- =====================================================
-- Données de test - Quelques terrains à Antananarivo
-- =====================================================

-- Insertion de terrains de test (coordonnées autour d'Antananarivo)
INSERT INTO terrains (commune, accessibilite, is_batissable, distance_route_nationale, 
                      distance_route_principale, distance_jirama, type_papier, prix_proprietaire, geom)
VALUES 
    -- Terrain 1: Ivandry, accès voiture, bien placé
    ('Ivandry', 'voiture', true, 150.5, 50.0, 30.0, 'titre_borne', 350000.00, 
     ST_SetSRID(ST_MakePoint(47.5250, -18.8700), 4326)),
    
    -- Terrain 2: Ankorondrano, accès moto
    ('Ankorondrano', 'moto', true, 800.0, 200.0, 150.0, 'kadasitra', 180000.00, 
     ST_SetSRID(ST_MakePoint(47.5150, -18.8850), 4326)),
    
    -- Terrain 3: Ambohidratrimo, aucun accès
    ('Ambohidratrimo', 'aucun', false, 2500.0, 800.0, 500.0, 'fanolorana', 75000.00, 
     ST_SetSRID(ST_MakePoint(47.4500, -18.9000), 4326)),
    
    -- Terrain 4: Analakely, centre-ville, accès voiture
    ('Analakely', 'voiture', true, 50.0, 20.0, 10.0, 'titre_borne', 500000.00, 
     ST_SetSRID(ST_MakePoint(47.5070, -18.9070), 4326)),
    
    -- Terrain 5: Ambatobe, accès moto
    ('Ambatobe', 'moto', true, 600.0, 150.0, 100.0, 'kadasitra', 220000.00, 
     ST_SetSRID(ST_MakePoint(47.5400, -18.8650), 4326));

-- =====================================================
-- Vérification des données insérées
-- =====================================================
SELECT id, commune, accessibilite, type_papier, prix_proprietaire, 
       ST_AsText(geom) as coordonnees, created_at
FROM terrains;

-- =====================================================
-- Fonction utilitaire: Rechercher un terrain par coordonnées (rayon de 50m)
-- =====================================================
CREATE OR REPLACE FUNCTION find_terrain_near_point(lat FLOAT, lon FLOAT, radius_meters FLOAT DEFAULT 50)
RETURNS TABLE (
    id INTEGER,
    commune VARCHAR,
    accessibilite VARCHAR,
    is_batissable BOOLEAN,
    distance_route_nationale FLOAT,
    distance_route_principale FLOAT,
    distance_jirama FLOAT,
    type_papier VARCHAR,
    prix_proprietaire DECIMAL,
    distance_meters FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.commune,
        t.accessibilite,
        t.is_batissable,
        t.distance_route_nationale,
        t.distance_route_principale,
        t.distance_jirama,
        t.type_papier,
        t.prix_proprietaire,
        ST_Distance(
            t.geom::geography,
            ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
        )::FLOAT as distance_meters
    FROM terrains t
    WHERE ST_DWithin(
        t.geom::geography,
        ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography,
        radius_meters
    )
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql;

-- Commentaire: Utiliser la fonction avec:
-- SELECT * FROM find_terrain_near_point(-18.8700, 47.5250, 100);