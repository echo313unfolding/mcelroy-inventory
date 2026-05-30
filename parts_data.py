"""
McElroy Parts Database for Underground Solutions
Built from TracStar 618/900/1200 operator manuals + McElroy Parts Finder.

Machine fleet:
  ~20x 618 (TracStar, Rolling, Pit Bull — standard + i-series)
  ~12x 900 (TracStar — standard + i-series)
  ~4x 1200 (TracStar + MegaMc 1648 — standard + i-series)

All machines do Fusible PVC (C-900/C-905) butt fusion.
"""

# ============================================================
# PART CATEGORIES (InvenTree category tree)
# ============================================================

CATEGORIES = [
    # Top-level
    {"name": "Carriage Assembly", "parent": None, "description": "Fusion carriage, jaws, guides, cylinders"},
    {"name": "Jaw Inserts", "parent": "Carriage Assembly", "description": "Pipe-size-specific jaw inserts (cast & fabricated)"},
    {"name": "Hydraulic Cylinders", "parent": "Carriage Assembly", "description": "High/Medium/Low force carriage cylinders"},
    {"name": "Carriage Hardware", "parent": "Carriage Assembly", "description": "Guide rods, bushings, pins, bolts"},

    {"name": "Facer", "parent": None, "description": "Rotating planer-block facer assembly"},
    {"name": "Facer Blades", "parent": "Facer", "description": "Replaceable carbide facer blades"},
    {"name": "Facer Drive", "parent": "Facer", "description": "Chain, sprockets, hydraulic motor"},

    {"name": "Heater", "parent": None, "description": "Heater plate assembly with PTFE coating"},
    {"name": "Heater Plates", "parent": "Heater", "description": "Replaceable heater plates"},
    {"name": "Heater Electrical", "parent": "Heater", "description": "Elements, thermostats, cords, connectors"},
    {"name": "Heater Stand", "parent": "Heater", "description": "Insulated heater stand/blanket"},

    {"name": "Hydraulic System", "parent": None, "description": "Hydraulic power unit components"},
    {"name": "Manifold Block", "parent": "Hydraulic System", "description": "Control valves, pressure reducing valves, gauge"},
    {"name": "Hydraulic Hoses", "parent": "Hydraulic System", "description": "Hoses, fittings, quick-disconnects"},
    {"name": "Hydraulic Filters", "parent": "Hydraulic System", "description": "10-micron return filter elements"},
    {"name": "Hydraulic Fluid", "parent": "Hydraulic System", "description": "AW-46 hydraulic oil"},
    {"name": "Hydraulic Pump", "parent": "Hydraulic System", "description": "Gear pump, couplings"},

    {"name": "Power Unit", "parent": None, "description": "Engine, alternator, electrical"},
    {"name": "Diesel Engine", "parent": "Power Unit", "description": "3-cylinder water-cooled diesel (Kubota/Yanmar)"},
    {"name": "Gas Engine", "parent": "Power Unit", "description": "Single-cylinder air-cooled gas (Honda)"},
    {"name": "Alternator", "parent": "Power Unit", "description": "240V alternator for heater power"},
    {"name": "Fuel System", "parent": "Power Unit", "description": "Fuel tank, lines, filters, pump"},
    {"name": "Electrical", "parent": "Power Unit", "description": "Battery, switches, wiring, hour meter"},

    {"name": "Chassis / Track", "parent": None, "description": "Track drive, frame, transport components"},
    {"name": "Track System", "parent": "Chassis / Track", "description": "Tracks, sprockets, idlers, rollers"},
    {"name": "Frame", "parent": "Chassis / Track", "description": "Main frame, sub-frame, supports"},

    {"name": "DataLogger", "parent": None, "description": "McElroy DataLogger joint recording system"},
    {"name": "DataLogger Accessories", "parent": "DataLogger", "description": "Cables, sensors, software, mounts"},

    {"name": "Consumables", "parent": None, "description": "Items consumed during normal operation"},
    {"name": "Filters & Fluids", "parent": "Consumables", "description": "Oil filters, fuel filters, hydraulic fluid, coolant"},
    {"name": "Heater Supplies", "parent": "Consumables", "description": "PTFE spray, cleaning cloths, temperature crayons"},
    {"name": "Fusion Supplies", "parent": "Consumables", "description": "Pipe supports, clamps, testing supplies"},

    {"name": "Safety Equipment", "parent": None, "description": "PPE and safety items for fusion operations"},

    {"name": "Accessories", "parent": None, "description": "Optional equipment and accessories"},
    {"name": "Extension Kits", "parent": "Accessories", "description": "Remote carriage operation kits"},
    {"name": "Pipe Lifts", "parent": "Accessories", "description": "Hydraulic pipe lift attachments"},
    {"name": "Tensile Testers", "parent": "Accessories", "description": "In-field joint testing equipment"},
]

