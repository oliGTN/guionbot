# HiGHS-JS mod optimizer proof of concept

This directory is an isolated browser-side experiment. It does not replace or
modify the Python optimizer.

## What it tests

- HiGHS compiled to WebAssembly, loaded in a browser Web Worker.
- Binary candidate-mod selection, with exactly one mod per each of six slots.
- Integer set-group/remainder variables.
- Four monotonic target bands for two stats.
- A weighted objective with stat bands dominating secondary preferences.
- Worker execution and basic timing instrumentation.

The fixture is intentionally synthetic. It verifies the solver integration and
the structure of a small MILP; it does **not** claim parity with the full
solve_hero() implementation yet.

## Run locally

Requires Node.js 18 or newer.

    cd modopt-poc
    npm install
    npm run dev

Open the local URL printed by Vite and choose the Grandivory progress JSON,
`GameData.json`, `keystats.json`, and `stats_v2_top100.json` in the file pickers.
The browser parses these files locally and reports their basic structure; it
does not upload them or run optimization yet. Browsers cannot read arbitrary
absolute paths such as `/home/pi/GuionBot/warstats/GameData.json` directly, so
the files must be selected by the user unless a separate local server explicitly
serves them. Use `npm run build` to check that Vite can bundle the browser code.

## Step 1: local progress-file inspection

The browser UI expects a Grandivory-style JSON object with a non-empty
`profiles` array and a `mods` array in the first profile. It reports basic
counts and key names to help establish the real file schema. Separate file
pickers also inspect the top-level shapes of the game data, keystats, and
stats data. These are schema-discovery steps only: they do not yet normalize
mods or run the solver. No file data is sent over the network by this UI.

## Next validation stage

1. Add a sanitized, fixed input from a real hero and preserve the exact
   candidates, stat forms, target thresholds, set bonuses, and objective terms.
2. Run the same input through Python/SciPy and HiGHS-JS.
3. Compare objective value, selected-mod feasibility, and exact post-evaluation
   statq points. Different mod selections are acceptable if multiple solutions
   have the same optimal objective.
4. Benchmark model construction and solve time separately on the same device.

The current fixture uses illustrative stat values and simplified set bonuses.
It must not be used to make real remodding decisions.


## First port of the real per-hero MILP

`src/hero-milp.js` now contains a data-driven JavaScript implementation of
the core `Problem`, `StatForm`, candidate filtering, set-group/remainder,
combo, stat-band, secondary-stat and health-linearization logic from
`swgoh_modopt.py`. It can be invoked from the worker with a message of this
shape:

```js
worker.postMessage({
  type: "run",
  mode: "hero",
  input: {
    base: { level: 85, stats: { "1": 10000, "5": 150, "6": 1000, "7": 1000, "28": 10000 }, armor_flat: 100, resist_flat: 100 },
    modsAvailable: [ /* normalized parsed mods; see below */ ],
    currentIds: [],
    keyStats: [{ stat: "speed", mod_key: "speed", target: 300 }],
    also: [],
    setBonuses: {
      "1": { count: 2, stat: 55, lvl15: 1000000 },
      "4": { count: 4, stat: 57, lvl15: 1000000 }
    },
    combos: [],
    lockedPrimary: {},
    timeLimit: 8,
    keepBonus: 150,
    setReward: 5000
  }
});
```

Each entry in `modsAvailable` must already be normalized to the Python
`parse_mod()` representation: `{id, set, slot, primary, flat, pct, quality,
owner?, virtual?}`. `setBonuses` must contain the exact `count`, `stat` and
`lvl15` values from `swgoh_cron.MOD_SET_BONUSES`. Combo `groups` is keyed by
numeric set ID. `lockedPrimary` maps slot numbers to primary stat IDs.

**Important limitations:** this is an initial core port, not yet a parity
claim. Python still owns game-data loading, raw-mod parsing, K1/keystats
preparation, candidate data generation, exact in-game stat evaluation,
multi-hero inventory allocation, farm-mod generation and report output.
The JS model must be tested against Python using identical normalized
single-hero inputs before it can be trusted. In particular, compare the
objective and feasibility first, then compare selected mods and exact statq
points; equally optimal solutions may choose different mods.


## Current browser-side normalization stage

