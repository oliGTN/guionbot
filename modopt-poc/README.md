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

Open the local URL printed by Vite and click **Run proof of concept**. Use
npm run build to check that Vite can bundle the browser and worker code.

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
