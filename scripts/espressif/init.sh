#!/bin/bash
cd /workspace
west init -l manifest/
west update --narrow -o=--depth=1
west blobs fetch hal_espressif
