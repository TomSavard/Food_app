"""Collapse CIQUAL preparation-state variants into one row per food.

CIQUAL splits every food by cooking state and preservation form because the
nutrient values differ. For a cooking app that granularity is noise: `Brocoli,
cru` / `Brocoli, cuit` / `Brocoli, surgelé, cru` are one shopping item.

Identity is preserved: cultivars and real transformations stay separate rows
(`Tomate cerise`, `Tomate, concentré`), only state qualifiers collapse.

Keeper per group, in order: `aliment moyen` (CIQUAL's own average) > `cru` >
`cuit` > a curated user row. Groups matching none are skipped for manual review.
Curation (category, density, aliases) is absorbed from losers regardless of
which row wins on nutrition.

Dry-run by default; pass --apply to write.
"""
import argparse, collections, json, re, sys, unicodedata
from datetime import datetime, timezone
from sqlalchemy import text
from backend.db.session import get_engine

COOK = r"(crue?s?|cuite?s?|bouillie?s?|rotie?s?|grillee?s?|poelee?s?|sautee?s?|frite?s?|vapeur|au four|a l eau|sans matiere grasse|avec matiere grasse|aliment moyen|sans precision|croquant|fondant)"
PRES = r"(surgelee?s?|appertisee?s?|conserve|egouttee?s?|non egouttee?s?|au jus|deshydratee?s?|reconstituee?s?|sous vide|pasteurisee?s?|uht|sterilisee?s?)"
DISH = r"(preemballee?s?|fait maison|sandwich|soupe|ravioli|pizza|tarte|quiche|farcie?s?|boulette|gratin|bolognaise|escabeche|a la provencale|a la catalane)"
STATE = f"(?:{COOK}|{PRES})"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9%/ ]", " ", s).split())


def segments(name: str):
    """Split a CIQUAL name into its comma/paren-delimited segments."""
    return [p.strip() for p in re.split(r"[,()]", name) if p.strip()]


def is_state(seg: str) -> bool:
    """True if a name segment carries only preparation info, no food identity."""
    n = norm(seg)
    if not n:
        return False
    n = re.sub(r"\b(aliment moyen|sans precision|non precise)\b", " ", n)
    n = re.sub(rf"\b{STATE}\b", " ", n)
    n = re.sub(r"\b(ou|a|l|de|du|des|et|en|sans|avec|le|la|les|au|aux|type)\b", " ", n)
    return not re.sub(r"[^a-z0-9%]", "", n)


def base_key(name: str) -> str:
    """Group key: the food, with all state qualifiers removed."""
    keep = [norm(s) for s in segments(name) if not is_state(s)]
    keep = [re.sub(rf"\b{STATE}\b", "", re.sub(r"\b(aliment moyen|sans precision)\b", "", k)).strip() for k in keep]
    keep = [k for k in keep if k]
    return " ".join(keep) or norm(segments(name)[0])


def display_name(name: str) -> str:
    """Same removal as base_key, but preserving original accents and casing."""
    keep = []
    for seg in segments(name):
        if is_state(seg):
            continue
        # a state word glued to the end of a segment: "gîte à la noix cru"
        words = seg.split()
        while len(words) > 1 and is_state(" ".join(words[-1:])) :
            words.pop()
        while len(words) > 2 and is_state(" ".join(words[-2:])):
            words.pop(); words.pop()
        if words:
            keep.append(" ".join(words))
    return ", ".join(keep).strip(" ,-") or name


