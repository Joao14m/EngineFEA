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

#add_executable(helloWindow engine/experiments/hello_window.cpp)
#target_link_libraries(helloWindow PRIVATE glfw glm::glm glad)

#add_executable(rectangle engine/experiments/rectangle.cpp)
#target_link_libraries(rectangle PRIVATE glfw glm::glm glad)

#add_executable(ex1 engine/experiments/ex1.cpp)
#target_link_libraries(ex1 PRIVATE glfw glm::glm glad)

#add_executable(ex2 engine/experiments/ex2.cpp)
#target_link_libraries(ex2 PRIVATE glfw glm::glm glad)

#add_executable(ex3 engine/experiments/ex3.cpp)
#target_link_libraries(ex3 PRIVATE glfw glm::glm glad)

#add_executable(shader engine/experiments/shader.cpp)
#target_link_libraries(shader PRIVATE glfw glm::glm glad)

#add_executable(shader2 engine/experiments/shader2.cpp)
#target_link_libraries(shader2 PRIVATE glfw glm::glm glad)

add_executable(shader_class engine/experiments/shader_class.cpp)
target_link_libraries(shader_class PRIVATE glfw glm::glm glad)

# Copy the GLSL files next to the shader_class executable so the relative
# paths passed to the Shader constructor resolve at runtime.
add_custom_command(TARGET shader_class POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${CMAKE_SOURCE_DIR}/engine/experiments/shader.vs"
        "${CMAKE_SOURCE_DIR}/engine/experiments/shader.fs"
        "$<TARGET_FILE_DIR:shader_class>")

# Production 
#add_executable(eng engine/prod/eng.cpp)
#target_link_libraries(eng PRIVATE glfw glm::glm glad)