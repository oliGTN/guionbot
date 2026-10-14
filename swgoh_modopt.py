"""
swgoh_modopt.py
===============
Optimiseur de mods "statq" : à partir du roster d'un joueur (mods équipés + non équipés),
de l'ordre de priorité des héros et des cibles K1 (keystats:v1), propose le remod complet
qui maximise les points statq héros après héros.

POURQUOI C'EST RAPIDE (pas de O(n^6))
-------------------------------------
Le site modoptimizer, en mode "target stats", teste des combinaisons de mods (6 slots x
des centaines de mods = explosion combinatoire). Ici chaque héros est un petit programme
linéaire en nombres entiers (MILP, solveur HiGHS via scipy) :
    - x[m] = 1 si le mod m est choisi ; exactement 1 mod par slot (6 contraintes) ;
    - groupes de sets (2 ou 4 mods) = variables entières, bonus de set exact ;
    - pour chaque stat clé, 4 variables "palier atteint" (>= 90 / 95 / 98 / 102 % de la cible K1) :
      maximiser leur somme = maximiser EXACTEMENT les points statq (0 à 4 par stat) ;
    - objectifs secondaires (ne coûtent jamais un point) : approcher les stats "également
      notables", respecter les sets habituels du héros, ne pas gaspiller les meilleurs mods
      (ils restent pour les héros suivants), et limiter le nombre de mods à déplacer.
Le solveur raisonne sur toutes les combinaisons sans les énumérer. Coût : ~1 s par héros.
Les héros sont traités dans l'ordre de priorité (les mods pris ne sont plus disponibles
pour les suivants). Les résultats sont ensuite recalculés EXACTEMENT avec le calcul de stats
du jeu (le modèle linéaire n'est qu'une aide à la décision).

ENTRÉES
-------
  --player-file initialdata.json   roster + mods (équipés ET non équipés : "unequippedMod")
  --allycode 123456789             via Comlink : mods ÉQUIPÉS seulement (Comlink n'expose pas
                                   les mods non équipés)
  --order ordre.txt                un héros par ligne (id du jeu, nom, abréviation), # = commentaire
                                   sans --order : ordre PROVISOIRE = Légendes galactiques puis
                                   puissance (à remplacer par ton vrai ordre)
  --keystats-file / KV             cibles K1 (par défaut KV keystats:v1)

SORTIES (dossier --out, défaut modopt_out/)
  plan.json                        pour chaque héros : mods, points avant/après, déplacements
  assignments.csv                  héros ; slot ; id du mod ; d'où il vient (pour le bot)
  progress_out.json                fichier « Restore my progress » (avec --progress-file) : ordre + mods par héros
  modoptimizer_template.json       modèle de personnages au format du site (Load > Character Templates)
  resume.txt                       résumé lisible

OPTIONS UTILES
  --min-relic 3        héros sous R3 ignorés (leurs mods restent verrouillés)
  --lock-unselected    (défaut) les mods des héros hors ordre ne sont pas touchés ; --free-unselected pour les libérer
  --primary-lock 75    impose le primaire dominant d'un slot s'il est utilisé par >= 75 % du top K1 (0 = libre)
  --time-limit 8       secondes max par héros
  --max-heroes N       s'arrêter après N héros (tests)
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict

## START modif oliGTN
from typing import Optional
## END modif oliGTN

import numpy as np
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import swgoh_cron as sc
import swgoh_keystats as ks
import swgoh_statq as sq

BAND_THRESHOLDS = [0.90, 0.95, 0.98, 1.02]      # paliers statq -> 1, 2, 3, 4 points
BIG = 100_000.0                                  # un point statq vaut plus que tout l'objectif secondaire
SLOTS = [1, 2, 3, 4, 5, 6]
COMBO_MIN_PCT = 25.0    # une combinaison de sets est acceptée si >= 25 % du top K1 la joue
VIRTUAL_PENALTY = 800.0  # coût d'un mod fictif (calcul « mods à farmer ») : utilisé seulement s'il apporte vraiment
SET_REWARD = 5000.0     # récompense par groupe de set du template (une bande de statq vaut 100000) — voir --set-reward
NAME_TO_SID = {v: k for k, v in sc.MODRAW_NAMES.items()}
STAT_DISPLAY = {1: "Health", 5: "Speed", 28: "Protection", 41: "Offense", 42: "Defense", 48: "Offense %",
                49: "Defense %", 53: "Critical Chance %", 16: "Critical Damage %", 17: "Potency %",
                18: "Tenacity %", 55: "Health %", 56: "Protection %", 57: "Speed %",
                52: "Accuracy %", 54: "Critical Avoidance %"}
SET_KEY = {1: "health", 2: "offense", 3: "defense", 4: "speed", 5: "critchance", 6: "critdamage",
           7: "potency", 8: "tenacity"}
SET_BY_NAME = {v: k for k, v in sc.SET_NAMES.items()}
SLOT_NAME = {1: "square", 2: "arrow", 3: "diamond", 4: "triangle", 5: "circle", 6: "cross"}
# stat clé keystats -> clé de poids du modèle Grandivory
GRANDIVORY_WEIGHT = {"speed": "speed", "health": "health", "protection": "protection", "armor": "armor",
                     "resistance": "resistance", "crit_damage": "critDmg", "potency": "potency",
                     "tenacity": "tenacity", "crit_chance": "critChance"}


# ─────────────────────────────────────────────────────────────────────────────
# Mods
# ─────────────────────────────────────────────────────────────────────────────

def parse_mod(m: dict, owner: str = ""):
    """Mod du jeu -> dict compact avec ses apports (flat / pct par stat)."""
    try:
        d = int(m.get("definitionId") or 0)
    except ValueError:
        return None
    c = sc._collect_mods([m])
    ps = ((m.get("primaryStat") or {}).get("stat") or {}).get("unitStatId")
    quality = 0.0
    for sec in m.get("secondaryStat") or []:
        for r in sec.get("roll") or []:
            try:
                quality += float(r) * (2.0 if (sec.get("stat") or {}).get("unitStatId") == 5 else 1.0)
            except (TypeError, ValueError):
                pass
    return {"id": m.get("id"), "set": d // 100, "pips": (d // 10) % 10, "slot": d % 10,
            "level": m.get("level") or 0, "owner": owner, "raw": m, "primary": ps,
            "flat": dict(c["flat"]), "pct": dict(c["pct"]), "quality": quality}


def load_mods(player: dict) -> list:
    mods = []
    for u in player.get("rosterUnit") or []:
        base = (u.get("definitionId") or "").split(":")[0]
        for m in u.get("equippedStatMod") or []:
            pm = parse_mod(m, base)
            if pm:
                mods.append(pm)
    for m in player.get("unequippedMod") or []:
        pm = parse_mod(m, "")
        if pm:
            mods.append(pm)
    return mods


# ─────────────────────────────────────────────────────────────────────────────
# Formes linéaires des stats (apport des mods) — mêmes formules que sc._apply_mods
# ─────────────────────────────────────────────────────────────────────────────

class StatForm:
    """Apport d'un mod / d'un groupe de set à UNE stat clé (en unité de la stat)."""

    def __init__(self, mod_key: str, base: dict):
        self.key = mod_key
        st = base["stats"]
        self.base = st
        lvl = base["level"]
        K = lvl * 7.5 * 1e8
        self.kind = "linear"
        if mod_key == "health":
            self.kind = "health"
            self.B = st[1]
        elif mod_key == "armor":
            A0 = base["armor_flat"]
            self.slope = 100.0 * K / (A0 + K) ** 2
            self.A0 = A0
        elif mod_key == "resistance":
            R0 = base["resist_flat"]
            self.slope = 100.0 * K / (R0 + K) ** 2
            self.R0 = R0

    def mod(self, flat: dict, pct: dict) -> float:
        k, st = self.key, self.base
        g = lambda d, i: d.get(i, 0.0)
        if k == "protection":
            return st[28] * g(pct, 56) / 100 + g(flat, 28)
        if k == "speed":
            return st[5] * g(pct, 57) / 100 + g(flat, 5)
        if k == "physical_damage":
            return st[6] * g(pct, 48) / 100 + g(flat, 41)
        if k == "special_damage":
            return st[7] * g(pct, 48) / 100 + g(flat, 41)
        if k == "crit_damage":
            return g(pct, 16)
        if k == "potency":
            return g(pct, 17)
        if k == "tenacity":
            return g(pct, 18)
        if k == "crit_chance_pct":
            return g(pct, 53)
        if k == "armor":
            return self.slope * (g(flat, 42) * 1e8 + self.A0 * g(pct, 49) / 100)
        if k == "resistance":
            return self.slope * (self.R0 * g(pct, 49) / 100)
        return 0.0        # health traité à part

    def bonus(self, set_id: int) -> float:
        """Apport d'UN groupe complet de ce set (bonus niveau 15) à la stat."""
        b = sc.MOD_SET_BONUSES[set_id]
        v = b["lvl15"] / 1e6
        return self.mod({}, {b["stat"]: v})


