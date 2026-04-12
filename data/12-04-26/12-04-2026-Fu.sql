-- =====================================================
-- Map-Tana - Migration + donnees immobilieres reelles (Antananarivo)
-- Date: 2026-04-12
-- Sources publiques utilisees:
--   - Expat Madagascar (annonces a vendre Antananarivo)
--   - Numbeo Property Prices (repere marche global)
--
-- IMPORTANT:
-- - Ces donnees proviennent d'annonces publiques (prix demandes, pas actes notaries).
-- - Verifier les annonces periodiquement (marches evolutifs).
-- - Ce script complete la table existante `terrains` du projet.
-- =====================================================

BEGIN;

-- -----------------------------------------------------
-- 1) Evolution de schema pour estimation avancee
-- -----------------------------------------------------

ALTER TABLE terrains
	ADD COLUMN IF NOT EXISTS quartier VARCHAR(120),
	ADD COLUMN IF NOT EXISTS type_bien VARCHAR(30) DEFAULT 'terrain' NOT NULL,
	ADD COLUMN IF NOT EXISTS surface_m2 FLOAT CHECK (surface_m2 > 0),
	ADD COLUMN IF NOT EXISTS source_annonce VARCHAR(255),
	ADD COLUMN IF NOT EXISTS date_reference DATE,
	ADD COLUMN IF NOT EXISTS devise VARCHAR(10) DEFAULT 'Ar',
	ADD COLUMN IF NOT EXISTS prix_total DECIMAL(14,2) CHECK (prix_total >= 0);

DO $$
BEGIN
	IF NOT EXISTS (
		SELECT 1
		FROM pg_constraint
		WHERE conname = 'chk_type_bien'
	) THEN
		ALTER TABLE terrains
			ADD CONSTRAINT chk_type_bien CHECK (type_bien IN ('terrain', 'maison', 'appartement'));
	END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_terrains_quartier ON terrains(quartier);
CREATE INDEX IF NOT EXISTS idx_terrains_type_bien ON terrains(type_bien);
CREATE INDEX IF NOT EXISTS idx_terrains_surface_m2 ON terrains(surface_m2);

