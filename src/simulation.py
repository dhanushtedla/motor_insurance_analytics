"""Live fleet simulation ("real-time scenario").

Idea: take real ACTIVE policies from your data, put each insured vehicle on the road
between Indian cities, and let accidents happen with the SAME probabilities that your
historical claims show (claims per policy by policy type, severity mix, claim types,
claim amounts). Every accident becomes a live "first notice of loss" (FNOL) claim event.

This is a simulation for training / demo. It is NOT live telematics data.
One tick = one simulated day.
"""
import numpy as np
import pandas as pd

CITY_COORDS = {
    "Ahmedabad": (23.0225, 72.5714), "Bengaluru": (12.9716, 77.5946), "Bhopal": (23.2599, 77.4126),
    "Bhubaneswar": (20.2961, 85.8245), "Chandigarh": (30.7333, 76.7794), "Chennai": (13.0827, 80.2707),
    "Coimbatore": (11.0168, 76.9558), "Delhi": (28.6139, 77.2090), "Gurugram": (28.4595, 77.0266),
    "Hyderabad": (17.3850, 78.4867), "Indore": (22.7196, 75.8577), "Jaipur": (26.9124, 75.7873),
    "Karimnagar": (18.4386, 79.1288), "Kochi": (9.9312, 76.2673), "Kolkata": (22.5726, 88.3639),
    "Kota": (25.2138, 75.8648), "Lucknow": (26.8467, 80.9462), "Madurai": (9.9252, 78.1198),
    "Mangaluru": (12.9141, 74.8560), "Mumbai": (19.0760, 72.8777), "Mysuru": (12.2958, 76.6394),
    "Nagpur": (21.1458, 79.0882), "Nashik": (19.9975, 73.7898), "Nizamabad": (18.6725, 78.0941),
    "Noida": (28.5355, 77.3910), "Patna": (25.5941, 85.1376), "Pune": (18.5204, 73.8567),
    "Surat": (21.1702, 72.8311), "Thiruvananthapuram": (8.5241, 76.9366), "Tirupati": (13.6288, 79.4192),
    "Vadodara": (22.3072, 73.1812), "Vijayawada": (16.5062, 80.6480), "Visakhapatnam": (17.6868, 83.2185),
    "Warangal": (17.9689, 79.5941),
}

ACCIDENT_PAUSE_TICKS = 4          # an accident vehicle stands still for a few ticks
REVIEW_RATIO = 10                 # claim > 10x premium is flagged for review (same rule as the insights)


def _nearby_cities(city, k=5):
    """The k closest cities to `city` (used to pick a believable next destination)."""
    lat, lon = CITY_COORDS[city]
    others = [c for c in CITY_COORDS if c != city]
    others.sort(key=lambda c: (CITY_COORDS[c][0] - lat) ** 2 + (CITY_COORDS[c][1] - lon) ** 2)
    return others[:k]


def learn_risk_profile(policies, claims):
    """Learn accident probabilities and claim behaviour from the historical (filtered) data.

    Returns a dictionary used by step_fleet(). Works on the policy master and claims master.
    """
    if len(policies) == 0 or len(claims) == 0:
        return None
    freq = (policies.groupby("policy_type")["claim_count"].sum() / policies.groupby("policy_type").size()).to_dict()
    overall = policies["claim_count"].sum() / len(policies)
    sev_share = claims["damage_severity"].value_counts(normalize=True)
    type_share = claims["claim_type"].value_counts(normalize=True)
    amounts = {sev: grp["claim_amount"].to_numpy() for sev, grp in claims.groupby("damage_severity")}
    approval = {sev: float((grp["claim_status"].isin(["Approved", "Settled"])).mean())
                for sev, grp in claims.groupby("damage_severity")}
    paid_ratio = float(claims.loc[claims["paid_amount"] > 0, "paid_amount"].sum()
                       / max(claims.loc[claims["paid_amount"] > 0, "claim_amount"].sum(), 1)) if "paid_amount" in claims else 0.87
    return {"frequency": freq, "overall_frequency": float(overall), "severity_share": sev_share,
            "type_share": type_share, "amounts": amounts, "approval": approval, "paid_ratio": paid_ratio}