def keeper_rank(row):
    n = norm(row["alim_nom_fr"])
    if "aliment moyen" in n or "sans precision" in n:
        return 0
    if re.search(r"\bcrue?s?\b", n):
        return 1
    if re.search(r"\bcuite?s?\b", n):
        return 2
    if row["source"] != "ciqual":
        return 3
    return 99


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    engine = get_engine()
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(
            "SELECT id, alim_nom_fr, category, source, modified, density_g_per_ml FROM ingredient_database"))]
        aliases = [dict(r._mapping) for r in conn.execute(text(
            "SELECT ingredient_db_id, alias_text FROM ingredient_aliases"))]

    all_names = {r["alim_nom_fr"] for r in rows}
    alias_by_row = collections.defaultdict(set)
    for a in aliases:
        alias_by_row[a["ingredient_db_id"]].add(a["alias_text"])

    groups = collections.defaultdict(list)
    for r in rows:
        if re.search(DISH, norm(r["alim_nom_fr"])):
            continue  # prepared dishes are not state-variants of each other
        groups[base_key(r["alim_nom_fr"])].append(r)

    plan, skipped, taken = [], [], set()
    for key, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        members.sort(key=lambda r: (keeper_rank(r), r["alim_nom_fr"]))
        if keeper_rank(members[0]) == 99:
            skipped.append((key, members))
            continue
        keeper, losers = members[0], members[1:]

        new_name = display_name(keeper["alim_nom_fr"])
        group_names = {m["alim_nom_fr"] for m in members}
        if new_name in (all_names - group_names) | taken:
            new_name = keeper["alim_nom_fr"]  # UNIQUE collision: keep the full name
        taken.add(new_name)

        # absorb curation the keeper is missing
        cat = keeper["category"] or next((l["category"] for l in losers if l["category"]), None)
        dens = keeper["density_g_per_ml"] or next((l["density_g_per_ml"] for l in losers if l["density_g_per_ml"]), None)
        new_aliases = set()
        for m in members:
            new_aliases |= alias_by_row[m["id"]]
            new_aliases.add(m["alim_nom_fr"])   # old names stay searchable
        new_aliases -= {new_name} | alias_by_row[keeper["id"]]

        plan.append(dict(keeper=keeper, losers=losers, new_name=new_name,
                         category=cat, density=dens, aliases=sorted(new_aliases)))

    n_del = sum(len(p["losers"]) for p in plan)
    for p in plan:
        rename = "" if p["new_name"] == p["keeper"]["alim_nom_fr"] else f"  -> rename to {p['new_name']!r}"
        print(f"\nKEEP {p['keeper']['alim_nom_fr']!r}{rename}")
        for l in p["losers"]:
            print(f"  del {l['alim_nom_fr']!r}")
        if p["aliases"]:
            print(f"  +aliases: {', '.join(p['aliases'])}")

    print(f"\n{'='*60}\ngroups merged      : {len(plan)}")
    print(f"rows deleted       : {n_del}   ({len(rows)} -> {len(rows)-n_del})")
    print(f"groups skipped     : {len(skipped)}  (no keeper rule matched)")
    for key, members in skipped:
        print(f"   ? {' | '.join(m['alim_nom_fr'] for m in members)}")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
        return

    with engine.begin() as conn:
        for p in plan:
            kid = p["keeper"]["id"]
            lids = [l["id"] for l in p["losers"]]
            # 1. re-point recipe + shopping references BEFORE deleting (FK is SET NULL)
            conn.execute(text("UPDATE ingredients SET ingredient_db_id=:k WHERE ingredient_db_id = ANY(:l)"), {"k": kid, "l": lids})
            conn.execute(text("UPDATE shopping_list SET ingredient_db_id=:k WHERE ingredient_db_id = ANY(:l)"), {"k": kid, "l": lids})
            # 2. rescue aliases before the CASCADE takes them
            conn.execute(text("DELETE FROM ingredient_aliases WHERE ingredient_db_id = ANY(:l)"), {"l": lids})
            for a in p["aliases"]:
                conn.execute(text(
                    "INSERT INTO ingredient_aliases (alias_id, ingredient_db_id, alias_text, created_by, created_at)"
                    " VALUES (gen_random_uuid(), :k, :a, 'llm', now())"), {"k": kid, "a": a})
            # 3. delete losers, then update the keeper (NULL embedding -> lazily recomputed)
            conn.execute(text("DELETE FROM ingredient_database WHERE id = ANY(:l)"), {"l": lids})
            conn.execute(text(
                "UPDATE ingredient_database SET alim_nom_fr=:n, category=:c, density_g_per_ml=:d,"
                " embedding=NULL, updated_at=now() WHERE id=:k"),
                {"n": p["new_name"], "c": p["category"], "d": p["density"], "k": kid})
    print(f"\nAPPLIED: {n_del} rows deleted, {len(plan)} keepers updated.")


if __name__ == "__main__":
    main()
