cmake_minimum_required(VERSION 3.22.1)

project(x1framegen LANGUAGES CXX)

add_library(
    x1framegen
    SHARED
    framegen.cpp
)

target_compile_features(x1framegen PRIVATE cxx_std_17)

find_library(log-lib log)

target_link_libraries(
    x1framegen
    PRIVATE
    ${log-lib}
)