# ============================================================
# MACHINES (InvenTree stock locations + tracked assets)
# ============================================================

MACHINE_MODELS = [
    # 618 Family — 6" to 18" IPS
    {
        "model": "TracStar 618",
        "model_i": "TracStar 618i",
        "family": "618",
        "pipe_range": '6" IPS to 18" IPS',
        "pipe_od_range": '6.625" to 18.000"',
        "power": "Diesel (Kubota D1105) or Gas (Honda GX390)",
        "heater_voltage": "240V",
        "mcelroy_pn": "at1830002",
        "variants": ["HF", "MF", "LF", "HYD CLMPNG HF", "HYD CLMPNG MF", "HYD CLMPNG LF"],
    },
    {
        "model": "Rolling 618",
        "model_i": "Rolling 618i",
        "family": "618",
        "pipe_range": '6" IPS to 18" IPS',
        "pipe_od_range": '6.625" to 18.000"',
        "power": "External hydraulic or Electric",
        "heater_voltage": "240V",
        "mcelroy_pn": "1855602",
    },
    {
        "model": "Pit Bull 618",
        "model_i": "Pit Bull 618i",
        "family": "618",
        "pipe_range": '6" IPS to 18" IPS',
        "pipe_od_range": '6.625" to 18.000"',
        "power": "Diesel or Gas",
        "heater_voltage": "240V",
    },
    # 900 Family — 8" to 24/36" IPS
    {
        "model": "TracStar 900",
        "model_i": "TracStar 900i",
        "family": "900",
        "pipe_range": '8" IPS to 24" IPS (to 36" with adapters)',
        "pipe_od_range": '8.625" to 24.000"',
        "power": "Diesel (Kubota V2403)",
        "heater_voltage": "240V",
        "mcelroy_pn": "at9057801",
        "variants": ["HF", "MF", "LF"],
    },
    # 1200 Family — 12" to 48" IPS
    {
        "model": "TracStar 1200",
        "model_i": "TracStar 1200i",
        "family": "1200",
        "pipe_range": '12" IPS to 48" IPS',
        "pipe_od_range": '12.750" to 48.000"',
        "power": "Diesel (Kubota V3307)",
        "heater_voltage": "240V",
        "mcelroy_pn": "at4800101",
    },
    {
        "model": "MegaMc 1648",
        "model_i": None,
        "family": "1200",
        "pipe_range": '16" IPS to 48" IPS',
        "pipe_od_range": '16.000" to 48.000"',
        "power": "Diesel",
        "heater_voltage": "240V",
    },
]

# ============================================================
# PARTS DATABASE
# Each part has: name, category, description, mcelroy_pn (if known),
# machines (which families it fits), is_serialized, is_consumable,
# reorder_point, reorder_qty
# ============================================================

