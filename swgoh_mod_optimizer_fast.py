"""Python port of the optimizer.js algorithm.

Source basis: optimizer.js supplied in the conversation.
The public entry point is optimize_mods_from_profile(), which accepts one
myProgress profile and an optional external optimization template.

This is intentionally a close behavioral port rather than a redesign.
Browser/IndexedDB/WebWorker messaging has been removed. Progress callbacks
are optional and are not required by the algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from math import floor, inf
from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple
import time
import emojis
import goutils

# ---------------------------------------------------------------------------
# Static data copied from optimizer.js
# ---------------------------------------------------------------------------
STAT_TYPE_MAP = {
    "Health": ["health"], "Protection": ["protection"], "Speed": ["speed"],
    "Critical Damage": ["critDmg"], "Potency": ["potency"], "Tenacity": ["tenacity"],
    "Offense": ["physDmg", "specDmg"], "Physical Damage": ["physDmg"],
    "Special Damage": ["specDmg"], "Critical Chance": ["physCritChance", "specCritChance"],
    "Physical Critical Chance": ["physCritChance"], "Special Critical Chance": ["specCritChance"],
    "Defense": ["armor", "resistance"], "Armor": ["armor"], "Resistance": ["resistance"],
    "Accuracy": ["accuracy"], "Critical Avoidance": ["critAvoid"],
}

STAT_DISPLAY_NAMES = {
    "health": "Health", "protection": "Protection", "speed": "Speed", "critDmg": "Critical Damage",
    "potency": "Potency", "tenacity": "Tenacity", "physDmg": "Physical Damage", "specDmg": "Special Damage",
    "critChance": "Critical Chance", "physCritChance": "Physical Critical Chance",
    "specCritChance": "Special Critical Chance", "defense": "Defense", "armor": "Armor",
    "resistance": "Resistance", "accuracy": "Accuracy", "critAvoid": "Critical Avoidance",
    "physCritAvoid": "Physical Critical Avoidance", "specCritAvoid": "Special Critical Avoidance",
}

WHOLE_STAT_TYPES = ["Health", "Protection", "Offense", "Physical Damage", "Special Damage",
                    "Speed", "Defense", "Armor", "Resistance"]
MOD_SLOTS = ["square", "arrow", "diamond", "triangle", "circle", "cross"]

@dataclass(frozen=True)
class Stat:
    type: str
    displayType: str
    value: float
    isPercent: bool

@dataclass(frozen=True)
class SetBonus:
    name: str
    numberOfModsRequired: int
    smallBonus: Stat
    maxBonus: Stat


def _stat(display: str, value: float, percent: bool = False) -> Stat:
    return Stat(type=display + (" %" if percent else ""), displayType=display,
                value=value, isPercent=percent)

SET_BONUSES = {
    "health": SetBonus("health", 2, _stat("Health", 5, True), _stat("Health", 10, True)),
    "defense": SetBonus("defense", 2, _stat("Defense", 12.5, True), _stat("Defense", 25, True)),
    "critdamage": SetBonus("critdamage", 4, _stat("Critical Damage", 15), _stat("Critical Damage", 30)),
    "critchance": SetBonus("critchance", 2, _stat("Critical Chance", 4), _stat("Critical Chance", 8)),
    "tenacity": SetBonus("tenacity", 2, _stat("Tenacity", 10), _stat("Tenacity", 20)),
    "offense": SetBonus("offense", 4, _stat("Offense", 7.5, True), _stat("Offense", 15, True)),
    "potency": SetBonus("potency", 2, _stat("Potency", 7.5), _stat("Potency", 15)),
    "speed": SetBonus("speed", 4, _stat("Speed", 5, True), _stat("Speed", 10, True)),
}

MAX_STAT_PRIMARIES = {
    "Offense": {1: 1.88, 2: 2, 3: 3.88, 4: 4, 5: 5.88, 6: 8.50},
    "Defense": {1: 3.75, 2: 4, 3: 7.75, 4: 8, 5: 11.75, 6: 20},
    "Health": {1: 1.88, 2: 2, 3: 3.88, 4: 4, 5: 5.88, 6: 16},
    "Protection": {1: 7.5, 2: 8, 3: 15.5, 4: 16, 5: 23.5, 6: 24},
    "Speed": {1: 17, 2: 19, 3: 21, 4: 26, 5: 30, 6: 32},
    "Accuracy": {1: 7.5, 2: 8, 3: 8.75, 4: 10.5, 5: 12, 6: 30},
    "Critical Avoidance": {1: 15, 2: 16, 3: 18, 4: 21, 5: 24, 6: 35},
    "Critical Chance": {1: 7.50, 2: 8, 3: 8.75, 4: 10.5, 5: 12, 6: 20},
    "Critical Damage": {1: 22.50, 2: 24, 3: 27, 4: 31.5, 5: 36, 6: 42},
    "Potency": {1: 15, 2: 16, 3: 18, 4: 21, 5: 24, 6: 30},
    "Tenacity": {1: 15, 2: 16, 3: 18, 4: 21, 5: 24, 6: 35},
}

SLICING_UPGRADE_FACTORS = {
    "Offense %": 3.02, "Defense %": 2.34, "Health %": 1.86, "Defense": 1.63,
    "Tenacity": 1.33, "Potency": 1.33, "Protection %": 1.33, "Health": 1.26,
    "Protection": 1.11, "Offense": 1.10, "Critical Chance": 1.04,
}

STAT_WEIGHTS = {
    "health": 2000, "protection": 4000, "speed": 20, "critDmg": 30, "potency": 15,
    "tenacity": 15, "physDmg": 225, "specDmg": 450, "offense": 225, "critChance": 10,
    "armor": 33, "resistance": 33, "accuracy": 10, "critAvoid": 10,
}

ProgressCallback = Optional[Callable[[Dict[str, Any]], None]]

class OptimizerError(RuntimeError):
    pass


class Optimizer:
    def __init__(self, progress_callback: ProgressCallback = None):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.progress_callback = progress_callback
        self.clear_cache()

    def clear_cache(self):
        self.cache = {"modScores": {}, "modUpgrades": {}, "modStats": {}, "statValues": {}}

    def progress(self, character: Dict[str, Any], step: str, percent: float = 100):
        if self.progress_callback:
            self.progress_callback({"character": character.get("baseID"), "step": step, "progress": percent})

    # ------------------------------------------------------------------
    # Deserialization
    # ------------------------------------------------------------------
    @staticmethod
    def deserialize_stat(type_: str, value: Any) -> Stat:
        type_ = type_ or ""
        display = type_[:-1].strip() if type_.endswith("%") else type_
        raw = str(value).replace("+", "").replace("%", "")
        real = float(raw)
        is_percent = (type_.endswith("%") or str(value).endswith("%")) and display in WHOLE_STAT_TYPES
        return Stat(type=type_, displayType=display, value=real, isPercent=is_percent)

    @classmethod
    def deserialize_mod(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        primary = cls.deserialize_stat(raw.get("primaryBonusType", ""), raw.get("primaryBonusValue", "0"))
        secondaries = []
        for i in range(1, 5):
            t = raw.get(f"secondaryType_{i}")
            v = raw.get(f"secondaryValue_{i}")
            if t not in (None, "None") and v not in (None, ""):
                secondaries.append(cls.deserialize_stat(t, v))
        set_key = str(raw["set"]).lower().replace(" ", "")
        if set_key not in SET_BONUSES:
            raise OptimizerError(f"Unknown mod set: {raw['set']}")
        return {
            "id": raw["mod_uid"], "slot": str(raw["slot"]).lower(), "set": SET_BONUSES[set_key],
            "level": raw["level"], "pips": raw["pips"], "primaryStat": primary,
            "secondaryStats": secondaries, "characterID": raw.get("characterID"), "tier": raw.get("tier"),
        }

    @staticmethod
    def deserialize_target(target: Dict[str, Any]) -> Dict[str, Any]:
        updated = deepcopy(target)
        for stat, weight in STAT_WEIGHTS.items():
            if stat in updated:
                updated[stat] = updated[stat] / weight
        if not updated.get("targetStats"):
            if target.get("targetStat") is not None:
                updated["targetStats"] = [target["targetStat"]]
                updated.pop("targetStat", None)
            else:
                updated["targetStats"] = []
        updated["targetStats"] = [
            ts if "optimizeForTarget" in ts else {**ts, "optimizeForTarget": True}
            for ts in updated["targetStats"]
        ]
        # JS code assumes these exist when later accessed. Supplying defaults here
        # makes raw templates with omitted empty structures usable without changing
        # the semantics of structures that are explicitly present.
        updated.setdefault("primaryStatRestrictions", {})
        updated.setdefault("setRestrictions", {})
        updated.setdefault("useOnlyFullSets", False)
        updated.setdefault("upgradeMods", False)
        return updated

    # ------------------------------------------------------------------
    # Stat/mod calculations
    # ------------------------------------------------------------------
    def flatten_stat_values(self, stat: Stat, character: Dict[str, Any]) -> List[Dict[str, Any]]:
        key = f"{stat.displayType}{stat.isPercent}{stat.value}"
        if key in self.cache["statValues"]:
            return self.cache["statValues"][key]
        properties = STAT_TYPE_MAP.get(stat.displayType)
        if properties is None:
            raise OptimizerError(f"Unknown stat display type: {stat.displayType}")
        result = []
        for prop in properties:
            display = STAT_DISPLAY_NAMES[prop]
            if stat.isPercent and character.get("playerValues", {}).get("baseStats") is not None:
                base = character["playerValues"]["baseStats"].get(prop, 0)
                result.append({"displayType": display, "value": stat.value * base / 100})
            elif not stat.isPercent:
                result.append({"displayType": display, "value": stat.value})
            else:
                raise OptimizerError(f"Stat is given as a percentage, but {character['baseID']} has no base stats")
        self.cache["statValues"][key] = result
        return result

    def get_upgraded_mod(self, mod: Dict[str, Any], character: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        if mod["id"] in self.cache["modUpgrades"]:
            return self.cache["modUpgrades"][mod["id"]]
        working = dict(mod)
        if working["level"] < 15 and target.get("upgradeMods"):
            primary = working["primaryStat"]
            working["primaryStat"] = Stat(primary.type, primary.displayType,
                                            MAX_STAT_PRIMARIES[primary.displayType][working["pips"]], primary.isPercent)
            working["level"] = 15
        if working["level"] == 15 and working["pips"] == 5 and character.get("optimizerSettings", {}).get("sliceMods"):
            primary = working["primaryStat"]
            working["pips"] = 6
            working["primaryStat"] = Stat(primary.type, primary.displayType,
                                            MAX_STAT_PRIMARIES[primary.displayType][6], primary.isPercent)
            upgraded = []
            for stat in working["secondaryStats"]:
                stat_name = f"{stat.displayType} %" if stat.isPercent else stat.displayType
                value = stat.value + 1 if stat.displayType == "Speed" else SLICING_UPGRADE_FACTORS[stat_name] * stat.value
                upgraded.append(Stat(stat.type, stat.displayType, value, stat.isPercent))
            working["secondaryStats"] = upgraded
            working["tier"] = 1
        self.cache["modUpgrades"][mod["id"]] = working
        return working

    def get_flat_stats_from_mod(self, mod: Dict[str, Any], character: Dict[str, Any], target: Dict[str, Any]) -> List[Dict[str, Any]]:
        if mod["id"] in self.cache["modStats"]:
            return self.cache["modStats"][mod["id"]]
        working = self.get_upgraded_mod(mod, character, target)
        flat = self.flatten_stat_values(working["primaryStat"], character)
        for stat in working["secondaryStats"]:
            flat.extend(self.flatten_stat_values(stat, character))
        self.cache["modStats"][mod["id"]] = flat
        return flat

    def get_set_bonus_stats_from_mod_set(self, mod_set: Sequence[Dict[str, Any]], upgrade_mods: bool) -> List[Stat]:
        counts: Dict[str, Dict[str, Any]] = {}
        for mod in mod_set:
            sb = mod["set"]
            high = 1 if (upgrade_mods or mod["level"] == 15) else 0
            if sb.name not in counts:
                counts[sb.name] = {"setBonus": sb, "lowCount": 1, "highCount": high}
            else:
                counts[sb.name]["lowCount"] += 1
                counts[sb.name]["highCount"] += high
        result = []
        for c in counts.values():
            sb = c["setBonus"]
            max_count = c["highCount"] // sb.numberOfModsRequired
            small_count = (c["lowCount"] - max_count * sb.numberOfModsRequired) // sb.numberOfModsRequired
            result.extend([sb.maxBonus] * max_count)
            result.extend([sb.smallBonus] * small_count)
        return result

    def get_flat_stats_from_mod_set(self, mod_set: Sequence[Dict[str, Any]], character: Dict[str, Any], target: Dict[str, Any]) -> List[Dict[str, Any]]:
        flattened = []
        for stat in self.get_set_bonus_stats_from_mod_set(mod_set, bool(target.get("upgradeMods"))):
            flattened.extend(self.flatten_stat_values(stat, character))
        for mod in mod_set:
            flattened.extend(self.cache["modStats"][mod["id"]])
        combined: Dict[str, Dict[str, Any]] = {}
        for stat in flattened:
            if stat["displayType"] in combined:
                combined[stat["displayType"]] = {
                    "displayType": stat["displayType"],
                    "isPercent": stat.get("isPercent"),
                    "value": combined[stat["displayType"]]["value"] + stat["value"],
                }
            else:
                combined[stat["displayType"]] = dict(stat)
        result = list(combined.values())
        for stat in result:
            if stat["displayType"] in WHOLE_STAT_TYPES:
                stat["value"] = int(stat["value"])
        return result

    # ------------------------------------------------------------------
    # Restrictions/scoring
    # ------------------------------------------------------------------
    @staticmethod
    def are_sets_complete(defn: Dict[str, int]) -> bool:
        filled = sum(SET_BONUSES[name].numberOfModsRequired * count
                     for name, count in defn.items() if count != -1)
        return filled == 6

    @staticmethod
    def mod_set_fulfills_full_set_restriction(mod_set: Sequence[Dict[str, Any]]) -> bool:
        counts: Dict[str, int] = {}
        for mod in mod_set:
            counts[mod["set"].name] = counts.get(mod["set"].name, 0) + 1
        return all(count % SET_BONUSES[name].numberOfModsRequired == 0 for name, count in counts.items())

    @staticmethod
    def mod_set_fulfills_set_restriction(mod_set: Sequence[Dict[str, Any]], definition: Dict[str, int]) -> bool:
        counts: Dict[str, int] = {}
        for mod in mod_set:
            counts[mod["set"].name] = counts.get(mod["set"].name, 0) + 1
        for name, count in definition.items():
            full = counts.get(name, 0) // SET_BONUSES[name].numberOfModsRequired
            if count >= 0:
                if full < count:
                    return False
            elif full != 0:
                return False
        return True

    def get_stat_value_for_character_with_mods(self, mod_set: Sequence[Dict[str, Any]], character: Dict[str, Any], stat: str, target: Dict[str, Any]) -> float:
        if stat in STAT_TYPE_MAP and len(STAT_TYPE_MAP[stat]) > 1:
            raise OptimizerError("Trying to set an ambiguous target stat. Offense, Crit Chance, etc. need to be broken into physical or special.")
        equipped = character["playerValues"]["equippedStats"]
        if stat == "Health+Protection":
            base = equipped["health"] + equipped["protection"]
            target_stats = self.get_flat_stats_from_mod_set(mod_set, character, target)
            return base + sum(s["value"] for s in target_stats if s["displayType"] in ("Health", "Protection"))
        prop = STAT_TYPE_MAP[stat][0]
        base = equipped.get(prop, 0)
        set_stats = self.get_flat_stats_from_mod_set(mod_set, character, target)
        value = base + sum(s["value"] for s in set_stats if s["displayType"] == stat)
        if prop in ("armor", "resistance"):
            value = 100 * value / (character["playerValues"]["level"] * 7.5 + value)
        return value

    def mod_set_fulfills_target_stat_restriction(self, mod_set, character, target) -> bool:
        for ts in target.get("targetStats", []):
            value = self.get_stat_value_for_character_with_mods(mod_set, character, ts["stat"], target)
            if not (value <= ts["maximum"] and value >= ts["minimum"]):
                return False
        return True

    def mod_set_satisfies_character_restrictions(self, mod_set, character, target) -> bool:
        minimum = character["optimizerSettings"]["minimumModDots"]
        slots = {m["slot"]: m for m in mod_set}
        primary = target.get("primaryStatRestrictions", {})
        return (
            all(m["pips"] >= minimum for m in mod_set)
            and (not primary.get("arrow") or (slots.get("arrow") and slots["arrow"]["primaryStat"].type == primary["arrow"]))
            and (not primary.get("triangle") or (slots.get("triangle") and slots["triangle"]["primaryStat"].type == primary["triangle"]))
            and (not primary.get("circle") or (slots.get("circle") and slots["circle"]["primaryStat"].type == primary["circle"]))
            and (not primary.get("cross") or (slots.get("cross") and slots["cross"]["primaryStat"].type == primary["cross"]))
            and (not target.get("useOnlyFullSets") or self.mod_set_fulfills_full_set_restriction(mod_set))
            and self.mod_set_fulfills_set_restriction(mod_set, target.get("setRestrictions", {}))
            and self.mod_set_fulfills_target_stat_restriction(mod_set, character, target)
        )

    def score_stat(self, stat: Dict[str, Any] | Stat, target: Dict[str, Any]) -> float:
        display = stat.displayType if isinstance(stat, Stat) else stat["displayType"]
        value = stat.value if isinstance(stat, Stat) else stat["value"]
        props = ["critChance"] if display in ("Critical Chance", "Physical Critical Chance") else STAT_TYPE_MAP.get(display, [])
        return sum(target.get(p, 0) * value for p in props)

    def score_mod(self, mod, character, target) -> float:
        if mod["id"] in self.cache["modScores"]:
            return self.cache["modScores"][mod["id"]]
        score = sum(self.score_stat(s, target) for s in self.cache["modStats"][mod["id"]])
        self.cache["modScores"][mod["id"]] = score
        return score

    def score_mod_set(self, mod_set, character, target) -> float:
        return sum(self.score_stat(s, target) for s in self.get_flat_stats_from_mod_set(mod_set, character, target))

    # ------------------------------------------------------------------
    # Target transformations
    # ------------------------------------------------------------------
    def change_relative_target_stats_to_absolute(self, mod_suggestions, characters, locked_characters,
                                                   all_mods, target, character):
        old_stats = target.get("targetStats", [])
        result = deepcopy(target)
        new_stats = []
        for ts in old_stats:
            if not ts.get("relativeCharacterId"):
                new_stats.append(deepcopy(ts))
                continue
            rel_id = ts["relativeCharacterId"]
            relative_character = characters[rel_id]
            if rel_id in locked_characters:
                character_mods = [m for m in all_mods if m.get("characterID") == rel_id]
            else:
                entry = next((x for x in reversed([x for x in mod_suggestions if x is not None]) if x["id"] == rel_id), None)
                if entry is None:
                    raise OptimizerError(f"Could not find suggested mods for {rel_id}. Make sure they are selected above {character['baseID']}")
                character_mods = [next(m for m in all_mods if m["id"] == mid) for mid in entry["assignedMods"]]
            self.clear_cache()
            for m in character_mods:
                self.get_flat_stats_from_mod(m, relative_character, target)
            value = self.get_stat_value_for_character_with_mods(character_mods, relative_character, ts["stat"], target)
            if ts.get("type") == "%":
                minimum = value * ts["minimum"] / 100
                maximum = value * ts["maximum"] / 100
            else:
                minimum = value + ts["minimum"]
                maximum = value + ts["maximum"]
            new_stats.append({"minimum": minimum, "maximum": maximum, "stat": ts["stat"],
                              "relativeCharacterId": None, "type": None,
                              "optimizeForTarget": ts.get("optimizeForTarget")})
        result["targetStats"] = new_stats
        return result

    @staticmethod
    def combine_target_stats(target, character):
        mapped = {}
        for ts in target.get("targetStats", []):
            name = ts["stat"]
            if name not in mapped:
                mapped[name] = deepcopy(ts)
            else:
                mn = max(mapped[name]["minimum"], ts["minimum"])
                mx = min(mapped[name]["maximum"], ts["maximum"])
                if mn > mx:
                    raise OptimizerError(
                        f"The multiple {name} targets on {character['baseID']} don't have any solution. "
                        f"First Target: {mapped[name]['minimum']}-{mapped[name]['maximum']}. "
                        f"Second Target: {ts['minimum']}-{ts['maximum']}."
                    )
                mapped[name]["minimum"] = mn
                mapped[name]["maximum"] = mx
        result = deepcopy(target)
        result["targetStats"] = list(mapped.values())
        return result

    # ------------------------------------------------------------------
    # Candidate generation
    # ------------------------------------------------------------------
    @staticmethod
    def choose_from_array(items: Sequence[str], choices: int) -> List[List[str]]:
        return [list(c) for c in combinations(items, choices)]

    def filter_mods(self, base_mods, slot, min_dots, primary_stat):
        if primary_stat:
            full = [m for m in base_mods if m["slot"] == slot and m["pips"] >= min_dots and m["primaryStat"].type == primary_stat]
            if full:
                return {"mods": full, "messages": []}
        dots = [m for m in base_mods if m["slot"] == slot and m["pips"] >= min_dots]
        if dots:
            return {"mods": dots, "messages": ([f"No {primary_stat} {slot} mods were available, so the primary stat restriction was dropped."] if primary_stat else [])}
        slot_only = [m for m in base_mods if m["slot"] == slot]
        if slot_only:
            if primary_stat:
                msg = f"No {primary_stat} or {min_dots}-dot {slot} mods were available, so both restrictions were dropped."
            else:
                msg = f"No {min_dots}-dot {slot} mods were available, so the dots restriction was dropped."
            return {"mods": slot_only, "messages": [msg]}
        return {"mods": [], "messages": [f"No {slot} mods were available to use."]}

    def mod_sort_key(self, mod, character):
        # Python sort is stable, matching JS's stable modern Array.sort. Equal-score
        # ties are explicitly resolved by current ownership.
        return (-self.cache["modScores"][mod["id"]], 0 if mod.get("characterID") == character.get("baseID") else 1)

    @staticmethod
    def restrict_mods(all_mods, set_restriction):
        if Optimizer.are_sets_complete(set_restriction):
            potential = [name for name, count in set_restriction.items() if count > 0]
        else:
            potential = [s.name for s in SET_BONUSES.values()]
        return [m for m in all_mods if m["set"].name in potential]

    def loosen_restrictions(self, restrictions):
        result = [{"restriction": deepcopy(restrictions), "messages": []}]
        if restrictions:
            result.append({"restriction": {}, "messages": ["No mod sets could be found using the given sets, so the sets restriction was removed"]})
        return result

    def get_set_bonuses_that_have_value_for_stats(self, stats, character, restrictions):
        result = {}
        for sb in SET_BONUSES.values():
            if restrictions.get(sb.name) == -1:
                continue
            vals = self.flatten_stat_values(sb.maxBonus, character)
            for stat in stats:
                found = next((x for x in vals if x["displayType"] == stat), None)
                if found:
                    value = floor(found["value"]) if sb.name in ("health", "defense", "offense", "speed") else found["value"]
                    result[stat] = {"set": sb, "value": value}
        return result

    def get_stat_values_for_character(self, character, stats):
        result = {}
        for stat in stats:
            props = STAT_TYPE_MAP.get(stat)
            if stat == "Health+Protection":
                raise OptimizerError("Cannot optimize Health+Protection. Use as Report Only.")
            if props is None:
                raise OptimizerError(f"Unknown target stat: {stat}")
            if len(props) > 1:
                raise OptimizerError("Trying to set an ambiguous target stat. Offense, Crit Chance, etc. need to be broken into physical or special.")
            result[stat] = character["playerValues"]["equippedStats"].get(props[0], 0)
        return result

    def filter_out_unusable_mods(self, mods, target, slots_open, minimum_dots):
        mods_in_sets = mods if slots_open > 0 else [m for m in mods if m["set"].name in target.get("setRestrictions", {})]
        primary = target.get("primaryStatRestrictions", {})
        return [m for m in mods_in_sets if (not primary.get(m["slot"]) or m["primaryStat"].type == primary[m["slot"]]) and m["pips"] >= minimum_dots]

    def collect_mod_values_by_slot(self, mods, stats):
        mod_values = {s: {} for s in stats}
        values_by_slot = {s: {slot: {0} for slot in MOD_SLOTS} for s in stats}
        for mod in mods:
            combined = {}
            for st in self.cache["modStats"][mod["id"]]:
                if st["displayType"] in combined:
                    combined[st["displayType"]] += st["value"]
                else:
                    combined[st["displayType"]] = st["value"]
            for stat in stats:
                value = combined.get(stat, 0)
                mod_values[stat][mod["id"]] = value
                values_by_slot[stat][mod["slot"]].add(value)
        return mod_values, values_by_slot

    def find_stat_values_that_meet_target(self, values_by_slot, target_min, target_max, progress_min, progress_max, character):
        slots = MOD_SLOTS
        result = []
        ranges = [values_by_slot[s] for s in slots]
        for vals in self._cartesian(ranges):
            total = sum(vals)
            if target_min <= total <= target_max:
                result.append(dict(zip(slots, vals)))
        return result

    @staticmethod
    def _cartesian(sequences):
        if not sequences:
            yield ()
            return
        def rec(i, cur):
            if i == len(sequences):
                yield tuple(cur)
                return
            for v in sequences[i]:
                cur.append(v)
                yield from rec(i + 1, cur)
                cur.pop()
        yield from rec(0, [])

    def get_potential_mods_to_satisfy_target_stats(self, all_mods, character, target):
        restrictions = target.get("setRestrictions", {})
        target_stats = list(target.get("targetStats", []))
        stat_names = [x["stat"] for x in target_stats]
        set_values = self.get_set_bonuses_that_have_value_for_stats(stat_names, character, restrictions)
        character_values = self.get_stat_values_for_character(character, stat_names)
        total_open = 6 - sum(SET_BONUSES[name].numberOfModsRequired * count
                             for name, count in restrictions.items() if count != -1)
        usable = self.filter_out_unusable_mods(all_mods, target, total_open, character["optimizerSettings"]["minimumModDots"])
        mod_values, values_by_slot = self.collect_mod_values_by_slot(usable, stat_names)
        configurations = {}
        for ts in target_stats:
            name = ts["stat"]
            sv = set_values.get(name)
            configurations[name] = {}
            if sv:
                min_sets = restrictions.get(sv["set"].name, 0)
                max_sets = min_sets + (total_open // sv["set"].numberOfModsRequired)
                for n in range(min_sets, max_sets + 1):
                    non_mod = character_values[name] + sv["value"] * n
                    configurations[name][n] = self.find_stat_values_that_meet_target(
                        values_by_slot[name], ts["minimum"] - non_mod, ts["maximum"] - non_mod, 0, 100, character)
            else:
                configurations[name][0] = self.find_stat_values_that_meet_target(
                    values_by_slot[name], ts["minimum"] - character_values[name], ts["maximum"] - character_values[name], 0, 100, character)

        def rec(mods, set_restrictions, remaining):
            if not remaining:
                if len(mods) >= 6:
                    yield (mods, set_restrictions)
                return
            current = remaining[-1]
            rest = remaining[:-1]
            name = current["stat"]
            sv = set_values.get(name)
            if sv:
                open_slots = 6 - sum(SET_BONUSES[n].numberOfModsRequired * c
                                     for n, c in set_restrictions.items() if c != -1)
                min_sets = set_restrictions.get(sv["set"].name, 0)
                max_sets = min_sets + (open_slots // sv["set"].numberOfModsRequired)
                for n in range(min_sets, max_sets + 1):
                    updated = dict(set_restrictions)
                    updated[sv["set"].name] = -1 if n == 0 else n
                    for pv in configurations[name][n]:
                        fitting = [m for m in mods if mod_values[name][m["id"]] == pv[m["slot"]]]
                        yield from rec(fitting, updated, rest)
            else:
                for pv in configurations[name][0]:
                    fitting = [m for m in mods if mod_values[name][m["id"]] == pv[m["slot"]]]
                    yield from rec(fitting, set_restrictions, rest)
        return rec(all_mods, dict(restrictions), target_stats)

    # ------------------------------------------------------------------
    # Set candidate search
    # ------------------------------------------------------------------
    def find_best_mod_set_from_potential_mods(self, potential_mod_sets, character, target):
        best = {"modSet": [], "messages": []}
        best_score = -inf
        best_unmoved = 0
        for mods, candidate_restrictions in potential_mod_sets:
            current = self.find_best_mod_set_without_changing_restrictions(mods, character, target, candidate_restrictions)
            if current["modSet"] is None:
                continue
            score = self.score_mod_set(current["modSet"], character, target)
            if (not self.mod_set_satisfies_character_restrictions(current["modSet"], character, target)
                    and best["modSet"] and self.mod_set_satisfies_character_restrictions(best["modSet"], character, target)):
                continue
            if score > best_score or (score > 0 and not self.mod_set_satisfies_character_restrictions(best["modSet"], character, target)
                                      and self.mod_set_satisfies_character_restrictions(current["modSet"], character, target)):
                best, best_score, best_unmoved = current, score, None
            elif score == best_score:
                unmoved = sum(m.get("characterID") == character.get("baseID") for m in current["modSet"])
                if best_unmoved is None:
                    best_unmoved = sum(m.get("characterID") == character.get("baseID") for m in best["modSet"])
                if unmoved > best_unmoved or (unmoved == best_unmoved and len(current["modSet"]) > len(best["modSet"])):
                    best, best_unmoved = current, unmoved
        return best

    def find_best_mod_set_by_loosening_set_restrictions(self, usable, character, target, restrictions):
        for option in self.loosen_restrictions(restrictions):
            restricted = self.restrict_mods(usable, option["restriction"])
            result = self.find_best_mod_set_without_changing_restrictions(restricted, character, target, option["restriction"])
            if result["modSet"] is not None:
                return {"modSet": result["modSet"], "messages": option["messages"] + result["messages"]}
        return {"modSet": [], "messages": [f"No mod sets could be found for {character['baseID']}"]}

    def find_best_mod_set_for_character(self, mods, character, target):
        if character["playerValues"]["gearLevel"] < 12:
            mods_to_cache = [m for m in mods if m["pips"] < 6 or m.get("characterID") == character["baseID"]]
            usable = list(mods_to_cache)
        else:
            mods_to_cache = list(mods)
            usable = list(mods)
        restrictions = target.get("setRestrictions", {})
        target_stats = target.get("targetStats", [])
        self.clear_cache()
        for mod in mods_to_cache:
            self.get_flat_stats_from_mod(mod, character, target)
            self.score_mod(mod, character, target)
        mutable = deepcopy(target)
        extra = []
        if target_stats:
            potentials = list(self.get_potential_mods_to_satisfy_target_stats(usable, character, mutable))
            found = self.find_best_mod_set_from_potential_mods(potentials, character, mutable)
            if not found["modSet"]:
                reduced = dict(mutable)
                if mutable.get("useOnlyFullSets"):
                    reduced["useOnlyFullSets"] = False
                    extra.append("Could not fill the target stat with full sets, so the full sets restriction was dropped")
                    potentials = list(self.get_potential_mods_to_satisfy_target_stats(usable, character, mutable))
                    found = self.find_best_mod_set_from_potential_mods(potentials, character, reduced)
            if not found["modSet"]:
                found = self.find_best_mod_set_by_loosening_set_restrictions(usable, character, reduced if 'reduced' in locals() else mutable, restrictions)
                extra.append("Could not fill the target stats as given, so the target stat restriction was dropped")
            if found["modSet"]:
                return {"modSet": found["modSet"], "messages": found["messages"] + extra}
            extra = ["Could not fulfill the target stat as given, so the target stat restriction was dropped"]
            mutable.pop("targetStat", None)
        self.progress(character, "Finding the best mod set")
        found = self.find_best_mod_set_by_loosening_set_restrictions(usable, character, mutable, restrictions)
        if not found["modSet"] and mutable.get("useOnlyFullSets"):
            reduced = dict(mutable); reduced["useOnlyFullSets"] = False
            extra.append("Could not find a mod set using only full sets, so the full sets restriction was dropped")
            found = self.find_best_mod_set_by_loosening_set_restrictions(usable, character, reduced, restrictions)
        return {"modSet": found["modSet"], "messages": found["messages"] + extra}

    def find_best_mod_set_without_changing_restrictions(self, usable, character, target, sets_to_use):
        messages = []
        usable = sorted(list(usable), key=lambda m: self.mod_sort_key(m, character))
        slot_lists = {}
        for slot in MOD_SLOTS:
            r = self.filter_mods(usable, slot, character["optimizerSettings"]["minimumModDots"], target.get("primaryStatRestrictions", {}).get(slot))
            slot_lists[slot] = r["mods"]
            messages.extend(r["messages"])
        squares, arrows, diamonds = slot_lists["square"], slot_lists["arrow"], slot_lists["diamond"]
        triangles, circles, crosses = slot_lists["triangle"], slot_lists["circle"], slot_lists["cross"]
        if all(len(slot_lists[s]) == 1 for s in MOD_SLOTS):
            ms = [slot_lists[s][0] for s in MOD_SLOTS]
            if self.mod_set_fulfills_set_restriction(ms, sets_to_use):
                return {"modSet": ms, "messages": messages}
            return {"modSet": None, "messages": []}

        def top(cands):
            return cands[0] if cands and self.cache["modScores"][cands[0]["id"]] >= 0 else None
        used_sets = [name for name, count in sets_to_use.items() if count > 0]
        open_slots = 6 - sum(SET_BONUSES[name].numberOfModsRequired * count for name, count in sets_to_use.items() if count != -1)
        potential = set()
        setless = None
        if open_slots == 0:
            potential.update(used_sets); setless = None
        elif target.get("useOnlyFullSets"):
            potential.update(SET_BONUSES.keys()); setless = None
        else:
            for sb in SET_BONUSES.values():
                if sb.numberOfModsRequired <= open_slots and self.score_stat(sb.maxBonus, target) > 0:
                    potential.add(sb.name)
            potential.update(used_sets)
            setless = {s: top(slot_lists[s]) for s in MOD_SLOTS}
        base_sets = {}
        for name in potential:
            base_sets[name] = {s: next((m for m in slot_lists[s] if m["set"].name == name), None) for s in MOD_SLOTS}
        best = None; best_score = -inf; best_unmoved = None
        for candidate in self.get_candidate_sets_generator(potential, base_sets, setless, sets_to_use):
            score = self.score_mod_set(candidate, character, target)
            if score > best_score:
                best, best_score, best_unmoved = candidate, score, None
            elif score == best_score and best is not None:
                unmoved = sum(m.get("characterID") == character.get("baseID") for m in candidate)
                if best_unmoved is None:
                    best_unmoved = sum(m.get("characterID") == character.get("baseID") for m in best)
                if unmoved > best_unmoved or (unmoved == best_unmoved and len(candidate) > len(best)):
                    best, best_unmoved = candidate, unmoved
        return {"modSet": best, "messages": messages}

    def get_candidate_sets_generator(self, potential_used_sets, base_sets, setless_mods, sets_to_use):
        potential = list(potential_used_sets)
        four = [n for n in potential if SET_BONUSES[n].numberOfModsRequired == 4]
        two = [n for n in potential if SET_BONUSES[n].numberOfModsRequired == 2]
        forced = {4: [], 2: []}
        for name, count in sets_to_use.items():
            for _ in range(count):
                forced[SET_BONUSES[name].numberOfModsRequired].append(name)
        set_object = {}
        def to_array():
            return [set_object[s] for s in MOD_SLOTS if s in set_object and set_object[s] is not None]
        def combine(first, second, third=None, allow_first_null=False, allow_second_null=False):
            if not first or not second:
                return
            if third is None:
                for first_slots in combinations(MOD_SLOTS, 4):
                    first_slots = list(first_slots); second_slots = [s for s in MOD_SLOTS if s not in first_slots]
                    if any(first.get(s) is None and not allow_first_null for s in first_slots): continue
                    if any(second.get(s) is None and not allow_second_null for s in second_slots): continue
                    for s in first_slots: set_object[s] = first.get(s)
                    for s in second_slots: set_object[s] = second.get(s)
                    yield to_array()
            else:
                for first_slots in combinations(MOD_SLOTS, 2):
                    rem = [s for s in MOD_SLOTS if s not in first_slots]
                    for second_slots in combinations(rem, 2):
                        third_slots = [s for s in rem if s not in second_slots]
                        if any(first.get(s) is None and not allow_first_null for s in first_slots): continue
                        if any(second.get(s) is None and not allow_second_null for s in second_slots): continue
                        if any(third.get(s) is None for s in third_slots): continue
                        for s in first_slots: set_object[s] = first.get(s)
                        for s in second_slots: set_object[s] = second.get(s)
                        for s in third_slots: set_object[s] = third.get(s)
                        yield to_array()
        if forced[4]:
            first = base_sets[forced[4][0]]
            if forced[2]:
                yield from combine(first, base_sets[forced[2][0]])
            else:
                yield from combine(first, setless_mods, None, False, True)
                for typ in two:
                    yield from combine(first, base_sets[typ])
        elif len(forced[2]) == 1:
            first = base_sets[forced[2][0]]
            yield from combine(setless_mods, first, None, True)
            for i in range(len(two)):
                second = base_sets[two[i]]
                yield from combine(setless_mods, first, second, True)
                for j in range(i, len(two)):
                    yield from combine(first, second, base_sets[two[j]])
        elif len(forced[2]) == 2:
            first, second = base_sets[forced[2][0]], base_sets[forced[2][1]]
            yield from combine(setless_mods, first, second, True)
            for typ in two:
                yield from combine(first, second, base_sets[typ])
        elif len(forced[2]) == 3:
            yield from combine(base_sets[forced[2][0]], base_sets[forced[2][1]], base_sets[forced[2][2]])
        else:
            if setless_mods:
                set_object.clear(); set_object.update({s: setless_mods[s] for s in MOD_SLOTS}); yield to_array()
            for typ in four:
                first = base_sets[typ]
                yield from combine(first, setless_mods, None, False, True)
                for typ2 in two:
                    yield from combine(first, base_sets[typ2])
            for i, typ1 in enumerate(two):
                first = base_sets[typ1]
                yield from combine(setless_mods, first, None, True)
                for j in range(i, len(two)):
                    second = base_sets[two[j]]
                    yield from combine(setless_mods, first, second, True)
                    for k in range(j, len(two)):
                        yield from combine(first, second, base_sets[two[k]])

    # ------------------------------------------------------------------
    # Top-level optimizeMods
    # ------------------------------------------------------------------
    @staticmethod
    def objects_equivalent(a, b) -> bool:
        # JS compares own properties recursively. Dict/list ordering is not relevant
        # to semantic JSON objects, but all keys and values must match.
        if a is None or b is None:
            return a is b
        if isinstance(a, dict) and isinstance(b, dict):
            return set(a.keys()) == set(b.keys()) and all(Optimizer.objects_equivalent(a[k], b[k]) for k in a)
        if isinstance(a, list) and isinstance(b, list):
            return len(a) == len(b) and all(Optimizer.objects_equivalent(x, y) for x, y in zip(a, b))
        return a == b

    def get_missed_goals(self, mod_set, character, goals, target):
        missed = []
        for goal in goals:
            value = self.get_stat_value_for_character_with_mods(mod_set, character, goal["stat"], target)
            if value < goal["minimum"] or value > goal["maximum"]:
                missed.append([goal, value])
        return missed

    def optimize_mods(self, available_mods, characters, order, incremental_optimize_index,
                      global_settings, previous_run=None):
        previous_run = previous_run or {}
        previous_mods = previous_run.get("mods", [])
        recalc = (
            not previous_run.get("globalSettings") or
            global_settings.get("modChangeThreshold") != previous_run.get("globalSettings", {}).get("modChangeThreshold") or
            global_settings.get("lockUnselectedCharacters") != previous_run.get("globalSettings", {}).get("lockUnselectedCharacters") or
            global_settings.get("forceCompleteSets") != previous_run.get("globalSettings", {}).get("forceCompleteSets") or
            len(available_mods) != len(previous_mods)
        )
        if not recalc:
            for cid, char in characters.items():
                prev = previous_run.get("characters", {}).get(cid)
                if not prev or prev.get("optimizerSettings", {}).get("isLocked") != char.get("optimizerSettings", {}).get("isLocked"):
                    recalc = True; break
        usable = [m for m in available_mods if not m.get("characterID") or not characters[m["characterID"]]["optimizerSettings"]["isLocked"]]
        if global_settings.get("lockUnselectedCharacters"):
            selected_ids = [x["id"] for x in order]
            usable = [m for m in usable if not m.get("characterID") or m["characterID"] in selected_ids]
        selected_ids = [x["id"] for x in order]
        unselected = [cid for cid in characters if cid not in selected_ids]
        locked = [cid for cid, c in characters.items() if c["optimizerSettings"]["isLocked"]]
        if global_settings.get("lockUnselectedCharacters"):
            locked += unselected
        end = incremental_optimize_index + 1 if incremental_optimize_index is not None else len(order)
        results = []
        for index, item in enumerate(order[:end]):
            cid, target = item["id"], deepcopy(item["target"])
            character = characters[cid]
            previous_char = previous_run.get("characters", {}).get(cid)
            if character["optimizerSettings"]["isLocked"]:
                results.append(None); continue
            can_reuse = (
                not recalc and previous_run.get("selectedCharacters") and index < len(previous_run["selectedCharacters"]) and
                cid == previous_run["selectedCharacters"][index].get("id") and previous_char and
                self.objects_equivalent(character.get("playerValues"), previous_char.get("playerValues")) and
                self.objects_equivalent(target, previous_run["selectedCharacters"][index].get("target")) and
                character["optimizerSettings"].get("minimumModDots") == previous_char.get("optimizerSettings", {}).get("minimumModDots") and
                character["optimizerSettings"].get("sliceMods") == previous_char.get("optimizerSettings", {}).get("sliceMods") and
                character["optimizerSettings"].get("isLocked") == previous_char.get("optimizerSettings", {}).get("isLocked") and
                previous_run.get("modAssignments", []) and index < len(previous_run["modAssignments"]) and
                previous_run["modAssignments"][index]
            )
            if can_reuse:
                assignment = previous_run["modAssignments"][index]
                assigned = list(assignment.get("assignedMods", [])); messages = assignment.get("messages", []); missed = assignment.get("missedGoals", [])
                usable = [m for m in usable if m["id"] not in assigned]
                results.append({"id": cid, "target": target, "assignedMods": assigned, "messages": messages, "missedGoals": missed})
                continue
            recalc = True
            if global_settings.get("forceCompleteSets"):
                target["useOnlyFullSets"] = True
            absolute = self.change_relative_target_stats_to_absolute(results, characters, locked, available_mods, target, character)
            goals = [ts for ts in absolute.get("targetStats", []) if not ts.get("optimizeForTarget")]
            filtered = deepcopy(absolute)
            filtered["targetStats"] = [ts for ts in absolute.get("targetStats", []) if ts.get("optimizeForTarget")]
            real_target = self.combine_target_stats(filtered, character)
            found = self.find_best_mod_set_for_character(usable, character, real_target)
            new_set = found["modSet"]
            old_set = [m for m in usable if m.get("characterID") == character["baseID"]]
            new_value = self.score_mod_set(new_set, character, real_target)
            old_value = self.score_mod_set(old_set, character, real_target)
            assignment_messages = []
            threshold = global_settings.get("modChangeThreshold", 0)
            same = len(new_set) == len(old_set) and all(any(n["id"] == o["id"] for n in new_set) for o in old_set)
            old_bad = not self.mod_set_satisfies_character_restrictions(old_set, character, real_target)
            new_good = self.mod_set_satisfies_character_restrictions(new_set, character, real_target)
            ratio_better = ((new_value / old_value) * 100 - 100 > threshold) if old_value != 0 else (new_value > old_value)
            should_change = (
                (threshold == 0 and new_value >= old_value) or same or (old_bad and new_good) or ratio_better or
                (len(old_set) < 6 and len(new_set) > len(old_set))
            )
            if should_change:
                assigned_set = new_set; assignment_messages = found["messages"]
            else:
                assigned_set = old_set
                if not new_good:
                    assignment_messages.append("Could not find a new mod set that satisfies the given restrictions. Leaving the old mods equipped.")
            assigned_ids = [m["id"] for m in assigned_set]
            usable = [m for m in usable if m["id"] not in assigned_ids]
            results.append({"id": cid, "target": target, "assignedMods": assigned_ids,
                            "messages": assignment_messages,
                            "missedGoals": self.get_missed_goals(assigned_set, character, goals, target)})
        self.clear_cache()
        return results


def profile_from_my_progress(
        my_progress: Dict[str, Any], 
        ally_code: Optional[str] = None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:

    #Check if the provided allyCode is usable
    if not "profiles" in my_progress:
        raise KeyError(f"Incorrect file format")

    list_allyCodes = [p["allyCode"] for p in my_progress["profiles"]]
    if ally_code is None and len(list_allyCodes)==1:
        ally_code = list_allyCodes[0]
    elif ally_code is None:
        raise KeyError(f"Several profiles found {str(list_allyCodes)}, please provide allyCode")

    #Get associated profile
    my_profile = None
    for profile in my_progress.get("profiles", []):
        if str(profile.get("allyCode")) == str(ally_code):
            my_profile = profile

    if my_profile is None:
        raise KeyError(f"Profile {ally_code} not found")

    #Get last run
    my_previous_run = None
    for previous_run in my_progress.get("lastRuns", []):
        if str(previous_run.get("allyCode")) == str(ally_code):
            my_previous_run = previous_run

    return my_profile, my_previous_run

def build_order_from_template(template: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [{"id": x["id"], "target": Optimizer.deserialize_target(x["target"])}
            for x in template.get("selectedCharacters", [])]


def optimize_mods_from_profile(profile: Dict[str, Any], template: Optional[Dict[str, Any]] = None,
                               previous_run: Optional[Dict[str, Any]] = None,
                               progress_callback: ProgressCallback = None) -> List[Dict[str, Any]]:
    """Run the Python port using a myProgress profile.

    If template is supplied, its selectedCharacters are used as the optimization
    order/targets. Otherwise profile.selectedCharacters are used, matching the JS
    worker input path.
    """
    opt = Optimizer(progress_callback)
    available_mods = [opt.deserialize_mod(m) for m in profile.get("mods", [])]
    characters = {}
    for c in profile.get("characters", {}).values():
        c = deepcopy(c)
        c.setdefault("optimizerSettings", {})
        c["optimizerSettings"].pop("target", None)
        characters[c["baseID"]] = c
    raw_order = template.get("selectedCharacters", []) if template is not None else profile.get("selectedCharacters", [])
    order = [{"id": x["id"], "target": opt.deserialize_target(x["target"])} for x in raw_order]
    previous = deepcopy(previous_run) if previous_run is not None else {}
    if previous:
        previous["modAssignments"] = deepcopy(profile.get("modAssignments", previous.get("modAssignments", [])))
        if isinstance(previous.get("selectedCharacters"), list):
            previous["selectedCharacters"] = [{"id": x["id"], "target": opt.deserialize_target(x["target"])} for x in previous["selectedCharacters"]]
    return opt.optimize_mods(available_mods, characters, order,
                             profile.get("incrementalOptimizeIndex"),
                             profile.get("globalSettings", {}), previous)


__all__ = [
    "Optimizer", "OptimizerError", "Stat", "SetBonus", "SET_BONUSES",
    "optimize_mods_from_profile", "profile_from_my_progress", "build_order_from_template",
]


# =============================================================================
# FAST OPTIMIZER
# =============================================================================
# Performance-oriented implementation layered on top of the behavioral port
# above. The public API remains compatible with the original module.
#
# Main optimizations:
#   * cache compact per-mod numeric stat maps instead of rebuilding stat lists
#   * score a candidate set additively (mods + set bonuses)
#   * evaluate target-stat restrictions from numeric maps
#   * build all six slot candidate lists in one pass
#   * avoid repeated scans for the common scoring path
#
# The original Optimizer implementation remains available as BaseOptimizer for
# comparison/debugging.

BaseOptimizer = Optimizer


class FastOptimizer(BaseOptimizer):
    """Performance-oriented drop-in replacement for Optimizer."""

    def clear_cache(self):
        super().clear_cache()
        self.cache["fastModValues"] = {}
        self.cache["fastModScores"] = {}
        self.cache["fastSetValues"] = {}
        self.cache["modScores"] = {}
        self._active_target = {}

    # ------------------------------------------------------------------
    # Compact numeric representation
    # ------------------------------------------------------------------
    def _ensure_fast_mod(self, mod, character, target):
        mid = mod["id"]
        values = self.cache["fastModValues"].get(mid)
        if values is not None:
            return values

        # Calling the original implementation once preserves all upgrade,
        # slicing and percentage-to-flat-stat behavior.
        flat = BaseOptimizer.get_flat_stats_from_mod(self, mod, character, target)

        combined = {}
        for st in flat:
            name = st["displayType"]
            combined[name] = combined.get(name, 0.0) + st["value"]

        # The original get_flat_stats_from_mod_set truncates whole stats only
        # after combining the complete set. Keep floats here and perform that
        # truncation at set-evaluation time.
        self.cache["fastModValues"][mid] = combined
        return combined

    def _score_values(self, values, target):
        score = 0.0
        for display, value in values.items():
            if display in ("Critical Chance", "Physical Critical Chance"):
                score += target.get("critChance", 0) * value
            else:
                for prop in STAT_TYPE_MAP.get(display, ()):
                    score += target.get(prop, 0) * value
        return score

    def _ensure_fast_mod_score(self, mod, character, target):
        mid = mod["id"]
        scores = self.cache["fastModScores"]
        if mid not in scores:
            scores[mid] = self._score_values(
                self._ensure_fast_mod(mod, character, target), target
            )
        return scores[mid]

    def _set_bonus_values(self, mod_set, character, target):
        """Return combined flattened set-bonus values only."""
        # Build a compact signature. Candidate sets contain at most six mods.
        counts = {}
        upgrade_mods = bool(target.get("upgradeMods"))
        for mod in mod_set:
            name = mod["set"].name
            if name not in counts:
                counts[name] = [mod["set"], 1, 1 if (upgrade_mods or mod["level"] == 15) else 0]
            else:
                counts[name][1] += 1
                counts[name][2] += 1 if (upgrade_mods or mod["level"] == 15) else 0

        result = {}
        for sb, low_count, high_count in counts.values():
            max_count = high_count // sb.numberOfModsRequired
            small_count = (
                (low_count - max_count * sb.numberOfModsRequired)
                // sb.numberOfModsRequired
            )

            for stat, count in ((sb.maxBonus, max_count), (sb.smallBonus, small_count)):
                if count <= 0:
                    continue
                for flat in self.flatten_stat_values(stat, character):
                    name = flat["displayType"]
                    result[name] = result.get(name, 0.0) + flat["value"] * count

        # Match get_flat_stats_from_mod_set(): whole stats are integer values.
        for name in tuple(result):
            if name in WHOLE_STAT_TYPES:
                result[name] = int(result[name])
        return result

    def _get_fast_set_values(self, mod_set, character, target):
        # Candidate sets are tiny, so a tuple of mod ids is a cheap key.
        key = (
            tuple(m["id"] for m in mod_set),
            bool(target.get("upgradeMods")),
            id(character),
        )
        cached = self.cache["fastSetValues"].get(key)
        if cached is not None:
            return cached

        values = self._set_bonus_values(mod_set, character, target)
        self.cache["fastSetValues"][key] = values
        return values

    def _combined_set_values(self, mod_set, character, target):
        combined = {}
        for mod in mod_set:
            values = self._ensure_fast_mod(mod, character, target)
            for name, value in values.items():
                combined[name] = combined.get(name, 0.0) + value

        bonus = self._get_fast_set_values(mod_set, character, target)
        for name, value in bonus.items():
            combined[name] = combined.get(name, 0.0) + value

        # Match original integer conversion after all components are combined.
        for name in tuple(combined):
            if name in WHOLE_STAT_TYPES:
                combined[name] = int(combined[name])
        return combined

    # ------------------------------------------------------------------
    # Fast scoring
    # ------------------------------------------------------------------
    def score_mod(self, mod, character, target) -> float:
        score = self._ensure_fast_mod_score(mod, character, target)
        # Some inherited candidate-generation code still reads the legacy
        # modScores cache. Keep it populated for compatibility.
        self.cache["modScores"][mod["id"]] = score
        return score

    def mod_sort_key(self, mod, character):
        # The original implementation assumes modScores was populated before
        # sorting. The fast path scores lazily, so make sorting self-contained.
        target = getattr(self, "_active_target", {})
        score = self._ensure_fast_mod_score(mod, character, target)
        self.cache["modScores"][mod["id"]] = score
        return (
            -score,
            0 if mod.get("characterID") == character.get("baseID") else 1,
        )

    def score_mod_set(self, mod_set, character, target) -> float:
        if not mod_set:
            return 0.0

        score = 0.0
        for mod in mod_set:
            score += self._ensure_fast_mod_score(mod, character, target)

        # Set bonuses are generally much cheaper to score directly than
        # rebuilding the complete flattened set.
        bonus = self._get_fast_set_values(mod_set, character, target)
        score += self._score_values(bonus, target)
        return score

    # ------------------------------------------------------------------
    # Fast target-stat evaluation
    # ------------------------------------------------------------------
    def get_stat_value_for_character_with_mods(self, mod_set, character, stat, target):
        if stat in STAT_TYPE_MAP and len(STAT_TYPE_MAP[stat]) > 1:
            raise OptimizerError(
                "Trying to set an ambiguous target stat. Offense, Crit Chance, etc. "
                "need to be broken into physical or special."
            )

        equipped = character["playerValues"]["equippedStats"]

        if stat == "Health+Protection":
            base = equipped["health"] + equipped["protection"]
            values = self._combined_set_values(mod_set, character, target)
            return base + values.get("Health", 0) + values.get("Protection", 0)

        prop = STAT_TYPE_MAP[stat][0]
        base = equipped.get(prop, 0)
        values = self._combined_set_values(mod_set, character, target)
        value = base + values.get(stat, 0)

        if prop in ("armor", "resistance"):
            value = 100 * value / (character["playerValues"]["level"] * 7.5 + value)
        return value

    def mod_set_fulfills_target_stat_restriction(self, mod_set, character, target) -> bool:
        target_stats = target.get("targetStats", [])
        if not target_stats:
            return True

        values = self._combined_set_values(mod_set, character, target)
        equipped = character["playerValues"]["equippedStats"]
        level = character["playerValues"]["level"]

        for ts in target_stats:
            stat = ts["stat"]

            if stat in STAT_TYPE_MAP and len(STAT_TYPE_MAP[stat]) > 1:
                raise OptimizerError(
                    "Trying to set an ambiguous target stat. Offense, Crit Chance, etc. "
                    "need to be broken into physical or special."
                )

            if stat == "Health+Protection":
                value = (
                    equipped["health"] + equipped["protection"]
                    + values.get("Health", 0)
                    + values.get("Protection", 0)
                )
            else:
                prop = STAT_TYPE_MAP[stat][0]
                value = equipped.get(prop, 0) + values.get(stat, 0)
                if prop in ("armor", "resistance"):
                    value = 100 * value / (level * 7.5 + value)

            if value < ts["minimum"] or value > ts["maximum"]:
                return False

        return True

    # ------------------------------------------------------------------
    # Fast six-slot filtering
    # ------------------------------------------------------------------
    def _filter_slot_lists(self, usable, character, target):
        minimum = character["optimizerSettings"]["minimumModDots"]
        primary = target.get("primaryStatRestrictions", {})

        all_lists = {slot: [] for slot in MOD_SLOTS}
        dot_lists = {slot: [] for slot in MOD_SLOTS}
        primary_lists = {slot: [] for slot in MOD_SLOTS}

        for mod in usable:
            slot = mod["slot"]
            all_lists[slot].append(mod)
            if mod["pips"] >= minimum:
                dot_lists[slot].append(mod)
                req = primary.get(slot)
                if req and mod["primaryStat"].type == req:
                    primary_lists[slot].append(mod)

        result = {}
        messages = []

        for slot in MOD_SLOTS:
            req = primary.get(slot)
            if req and primary_lists[slot]:
                result[slot] = primary_lists[slot]
            elif dot_lists[slot]:
                result[slot] = dot_lists[slot]
                if req:
                    messages.append(
                        f"No {req} {slot} mods were available, so the primary stat restriction was dropped."
                    )
            elif all_lists[slot]:
                result[slot] = all_lists[slot]
                if req:
                    messages.append(
                        f"No {req} or {minimum}-dot {slot} mods were available, so both restrictions were dropped."
                    )
                else:
                    messages.append(
                        f"No {minimum}-dot {slot} mods were available, so the dots restriction was dropped."
                    )
            else:
                result[slot] = []
                messages.append(f"No {slot} mods were available to use.")

        return result, messages

    def find_best_mod_set_without_changing_restrictions(
        self, usable, character, target, sets_to_use
    ):
        messages = []

        # The original method sorts once by score/ownership before filtering.
        # Store the target used by this search because mod_sort_key is called
        # by Python's sort callback and therefore receives no target argument.
        self._active_target = target
        usable = sorted(usable, key=lambda m: self.mod_sort_key(m, character))
        slot_lists, filter_messages = self._filter_slot_lists(usable, character, target)
        messages.extend(filter_messages)

        if all(len(slot_lists[s]) == 1 for s in MOD_SLOTS):
            ms = [slot_lists[s][0] for s in MOD_SLOTS]
            if self.mod_set_fulfills_set_restriction(ms, sets_to_use):
                return {"modSet": ms, "messages": messages}
            return {"modSet": None, "messages": []}

        def top(cands):
            if not cands:
                return None
            m = cands[0]
            return m if self.cache["fastModScores"].get(m["id"], 0.0) >= 0 else None

        used_sets = [name for name, count in sets_to_use.items() if count > 0]
        open_slots = 6 - sum(
            SET_BONUSES[name].numberOfModsRequired * count
            for name, count in sets_to_use.items()
            if count != -1
        )

        potential = set()
        setless = None

        if open_slots == 0:
            potential.update(used_sets)
        elif target.get("useOnlyFullSets"):
            potential.update(SET_BONUSES.keys())
        else:
            for sb in SET_BONUSES.values():
                if (
                    sb.numberOfModsRequired <= open_slots
                    and self.score_stat(sb.maxBonus, target) > 0
                ):
                    potential.add(sb.name)
            potential.update(used_sets)
            setless = {s: top(slot_lists[s]) for s in MOD_SLOTS}

        base_sets = {}
        for name in potential:
            sbmods = {}
            for slot in MOD_SLOTS:
                # slot lists are score sorted, so first matching mod is the JS
                # behavior used by the original implementation.
                found = None
                for mod in slot_lists[slot]:
                    if mod["set"].name == name:
                        found = mod
                        break
                sbmods[slot] = found
            base_sets[name] = sbmods

        best = None
        best_score = -inf
        best_unmoved = None

        for candidate in self.get_candidate_sets_generator(
            potential, base_sets, setless, sets_to_use
        ):
            score = self.score_mod_set(candidate, character, target)
            if score > best_score:
                best = candidate
                best_score = score
                best_unmoved = None
            elif score == best_score and best is not None:
                unmoved = sum(
                    m.get("characterID") == character.get("baseID")
                    for m in candidate
                )
                if best_unmoved is None:
                    best_unmoved = sum(
                        m.get("characterID") == character.get("baseID")
                        for m in best
                    )
                if (
                    unmoved > best_unmoved
                    or (unmoved == best_unmoved and len(candidate) > len(best))
                ):
                    best = candidate
                    best_unmoved = unmoved

        return {"modSet": best, "messages": messages}

    # ------------------------------------------------------------------
    # Avoid repeated "id not in list" scans after each assignment.
    # ------------------------------------------------------------------
    async def optimize_mods(
        self, available_mods, characters, order, incremental_optimize_index,
        global_settings, previous_run=None
    ):
        # Keep the original top-level semantics. This version only changes the
        # removal of assigned mods from the usable pool.
        previous_run = previous_run or {}
        previous_mods = previous_run.get("mods", [])

        recalc = (
            not previous_run.get("globalSettings")
            or global_settings.get("modChangeThreshold")
            != previous_run.get("globalSettings", {}).get("modChangeThreshold")
            or global_settings.get("lockUnselectedCharacters")
            != previous_run.get("globalSettings", {}).get("lockUnselectedCharacters")
            or global_settings.get("forceCompleteSets")
            != previous_run.get("globalSettings", {}).get("forceCompleteSets")
            or len(available_mods) != len(previous_mods)
        )

        if not recalc:
            for cid, char in characters.items():
                prev = previous_run.get("characters", {}).get(cid)
                if (
                    not prev
                    or prev.get("optimizerSettings", {}).get("isLocked")
                    != char.get("optimizerSettings", {}).get("isLocked")
                ):
                    recalc = True
                    break

        usable = [
            m for m in available_mods
            if not m.get("characterID")
            or not characters[m["characterID"]]["optimizerSettings"]["isLocked"]
        ]

        selected_ids = [x["id"] for x in order]

        if global_settings.get("lockUnselectedCharacters"):
            usable = [
                m for m in usable
                if not m.get("characterID") or m["characterID"] in selected_ids
            ]

        unselected = [cid for cid in characters if cid not in selected_ids]
        locked = [
            cid for cid, c in characters.items()
            if c["optimizerSettings"]["isLocked"]
        ]
        if global_settings.get("lockUnselectedCharacters"):
            locked += unselected

        end = (
            incremental_optimize_index + 1
            if incremental_optimize_index is not None
            else len(order)
        )

        results = []

        prev_display_time = 0
        for index, item in enumerate(order[:end]):
            cid, target = item["id"], deepcopy(item["target"])

            #Display progress, but not less than 5 seconds
            if (time.time() - prev_display_time) > 5:
                new_msg_content = emojis.hourglass+" Remod de "+cid+" ("+str(index+1)+"/"+str(end)+")"
            try:
                if interaction != None:
                    await interaction.edit_original_response(content=new_msg_content)
                else:
                    print(new_msg_content)
            except Exception as e:
                goutils.log2("WAR", "Unable to update discord msg to: "+new_msg_content)
            prev_display_time = time.time()

            #Run remod
            character = characters[cid]
            previous_char = previous_run.get("characters", {}).get(cid)

            if character["optimizerSettings"]["isLocked"]:
                results.append(None)
                continue

            can_reuse = (
                not recalc
                and previous_run.get("selectedCharacters")
                and index < len(previous_run["selectedCharacters"])
                and cid == previous_run["selectedCharacters"][index].get("id")
                and previous_char
                and self.objects_equivalent(
                    character.get("playerValues"),
                    previous_char.get("playerValues"),
                )
                and self.objects_equivalent(
                    target,
                    previous_run["selectedCharacters"][index].get("target"),
                )
                and character["optimizerSettings"].get("minimumModDots")
                == previous_char.get("optimizerSettings", {}).get("minimumModDots")
                and character["optimizerSettings"].get("sliceMods")
                == previous_char.get("optimizerSettings", {}).get("sliceMods")
                and character["optimizerSettings"].get("isLocked")
                == previous_char.get("optimizerSettings", {}).get("isLocked")
                and previous_run.get("modAssignments", [])
                and index < len(previous_run["modAssignments"])
                and previous_run["modAssignments"][index]
            )

            if can_reuse:
                assignment = previous_run["modAssignments"][index]
                assigned = list(assignment.get("assignedMods", []))
                messages = assignment.get("messages", [])
                missed = assignment.get("missedGoals", [])

                assigned_set = set(assigned)
                usable = [m for m in usable if m["id"] not in assigned_set]

                results.append({
                    "id": cid,
                    "target": target,
                    "assignedMods": assigned,
                    "messages": messages,
                    "missedGoals": missed,
                })
                continue

            recalc = True

            if global_settings.get("forceCompleteSets"):
                target["useOnlyFullSets"] = True

            absolute = self.change_relative_target_stats_to_absolute(
                results, characters, locked, available_mods, target, character
            )

            goals = [
                ts for ts in absolute.get("targetStats", [])
                if not ts.get("optimizeForTarget")
            ]

            filtered = deepcopy(absolute)
            filtered["targetStats"] = [
                ts for ts in absolute.get("targetStats", [])
                if ts.get("optimizeForTarget")
            ]

            real_target = self.combine_target_stats(filtered, character)
            found = self.find_best_mod_set_for_character(
                usable, character, real_target
            )

            new_set = found["modSet"]
            old_set = [
                m for m in usable
                if m.get("characterID") == character["baseID"]
            ]

            new_value = self.score_mod_set(new_set, character, real_target)
            old_value = self.score_mod_set(old_set, character, real_target)

            assignment_messages = []
            threshold = global_settings.get("modChangeThreshold", 0)

            same = (
                len(new_set) == len(old_set)
                and all(
                    any(n["id"] == o["id"] for n in new_set)
                    for o in old_set
                )
            )

            old_bad = not self.mod_set_satisfies_character_restrictions(
                old_set, character, real_target
            )
            new_good = self.mod_set_satisfies_character_restrictions(
                new_set, character, real_target
            )

            ratio_better = (
                ((new_value / old_value) * 100 - 100 > threshold)
                if old_value != 0
                else (new_value > old_value)
            )

            should_change = (
                (threshold == 0 and new_value >= old_value)
                or same
                or (old_bad and new_good)
                or ratio_better
                or (len(old_set) < 6 and len(new_set) > len(old_set))
            )

            if should_change:
                assigned_set = new_set
                assignment_messages = found["messages"]
            else:
                assigned_set = old_set
                if not new_good:
                    assignment_messages.append(
                        "Could not find a new mod set that satisfies the given "
                        "restrictions. Leaving the old mods equipped."
                    )

            assigned_ids = [m["id"] for m in assigned_set]
            assigned_id_set = set(assigned_ids)
            usable = [m for m in usable if m["id"] not in assigned_id_set]

            results.append({
                "id": cid,
                "target": target,
                "assignedMods": assigned_ids,
                "messages": assignment_messages,
                "missedGoals": self.get_missed_goals(
                    assigned_set, character, goals, target
                ),
            })

        self.clear_cache()
        return results


# ---------------------------------------------------------------------------
# Public API: intentionally mirrors the original module.
# ---------------------------------------------------------------------------
async def optimize_mods_from_profile(
    profile: Dict[str, Any],
    template: Optional[Dict[str, Any]] = None,
    previous_run: Optional[Dict[str, Any]] = None,
    progress_callback: ProgressCallback = None,
    interaction = None,
) -> List[Dict[str, Any]]:

    if interaction != None:
        await interaction.edit_original_response(content=emojis.hourglass+" Préparation du remod auto...")
    else:
        print("Récupération des infos du joueur...")

    """Run the optimized Python port from one myProgress profile."""
    opt = FastOptimizer(progress_callback)

    available_mods = [
        opt.deserialize_mod(m) for m in profile.get("mods", [])
    ]

    characters = {}
    for c in profile.get("characters", {}).values():
        c = deepcopy(c)
        c.setdefault("optimizerSettings", {})
        c["optimizerSettings"].pop("target", None)
        characters[c["baseID"]] = c

    raw_order = (
        template.get("selectedCharacters", [])
        if template is not None
        else profile.get("selectedCharacters", [])
    )

    order = [
        {"id": x["id"], "target": opt.deserialize_target(x["target"])}
        for x in raw_order
    ]

    previous = deepcopy(previous_run) if previous_run is not None else {}

    if previous:
        previous["modAssignments"] = deepcopy(
            profile.get("modAssignments", previous.get("modAssignments", []))
        )
        if isinstance(previous.get("selectedCharacters"), list):
            previous["selectedCharacters"] = [
                {
                    "id": x["id"],
                    "target": opt.deserialize_target(x["target"]),
                }
                for x in previous["selectedCharacters"]
            ]

    return await opt.optimize_mods(
        available_mods,
        characters,
        order,
        profile.get("incrementalOptimizeIndex"),
        profile.get("globalSettings", {}),
        previous,
    )


# Preserve the same convenient import name while retaining the original class
# as BaseOptimizer for behavioral comparison.
Optimizer = FastOptimizer

__all__ = [
    "Optimizer",
    "FastOptimizer",
    "BaseOptimizer",
    "OptimizerError",
    "Stat",
    "SetBonus",
    "SET_BONUSES",
    "optimize_mods_from_profile",
    "profile_from_my_progress",
    "build_order_from_template",
]
