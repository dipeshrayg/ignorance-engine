from core.schema import Paper

# Synthetic corpus for prototyping — NOT real data. Deliberately shaped so
# materials_science and pharmacology are both well-studied (11 and 9 papers)
# but never co-occur: the "unbuilt bridge" the bridges detector should surface.
# Replace with the real ingestion pipeline's output once it exists (same
# Paper(id, title, year, fields) shape).

SAMPLE_PAPERS = [
    # materials_science solo (6)
    Paper("m1", "Perovskite thin films for solar absorption", 2018, frozenset({"materials_science"})),
    Paper("m2", "Grain boundary engineering in structural alloys", 2019, frozenset({"materials_science"})),
    Paper("m3", "Self-healing polymer coatings", 2020, frozenset({"materials_science"})),
    Paper("m4", "MOF synthesis for gas storage", 2021, frozenset({"materials_science"})),
    Paper("m5", "2D material heterostructures", 2021, frozenset({"materials_science"})),
    Paper("m6", "High-entropy alloy phase stability", 2022, frozenset({"materials_science"})),

    # pharmacology solo (6)
    Paper("d1", "Pharmacokinetics of extended-release opioids", 2017, frozenset({"pharmacology"})),
    Paper("d2", "Drug-drug interaction screening at scale", 2018, frozenset({"pharmacology"})),
    Paper("d3", "Receptor binding affinity prediction", 2019, frozenset({"pharmacology"})),
    Paper("d4", "Dose-response modeling in oncology trials", 2020, frozenset({"pharmacology"})),
    Paper("d5", "Blood-brain barrier permeability of small molecules", 2021, frozenset({"pharmacology"})),
    Paper("d6", "Off-target effects of kinase inhibitors", 2022, frozenset({"pharmacology"})),

    # materials_science x robotics — an existing bridge (3)
    Paper("mr1", "Soft robotic actuators from shape-memory alloys", 2019, frozenset({"materials_science", "robotics"})),
    Paper("mr2", "Self-healing polymers for robot skin", 2021, frozenset({"materials_science", "robotics"})),
    Paper("mr3", "3D-printed lattice structures for gripper design", 2022, frozenset({"materials_science", "robotics"})),

    # robotics solo (3)
    Paper("r1", "SLAM for warehouse navigation", 2020, frozenset({"robotics"})),
    Paper("r2", "Reinforcement learning for bipedal gait", 2021, frozenset({"robotics"})),
    Paper("r3", "Swarm coordination under communication delay", 2022, frozenset({"robotics"})),

    # climate_science solo (4)
    Paper("c1", "Ocean heat uptake in coupled climate models", 2018, frozenset({"climate_science"})),
    Paper("c2", "Aerosol forcing uncertainty", 2019, frozenset({"climate_science"})),
    Paper("c3", "Permafrost carbon feedback", 2020, frozenset({"climate_science"})),
    Paper("c4", "Regional precipitation extremes under warming", 2022, frozenset({"climate_science"})),

    # climate_science x materials_science — a thin existing bridge (2)
    Paper("cm1", "Carbon capture sorbent materials", 2020, frozenset({"climate_science", "materials_science"})),
    Paper("cm2", "Reflective coatings for urban heat mitigation", 2022, frozenset({"climate_science", "materials_science"})),

    # immunology x pharmacology — an existing bridge (3)
    Paper("ip1", "Adjuvant design for vaccine immunogenicity", 2019, frozenset({"immunology", "pharmacology"})),
    Paper("ip2", "Checkpoint inhibitor pharmacodynamics", 2021, frozenset({"immunology", "pharmacology"})),
    Paper("ip3", "Cytokine release syndrome risk modeling", 2022, frozenset({"immunology", "pharmacology"})),

    # linguistics solo (3)
    Paper("l1", "Syntactic parsing of low-resource languages", 2020, frozenset({"linguistics"})),
    Paper("l2", "Cross-linguistic phoneme inventories", 2021, frozenset({"linguistics"})),
    Paper("l3", "Diachronic semantic drift", 2022, frozenset({"linguistics"})),

    # immunology solo (2)
    Paper("i1", "T-cell exhaustion markers", 2020, frozenset({"immunology"})),
    Paper("i2", "Mucosal immunity in the gut", 2021, frozenset({"immunology"})),
]
