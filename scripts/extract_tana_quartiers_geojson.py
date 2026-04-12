import json
from pathlib import Path

import shapefile
from shapely.geometry import shape as shp_shape, mapping

# Source officiel HDX OCHA/BNGRC (ADM4 fokontany)
SOURCE_SHP = Path("data/geodata/mdg_adm_bngrc_ocha_20181031_shp/mdg_admbnda_adm4_BNGRC_OCHA_20181031.shp")
OUT_GEOJSON_FULL = Path("static/data/quartiers_tana_full.geojson")
OUT_GEOJSON_SIMPLIFIED = Path("static/data/quartiers_tana.geojson")
OUT_GEOJSON_CITY_ONLY = Path("static/data/quartiers_tana_ville.geojson")

# Couvre Tana ville + peripherie immediate frequemment utilisee dans les annonces
DISTRICTS_TANA = {
    "1er Arrondissement",
    "2e Arrondissement",
    "3e Arrondissement",
    "4e Arrondissement",
    "5e Arrondissement",
    "6e Arrondissement",
    "Antananarivo Avaradrano",
    "Antananarivo Atsimondrano",
    "Ambohidratrimo",
}

CITY_ARRONDISSEMENTS = {
    "1er Arrondissement",
    "2e Arrondissement",
    "3e Arrondissement",
    "4e Arrondissement",
    "5e Arrondissement",
    "6e Arrondissement",
}


def write_geojson(path: Path, features: list[dict]) -> None:
    feature_collection = {
        "type": "FeatureCollection",
        "name": path.stem,
        "features": features,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feature_collection, ensure_ascii=False), encoding="utf-8")


def simplify_features(features: list[dict], tolerance: float = 0.00018) -> list[dict]:
    simplified = []
    for feature in features:
        geom = shp_shape(feature["geometry"])
        simple_geom = geom.simplify(tolerance, preserve_topology=True)
        new_feature = {
            "type": "Feature",
            "properties": feature["properties"],
            "geometry": mapping(simple_geom),
        }
        simplified.append(new_feature)
    return simplified


def main() -> None:
    if not SOURCE_SHP.exists():
        raise FileNotFoundError(f"Shapefile introuvable: {SOURCE_SHP}")

    reader = shapefile.Reader(str(SOURCE_SHP), encoding="utf-8")
    fields = [f[0] for f in reader.fields[1:]]
    idx = {name: i for i, name in enumerate(fields)}

    required = ["ADM1_EN", "ADM2_EN", "ADM3_EN", "ADM4_EN", "ADM4_PCODE"]
    missing = [f for f in required if f not in idx]
    if missing:
        raise ValueError(f"Colonnes manquantes dans shapefile: {missing}")

    features = []
    for shape_record in reader.iterShapeRecords():
        rec = shape_record.record
        region = rec[idx["ADM1_EN"]]
        district = rec[idx["ADM2_EN"]]

        if region != "Analamanga" or district not in DISTRICTS_TANA:
            continue

        geometry = shape_record.shape.__geo_interface__
        props = {
            "quartier": rec[idx["ADM4_EN"]],
            "fokontany": rec[idx["ADM4_EN"]],
            "commune": rec[idx["ADM3_EN"]],
            "district": district,
            "region": region,
            "pcode": rec[idx["ADM4_PCODE"]],
            "name": rec[idx["ADM4_EN"]],
        }

        features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": geometry,
            }
        )

    city_only = [f for f in features if f["properties"]["district"] in CITY_ARRONDISSEMENTS]
    simplified = simplify_features(features)
    simplified_city = simplify_features(city_only)

    write_geojson(OUT_GEOJSON_FULL, features)
    write_geojson(OUT_GEOJSON_SIMPLIFIED, simplified)
    write_geojson(OUT_GEOJSON_CITY_ONLY, simplified_city)

    print(f"GeoJSON full genere: {OUT_GEOJSON_FULL} ({len(features)} polygones)")
    print(f"GeoJSON simplifie genere: {OUT_GEOJSON_SIMPLIFIED} ({len(simplified)} polygones)")
    print(f"GeoJSON ville stricte genere: {OUT_GEOJSON_CITY_ONLY} ({len(simplified_city)} polygones)")


if __name__ == "__main__":
    main()
