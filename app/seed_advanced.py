from __future__ import annotations

import math
import random

from sqlalchemy.orm import Session

from app.engine.ringeye import RingEyeParams, analyze_ring, simulate_scan
from app.models import RingEyeReading, ShmReading, SpatialAsset

LINE = "Beijing Metro Line 12"
SECTION = "TBM-left-line"
BASE_CHAINAGE_M = 100.0
RING_LENGTH_M = 1.2


def seed_shm(db: Session, rings: int = 36) -> int:
    if db.query(ShmReading).count() > 0:
        return 0
    rng = random.Random(7)
    count = 0
    for ring in range(1, rings + 1):
        chainage = BASE_CHAINAGE_M + ring * RING_LENGTH_M
        # seepage m3/day, mild drift + noise
        seepage = 0.6 + 0.25 * math.sin(ring / 6.0) + rng.uniform(-0.05, 0.05)
        if ring in (19, 27):
            seepage += 0.55  # induced leaks
        # segment displacement mm
        displace = 1.4 + 0.5 * math.sin(ring / 9.0) + rng.uniform(-0.15, 0.15)
        # lining strain microstrain
        strain = 180.0 + 45.0 * math.sin(ring / 11.0) + rng.uniform(-8, 8)
        if ring == 33:
            strain += 120.0  # induced strain spike

        for sensor_id, stype, value, unit, status in [
            (f"SEEP-{ring:03d}", "seepage", round(seepage, 3), "m3/day", "alert" if seepage > 1.0 else "normal"),
            (f"SEGM-{ring:03d}", "segment_displacement", round(displace, 2), "mm", "alert" if displace > 2.2 else "normal"),
            (f"STRAIN-{ring:03d}", "lining_strain", round(strain, 1), "ue", "alert" if strain > 250 else "normal"),
        ]:
            db.add(
                ShmReading(
                    line=LINE,
                    section=SECTION,
                    ring_no=ring,
                    chainage_m=round(chainage, 2),
                    sensor_id=sensor_id,
                    sensor_type=stype,
                    measured_value=value,
                    unit=unit,
                    status=status,
                )
            )
            count += 1
    db.commit()
    return count


def seed_spatial_assets(db: Session) -> int:
    if db.query(SpatialAsset).count() > 0:
        return 0
    assets = [
        SpatialAsset(
            name="Building B-01 Foundation",
            asset_type="foundation",
            x_enu=180.0,
            y_enu=-2.5,
            z_enu=-8.0,
            radius_m=0.5,
            clearance_limit_m=3.0,
            note="Adjacent building foundation",
        ),
        SpatialAsset(
            name="Sewer DN800",
            asset_type="sewer",
            x_enu=158.0,
            y_enu=2.186,
            z_enu=-10.0,
            radius_m=0.4,
            clearance_limit_m=2.186,
            note="Clearance 2.186 m - verify",
        ),
        SpatialAsset(
            name="Water Main DN1200",
            asset_type="water_main",
            x_enu=264.0,
            y_enu=1.5,
            z_enu=-9.0,
            radius_m=0.6,
            clearance_limit_m=3.0,
            note="20 m ahead of face",
        ),
        SpatialAsset(
            name="Metro Line L Tunnel",
            asset_type="metro_tunnel",
            x_enu=120.0,
            y_enu=5.2,
            z_enu=-20.0,
            radius_m=3.1,
            clearance_limit_m=6.0,
            note="Adjacent operating metro tunnel",
        ),
        SpatialAsset(
            name="HV Cable Duct",
            asset_type="utility",
            x_enu=205.0,
            y_enu=-4.2,
            z_enu=-6.0,
            radius_m=0.3,
            clearance_limit_m=2.0,
            note="Buried HV cable",
        ),
        SpatialAsset(
            name="Underpass Piles",
            asset_type="structure",
            x_enu=232.0,
            y_enu=-1.8,
            z_enu=-12.0,
            radius_m=0.5,
            clearance_limit_m=2.5,
            note="Road underpass pile group",
        ),
    ]
    db.add_all(assets)
    db.commit()
    return len(assets)


def seed_ringeye(db: Session, rings: int = 36) -> int:
    if db.query(RingEyeReading).count() > 0:
        return 0
    rng = random.Random(11)
    count = 0
    for ring in range(1, rings + 1):
        chainage = BASE_CHAINAGE_M + ring * RING_LENGTH_M
        ovalization = 3.0 + 1.2 * math.sin(ring / 5.0) + rng.uniform(-0.5, 0.5)
        if ring in (19, 27):
            ovalization += 6.0  # induced ovalization events
        if ring == 33:
            ovalization += 4.0
        cloud = simulate_scan(ovalization, seed=ring)
        analysis = analyze_ring(ring, chainage, cloud["radial_devs_mm"], cloud["angles_deg"], RingEyeParams())
        db.add(
            RingEyeReading(
                line=LINE,
                section=SECTION,
                ring_no=ring,
                chainage_m=round(chainage, 2),
                nominal_diameter_mm=analysis["nominal_diameter_mm"],
                delta_d_mm=analysis["delta_d_mm"],
                ovalization_pct=analysis["ovalization_pct"],
                eccentricity_mm=analysis["eccentricity_mm"],
                joint_gap_mm=analysis["joint_gap_mm"],
                seepage_risk=analysis["seepage_risk"],
                status=analysis["status"],
            )
        )
        count += 1
    db.commit()
    return count


def seed_advanced(db: Session) -> dict:
    return {
        "shm_readings": seed_shm(db),
        "spatial_assets": seed_spatial_assets(db),
        "ringeye_readings": seed_ringeye(db),
    }
