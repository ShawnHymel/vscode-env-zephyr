# Minimum CMake version
cmake_minimum_required(VERSION 3.22.0)

# Locate the Zephyr RTOS source
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})

# Name the project
project(blink)

# Include the library (via directory)
add_subdirectory(lib/say_hello)

# Locate the source code for the application
# Assumes add_executable(app "")
target_sources(app PRIVATE src/main.c)

# Link the say_hello library to the application
target_link_libraries(app PRIVATE hello_lib)