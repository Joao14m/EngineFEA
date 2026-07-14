# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A finite-element model of a **two-material vibrating beam** (steel joined end to end with titanium), plus a **custom OpenGL renderer** that draws its mode shapes in 2D. Python solves; C++ draws. Neither half makes sense without the other.

## Commands

```powershell
# Configure (once). The quotes around -D are required: unquoted, PowerShell
# splits the path at the dot and CMake reports a missing toolchain file.
cmake -B build -S . -G Ninja "-DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake"

python -m modelo_matematico.main               # solve 201 beams  -> output/Resultados_FEA.npz  (slow)
python -m modelo_matematico.exportar_engine    # flatten for C++  -> output/viga.bin             (fast)
cmake --build build --target eng               # build the renderer
.\build\eng.exe                                # run it

.\build\eng.exe --config 98 --mode 6 --paused  # open straight into a case
```

**After any solver change, rerun both Python steps.** The renderer reads `viga.bin`, never the `.npz`, so re-solving without re-exporting silently shows stale results.

There is **no test suite and no linter**. Dependencies are implicit: `numpy` + `scipy` for Python, and vcpkg in classic mode (`glfw3`, `glm`) for C++ — there is no `requirements.txt` and no `vcpkg.json`.

## Architecture

Three layers, each of which only makes sense in terms of the next:

**`modelo_core/`** — a port of the relevant parts of **CALFEM** (a MATLAB FEA toolbox). Generic and problem-agnostic: `beam2d` builds one element's 6×6 stiffness/mass matrices (3 DOF per node: axial `u`, deflection `v`, rotation `theta`), `assem` scatters them into the global matrices, `eigen_solver` solves `K·x = λ·M·x` by deleting restrained DOF rows/columns. **`edof` is base-zero here**, unlike CALFEM's base-one original: column 0 is the element index, columns 1: are global DOFs.

**`modelo_matematico/`** — the study. `config.py` (`AnalysisConfig`, a frozen dataclass) is the control panel for everything; `fem_solver.py` is the pipeline, entered at `run_analysis(config)`.

**`engine/prod/`** — the renderer. **This is the product. `engine/experiments/` is a LearnOpenGL archive — never build against it or treat it as a library.** Every experiment file is a standalone `main()` with duplicate globals; putting two in one `add_executable` gives `LNK2005` "already defined".

### Three ideas explain almost all of `fem_solver.py`

1. **Composition sweep.** `p_aco` is the fraction of the beam that's steel; the rest is titanium. `passo_composicao = 0.005` walks it from 1.0 to 0.0, giving **201 independent beams**. Set `composicoes_aco_interesse = (1.0, 0.5, 0.0)` in the config to solve only a few — much faster while iterating.

2. **Mesh convergence loop.** Element count is *not* fixed. Each configuration starts at `NE_ini` elements and adds more until the largest percent change in the tracked frequencies drops below `erro_admissivel`. Configurations therefore converge at *different* mesh sizes.

3. **Boundary conditions** via the `cc` field: `0` free-free (3 rigid modes computed then discarded), `1` cantilever (default), `2` clamped-clamped, `3` simply supported.

### The results arrays are padded — always slice with the counts

Because (2) leaves every configuration with a different mesh, every per-config array in the `.npz` is padded to the maximum across all of them. `nodes` is `(201, 33)` but config `ic` only has `node_count[ic]` valid entries; **reading past that gives you garbage padding**. The metadata JSON's `valid_slices` key documents the correct slice for every array. Consult it rather than trusting a shape.

**Mode shapes carry no physical amplitude.** They are normalized so `max|v| = 1`. Any displayed deflection scale is invented by the renderer.

### The Python→C++ seam is `output/viga.bin`, not the `.npz`

A `.npz` is a ZIP of `.npy` files and C++ cannot open one without zlib. `exportar_engine.py` therefore writes a flat, versioned, little-endian binary — unpadded, `float32`, no new dependencies. Its layout is documented in that module's docstring and mirrored by `struct Config` in `eng.cpp`: **change one and you must change the other**, and bump `VERSION`.

**Why it exports slope, and why the renderer ignores `opengl_beam_vertices`.** The `.npz` beam vertices (from `gerar_malha_opengl.py`) have the ±h/2 thickness offset already baked in, computed against the normal of the *unscaled* mode shape. The renderer needs an adjustable deflection scale, and multiplying `y` by 0.25 would shrink the offset's y-component too — the beam would come out ~4× too thin at every steep slope. So `viga.bin` ships only the neutral axis (`x`, `v`, `dv/dx`, material id) and `shaders/viga.vs` rebuilds the thickness by offsetting along the normal of the **already-scaled** curve. That needs the slope, which `gerar_malha_opengl.py` computes and throws away.

`gerar_malha_opengl.py` still exists and still appends `opengl_*` buffers to the `.npz` — they're just for Python-side use now.

### Rendering notes

Orthographic and **uniform in both axes**, so the beam shows its true 60:1 slenderness. Both files evaluate the **cubic Hermite beam shape functions** to subdivide each element (default 8 samples), which is what makes the beam curve smoothly instead of looking like a polyline — the element already carries the exact cubic deflection, so the accuracy is free.

**Animation is deliberately not real-time.** True frequencies span 4 Hz to ~400 Hz; mode 6 against a 60 Hz display would alias into noise. Every mode oscillates at a fixed visual rate and the real frequency is reported in the window title.

Targets that load shaders or data from disk need a `POST_BUILD` copy next to the executable — `eng` copies both its `shaders/` directory and `viga.bin` (the latter through `cmake/copy_if_exists.cmake`, so a fresh clone builds before the exporter has ever run).

## Conventions

- Python 3.10+ syntax (`X | None`), `from __future__ import annotations`, type hints throughout.
- **Code, comments, and commit messages are in Portuguese without accents** (`Configuracao`, `frequencias`). Match this.
- C++17.
- `build/` and `output/` are generated and gitignored. Never hand-edit anything in them.