def build_fleet(policies, size, rng):
    """Pick `size` real ACTIVE policies and place each vehicle in its customer's home city."""
    active = policies[(policies["policy_status"] == "Active") & policies["city"].isin(CITY_COORDS.keys())]
    if active.empty:
        active = policies[policies["city"].isin(CITY_COORDS.keys())]
    if active.empty:
        return pd.DataFrame()
    chosen = active.sample(n=min(size, len(active)), random_state=int(rng.integers(0, 1_000_000))).reset_index(drop=True)

    rows = []
    for _, p in chosen.iterrows():
        home = p["city"]
        dest = str(rng.choice(_nearby_cities(home)))
        rows.append({
            "vehicle_id": p["vehicle_id"], "policy_id": p["policy_id"], "make": p.get("vehicle_make", ""),
            "model": p.get("vehicle_model", ""), "policy_type": p["policy_type"],
            "premium": float(p["premium_amount"]), "home_city": home, "city": home,
            "start_lat": CITY_COORDS[home][0], "start_lon": CITY_COORDS[home][1],
            "dest": dest, "dest_lat": CITY_COORDS[dest][0], "dest_lon": CITY_COORDS[dest][1],
            "progress": float(rng.random()), "speed": float(rng.uniform(0.04, 0.12)),
            "status": "Moving", "pause": 0,
        })
    fleet = pd.DataFrame(rows)
    return update_positions(fleet)


def update_positions(fleet):
    """Compute lat / lon of every vehicle from start, destination and progress."""
    fleet = fleet.copy()
    fleet["lat"] = fleet["start_lat"] + (fleet["dest_lat"] - fleet["start_lat"]) * fleet["progress"]
    fleet["lon"] = fleet["start_lon"] + (fleet["dest_lon"] - fleet["start_lon"]) * fleet["progress"]
    return fleet


def _move_vehicle(row, rng):
    """Advance one vehicle: drive, arrive, pick a new destination, or wait after an accident."""
    if row["pause"] > 0:                                    # standing still after an accident
        row["pause"] -= 1
        row["status"] = "Accident" if row["pause"] > 0 else "Moving"
        return row
    row["progress"] += row["speed"]
    if row["progress"] >= 1.0:                              # arrived -> choose the next trip
        row["city"] = row["dest"]
        row["start_lat"], row["start_lon"] = row["dest_lat"], row["dest_lon"]
        new_dest = str(rng.choice(_nearby_cities(row["city"])))
        row["dest"] = new_dest
        row["dest_lat"], row["dest_lon"] = CITY_COORDS[new_dest]
        row["progress"] = 0.0
    return row


def _make_event(vehicle, profile, rng, tick, sim_date):
    """Create one claim event for a vehicle that just had an accident."""
    sev = str(rng.choice(profile["severity_share"].index, p=profile["severity_share"].values))
    ctype = str(rng.choice(profile["type_share"].index, p=profile["type_share"].values))
    amount = float(rng.choice(profile["amounts"][sev]))
    approval = profile["approval"].get(sev, 0.7)
    expected_payout = amount * approval * profile["paid_ratio"]
    ratio = amount / vehicle["premium"] if vehicle["premium"] else 0
    return {
        "tick": tick, "date": sim_date.strftime("%d %b %Y"), "vehicle_id": vehicle["vehicle_id"],
        "make": vehicle["make"], "policy_type": vehicle["policy_type"], "near_city": vehicle["city"],
        "claim_type": ctype, "severity": sev, "claim_amount": round(amount), "approval_chance_%": round(100 * approval),
        "expected_payout": round(expected_payout),
        "action": "REVIEW (claim > 10x premium)" if ratio > REVIEW_RATIO else "Fast-track",
    }


def step_fleet(fleet, profile, rng, tick, start_date, rate_multiplier=1.0):
    """Advance the simulation by one tick (one day). Returns (new_fleet, list_of_new_events).

    accident probability per vehicle per tick = (claims per policy of its policy type / 365) x multiplier
    """
    if fleet.empty or profile is None:
        return fleet, []
    sim_date = start_date + pd.Timedelta(days=tick)
    events = []
    rows = []
    for _, row in fleet.iterrows():
        row = _move_vehicle(row.copy(), rng)
        if row["pause"] == 0 and row["status"] != "Accident":
            p = profile["frequency"].get(row["policy_type"], profile["overall_frequency"]) / 365 * rate_multiplier
            if rng.random() < min(p, 1.0):
                row["status"], row["pause"] = "Accident", ACCIDENT_PAUSE_TICKS
                events.append(_make_event(row, profile, rng, tick, sim_date))
        rows.append(row)
    return update_positions(pd.DataFrame(rows).reset_index(drop=True)), events