PARTS = [
    # ---- JAW INSERTS (pipe-size-specific, serialized) ----
    # 618 inserts (6" through 18") — PNs from mcelroyparts.com (MIMECO)
    {"name": "618 Insert Set - 6\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "1207007",
     "description": "Cast jaw insert master set for 6\" IPS pipe (6.625\" OD). 4 inserts per set. $3,122",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Insert Set - 8\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "1207104",
     "description": "Cast jaw insert set for 8\" IPS pipe (8.625\" OD). 4 inserts per set. $2,058",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Insert Set - 10\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "1207204",
     "description": "Cast jaw insert set for 10\" IPS pipe (10.750\" OD). 4 inserts per set. $2,058",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Insert Set - 12\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2411810",
     "description": "Cast jaw insert master set w/pins for 12\" IPS pipe (12.750\" OD). $6,035",
     "machines": ["618"], "is_serialized": True, "reorder_point": 4, "reorder_qty": 4},
    {"name": "618 Insert Set - 14\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2412206",
     "description": "Cast jaw insert set for 14\" OD / 355mm pipe (14.000\" OD). $4,986",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Insert Set - 16\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2412110",
     "description": "Cast jaw insert set for 16\" IPS pipe (16.000\" OD). $4,986",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Insert Set - 18\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2411708",
     "description": "Cast jaw insert master set w/pins for 18\" IPS pipe (18.000\" OD). $9,800",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    # 618 DIPS inserts (ductile iron pipe sizes)
    {"name": "618 Insert Set - 6\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "1207020",
     "description": "Cast jaw insert set for 6\" DIPS pipe (6.900\" OD). $3,122",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 8\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "1207107",
     "description": "Cast jaw insert set for 8\" DIPS pipe (9.050\" OD). $2,058",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 10\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "1207221",
     "description": "Cast jaw insert set for 10\" DIPS pipe (11.100\" OD). $2,058",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 12\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "2411826",
     "description": "Cast jaw insert set for 12\" DIPS pipe (13.200\" OD). $4,986",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 14\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "2412215",
     "description": "Cast jaw insert set for 14\" DIPS pipe. $4,986",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 16\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "2412117",
     "description": "Cast jaw insert set for 16\" DIPS pipe. $4,986",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 18\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "2412023",
     "description": "Cast jaw insert set for 18\" DIPS pipe. $8,479",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insert Set - 20\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2412010",
     "description": "Cast jaw insert set for 20\" IPS pipe. $8,479",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Insert Set - 20\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "2411922",
     "description": "Cast jaw insert set for 20\" DIPS pipe. $8,479",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Insert Set - 24\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "2411604",
     "description": "Cast jaw insert set for 24\" IPS pipe. $8,479",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},

    # 900/1200 inserts — from TracStar 900 / MegaMc 1236 cast insert collection
    {"name": "900 Insert Set - 24\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "3606617",
     "description": "Cast jaw insert set for 24\" DIPS pipe. $18,647",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 26\" IPS", "category": "Jaw Inserts", "mcelroy_pn": "3606614",
     "description": "Cast jaw insert set for 26\" IPS pipe. $18,647",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 28\" OD", "category": "Jaw Inserts", "mcelroy_pn": "3603418",
     "description": "Cast jaw insert set for 28\" OD / 710mm pipe. $18,647",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 30\" OD", "category": "Jaw Inserts", "mcelroy_pn": "3603515",
     "description": "Cast jaw insert set for 30\" OD pipe. $18,647",
     "machines": ["900", "1200"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 32\" OD / 30\" DIPS", "category": "Jaw Inserts", "mcelroy_pn": "3603512",
     "description": "Cast jaw insert set for 32\" OD / 30\" DIPS pipe. $18,647",
     "machines": ["900", "1200"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 34\" OD", "category": "Jaw Inserts", "mcelroy_pn": "3603532",
     "description": "Cast jaw insert set for 34\" OD pipe. $18,647",
     "machines": ["900", "1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "900 Insert Set - 630mm Master w/pins", "category": "Jaw Inserts", "mcelroy_pn": "3606604",
     "description": "Cast jaw insert master set w/pins for 630mm / ~24\" pipe. $17,501",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Insert Set - 800mm", "category": "Jaw Inserts", "mcelroy_pn": "3603509",
     "description": "Cast jaw insert set for 800mm / ~32\" pipe. $18,647",
     "machines": ["900", "1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},

    # ---- FACER BLADES (PNs from mcelroyparts.com) ----
    {"name": "618 Facer Blade Set (4.63\" standard)", "category": "Facer Blades", "mcelroy_pn": "T1208603",
     "description": "Set of 6 standard facer blades, 4.63\" long. For PB/Rolling/TracStar 618. $693",
     "machines": ["618"], "is_consumable": True, "reorder_point": 6, "reorder_qty": 10},
    {"name": "618 Facer Blade Set (9.12\" standard)", "category": "Facer Blades", "mcelroy_pn": "T1812602",
     "description": "Set of 6 standard facer blades, 9.12\" long. For PB/Rolling/TracStar 618. $1,014",
     "machines": ["618"], "is_consumable": True, "reorder_point": 4, "reorder_qty": 8},
    {"name": "900 Facer Blade Set (18/24 optional)", "category": "Facer Blades", "mcelroy_pn": "3615710",
     "description": "Set of 6 optional facer blades for TracStar 630 / MegaMc 824 / 900. $1,267",
     "machines": ["900"], "is_consumable": True, "reorder_point": 4, "reorder_qty": 6},
    {"name": "900/1200 Facer Blade Set (24\" standard)", "category": "Facer Blades", "mcelroy_pn": "3615712",
     "description": "Set of 6 standard 24\" facer blades for TracStar 900/1200 class. $1,737",
     "machines": ["900", "1200"], "is_consumable": True, "reorder_point": 2, "reorder_qty": 4},

    # ---- FACER ASSEMBLIES (serialized) ----
    {"name": "618 Facer Assembly", "category": "Facer",
     "description": "Complete facer assembly for 618-class. Rotating planer-block, ball bearing, chain-driven by hydraulic motor.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Facer Assembly", "category": "Facer",
     "description": "Complete facer assembly for 900-class.",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "1200 Facer Assembly", "category": "Facer",
     "description": "Complete facer assembly for 1200/MegaMc.",
     "machines": ["1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},

    # ---- HEATER PLATES / ASSEMBLIES (serialized) ----
    {"name": "618 Heater Assembly", "category": "Heater",
     "description": "Complete heater assembly for 618-class. 240V, PTFE-coated plates, thermostat-controlled.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 2, "reorder_qty": 2},
    {"name": "900 Heater Assembly", "category": "Heater",
     "description": "Complete heater assembly for 900-class. 240V, PTFE-coated plates.",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "1200 Heater Assembly", "category": "Heater",
     "description": "Complete heater assembly for 1200/MegaMc. 240V, PTFE-coated plates.",
     "machines": ["1200"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Heater Plate (Replacement)", "category": "Heater Plates",
     "description": "Replacement PTFE-coated heater plate for 618 heater. Resurface or replace when coating is damaged.",
     "machines": ["618"], "is_consumable": True, "reorder_point": 2, "reorder_qty": 4},
    {"name": "900 Heater Plate (Replacement)", "category": "Heater Plates",
     "description": "Replacement PTFE-coated heater plate for 900 heater.",
     "machines": ["900"], "is_consumable": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "1200 Heater Plate (Replacement)", "category": "Heater Plates",
     "description": "Replacement PTFE-coated heater plate for 1200/MegaMc heater.",
     "machines": ["1200"], "is_consumable": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "618 Insulated Heater Stand", "category": "Heater Stand",
     "description": "Insulated stand/blanket for 618 heater storage. Protects operator and minimizes heat loss.",
     "machines": ["618"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "900 Insulated Heater Stand", "category": "Heater Stand",
     "description": "Insulated stand/blanket for 900 heater.",
     "machines": ["900"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "Heater Stripper Bar", "category": "Heater",
     "description": "Bar for removing heater from pipe ends after heat soak. Used on 618/900.",
     "machines": ["618", "900"], "reorder_point": 2, "reorder_qty": 2},

    # ---- HEATER ELECTRICAL ----
    {"name": "618 Heater Cord Assembly", "category": "Heater Electrical",
     "description": "240V power cord with NEMA L6-30 plug for 618 heater.",
     "machines": ["618"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Heater Thermostat", "category": "Heater Electrical",
     "description": "Thermostat for 618 heater temperature control (400°F ± 10°F typical for HDPE).",
     "machines": ["618"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "618 Heater Element", "category": "Heater Electrical",
     "description": "Replacement heating element for 618 heater assembly.",
     "machines": ["618"], "reorder_point": 1, "reorder_qty": 2},

    # ---- HYDRAULIC CYLINDERS (serialized, color-coded) ----
    {"name": "618 High Force Cylinder Set (Green)", "category": "Hydraulic Cylinders",
     "description": "HIGH FORCE hydraulic carriage cylinders (GREEN). For high interfacial pressures, heavy wall pipe, large drag factors. 2 per set.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Medium Force Cylinder Set (Orange)", "category": "Hydraulic Cylinders",
     "description": "MEDIUM FORCE carriage cylinders (ORANGE). ~50% piston area of HF. Faster travel, for medium density pipe. 2 per set.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Low Force Cylinder Set (Yellow)", "category": "Hydraulic Cylinders",
     "description": "LOW FORCE carriage cylinders (YELLOW). For low interfacial pressure pipe (22 psi). 2 per set.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "900 High Force Cylinder Set", "category": "Hydraulic Cylinders",
     "description": "High force carriage cylinders for 900-class.",
     "machines": ["900"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "1200 High Force Cylinder Set", "category": "Hydraulic Cylinders",
     "description": "High force carriage cylinders for 1200/MegaMc.",
     "machines": ["1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},

    # ---- HYDRAULIC SYSTEM ----
    {"name": "618 Hydraulic Manifold Block Assembly", "category": "Manifold Block",
     "description": "Complete manifold block with directional control valve, selector valve, 3 pressure reducing valves (facing 400psi, heating 400psi, fusion 1500psi), 1500psi gauge, DataLogger port.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "1500 PSI Pressure Gauge", "category": "Manifold Block",
     "description": "Replacement 1500 PSI gauge for manifold block.",
     "machines": ["618", "900"], "reorder_point": 2, "reorder_qty": 4},
    {"name": "Carriage Directional Control Valve", "category": "Manifold Block",
     "description": "3-position directional valve for carriage left/right/neutral.",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "Pressure Reducing Valve (Facing)", "category": "Manifold Block",
     "description": "Adjustable pressure reducing valve for facing operation (max 400 PSI).",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "Pressure Reducing Valve (Heating)", "category": "Manifold Block",
     "description": "Adjustable pressure reducing valve for heating operation (max 400 PSI).",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "Pressure Reducing Valve (Fusion)", "category": "Manifold Block",
     "description": "Adjustable pressure reducing valve for fusion operation (max 1500 PSI).",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 1},

    {"name": "10 Micron Hydraulic Filter Element", "category": "Hydraulic Filters",
     "description": "Return-side 10 micron filter element. Replace every 500 hours or when indicator shows.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 10, "reorder_qty": 20},
    {"name": "Hydraulic Extension Hose Set (12/18)", "category": "Hydraulic Hoses", "mcelroy_pn": "1219105",
     "description": "25ft extension hose set for 12/18-class remote carriage operation. $1,063",
     "machines": ["618"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "240V Extension Cord Assembly", "category": "Heater Electrical", "mcelroy_pn": "1219002",
     "description": "240V, 1-phase, 15A extension cord assembly for heater. $228",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 4},
    {"name": "AW-46 Hydraulic Fluid (5 gal)", "category": "Hydraulic Fluid",
     "description": "AW-46 anti-wear hydraulic fluid. 5 gallon bucket.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 3, "reorder_qty": 5},
    {"name": "Hydraulic Quick-Disconnect Coupler Set", "category": "Hydraulic Hoses",
     "description": "Quick-disconnect hydraulic coupler (male + female). For carriage-to-chassis connection.",
     "machines": ["618", "900", "1200"], "reorder_point": 4, "reorder_qty": 8},

    # ---- CARRIAGE HARDWARE ----
    {"name": "618 Guide Rod Set", "category": "Carriage Hardware",
     "description": "Chrome-plated guide rods for 618 carriage. 4 rods per set.",
     "machines": ["618"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "618 Guide Rod Bushing Set", "category": "Carriage Hardware",
     "description": "Bronze guide rod bushings for 618 carriage. Replace when worn (excessive play).",
     "machines": ["618"], "is_consumable": True, "reorder_point": 2, "reorder_qty": 4},
    {"name": "Jaw Clamp Pin Set", "category": "Carriage Hardware",
     "description": "Pins for securing jaw inserts in carriage. Various sizes.",
     "machines": ["618", "900", "1200"], "reorder_point": 4, "reorder_qty": 8},

    # ---- DATALOGGER (serialized) ----
    {"name": "McElroy DataLogger 6", "category": "DataLogger", "mcelroy_pn": "DL18001",
     "description": "DataLogger 6 system. Records fusion joint parameters (pressure, temperature, time). WiFi-enabled. Generates QR-coded joint reports.",
     "machines": ["618", "900", "1200"], "is_serialized": True, "reorder_point": 1, "reorder_qty": 1},
    {"name": "DataLogger Pressure Transducer", "category": "DataLogger Accessories",
     "description": "Pressure transducer for DataLogger connection to manifold port.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "DataLogger Cable Assembly", "category": "DataLogger Accessories",
     "description": "Connection cable from DataLogger to machine manifold.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "DataLogger Temperature Sensor (RTD)", "category": "DataLogger Accessories",
     "description": "RTD temperature sensor for heater plate monitoring.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 4},

    # ---- ENGINE / POWER UNIT ----
    {"name": "Diesel Fuel Filter (Kubota)", "category": "Filters & Fluids",
     "description": "OEM fuel filter for Kubota diesel engines (D1105, V2403, V3307).",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 10, "reorder_qty": 20},
    {"name": "Diesel Oil Filter (Kubota)", "category": "Filters & Fluids",
     "description": "OEM oil filter for Kubota diesel engines.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 10, "reorder_qty": 20},
    {"name": "Air Filter Element (618 Diesel)", "category": "Filters & Fluids",
     "description": "Air filter element for 618 Kubota D1105 diesel engine.",
     "machines": ["618"], "is_consumable": True, "reorder_point": 4, "reorder_qty": 8},
    {"name": "Air Filter Element (900 Diesel)", "category": "Filters & Fluids",
     "description": "Air filter element for 900 Kubota V2403 diesel engine.",
     "machines": ["900"], "is_consumable": True, "reorder_point": 3, "reorder_qty": 6},
    {"name": "Engine Oil 15W-40 (1 gal)", "category": "Filters & Fluids",
     "description": "15W-40 diesel engine oil. 1 gallon.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 6, "reorder_qty": 12},
    {"name": "Engine Coolant 50/50 (1 gal)", "category": "Filters & Fluids",
     "description": "50/50 premixed coolant for diesel engines.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 4, "reorder_qty": 8},
    {"name": "V-Belt (Alternator Drive)", "category": "Alternator",
     "description": "Drive belt for engine-to-alternator. Check tension every 100 hours.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 4, "reorder_qty": 8},
    {"name": "Battery (12V Group 24)", "category": "Electrical",
     "description": "12V starting battery for diesel-powered machines.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 4},
    {"name": "Key Switch Assembly", "category": "Electrical",
     "description": "Ignition/preheat key switch. Turn left for glow plugs, right to start.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 4},
    {"name": "Hour Meter", "category": "Electrical",
     "description": "Engine hour meter. Displays total operating hours.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "Glow Plug Set", "category": "Diesel Engine",
     "description": "Glow plugs for cold-start preheat. Set of 3 (D1105) or 4 (V2403/V3307).",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 2, "reorder_qty": 4},

    # ---- TRACK / CHASSIS ----
    {"name": "618 Track (Rubber)", "category": "Track System",
     "description": "Replacement rubber track for TracStar 618 chassis.",
     "machines": ["618"], "reorder_point": 0, "reorder_qty": 2},
    {"name": "900 Track (Rubber)", "category": "Track System",
     "description": "Replacement rubber track for TracStar 900 chassis.",
     "machines": ["900"], "reorder_point": 0, "reorder_qty": 2},
    {"name": "Track Idler Wheel", "category": "Track System",
     "description": "Idler wheel assembly with bearings for track tensioning.",
     "machines": ["618", "900", "1200"], "reorder_point": 2, "reorder_qty": 2},
    {"name": "Track Drive Sprocket", "category": "Track System",
     "description": "Drive sprocket at hydraulic motor end of track.",
     "machines": ["618", "900", "1200"], "reorder_point": 1, "reorder_qty": 2},

    # ---- CONSUMABLES ----
    {"name": "PTFE Release Agent Spray", "category": "Heater Supplies",
     "description": "PTFE spray for heater plate maintenance. Apply when coating shows wear.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 6, "reorder_qty": 12},
    {"name": "Heater Cleaning Cloth (cotton)", "category": "Heater Supplies",
     "description": "Non-synthetic cotton cloth for cleaning heater plates. NEVER use synthetic — will melt to plate.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 1, "reorder_qty": 2},
    {"name": "Temperature Crayon (400°F)", "category": "Heater Supplies",
     "description": "Temperature-indicating crayon for verifying heater surface temperature. Melts at 400°F.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 6, "reorder_qty": 12},
    {"name": "Pipe Support Rollers (adjustable)", "category": "Fusion Supplies",
     "description": "Adjustable pipe support rollers for holding pipe at machine height.",
     "machines": ["618", "900", "1200"], "reorder_point": 4, "reorder_qty": 4},

    # ---- ACCESSORIES ----
    {"name": "618 3-Jaw Extension Kit", "category": "Extension Kits",
     "description": "Allows removal of inner fixed jaw + 2 movable jaws for 3-jaw remote operation. Includes extension hoses.",
     "machines": ["618"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "900 Extension Kit", "category": "Extension Kits",
     "description": "Remote carriage operation kit for 900.",
     "machines": ["900"], "reorder_point": 0, "reorder_qty": 1},
    {"name": "618 Pipe Lift", "category": "Pipe Lifts",
     "description": "Hydraulic pipe lift attachment for TracStar 618.",
     "machines": ["618"], "reorder_point": 0, "reorder_qty": 1},
    {"name": "In-Field Tensile Tester", "category": "Tensile Testers", "mcelroy_pn": "AS03501",
     "description": "Portable tensile testing fixture for field verification of fusion joints. $7,137",
     "machines": ["618", "900", "1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "Guided Side Bend Tester", "category": "Tensile Testers", "mcelroy_pn": "S05501",
     "description": "Side bend test fixture assembly for evaluating fusion joint quality. $5,334",
     "machines": ["618", "900", "1200"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},

    # ---- ADDITIONAL ACCESSORIES (from mcelroyparts.com) ----
    {"name": "12\" Heater Butt Plate Kit", "category": "Heater Plates", "mcelroy_pn": "A1242108",
     "description": "Replacement heater butt plate kit for 12\" pipe. $894",
     "machines": ["618"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "18\" Heater Butt Plate Kit", "category": "Heater Plates", "mcelroy_pn": "A1852013",
     "description": "Replacement heater butt plate kit for 18\" pipe. $1,111",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "Heater Bag Assembly", "category": "Heater Stand", "mcelroy_pn": "1234202",
     "description": "Insulated heater bag assembly for transport/storage. $876",
     "machines": ["618", "900"], "reorder_point": 1, "reorder_qty": 2},
    {"name": "Digital Pyrometer Kit", "category": "Accessories", "mcelroy_pn": "A218804",
     "description": "Digital pyrometer kit (-100 to +600°F) for verifying heater temperature. $743",
     "machines": ["618", "900", "1200"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "In-Ditch Facer Stand", "category": "Facer", "mcelroy_pn": "T801101",
     "description": "Stand for facer when used in-ditch. $500",
     "machines": ["618"], "reorder_point": 1, "reorder_qty": 1},
    {"name": "618 Stub End Holder Assembly", "category": "Accessories", "mcelroy_pn": "1879101",
     "description": "Stub end holder assembly for 618 fusion machines. $7,642",
     "machines": ["618"], "is_serialized": True, "reorder_point": 0, "reorder_qty": 1},
    {"name": "Fabric Heat Shield (18\" 21x30)", "category": "Heater Supplies", "mcelroy_pn": "203009",
     "description": "21x30 fabric heat shield for wind/draft protection during heating. $381",
     "machines": ["618", "900"], "is_consumable": True, "reorder_point": 2, "reorder_qty": 4},

    # ---- SAFETY ----
    {"name": "Heater Gloves (heat resistant)", "category": "Safety Equipment",
     "description": "Heat-resistant gloves rated to 500°F for handling heater assembly.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 6, "reorder_qty": 12},
    {"name": "Safety Glasses (anti-fog)", "category": "Safety Equipment",
     "description": "ANSI Z87.1 safety glasses. Required during facing and fusion operations.",
     "machines": ["618", "900", "1200"], "is_consumable": True, "reorder_point": 12, "reorder_qty": 24},
]

# ============================================================
# STOCK LOCATIONS (where parts are stored)
# ============================================================

STOCK_LOCATIONS = [
    {"name": "Shop - Main", "description": "Main shop storage at Underground Solutions"},
    {"name": "Shop - Parts Room", "parent": "Shop - Main", "description": "Locked parts room"},
    {"name": "Shop - Consumables Shelf", "parent": "Shop - Main", "description": "Open shelf for consumables"},
    {"name": "Shop - Serialized Assets", "parent": "Shop - Main", "description": "Tracked/serialized equipment storage"},
    {"name": "Shop - Fluid Storage", "parent": "Shop - Main", "description": "Oil, coolant, hydraulic fluid"},
    {"name": "Field - Truck Stock", "description": "Common spares carried on service trucks"},
    {"name": "Field - Job Site", "description": "Parts currently deployed to job sites"},
    {"name": "In Service", "description": "Parts currently installed on machines in the field"},
    {"name": "Repair / Out for Service", "description": "Parts out for repair or refurbishment"},
]

# ============================================================
# FLEET TEMPLATE (for generating machine instances)
# ============================================================

FLEET_TEMPLATE = {
    "618": {
        "count_standard": 10,
        "count_i_series": 10,
        "prefix": "UGSI-618",
    },
    "900": {
        "count_standard": 6,
        "count_i_series": 6,
        "prefix": "UGSI-900",
    },
    "1200": {
        "count_standard": 2,
        "count_i_series": 2,
        "prefix": "UGSI-1200",
    },
}
