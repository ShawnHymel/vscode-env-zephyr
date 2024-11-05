# Create the library target
add_library(hello_lib STATIC src/say_hello.c)

# Add the library's header file(s)
target_include_directories(
    hello_lib 
    PUBLIC   
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)