# ─────────────────────────────────────────────────────────────────────────────
# Modèle MILP d'un héros
# ─────────────────────────────────────────────────────────────────────────────

class Problem:
    """Petit constructeur de MILP (variables, contraintes, objectif à maximiser)."""

    def __init__(self):
        self.lb, self.ub, self.integ, self.obj = [], [], [], []
        self.rows = []     # (dict var->coef, lo, hi)

    def var(self, lb=0.0, ub=1.0, integer=True, obj=0.0) -> int:
        self.lb.append(lb); self.ub.append(ub); self.integ.append(1 if integer else 0); self.obj.append(obj)
        return len(self.lb) - 1

    def row(self, coefs: dict, lo=-np.inf, hi=np.inf):
        self.rows.append((coefs, lo, hi))

    def solve(self, time_limit: float, gap: float = 1e-3):
        n = len(self.lb)
        A = lil_matrix((len(self.rows), n))
        lo, hi = np.empty(len(self.rows)), np.empty(len(self.rows))
        for i, (co, l, h) in enumerate(self.rows):
            for j, v in co.items():
                A[i, j] = v
            lo[i], hi[i] = l, h
        res = milp(c=-np.array(self.obj), integrality=np.array(self.integ),
                   bounds=Bounds(np.array(self.lb), np.array(self.ub)),
                   constraints=LinearConstraint(A.tocsr(), lo, hi),
                   options={"time_limit": time_limit, "mip_rel_gap": gap, "disp": False})
        return res


def accepted_combos(kh: dict) -> list:
    """Combinaisons de sets acceptables : toutes celles jouées par >= COMBO_MIN_PCT % du top K1 (au moins la 1re).
    Retourne [{'name', 'pct', 'groups': {set_id: nb de groupes}}]."""
    st = kh.get("sets") or {}
    raw = [c for c in (st.get("combos") or []) if (c.get("pct") or 0) >= COMBO_MIN_PCT and c.get("sets")]
    top = st.get("top_combo") or {}
    if not raw and top.get("sets"):
        raw = [top]
    out = []
    for c in raw[:4]:
        gr = {}
        for sname, cnt in (c.get("sets") or {}).items():
            sid = SET_BY_NAME.get(sname)
            if sid:
                gr[sid] = cnt // sc.MOD_SET_BONUSES[sid]["count"]
        if gr:
            out.append({"name": c.get("combo") or "+".join(c["sets"]), "pct": c.get("pct"), "groups": gr})
    return out


