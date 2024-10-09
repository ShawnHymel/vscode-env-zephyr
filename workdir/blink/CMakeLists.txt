cmake_minimum_required(VERSION 3.22)
 
set(ZEPHYR_BASE /opt/toolchains/zephyr)
set(BOARD esp32s3_devkitc/esp32s3/procpu)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(blink)

target_sources(app PRIVATE src/main.c)