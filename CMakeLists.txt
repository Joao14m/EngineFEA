cmake_minimum_required(VERSION 3.20)
project(gaveaEngine LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 CONFIG REQUIRED)
find_package(glm CONFIG REQUIRED)

# GLAD lives at third_party/glad relative to this root file
add_library(glad STATIC third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# Your engine program
add_executable(helloWindow engine/hello_window.cpp)
target_link_libraries(helloWindow PRIVATE glfw glm::glm glad)

add_executable(rectangle engine/rectangle.cpp)
target_link_libraries(rectangle PRIVATE glfw glm::glm glad)