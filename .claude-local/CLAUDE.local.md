# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

`gaveaEngine` is an early-stage OpenGL graphics/engine project written in C++17, currently following the LearnOpenGL tutorial path (each source file in `engine/` is a self-contained tutorial step that opens a GLFW window and draws with modern core-profile OpenGL). The `math/`, `data/`, and `tests/` directories contain empty placeholder files (`materials.py`, `results.json`, `test.py`) and are not yet wired into the build.

## Build & run

The project uses **CMake + Ninja**, with dependencies provided by **vcpkg** (manifest-less / classic mode — `glfw3` and `glm` are consumed via the vcpkg toolchain file). GLAD is vendored in `third_party/glad` and built as a static lib by CMake itself.

Configure once (toolchain file is mandatory — without it `find_package(glfw3/glm)` fails):

```sh
cmake -B build -S . -G Ninja -DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake
```

Build:

```sh
cmake --build build --config Debug --target all
```

Run:

```sh
./build/gaveaEngine.exe
```

There is no lint or test target configured yet. Note the toolchain is mixed on this machine: CMake is invoked from `C:\mingw64\bin`, but the vcpkg `x64-windows` triplet pulls in the **MSVC** compiler/linker (`link.exe`) for the final executable. The `.vscode/c_cpp_properties.json` points IntelliSense at mingw gcc, which is for editor analysis only, not the actual build.

## Architecture & key constraints

**One `main()` per executable.** Every file in `engine/` (e.g. `hello_window.cpp`, `rectangle.cpp`) is a complete standalone program with its own `main()` plus duplicate globals (`vertexShaderSource`, `fragmentShaderSource`, `framebuffer_size_callback`, `processInput`). They are *iterations of the same demo*, not modules that compose. Listing more than one of them in a single `add_executable(...)` in `CMakeLists.txt` causes `LNK2005 / LNK1169` "already defined" link errors. When adding a new tutorial step, either swap which single `.cpp` the `gaveaEngine` target builds, or give each its own `add_executable` + `target_link_libraries(... glfw glm::glm glad)` target.

**Standard OpenGL setup order** that the engine files rely on, and that must be preserved: init GLFW → set window hints (context 3.3, core profile) → create window → `glfwMakeContextCurrent` → load GLAD via `gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)` **before any GL call** → compile/link shaders → set up VAO/VBO(/EBO) → render loop. Calling any `gl*` function before GLAD is loaded crashes.

**Linking pieces:** `target_link_libraries(gaveaEngine PRIVATE glfw glm::glm glad)` — `glfw` and `glm::glm` come from vcpkg's CONFIG packages; `glad` is the local static library target defined in `CMakeLists.txt` from `third_party/glad/src/glad.c` with public include dir `third_party/glad/include`.

## Conventions

- C++17 (`CMAKE_CXX_STANDARD 17`, required).
- Source lives in `engine/`; shaders are currently inline string literals inside each `.cpp`, not separate files.
- `build/` is committed in this repo's history but is generated output — prefer regenerating over hand-editing anything under it.
