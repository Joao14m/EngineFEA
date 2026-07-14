cmake_minimum_required(VERSION 3.20)
project(gaveaEngine LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 CONFIG REQUIRED)
find_package(glm CONFIG REQUIRED)

# GLAD lives at third_party/glad relative to this root file
add_library(glad STATIC third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# Experiments

#add_executable(helloWindow engine/experiments/learning/hello/hello_window.cpp)
#target_link_libraries(helloWindow PRIVATE glfw glm::glm glad)

#add_executable(rectangle engine/experiments/learning/hello/rectangle.cpp)
#target_link_libraries(rectangle PRIVATE glfw glm::glm glad)

#add_executable(ex1 engine/experiments/exercises/hello/ex1.cpp)
#target_link_libraries(ex1 PRIVATE glfw glm::glm glad)

#add_executable(ex2 engine/experiments/exercises/hello/ex2.cpp)
#target_link_libraries(ex2 PRIVATE glfw glm::glm glad)

#add_executable(ex3 engine/experiments/exercises/hello/ex3.cpp)
#target_link_libraries(ex3 PRIVATE glfw glm::glm glad)

#add_executable(shader engine/experiments/learning/shadersChap/shader.cpp)
#target_link_libraries(shader PRIVATE glfw glm::glm glad)

#add_executable(shader2 engine/experiments/learning/shadersChap/shader2.cpp)
#target_link_libraries(shader2 PRIVATE glfw glm::glm glad)

add_executable(shader_class engine/experiments/learning/shadersChap/shader_class.cpp)
target_link_libraries(shader_class PRIVATE glfw glm::glm glad)
# shaderh.h lives in engine/experiments/include, so add it to the include path
target_include_directories(shader_class PRIVATE engine/experiments/include)

# Copy the GLSL files into an "include" folder next to the shader_class
# executable so the relative paths passed to the Shader constructor
# ("include/shader.vs", "include/shader.fs") resolve at runtime.
add_custom_command(TARGET shader_class POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:shader_class>/include"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_SOURCE_DIR}/engine/experiments/include/shader.vs"
        "${CMAKE_SOURCE_DIR}/engine/experiments/include/shader.fs"
        "$<TARGET_FILE_DIR:shader_class>/include")

add_executable(ex4 engine/experiments/exercises/shadersChap/ex4.cpp)
target_link_libraries(ex4 PRIVATE glfw glm::glm glad)
# shaderh.h lives in engine/experiments/include, so add it to the include path
target_include_directories(ex4 PRIVATE engine/experiments/include)

# Copy the GLSL files into an "include" folder next to the ex4 executable so
# the relative paths passed to the Shader constructor resolve at runtime.
add_custom_command(TARGET ex4 POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E make_directory "$<TARGET_FILE_DIR:ex4>/include"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_SOURCE_DIR}/engine/experiments/include/shader.vs"
        "${CMAKE_SOURCE_DIR}/engine/experiments/include/shader.fs"
        "$<TARGET_FILE_DIR:ex4>/include")

# Production
add_executable(eng engine/prod/eng.cpp)
target_link_libraries(eng PRIVATE glfw glm::glm glad)
target_include_directories(eng PRIVATE engine/prod)

# The Shader constructor and the results loader take paths relative to the
# executable, so the GLSL files and the exported FEA binary are copied next to
# eng.exe. viga.bin is produced by "python -m modelo_matematico.exportar_engine"
# and may not exist yet, so its copy goes through a script that skips a missing
# source instead of failing the build.
add_custom_command(TARGET eng POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/engine/prod/shaders"
        "$<TARGET_FILE_DIR:eng>/shaders"
    COMMAND ${CMAKE_COMMAND}
        -DSRC=${CMAKE_SOURCE_DIR}/output/viga.bin
        -DDST=$<TARGET_FILE_DIR:eng>/viga.bin
        -P "${CMAKE_SOURCE_DIR}/cmake/copy_if_exists.cmake")
