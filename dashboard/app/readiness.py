"""What a store still lacks before it runs like its siblings (2026-11-02).

The registry can hold a store whose repository is only half set up - Kidoomi arrived with six secrets, no variables and
eight workflows parked - and every card then fails in its own quiet way; nothing says "these names are the gap". This
module compares one store against the REST OF THE FLEET: a secret or variable name counts as expected when at least half
of the other stores carry it (a one-store oddity like EUR_PER_GBP never nags), and a variable's fleet value is offered
for adoption only when every sibling that carries the name holds exactly the same value - store-specific values (sheet
names, delivery template ids) differ by design and must be typed, not copied. Workflows are the store's own list with
their state: a parked (disabled) workflow is the loudest activation item. Pure functions; the route feeds them the
GitHub answers.

An eBay-only store (config/stores.json "amazon": false) parks the Amazon lane's workflows (Keepa sync and probes) ON PURPOSE: they are listed apart as
'off on purpose', never counted as parked, and the Keepa / Amazon secrets and variables the other stores carry are not offered to it."""
from .catalog import is_amazon_lane


def is_amazon_name(name):
    """A secret / variable that only the Amazon lane uses (KEEPA_API_KEY, KEEPA_*, AMAZON_*)."""
    up = str(name or "").upper()
    return "KEEPA" in up or up.startswith("AMAZON")


def majority(n_others):
    """How many of the other stores must carry a name before this store is told it lacks it: at least half, and always
    at least one (a two-store fleet still compares)."""
    return max(1, (n_others + 1) // 2)


def gaps(mine, others_by_store):
    """[{name, held_by}] of the names at least half the OTHER stores carry and this one lacks, alphabetically."""
    counts = {}
    for names in others_by_store.values():
        for n in names:
            counts[n] = counts.get(n, 0) + 1
    need = majority(len(others_by_store))
    return [{"name": n, "held_by": c} for n, c in sorted(counts.items()) if c >= need and n not in mine]


def fleet_value(name, others_vars_by_store):
    """The value offered for adoption: the siblings' value when every sibling that carries the name agrees on one
    exact string, else '' (the owner types it)."""
    values = {str(v[name]) for v in others_vars_by_store.values() if name in v}
    return values.pop() if len(values) == 1 else ""


def report(mine, others, expected_secrets, amazon=True):
    """The card's whole answer. mine = {"secrets": set, "variables": {name: value}, "workflows": [{path, name, state}]};
    others = {store_id: {"secrets": set, "variables": {name: value}}} for every sibling the token could read.
    amazon=False (an eBay-only store): the Amazon lane is off on purpose - see the module note."""
    if not amazon:
        expected_secrets = [n for n in expected_secrets if not is_amazon_name(n)]
    expected_missing = [n for n in expected_secrets if n not in mine["secrets"]]
    secret_gaps = [g for g in gaps(mine["secrets"], {k: v["secrets"] for k, v in others.items()})
                   if g["name"] not in expected_missing and (amazon or not is_amazon_name(g["name"]))]
    var_gaps = [g for g in gaps(set(mine["variables"]), {k: set(v["variables"]) for k, v in others.items()})
                if amazon or not is_amazon_name(g["name"])]
    for g in var_gaps:
        g["value"] = fleet_value(g["name"], {k: v["variables"] for k, v in others.items()})
    workflows = sorted(mine["workflows"], key=lambda w: (w.get("state") == "active", w.get("path", "")))
    parked = [w for w in workflows if w.get("state") != "active"]
    off_on_purpose = [] if amazon else [w for w in parked if is_amazon_lane(w.get("path"))]
    parked = [w for w in parked if w not in off_on_purpose]
    return {"compared_against": sorted(others), "secrets_missing": expected_missing, "secret_gaps": secret_gaps,
            "variable_gaps": var_gaps, "workflows": workflows, "parked": parked, "off_on_purpose": off_on_purpose,
            "amazon": amazon, "ready": not expected_missing and not parked}