-- -----------------------------------------------------
-- 2) Insertion des comparables reels (prix annonces)
-- -----------------------------------------------------
INSERT INTO terrains (
	commune,
	quartier,
	type_bien,
	surface_m2,
	accessibilite,
	is_batissable,
	distance_route_nationale,
	distance_route_principale,
	distance_jirama,
	type_papier,
	prix_total,
	prix_proprietaire,
	devise,
	source_annonce,
	date_reference,
	geom
)
SELECT * FROM (
	VALUES
	(
		'Antananarivo', 'Andriantany', 'terrain', 2000.0,
		'moto', true, 420.0, 180.0, 220.0,
		'kadasitra',
		170000000.00, 85000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/44-terrains-a-vendre/800137-terrain-de-2000m2-andriantany.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5228, -18.8945), 4326)
	),
	(
		'Antananarivo', 'Ambatomirahavavy', 'terrain', 500.0,
		'voiture', true, 680.0, 260.0, 140.0,
		'titre_borne',
		800000000.00, 1600000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/44-terrains-a-vendre/794894-terrain-a-vendre-ambatomirahavavy.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.4102, -18.9210), 4326)
	),
	(
		'Antananarivo', 'Ambohimangakely (Behitsy)', 'terrain', 870.0,
		'voiture', true, 220.0, 90.0, 180.0,
		'kadasitra',
		95700000.00, 110000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/44-terrains-a-vendre/801426-vente-terrain-870m2-behitsy-ambohimangakely-accessible-par-la-by-pass-antananarivo.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5987, -18.9116), 4326)
	),
	(
		'Antananarivo', 'Faravohitra', 'maison', 373.0,
		'voiture', true, 95.0, 40.0, 20.0,
		'titre_borne',
		1650000000.00, 4423592.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/796750-villa-traditionnelle-f8-a-vendre-a-faravohitra.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5266, -18.9140), 4326)
	),
	(
		'Antananarivo', 'Antananarivo Ville', 'maison', 202.0,
		'voiture', true, 180.0, 70.0, 35.0,
		'titre_borne',
		1195000000.00, 5915842.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/795962-villa-de-luxe-de-202-m2-a-vendre-a-antananarivo.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5051, -18.8884), 4326)
	),
	(
		'Antananarivo', 'Antsakambahiny', 'maison', 250.0,
		'moto', true, 530.0, 220.0, 150.0,
		'kadasitra',
		300000000.00, 1200000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/792671-villa-f4-independante-a-vendre-antsakambahiny-ambohijanahary.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5510, -18.9030), 4326)
	),
	(
		'Antananarivo', 'Ankerana', 'maison', 330.0,
		'voiture', true, 260.0, 120.0, 90.0,
		'titre_borne',
		600000000.00, 1818182.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/764164-une-villa-a-etage-f5-a-ankerana.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5488, -18.8815), 4326)
	),
	(
		'Antananarivo', 'Ambatobe', 'maison', 400.0,
		'voiture', true, 330.0, 110.0, 70.0,
		'titre_borne',
		1000000000.00, 2500000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/774732-a-vendre-une-charmante-villa-f4-sur-ambatobe-a-5-min-a-pied-du-lycee-francais-dans-une-residence-securisee.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5440, -18.8690), 4326)
	),
	(
		'Antananarivo', 'Ivato', 'appartement', 166.0,
		'voiture', true, 1500.0, 450.0, 250.0,
		'kadasitra',
		615000000.00, 3704819.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/43-appartements-a-vendre/793802-appartement-t4-mamory-ivato.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.4802, -18.8037), 4326)
	),
	(
		'Antananarivo', 'Ambatobe', 'appartement', 166.0,
		'voiture', true, 380.0, 120.0, 60.0,
		'titre_borne',
		250000000.00, 1506024.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/43-appartements-a-vendre/791562-vente-beau-t2-ambatobe-antananarivo-vip.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5422, -18.8678), 4326)
	),
	(
		'Antananarivo', 'Ambatobe', 'appartement', 1000.0,
		'voiture', true, 410.0, 180.0, 95.0,
		'titre_borne',
		429000000.00, 429000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/43-appartements-a-vendre/805521-beau-t3-meuble-a-vendre-a-ambatobe-antananarivo-vip.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5453, -18.8706), 4326)
	),
	(
		'Antananarivo', 'Ambatovinaky', 'maison', 400.0,
		'moto', true, 120.0, 45.0, 28.0,
		'titre_borne',
		1250000000.00, 3125000.00, 'Ar',
		'https://www.expat.com/fr/immobilier/afrique/madagascar/antananarivo/42-maisons-a-vendre/782724-maison-a-vendre-centre-ville-ambatovinaky.html',
		DATE '2026-04-12',
		ST_SetSRID(ST_MakePoint(47.5170, -18.9186), 4326)
	)
) AS v(
	commune,
	quartier,
	type_bien,
	surface_m2,
	accessibilite,
	is_batissable,
	distance_route_nationale,
	distance_route_principale,
	distance_jirama,
	type_papier,
	prix_total,
	prix_proprietaire,
	devise,
	source_annonce,
	date_reference,
	geom
)
WHERE NOT EXISTS (
	SELECT 1
	FROM terrains t
	WHERE t.source_annonce = v.source_annonce
);

-- -----------------------------------------------------
-- 3) Reperes marche globaux (Numbeo) comme points ancres
-- -----------------------------------------------------
INSERT INTO terrains (
	commune,
	quartier,
	type_bien,
	surface_m2,
	accessibilite,
	is_batissable,
	distance_route_nationale,
	distance_route_principale,
	distance_jirama,
	type_papier,
	prix_total,
	prix_proprietaire,
	devise,
	source_annonce,
	date_reference,
	geom
)
VALUES
(
	'Antananarivo', 'Centre-ville (repere marche)', 'appartement', 100.0,
	'voiture', true, 80.0, 35.0, 25.0,
	'titre_borne',
	290452232.00, 2904522.32, 'Ar',
	'https://www.numbeo.com/property-investment/in/Antananarivo',
	DATE '2026-04-06',
	ST_SetSRID(ST_MakePoint(47.5079, -18.8792), 4326)
),
(
	'Antananarivo', 'Peripherie (repere marche)', 'appartement', 100.0,
	'moto', true, 750.0, 260.0, 180.0,
	'kadasitra',
	249687015.00, 2496870.15, 'Ar',
	'https://www.numbeo.com/property-investment/in/Antananarivo',
	DATE '2026-04-06',
	ST_SetSRID(ST_MakePoint(47.5600, -18.9200), 4326)
)
ON CONFLICT (geom) DO NOTHING;

COMMIT;

-- Verification rapide
SELECT
	id,
	quartier,
	type_bien,
	surface_m2,
	prix_total,
	prix_proprietaire,
	date_reference
FROM terrains
ORDER BY created_at DESC
LIMIT 25;