The page now has a **Single-hero optimizer preview** section. Load the Grandivory
progress JSON plus `GameData.json`, `keystats.json`, and
`stats_v2_top100.json`; select a hero and click **Prepare hero input**. The
normalizer in `src/grandivory-normalize.js` maps Grandivory mod fields to the
MILP's numeric stat IDs, maps set IDs, reads set bonuses from
`GameData.statModSet`, converts keystats targets and the selected character's
primary/set restrictions, and filters out mods below level 15 (matching the Python optimizer; lower-dot mods are not automatically excluded).
The page then can run the existing per-hero MILP in a Web Worker.

This remains a **prototype, not a trusted optimizer**. In particular:

- The stats-v2 file is parsed for inspection but is not yet used for exact
  in-game stat evaluation.
- Grandivory base stats do not necessarily expose the underlying defense and
  resistance ratings required by the Python linearization. A hero whose target
  includes armor/resistance is deliberately rejected if those inputs are
  missing.
- The Grandivory-to-Python stat-value mapping must still be checked against a
  real raw game mod and the Python `parse_mod()` result. Unknown stat labels
  cause a clear error rather than being silently treated as zero.
- This preview does not yet reproduce the Python optimizer's sequential
  multi-hero inventory allocation, virtual/farm mods, exact post-solve statq
  evaluation, report output, or all lock/unselected rules.

Do not use the returned mod assignments for live remodding until a real hero
has been compared with the Python optimizer using the same normalized mods,
set bonuses, target rows and objective, and the selected result has been
validated with the game's exact stat calculation.


## Python parity batch harness

The **Python parity test** controls run the real per-hero JavaScript MILP for a
repeatable list of heroes. Load the four local input files, choose a batch size
(default 10; enter 0 to run every eligible hero), and click **Run batch parity
test**. The first batch is intentionally small so you can validate the workflow
before committing to a long run.

To compare against Python, load a reference JSON file before starting the batch.
The harness accepts a JSON array of per-hero result objects, an object with a
`results` array, one result object with a `heroId`/ `hero_id`/ `unitId`/
`id` field, or an object keyed by hero ID. Each hero result should include
`selectedMods` (or `selected_mods` / `chosen` / `mods`) as an array of
objects with slot names and mod IDs. If present, `objectiveValue` is compared
as well. The report shows per-slot ID differences and objective mismatches.
Unmatched hero IDs or unrecognized reference shapes are called out rather than
counted as parity matches.

The **Download batch results JSON** button saves the report so you can archive
and compare runs. Reference and game data are read locally in the browser; they
are not uploaded. The batch worker initializes HiGHS once for the run, but each
hero still builds and solves its own MILP. Start with a small batch and inspect
the report for preparation errors, failed solves, and reference-format issues.
An assignment match is a useful regression signal, not a substitute for exact
in-game stat evaluation or multi-hero inventory-allocation validation.


## One-time extraction of optimizer reference data

The browser no longer needs the three large reference JSON files selected every
time. The app imports `src/optimizer-data.generated.js`, a compact generated
module containing only:

- `GameData.statModSet`, including the exact set-bonus records used by the normalizer;
- per-hero `key_stats`, `also`, and set-combo data from `keystats.json`;
- per-unit player counts and speed medians from `stats_v2_top100.json`.

From the `modopt-poc` directory on the GuionBot checkout, run this once after
pulling the branch:

```sh
npm run extract-data
```

The script's default paths match the local layout:
`../../warstats/GameData.json`, `../../DATA/keystats.json`, and
`../../DATA/stats_v2_top100.json`; it writes
`src/optimizer-data.generated.js`. These paths resolve relative to the
`modopt-poc` working directory. If your files
are elsewhere, pass explicit paths:

```sh
npm run extract-data -- /path/to/GameData.json /path/to/keystats.json /path/to/stats_v2_top100.json
```

Then restart/reload Vite. From then on, only the Grandivory progress export
needs to be selected for each run. The three reference-file pickers are under
an optional override section for testing alternate snapshots.

The generated module is derived data, not a copy of the source files. Re-run
the extraction command when you update the source JSONs. The source JSONs are
read locally and are not uploaded by the app. Because the generated module is
expected to be committed for other checkouts to use the same snapshot, review
its size and commit it only if that is appropriate for your repository.


### Very large GameData files

The extractor streams `GameData.json` rather than reading it into one JavaScript
string, so it avoids Node's `ERR_STRING_TOO_LONG` limit. If all four files
`GameData_segment1.json` through `GameData_segment4.json` exist beside
`GameData.json`, it automatically scans the four segments in order as one
continuous JSON byte stream and extracts only the top-level `statModSet`
array. The segment files must be consecutive pieces of the original JSON in
the correct order; they do not need to be individually valid JSON documents.