def solve_hero(unit: dict, base: dict, kh: dict, mods_avail: list, current_ids: set,
               gd_unit_name: str, primary_lock: float, time_limit: float, keep_bonus: float = 150.0,
               strict: bool = False):
    """
    Choisit 6 mods (un par slot) parmi mods_avail pour ce héros.
    kh = entrée keystats du héros. Retourne (liste de mods choisis, info) ou (None, raison).
    """
    key_rows = kh["key_stats"]
    also_rows = kh.get("also") or []
    forms, targets, key_set = {}, {}, set()
    for r in key_rows + also_rows:
        mk = r.get("mod_key") or sq.MOD_KEY_DEFAULT.get(r["stat"], "physical_damage")
        r["mod_key"] = mk
        if mk not in forms:
            forms[mk] = StatForm(mk, base)
            targets[mk] = r["target"]
    key_keys = [(r.get("mod_key"), r) for r in key_rows]
    also_keys = [(r.get("mod_key"), r) for r in also_rows if r.get("mod_key") not in {k for k, _ in key_keys}]

    # primaires imposés (slots 2,4,5,6) si dominants dans le top K1
    locked_primary = {}
    if primary_lock > 0:
        for slot, p in (kh.get("primaries") or {}).items():
            sid = NAME_TO_SID.get(p["main"])
            if int(slot) in (2, 4, 5, 6) and sid and p["pct"] >= primary_lock:
                locked_primary[int(slot)] = sid

    # combinaisons de sets habituelles du héros (>= COMBO_MIN_PCT % du top K1)
    combos = accepted_combos(kh)

    def relevance(m):
        s = 0.0
        for mk, f in forms.items():
            T = max(targets[mk], 1e-9)
            if mk == "health":
                v = m["flat"].get(1, 0.0) + f.B * m["pct"].get(55, 0.0) / 100
            else:
                v = f.mod(m["flat"], m["pct"])
            s += (3.0 if mk in {k for k, _ in key_keys} else 1.0) * v / T
        return s

    def solve_with(lock: dict, F0: float, P0: float):
        # --- candidats par slot : top par (slot, set) + mods déjà portés par le héros
        cand = []
        for slot in SLOTS:
            pool = [m for m in mods_avail if m["slot"] == slot and (slot not in lock or m["primary"] == lock[slot])]
            by_set = defaultdict(list)
            for m in pool:
                by_set[m["set"]].append(m)
            for sid, lst in by_set.items():
                lst.sort(key=lambda m: -(relevance(m) + 0.05 * m["quality"]))
                cand.extend(lst[:30])
            have = {m["id"] for m in cand}
            cand.extend(m for m in pool if m["id"] in current_ids and m["id"] not in have)
        if len({m["slot"] for m in cand}) < 6:
            return None, "slot sans mod disponible"
        P = Problem()
        xs = [P.var(0, 1, True) for _ in cand]
        hv = lambda m: m.get("virtual")
        for slot in SLOTS:
            P.row({xs[i]: 1.0 for i, m in enumerate(cand) if m["slot"] == slot}, 1, 1)
        # groupes de sets
        g, y = {}, {}
        for sid, b in sc.MOD_SET_BONUSES.items():
            need = b["count"]
            members = {xs[i]: 1.0 for i, m in enumerate(cand) if m["set"] == sid}
            if not members:
                continue
            g[sid] = P.var(0, 6 // need, True)
            r = P.var(0, need - 1, True)
            co = dict(members); co[g[sid]] = -float(need); co[r] = -1.0
            P.row(co, 0, 0)
        # une seule combinaison visée à la fois (c_k), récompense par groupe de set atteint
        if combos:
            cv = [P.var(0, 1, True) for _ in combos]
            P.row({v: 1.0 for v in cv}, 1 if strict else 0, 1)
            for k, cb in enumerate(combos):
                for sid, ng in cb["groups"].items():
                    if sid not in g:
                        if strict:
                            P.row({cv[k]: 1.0}, 0, 0)      # set sans aucun mod disponible : combinaison impossible
                        continue
                    yk = P.var(0, ng, False, obj=SET_REWARD)
                    P.row({yk: 1.0, g[sid]: -1.0}, -np.inf, 0)
                    P.row({yk: 1.0, cv[k]: -float(ng)}, -np.inf, 0)
                    if strict:
                        P.row({g[sid]: 1.0, cv[k]: -float(ng)}, 0, np.inf)

        def stat_expr(mk):
            """Expression linéaire S_mk (dict var->coef) + constante."""
            f = forms[mk]
            co, const = defaultdict(float), 0.0
            if f.kind == "health":
                # (B+F)(1+Pf/100)-B  ~ F + B*Pf/100 + (F0*Pf + P0*F - F0*P0)/100   (tangente de F*Pf)
                for i, m in enumerate(cand):
                    F = m["flat"].get(1, 0.0); Pf = m["pct"].get(55, 0.0)
                    co[xs[i]] += F + f.B * Pf / 100 + (F0 * Pf + P0 * F) / 100
                if 1 in g:
                    co[g[1]] += (f.B * 10.0 + F0 * 10.0) / 100
                const -= F0 * P0 / 100
            else:
                for i, m in enumerate(cand):
                    v = f.mod(m["flat"], m["pct"])
                    if v:
                        co[xs[i]] += v
                for sid in g:
                    bv = f.bonus(sid)
                    if bv:
                        co[g[sid]] += bv
            return co, const

        bands = {}
        for mk, r in key_keys:
            T = targets[mk]
            co, const = stat_expr(mk)
            bs = [P.var(0, 1, True, obj=BIG) for _ in BAND_THRESHOLDS]
            for j, thr in enumerate(BAND_THRESHOLDS):
                row = dict(co); row[bs[j]] = row.get(bs[j], 0.0) - thr * T
                P.row(row, -const, np.inf)             # S >= thr*T*b
                if j:
                    P.row({bs[j]: 1.0, bs[j - 1]: -1.0}, -np.inf, 0)
            bands[mk] = bs
        for mk, r in also_keys:
            T = max(targets[mk], 1e-9)
            co, const = stat_expr(mk)
            z = P.var(0, 1000.0, False, obj=1.0)       # progression plafonnée à 100 % de la cible
            row = {j: -v * 1000.0 / T for j, v in co.items()}; row[z] = 1.0
            P.row(row, -np.inf, const * 1000.0 / T)
        for i, m in enumerate(cand):
            P.obj[xs[i]] += keep_bonus * (1.0 if m["id"] in current_ids else 0.0) - 6.0 * m["quality"] \
                - (VIRTUAL_PENALTY if m.get("virtual") else 0.0)
        solve_started = time.monotonic()
        res = P.solve(time_limit)
        solve_seconds = time.monotonic() - solve_started

        # Keep enough HiGHS diagnostics in plan.json to distinguish a proven
        # optimum from a merely feasible incumbent returned at the time limit.
        status_names = {
            0: "optimal",
            1: "limit_reached",
            2: "infeasible",
            3: "unbounded",
            4: "solver_error",
        }

        def finite_float(value):
            try:
                value = float(value)
                return value if math.isfinite(value) else None
            except (TypeError, ValueError):
                return None

        if res.x is None or res.status not in (0, 1):
            return None, {
                "status": int(res.status),
                "status_name": status_names.get(int(res.status), "unknown"),
                "message": str(res.message),
                "n_candidates": len(cand),
                "n_variables": len(P.obj),
                "n_constraints": len(P.rows),
                "solve_seconds": round(solve_seconds, 3),
                "objective": finite_float(-res.fun) if res.fun is not None else None,
                "mip_gap": finite_float(getattr(res, "mip_gap", None)),
                "mip_dual_bound": finite_float(-res.mip_dual_bound)
                                  if getattr(res, "mip_dual_bound", None) is not None else None,
                "mip_node_count": getattr(res, "mip_node_count", None),
            }, f"échec solveur ({res.message})"

        chosen = [cand[i] for i in range(len(cand)) if res.x[xs[i]] > 0.5]
        info = {
            "status": int(res.status),
            "status_name": status_names.get(int(res.status), "unknown"),
            "message": str(res.message),
            "n_candidates": len(cand),
            "n_variables": len(P.obj),
            "n_constraints": len(P.rows),
            "solve_seconds": round(solve_seconds, 3),
            # P.solve maximizes by minimizing the negated objective.
            "objective": finite_float(-res.fun) if res.fun is not None else None,
            "mip_gap": finite_float(getattr(res, "mip_gap", None)),
            "mip_dual_bound": finite_float(-res.mip_dual_bound)
                              if getattr(res, "mip_dual_bound", None) is not None else None,
            "mip_node_count": getattr(res, "mip_node_count", None),
        }
        return chosen, info

    # point de linéarisation de la santé : mods actuels du héros (ou 0)
    cur = [m for m in mods_avail if m["id"] in current_ids]
    F0 = sum(m["flat"].get(1, 0.0) for m in cur)
    P0 = sum(m["pct"].get(55, 0.0) for m in cur)
    chosen, info = None, None
    seen = set()
    for it in range(3 if "health" in forms else 1):
        chosen, info = solve_with(locked_primary, F0, P0)
        if chosen is None and locked_primary:
            chosen, info = solve_with({}, F0, P0)
            locked_primary = {}
        if chosen is None:
            return None, info
        sig = tuple(sorted(m["id"] for m in chosen))
        if sig in seen:
            break
        seen.add(sig)
        F0 = sum(m["flat"].get(1, 0.0) for m in chosen)
        P0 = sum(m["pct"].get(55, 0.0) for m in chosen) + sum(
            10.0 * ((sum(1 for m in chosen if m["set"] == 1)) // 2) for _ in [0])
    cnt = Counter(m["set"] for m in chosen)
    best = None
    for cb in combos:
        miss = {sid: max(0, ng - cnt[sid] // sc.MOD_SET_BONUSES[sid]["count"]) for sid, ng in cb["groups"].items()}
        score = sum(cb["groups"].values()) - sum(miss.values())
        if best is None or score > best[0]:
            best = (score, cb, miss)
    if best:
        info["combo"] = best[1]["name"]
        info["set_ok"] = not any(best[2].values())
        info["set_missing"] = {SET_KEY[k]: v for k, v in best[2].items() if v}
    info["primary_lock"] = {SLOT_NAME[s]: STAT_DISPLAY.get(v, v) for s, v in locked_primary.items()}
    return chosen, info


# ─────────────────────────────────────────────────────────────────────────────
# Mods fictifs « idéaux » (calcul des mods à farmer)
# ─────────────────────────────────────────────────────────────────────────────

PCT_SCALE_IDS = {16, 17, 18, 27, 48, 49, 52, 53, 54, 55, 56, 57}     # stats stockées à 1e6 (les autres à 1e8)
# stat secondaire utile selon la stat clé (1er choix d'abord). Un mod n'a jamais en secondaire la stat de sa primaire.
MODKEY_SEC = {"speed": [5], "protection": [56, 28], "health": [55, 1], "potency": [17], "tenacity": [18],
              "crit_chance_pct": [53], "armor": [49, 42], "resistance": [49],
              "physical_damage": [48, 41], "special_damage": [48, 41], "crit_damage": []}
SLOT_PRIMARIES = {1: [48], 2: [5, 52, 54, 49, 55, 48, 56], 3: [49], 4: [53, 16, 49, 55, 48, 56],
                  5: [55, 56], 6: [18, 17, 49, 55, 48, 56]}
# valeurs par défaut (unités d'affichage) si l'inventaire n'en a pas assez pour les estimer
DEF_PRIMARY = {48: 8.5, 5: 32.0, 49: 20.0, 55: 16.0, 56: 24.0, 16: 42.0, 53: 20.0, 17: 30.0, 18: 35.0,
               52: 12.0, 54: 35.0}
DEF_SEC = {5: 25.0, 1: 1580.0, 28: 2600.0, 41: 150.0, 42: 39.0, 48: 0.62, 49: 1.2, 53: 7.0, 55: 6.7,
           56: 9.7, 17: 9.0, 18: 8.5}
SEC_PCTILES = (95, 90, 75, 50)       # 1re, 2e, 3e, 4e secondaire du mod fictif
SPEED_SEC_FLOOR = 25.0               # le top K1 a des centaines de mods avec >= 25 de vitesse


def _scale(sid):
    return 1e6 if sid in PCT_SCALE_IDS else 1e8


def build_profile(mods: list) -> dict:
    """Valeurs « bon mod » estimées sur l'inventaire : primaires max et percentiles des secondaires (unités d'affichage)."""
    prim, sec, qual = defaultdict(list), defaultdict(list), []
    for m in mods:
        if m["level"] < 15 or not m.get("raw"):
            continue
        qual.append(m["quality"])
        try:
            prim[m["primary"]].append(int(m["raw"]["primaryStat"]["stat"]["unscaledDecimalValue"]) / _scale(m["primary"]))
        except (KeyError, TypeError, ValueError):
            pass
        for sx in m["raw"].get("secondaryStat") or []:
            try:
                sid = sx["stat"]["unitStatId"]
                sec[sid].append(int(sx["stat"]["unscaledDecimalValue"]) / _scale(sid))
            except (KeyError, TypeError, ValueError):
                pass
    P = {"primary": {}, "sec": {}, "quality": float(np.median(qual)) if qual else 0.0}
    for sid, dv in DEF_PRIMARY.items():
        P["primary"][sid] = max(prim[sid]) if len(prim.get(sid, [])) >= 5 else dv
    for sid, dv in DEF_SEC.items():
        if len(sec.get(sid, [])) >= 20:
            P["sec"][sid] = [float(np.percentile(sec[sid], q)) for q in SEC_PCTILES]
        else:
            P["sec"][sid] = [dv, dv * 0.9, dv * 0.7, dv * 0.5]
    P["sec"][5] = [max(P["sec"][5][0], SPEED_SEC_FLOOR)] + P["sec"][5][1:]
    return P


def _sec_wishlist(kh: dict, primary: int) -> list:
    """Secondaires à viser pour ce héros (stats clés d'abord), sans jamais reprendre la stat de la primaire."""
    first, second = [], []
    for r in (kh.get("key_stats") or []) + (kh.get("also") or []):
        mk = r.get("mod_key") or sq.MOD_KEY_DEFAULT.get(r["stat"], "physical_damage")
        ids = MODKEY_SEC.get(mk, [])
        if ids:
            first.append(ids[0])
            second.extend(ids[1:])
    out = []
    for sid in first + second:
        if sid != primary and sid not in out:
            out.append(sid)
    return out[:4]


## START modif oliGTN
#def virtual_mods(kh: dict, prof: dict, locked: dict | None = None) -> list:
def virtual_mods(kh: dict, prof: dict, locked: Optional[dict] = None) -> list:
## END modif oliGTN
    """Un mod fictif par (slot, set, primaire plausible), avec les secondaires utiles au héros."""
    out = []
    prims_k1 = kh.get("primaries") or {}
    for slot in SLOTS:
        allowed = list(SLOT_PRIMARIES[slot])
        p = prims_k1.get(str(slot)) or prims_k1.get(slot)
        if p:
            keep = [NAME_TO_SID.get(p.get("main"))] + [NAME_TO_SID.get(n) for n, pc in (p.get("alts") or {}).items()
                                                        if pc >= 10]
            keep = [k for k in keep if k in allowed]
            if keep:
                allowed = keep
        for pr in allowed:
            wish = _sec_wishlist(kh, pr)
            secs = []
            for rank, sid in enumerate(wish):
                vals = prof["sec"].get(sid)
                if vals:
                    secs.append((sid, vals[min(rank, len(vals) - 1)]))
            for sid_set in sc.MOD_SET_BONUSES:
                raw = {"id": f"VIRT-{sid_set}-{slot}-{pr}", "definitionId": str(sid_set * 100 + 60 + slot),
                       "level": 15, "tier": 5,
                       "primaryStat": {"stat": {"unitStatId": pr,
                                                "unscaledDecimalValue": int(prof["primary"].get(pr, 0) * _scale(pr))}},
                       "secondaryStat": [{"stat": {"unitStatId": s, "unscaledDecimalValue": int(v * _scale(s))},
                                          "roll": [], "statRolls": 1} for s, v in secs]}
                pm = parse_mod(raw, "")
                pm["id"] = raw["id"]
                pm["virtual"] = True
                pm["quality"] = prof["quality"]
                pm["secs"] = secs
                out.append(pm)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Évaluation exacte (calcul de stats du jeu)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(unit: dict, mods: list, gd: dict, kh: dict) -> dict:
    u = dict(unit)
    u["equippedStatMod"] = [m["raw"] for m in mods]
    res = sc.calc_unit_full(u, gd)
    out, pts = [], 0
    for r in kh["key_stats"]:
        mk = r.get("mod_key") or sq.default_mod_key(r["stat"], res)
        val = res["mod_delta"].get(mk, 0.0)
        ratio = val / r["target"] if r["target"] else 0.0
        p = sq.points_for(ratio)
        pts += p
        out.append({"stat": r["stat"], "value": round(val, 2), "target": round(r["target"], 2),
                    "ratio": round(ratio, 4), "points": p})
    return {"points": pts, "max": 4 * len(kh["key_stats"]), "stats": out}


# ─────────────────────────────────────────────────────────────────────────────
# Ordre des héros
# ─────────────────────────────────────────────────────────────────────────────

def read_order(path: str, gd: dict, loc: dict) -> list:
    out, seen = [], set()
    for line in open(path, encoding="utf-8"):
        t = line.split("#")[0].strip()
        if not t:
            continue
        if t in gd["units"]:
            ids = [t]
        else:
            found, _ = sq.select_heroes(gd, loc, hero=t)
            q = sq.norm(t)
            exact = [b for b in (found or []) if sq.norm(b) == q or sq.norm(sq.hero_name(b, gd, loc)) == q]
            ids = exact or sorted(found or [])
            if len(ids) != 1:
                print(f"  ordre : '{t}' -> {len(ids)} correspondance(s), ligne ignorée" +
                      (f" ({', '.join(ids[:5])})" if ids else ""), flush=True)
                continue
        if ids[0] not in seen:
            seen.add(ids[0]); out.append(ids[0])
    return out


def default_order(player: dict, gd: dict, keystats: dict) -> list:
    """ORDRE PROVISOIRE : Légendes galactiques d'abord, puis puissance décroissante."""
    rows = []
    for u in player.get("rosterUnit") or []:
        b = (u.get("definitionId") or "").split(":")[0]
        if not (keystats["heroes"].get(b) or {}).get("key_stats"):
            continue
        cats = " ".join(gd["units"].get(b, {}).get("_cats", [])).lower()
        gl = 1 if "galacticlegend" in cats.replace("_", "") else 0
        rows.append((-gl, -(int(u.get("galacticPower") or 0)), b))
    return [b for _, _, b in sorted(rows)]


# ─────────────────────────────────────────────────────────────────────────────
# Modèle Grandivory (character template)
# ─────────────────────────────────────────────────────────────────────────────

def template_target(base: str, kh: dict, name: str) -> dict:
    w = {k: 0 for k in ("health", "protection", "speed", "critDmg", "potency", "tenacity", "physDmg",
                        "specDmg", "critChance", "armor", "resistance", "accuracy", "critAvoid")}
    ks_rows = list(kh["key_stats"])
    # convention du site : la vitesse, quand c'est une stat clé, est à 100 ; les autres se partagent 100/60/40
    ks_rows.sort(key=lambda r: 0 if r["stat"] == "speed" else 1)
    for r, weight in zip(ks_rows, (100, 60, 40)):
        if r["stat"] == "offense":
            w["specDmg" if r.get("mod_key") == "special_damage" else "physDmg"] = weight
        elif r["stat"] in GRANDIVORY_WEIGHT:
            w[GRANDIVORY_WEIGHT[r["stat"]]] = weight
    prim = {}
    for slot, p in (kh.get("primaries") or {}).items():
        sid = NAME_TO_SID.get(p["main"])
        if int(slot) in (2, 4, 5, 6) and sid and p["pct"] >= 75:
            prim[SLOT_NAME[int(slot)]] = STAT_DISPLAY.get(sid, "")
    sets = {}
    tc = (kh.get("sets") or {}).get("top_combo") or {}
    for sname, cnt in (tc.get("sets") or {}).items():
        sid = SET_BY_NAME.get(sname)
        if sid:
            k = cnt // sc.MOD_SET_BONUSES[sid]["count"]
            if k:
                sets[SET_KEY[sid]] = k
    return {"name": name, **w, "upgradeMods": True, "useOnlyFullSets": False,
            "primaryStatRestrictions": prim, "setRestrictions": sets, "targetStats": []}


# ─────────────────────────────────────────────────────────────────────────────
# Programme principal
# ─────────────────────────────────────────────────────────────────────────────

def load_base_template(path: str, keystats: dict) -> dict:
    """Template Grandivory exporté à la main : ses primaires et ses sets REMPLACENT ceux déduits du top K1
    pour les héros qu'il contient (leurs poids et noms sont repris tels quels dans le template de sortie).
    Retourne {héros: target}."""
    raw = json.load(open(path))
    chars = [c for t in (raw if isinstance(raw, list) else [raw]) for c in t.get("selectedCharacters", [])]
    disp_to_sid = {v: k for k, v in STAT_DISPLAY.items()}
    key_to_sid = {v: k for k, v in SET_KEY.items()}
    slot_num = {v: k for k, v in SLOT_NAME.items()}
    out = {}
    for c in chars:
        b, tg = c.get("id"), c.get("target") or {}
        kh = (keystats.get("heroes") or {}).get(b)
        if not kh:
            continue
        prim = {}
        for slot, disp in (tg.get("primaryStatRestrictions") or {}).items():
            sid, sn = disp_to_sid.get(disp), slot_num.get(slot)
            if sid and sn and sid in sc.MODRAW_NAMES:
                prim[str(sn)] = {"main": sc.MODRAW_NAMES[sid], "pct": 100.0}
        sets = {}
        for k, cnt in (tg.get("setRestrictions") or {}).items():
            sid = key_to_sid.get(k)
            if sid:
                sets[sc.SET_NAMES[sid]] = int(cnt) * sc.MOD_SET_BONUSES[sid]["count"]
        kh["primaries"] = prim
        kh["sets"] = {"top_combo": {"sets": sets}}
        out[b] = {**tg, "name": "statq K1"}
    return out


def optimise(player, gd, keystats, order, loc, min_relic=3, lock_unselected=True, primary_lock=75.0,
             time_limit=8.0, max_heroes=0, log=print, only_ids=None, strict_n=0, farm=True):
    heroes_ks = keystats["heroes"]
    roster = {}
    for u in player.get("rosterUnit") or []:
        roster[(u.get("definitionId") or "").split(":")[0]] = u
    mods = load_mods(player)
    if only_ids is not None:
        n0 = len(mods)
        mods = [m for m in mods if m["id"] in only_ids]
        if len(mods) < n0:
            log(f"  {n0 - len(mods)} mods absents du fichier progress : ignorés (ils ne pourraient pas être posés par le bot)")
    by_id = {m["id"]: m for m in mods}
    order_set = set(order)
    # mods verrouillés : portés par un héros hors ordre (ou ignoré)
    pool = {}
    for m in mods:
        if m["level"] < 15:
            continue
        if lock_unselected and m["owner"] and m["owner"] not in order_set:
            continue
        pool[m["id"]] = m
    log(f"Mods : {len(mods)} au total, {len(pool)} disponibles (niveau 15"
        f"{', hors héros non sélectionnés' if lock_unselected else ''})")

    prof = build_profile(list(pool.values())) if farm else None
    plan, used = [], set()
    t0 = time.time()
    for n, base in enumerate(order, 1):
        if max_heroes and n > max_heroes:
            break
        kh = heroes_ks.get(base)
        unit = roster.get(base)
        name = sq.hero_name(base, gd, loc)
        if not kh or not kh.get("key_stats") or unit is None or sq.unit_relic(unit) < min_relic:
            why = "pas de stats clés" if not kh or not kh.get("key_stats") else ("non possédé" if unit is None else "sous R3")
            plan.append({"base": base, "hero": name, "skipped": why})
            continue
        bstate = sc._base_state(unit, gd)
        if bstate is None:
            plan.append({"base": base, "hero": name, "skipped": "données de jeu manquantes"})
            continue
        current = [m for m in mods if m["owner"] == base]
        current_ids = {m["id"] for m in current}
        avail = [m for mid, m in pool.items() if mid not in used]
        t1 = time.time()
        strict = n <= strict_n
        chosen, info = solve_hero(unit, bstate, kh, avail, current_ids, name, primary_lock, time_limit, strict=strict)
        alt = None
        if strict:
            if chosen is None:
                # set imposé impossible avec ces mods : on retombe sur la meilleure combinaison possible pour le statq
                chosen, info = solve_hero(unit, bstate, kh, avail, current_ids, name, primary_lock, time_limit)
                if chosen is not None:
                    info["mode"] = "repli (set impossible)"
            else:
                info["mode"] = "sets imposés"
                alt = solve_hero(unit, bstate, kh, avail, current_ids, name, primary_lock, time_limit)
        if chosen is None:
            plan.append({"base": base, "hero": name, "skipped": f"solveur : {info}"})
            continue
        info.setdefault("mode", "souple")
        before = evaluate(unit, current, gd, kh) if len(current) == 6 else evaluate(unit, current, gd, kh)
        after = evaluate(unit, chosen, gd, kh)
        farm_entry = None
        if farm:
            try:
                vm = virtual_mods(kh, prof)
                ideal, iinfo = solve_hero(unit, bstate, kh, avail + vm, current_ids, name, primary_lock, time_limit)
                if ideal is not None:
                    vused = [m for m in ideal if m.get("virtual")]
                    if vused:
                        ev = evaluate(unit, ideal, gd, kh)
                        gain = ev["points"] - after["points"]
                        set_gain = bool(iinfo.get("set_ok")) and not info.get("set_ok")
                        if gain > 0 or set_gain:
                            farm_entry = {"points_ideal": ev["points"], "gain": gain,
                                          "set_ok_ideal": iinfo.get("set_ok"), "combo": iinfo.get("combo"),
                                          "mods": [{"slot": SLOT_NAME[m["slot"]], "set": sc.SET_NAMES.get(m["set"], m["set"]),
                                                    "primary": m["primary"],
                                                    "secondaries": [[sid, round(v, 2)] for sid, v in m["secs"]]}
                                                   for m in vused]}
            except Exception as e:          # le calcul des mods à farmer ne doit jamais bloquer le plan
                log(f"  (mods à farmer : {name} ignoré — {e})")
        alt_entry = None
        if alt and alt[0] is not None:
            aev = evaluate(unit, alt[0], gd, kh)
            if aev["points"] > after["points"]:
                alt_entry = {"points": aev["points"], "mods": {SLOT_NAME[m["slot"]]: m["id"] for m in alt[0]},
                             "sets": dict(sorted(((sc.SET_NAMES.get(s, s), c) for s, c in
                                                  Counter(m["set"] for m in alt[0]).items())))}
        used |= {m["id"] for m in chosen}
        moves = [{"slot": SLOT_NAME[m["slot"]], "mod": m["id"], "from": m["owner"] or "(inventaire)"}
                 for m in chosen if m["id"] not in current_ids]
        plan.append({"base": base, "hero": name, "before": before, "after": after,
                     "mods": {SLOT_NAME[m["slot"]]: m["id"] for m in chosen},
                     "sets": dict(sorted(((sc.SET_NAMES.get(s, s), c) for s, c in
                                          Counter(m["set"] for m in chosen).items()))),
                     "moves": moves, "seconds": round(time.time() - t1, 2), "solver": info,
                     "rank": n, "farm": farm_entry, "alt": alt_entry})
        log(f"  {n:>3}. {name:<28} {before['points']:>2} -> {after['points']:>2} / {after['max']}   "
            f"({len(moves)} déplacements, {time.time() - t1:.1f}s)")
    return plan, round(time.time() - t0, 1)


WEIGHT_KEYS = ("health", "protection", "speed", "critDmg", "potency", "tenacity", "physDmg", "specDmg",
               "critChance", "armor", "resistance", "accuracy", "critAvoid")
SLOT_ORDER = ("square", "arrow", "diamond", "triangle", "circle", "cross")


def write_progress(base_path, out_dir, plan, keystats, base_targets):
    """Fichier au format « Save my progress / Restore my progress » du site : le fichier de ton ami
    (roster + mods) dans lequel on remplace selectedCharacters (ordre de priorité + réglages)
    et modAssignments (mods à poser sur chaque héros)."""
    prog = json.load(open(base_path))
    prof = prog["profiles"][0]
    known = {m.get("mod_uid") for m in prof.get("mods", [])}
    sel, assigns, unknown = [], [], set()
    for p in plan:
        if "after" not in p:
            continue
        b = p["base"]
        tg = (base_targets or {}).get(b) or template_target(b, keystats["heroes"][b], "statq K1")
        sel.append({"id": b, "target": tg})
        norm = dict(tg)
        for k in WEIGHT_KEYS:                       # modAssignments : poids ramenés sur 0-5 (100 -> 5)
            norm[k] = round((tg.get(k) or 0) / 20.0, 4)
        ids = [p["mods"][sl] for sl in SLOT_ORDER if sl in p["mods"]]
        unknown |= {i for i in ids if known and i not in known}
        assigns.append({"id": b, "target": norm, "assignedMods": ids, "messages": [], "missedGoals": []})
    prof["selectedCharacters"] = sel
    prof["modAssignments"] = assigns
    json.dump(prog, open(os.path.join(out_dir, "progress_out.json"), "w"), ensure_ascii=False)
    return len(sel), sorted(unknown)


STAT_LABEL = {"health": "Santé", "protection": "Protection", "speed": "Vitesse", "offense": "Dégâts (offense)",
              "armor": "Armure", "resistance": "Résistance", "crit_chance": "Chance de critique",
              "crit_damage": "Dégâts critiques", "potency": "Pouvoir", "tenacity": "Ténacité"}
# statistique de all_scores -> clé dans stats / mod_stats du fichier top 100
_STATS_KEY = {"health": "health", "protection": "protection", "speed": "speed", "armor": "armor",
              "resistance": "resistance", "crit_damage": "crit_damage", "potency": "potency", "tenacity": "tenacity"}


def write_keystats_report(out_dir, keystats, stats_units, names, planned, base_targets=None):
    """stats_retenues.csv : pour chaque héros (ordre alphabétique) et chaque stat, le coefficient de pertinence
    (probabilité que la stat soit « clé » parmi les top 100 K1), si elle est retenue, et mini/moyenne/maxi."""
    def r(v, n=1):
        return "" if v is None else round(v, n)
    rows = []
    for base, kh in keystats["heroes"].items():
        su = (stats_units or {}).get(base) or {}
        ms, fs = su.get("mod_stats") or {}, su.get("stats") or {}
        kept = {x["stat"]: i + 1 for i, x in enumerate(kh.get("key_stats") or [])}
        also = {x["stat"] for x in kh.get("also") or []}
        tw = (base_targets or {}).get(base)
        for st, sc_ in (kh.get("all_scores") or {}).items():
            if st == "offense":
                # dégâts physiques ou spéciaux : celui dont la moyenne correspond à celle de all_scores
                cand = [k for k in ("physical_damage", "special_damage") if k in ms]
                mk = min(cand, key=lambda k: abs(ms[k]["mean"] - sc_["mean"])) if cand else None
                fk = mk
            elif st == "crit_chance":
                mk, fk = "crit_chance_pct", None
            else:
                mk = fk = _STATS_KEY.get(st)
            a, f = ms.get(mk) or {}, fs.get(fk) or {}
            rows.append([names.get(base, base), base, "oui" if base in planned else "non",
                         STAT_LABEL.get(st, st),
                         "CLÉ" if st in kept else ("secondaire" if st in also else "ignorée"),
                         kept.get(st, ""), r(sc_.get("prob"), 3), r(sc_.get("z"), 2), r(sc_.get("tight"), 2),
                         r(a.get("min")), r(a.get("mean")), r(a.get("max")),
                         r(f.get("min")), r(f.get("mean")), r(f.get("max")), kh.get("n", "")])
    rows.sort(key=lambda x: (x[0].lower(), -float(x[6] or 0)))
    with open(os.path.join(out_dir, "stats_retenues.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["heros", "heros_id", "dans_le_plan", "stat", "statut", "rang_cle", "coefficient",
                    "z_vs_autres", "regularite", "ajout_mods_mini", "ajout_mods_moyenne", "ajout_mods_maxi",
                    "final_mini", "final_moyenne", "final_maxi", "nb_joueurs_k1"])
        w.writerows(rows)
    return len(rows)


FR_SLOT = {"square": "Carré", "arrow": "Flèche", "diamond": "Losange", "triangle": "Triangle", "circle": "Rond",
           "cross": "Croix"}
FR_SET = {"health": "Santé", "offense": "Attaque", "defense": "Défense", "speed": "Vitesse",
          "critchance": "Chance critique", "critdamage": "Dégâts critiques", "potency": "Pouvoir",
          "tenacity": "Ténacité"}
FR_STAT = {1: "Santé", 5: "Vitesse", 28: "Protection", 41: "Attaque", 42: "Défense", 48: "Attaque %",
           49: "Défense %", 53: "Chance critique %", 16: "Dégâts critiques %", 17: "Pouvoir %",
           18: "Ténacité %", 55: "Santé %", 56: "Protection %", 52: "Précision %", 54: "Évitement critique %"}
SLOT_FR_ORDER = {"square": 1, "arrow": 2, "diamond": 3, "triangle": 4, "circle": 5, "cross": 6}


def _fr_set(name):
    return FR_SET.get(str(name).replace(" ", "").lower().replace("_", ""), name)


def _fmt_sec(sid, v):
    return f"{FR_STAT.get(sid, sid)} ≥ {round(v) if v >= 50 else round(v, 1):g}"


def write_farm_reports(out_dir, plan):
    """mods_a_farmer.csv (par héros, ordre alphabétique) + mods_a_farmer_resume.csv (cumul par type de mod)
    + alternatives_statq.csv (héros où ignorer l'imposition des sets rapporte plus de points)."""
    rows, agg = [], {}
    for p in plan:
        fm = p.get("farm")
        if not fm:
            continue
        pts_now = p["after"]["points"]
        for m in sorted(fm["mods"], key=lambda x: SLOT_FR_ORDER[x["slot"]]):
            secs = [_fmt_sec(sid, v) for sid, v in m["secondaries"]]
            secs += [""] * (4 - len(secs))
            rows.append([p["hero"], p["base"], p.get("rank", ""), FR_SLOT[m["slot"]], _fr_set(m["set"]),
                         FR_STAT.get(m["primary"], m["primary"])] + secs +
                        [pts_now, fm["points_ideal"], fm["gain"], p["after"]["max"],
                         "oui" if fm.get("set_ok_ideal") else "non", fm.get("combo") or ""])
            k = (SLOT_FR_ORDER[m["slot"]], FR_SLOT[m["slot"]], _fr_set(m["set"]), FR_STAT.get(m["primary"], m["primary"]))
            a = agg.setdefault(k, {"n": 0, "gain": 0, "best_rank": 10 ** 6, "heroes": [], "sec": Counter()})
            a["n"] += 1
            a["gain"] += fm["gain"] / max(1, len(fm["mods"]))
            a["best_rank"] = min(a["best_rank"], p.get("rank", 10 ** 6))
            a["heroes"].append(p["hero"])
            for s_ in secs:
                if s_:
                    a["sec"][s_.split(" ≥")[0]] += 1
    rows.sort(key=lambda r: (r[0].lower(), SLOT_FR_ORDER.get({v: k for k, v in FR_SLOT.items()}[r[3]], 9)))
    with open(os.path.join(out_dir, "mods_a_farmer.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["personnage", "id", "priorite", "emplacement", "set", "primaire", "secondaire_1", "secondaire_2",
                    "secondaire_3", "secondaire_4", "points_statq_actuels", "points_statq_avec_tous_les_mods_du_perso",
                    "gain_points", "points_max", "set_complet_avec_ce_mod", "combinaison_visee"])
        w.writerows(rows)
    with open(os.path.join(out_dir, "mods_a_farmer_resume.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["emplacement", "set", "primaire", "nb_heros_concernes", "meilleure_priorite",
                    "gain_points_cumule", "secondaires_utiles", "premiers_heros"])
        for k, a in sorted(agg.items(), key=lambda kv: (-kv[1]["gain"], kv[1]["best_rank"])):
            w.writerow([k[1], k[2], k[3], a["n"], a["best_rank"], round(a["gain"], 1),
                        ", ".join(n for n, _ in a["sec"].most_common(4)), ", ".join(a["heroes"][:6])])
    alts = [p for p in plan if p.get("alt")]
    with open(os.path.join(out_dir, "alternatives_statq.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["personnage", "id", "priorite", "points_avec_sets_imposes", "points_alternative",
                    "gain_alternative", "sets_alternative"] + [FR_SLOT[k] + "_mod_id" for k in FR_SLOT])
        for p in sorted(alts, key=lambda p: p["hero"].lower()):
            al = p["alt"]
            w.writerow([p["hero"], p["base"], p.get("rank", ""), p["after"]["points"], al["points"],
                        al["points"] - p["after"]["points"],
                        "+".join(f"{_fr_set(k)}{v}" for k, v in al["sets"].items())] +
                       [al["mods"].get(k, "") for k in FR_SLOT])
    return len(rows), len(agg), len(alts)


def write_outputs(out_dir, plan, keystats, order, secs, base_targets=None, progress_file=None, stats_units=None):
    os.makedirs(out_dir, exist_ok=True)
    done = [p for p in plan if "after" in p]
    tb = sum(p["before"]["points"] for p in done)
    ta = sum(p["after"]["points"] for p in done)
    mx = sum(p["after"]["max"] for p in done)
    summary = {"heroes_optimised": len(done), "points_before": tb, "points_after": ta, "max": mx,
               "pct_before": round(100 * tb / mx, 1) if mx else 0, "pct_after": round(100 * ta / mx, 1) if mx else 0,
               "seconds": secs}
    json.dump({"summary": summary, "order": order, "plan": plan}, open(os.path.join(out_dir, "plan.json"), "w"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "assignments.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["priorite", "heros_id", "heros", "slot", "mod_id", "vient_de"])
        for i, p in enumerate(done, 1):
            src = {mv["mod"]: mv["from"] for mv in p["moves"]}
            for slot, mid in p["mods"].items():
                w.writerow([i, p["base"], p["hero"], slot, mid, src.get(mid, p["hero"] + " (déjà équipé)")])
    tpl = [{"name": "statq K1", "selectedCharacters": [
        {"id": p["base"], "target": (base_targets or {}).get(p["base"])
                                    or template_target(p["base"], keystats["heroes"][p["base"]], "statq K1")}
        for p in done]}]
    json.dump(tpl, open(os.path.join(out_dir, "modoptimizer_template.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(out_dir, "ordre_utilise.txt"), "w", encoding="utf-8").write(
        "# Ordre de priorité utilisé par cette passe (réutilisable avec --order)\n" + "\n".join(order) + "\n")
    names = {p["base"]: p["hero"] for p in plan}
    nrep = write_keystats_report(out_dir, keystats, stats_units, names, {p["base"] for p in done}, base_targets)
    extra = [f"stats_retenues.csv : {nrep} lignes (héros × stat, coefficient de pertinence, mini/moyenne/maxi K1)"]
    if progress_file:
        n_sel, unk = write_progress(progress_file, out_dir, plan, keystats, base_targets)
        extra.append(f"progress_out.json : {n_sel} héros ordonnés avec leurs mods à poser")
        if unk:
            extra.append(f"  ATTENTION : {len(unk)} mods absents du fichier progress de base (export plus ancien ?) : {unk[:5]}...")
    nf, na, nalt = write_farm_reports(out_dir, plan)
    extra.append(f"mods_a_farmer.csv : {nf} mods à farmer (alphabétique) ; mods_a_farmer_resume.csv : {na} types ; "
                 f"alternatives_statq.csv : {nalt} héros où l'imposition des sets coûte des points")
    modes = Counter((p.get("solver") or {}).get("mode") for p in done)
    miss = sum(1 for p in done if (p.get("solver") or {}).get("set_ok") is False)
    extra.append(f"Sets : {len(done) - miss}/{len(done)} complets ; modes {dict(modes)}")
    lines = extra + [f"Héros optimisés : {len(done)}   (ignorés : {len(plan) - len(done)})",
             f"Points statq : {tb} -> {ta} / {mx}   ({summary['pct_before']} % -> {summary['pct_after']} %)",
             f"Déplacements de mods : {sum(len(p['moves']) for p in done)}   Durée : {secs}s", ""]
    for p in plan:
        if "skipped" in p:
            lines.append(f"- {p['hero']}: ignoré ({p['skipped']})")
    open(os.path.join(out_dir, "resume.txt"), "w", encoding="utf-8").write("\n".join(lines))
    return summary, lines


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--allycode", help="roster frais via Comlink (mods équipés seulement ; avec --progress-file, "
                                      "les mods en inventaire viennent du fichier progress)")
    g.add_argument("--player-file", help="initialdata du jeu")
    ap.add_argument("--keystats-file")
    ap.add_argument("--stats-file", help="stats top 100 K1 pour l'ordre automatique (défaut : Cloudflare KV)")
    ap.add_argument("--order")
    ap.add_argument("--out", default="modopt_out")
    ap.add_argument("--lang", default="FRE_FR")
    ap.add_argument("--no-names", action="store_true")
    ap.add_argument("--min-relic", type=int, default=3)
    ap.add_argument("--free-unselected", action="store_true")
    ap.add_argument("--primary-lock", type=float, default=75.0)
    ap.add_argument("--time-limit", type=float, default=8.0)
    ap.add_argument("--max-heroes", type=int, default=0)
    ap.add_argument("--set-reward", type=float, default=SET_REWARD,
                    help="poids du respect des sets du template (défaut 5000 ; une bande de statq vaut 100000)")
    ap.add_argument("--sets-stricts", type=int, default=40,
                    help="impose les sets aux N premiers héros (repli automatique si impossible ; 0 = jamais)")
    ap.add_argument("--no-farm", action="store_true", help="ne pas calculer les mods à farmer")
    ap.add_argument("--progress-file", help="export « Save my progress » du site (roster+mods) : sert de base à progress_out.json")
    ap.add_argument("--base-template", help="template Grandivory exporté (primaires/sets/poids repris pour ses héros)")
    a = ap.parse_args()

    if not (a.allycode or a.player_file or a.progress_file):
        sys.exit("ERREUR : fournis --allycode, --player-file ou --progress-file")
    if a.progress_file and not os.path.isfile(a.progress_file):
        sys.exit(f"ERREUR : fichier progress introuvable : {a.progress_file!r}")
    globals()['SET_REWARD'] = a.set_reward
## START modif oliGTN
    #gd = sc.load_game_data()
    #loc = {} if a.no_names else sq.load_localization(a.lang)
    gd = sc.load_game_data("/home/pi/GuionBot/warstats")
    loc = json.load(open("/home/pi/GuionBot/DATA/FRE_FR.json"))
## END modif oliGTN
    keystats = ks.ensure_speed(json.load(open(a.keystats_file)) if a.keystats_file else ks.load_from_kv("keystats:v1"))
    if a.player_file:
        raw = json.load(open(a.player_file))
        player = sc.normalize_player(raw)
        if "unequippedMod" not in player:
            player["unequippedMod"] = (raw.get("inventory") or {}).get("unequippedMod") or []
        print("Source : fichier initialdata", flush=True)
    elif a.allycode:
        player = sc.normalize_player(sc._post("player", {"allyCode": a.allycode.replace("-", "")}))
        if a.progress_file:
            import progress_adapter as pa
            inv = pa.load_progress_as_initialdata(a.progress_file)["inventory"]
            equipped = {m["id"] for u in player.get("rosterUnit") or [] for m in u.get("equippedStatMod") or []}
            extra = [m for m in inv["unequippedMod"] + [m for u in inv["unit"] for m in u["equippedStatMod"]]
                     if m["id"] not in equipped]
            player["unequippedMod"] = extra
            print(f"Source : Comlink (roster et mods équipés à jour) + {len(extra)} mods non équipés tirés du "
                  f"fichier progress", flush=True)
        else:
            print("Source : Comlink (seuls les mods équipés sont connus)", flush=True)
    else:
        import progress_adapter as pa
        inv = pa.load_progress_as_initialdata(a.progress_file)["inventory"]
        player = {"rosterUnit": inv["unit"], "unequippedMod": inv["unequippedMod"]}
        print(f"Source : fichier progress seul ({len(inv['unit'])} héros, "
              f"{sum(len(u['equippedStatMod']) for u in inv['unit']) + len(inv['unequippedMod'])} mods)", flush=True)

    if a.order:
        if not os.path.isfile(a.order):
            sys.exit(f"ERREUR : fichier d'ordre introuvable : {a.order!r} (vérifie le nom et l'extension, "
                     f"majuscules comprises, dans le dépôt)")
        order = read_order(a.order, gd, loc)
        print(f"Ordre : {len(order)} héros (fichier {a.order})", flush=True)
    else:
        try:
            import generer_ordre_auto as go
            stats = json.load(open(a.stats_file)) if a.stats_file else ks.load_from_kv("stats:v2:top100")
            order = go.compute_order(player.get("rosterUnit") or [], player.get("unequippedMod"), stats["units"],
                                     keystats["heroes"], 0.5, a.min_relic)[0]
            print(f"Ordre AUTOMATIQUE (top 100 K1 + tes mods) : {len(order)} héros", flush=True)
        except Exception as e:  # stats K1 indisponibles
            order = default_order(player, gd, keystats)
            print(f"Ordre PROVISOIRE (GL puis puissance) : {len(order)} héros — ordre automatique impossible ({e})",
                  flush=True)

    base_targets = {}
    if a.base_template:
        if not os.path.isfile(a.base_template):
            sys.exit(f"ERREUR : template introuvable : {a.base_template!r}")
        base_targets = load_base_template(a.base_template, keystats)
        print(f"Template de base : {len(base_targets)} héros (primaires et sets repris)", flush=True)
    only_ids = None
    if a.progress_file:
        only_ids = {m.get("mod_uid") for m in json.load(open(a.progress_file))["profiles"][0].get("mods", [])}
    plan, secs = optimise(player, gd, keystats, order, loc, a.min_relic, not a.free_unselected,
                          a.primary_lock, a.time_limit, a.max_heroes, only_ids=only_ids,
                          strict_n=a.sets_stricts, farm=not a.no_farm)
    stats_units = None
    try:
        stats_units = (json.load(open(a.stats_file)) if a.stats_file else ks.load_from_kv("stats:v2:top100"))["units"]
    except Exception as e:
        print(f"(stats K1 indisponibles pour le rapport : mini/maxi laissés vides — {e})", flush=True)
    summary, lines = write_outputs(a.out, plan, keystats, order, secs, base_targets, a.progress_file, stats_units)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
