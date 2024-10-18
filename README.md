# VS Code Docker Environment for Zephyr

This is a development environment for creating Docker images with the Zephyr toolchain used to build source code for various embedded targets. You build the image for your desired toolchain, store projects in the *workspace/* directory, and then run the image whenever you want to build (e.g. `west build`) the project. Separate Dockerfiles exist for different target families (ARM, Espressif, etc.). The intention is to use this environment as your VS Code working directory, but it is usable outside of VS Code.

> **Note**: the instructions below were verified with Python 3.12 running on the host system. If one of the *pip install* steps fails, try installing exactly Python 3.12 and running the command again with `python3.12 -m pip install ...`

## Getting Started

Before you start, install the following programs on your computer:

 * (Windows) [WSL 2](https://learn.microsoft.com/en-us/windows/wsl/install)
 * [Docker Desktop](https://www.docker.com/products/docker-desktop/)
 * [Python](https://www.python.org/downloads/)

Open a terminal, navigate to this directory, and install the following dependencies:

Linux/macOS:
```sh
python -m venv venv
source venv/bin/activate
python -m pip install pyserial==3.5
```

Windows:
```bat
python -m venv venv
venv\Scripts\activate
python -m pip install pyserial==3.5
```

Choose your desired target family below and follow the steps to build image and compile an example program.

### Espressif (ESP32)

Build the image (this will take some time):

```sh
docker build -t env-zephyr-espressif -f Dockerfile.espressif .
```

Run the image in interactive mode:

Linux/macOS:
```sh
docker run --rm -it -v $(pwd)/workspace:/workspace -w /workspace --add-host=host.docker.internal:host-gateway env-zephyr-espressif bash
```

Windows:
```bat
docker run --rm -it -v %cd%\workspace\:/workspace -w /workspace --add-host=host.docker.internal:host-gateway env-zephyr-espressif bash
```

In the container, build the project. Note that I'm using the [ESP32-S3-DevKitC](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/hw-reference/esp32s3/user-guide-devkitc-1.html) as my target board. Feel free to change it to one of the [other ESP32 dev boards](https://docs.zephyrproject.org/latest/boards/index.html#vendor=espressif).

```
# cd blink
# west build -p always -b esp32s3_devkitc/esp32s3/procpu
# exit
```

Connect the ESP32 board to your computer. In the terminal, activate the Python virtual environment (Linux/macOS: `source venv/bin/activate`, Windows: `venv\Scripts\activate`) if not done so already. Install the ESP flashing tool:

```sh
python -m pip install esptool==4.8.1 
```

Flash the binary to your board. For some ESP32 boards, you need to put it into bootloader by holding the *BOOTSEL* button and pressing the *RESET* button (or cycling power). Change `<PORT>` to the serial port for your ESP32 board (e.g. `/dev/ttyS0` for Linux, `/dev/tty.usbserial-1420` for macOS, `COM7` for Windows). You might also need to install a serial port driver, depending on the particular board.

```sh
python -m esptool --port "<PORT>" --chip auto --baud 921600 --before default_reset --after hard_reset write_flash -u --flash_mode keep --flash_freq 40m --flash_size detect 0x0 workspace/blink/build/zephyr/zephyr.bin
```

Open a serial port for debugging. Change `<PORT>` to the serial port for your ESP32 board.

```sh
python -m serial.tools.miniterm "<PORT>" 115200
```

You should see the LED state printed to the console. Exit with *ctrl+]* (or *cmd+]* for macOS).

## License

All software in this repository, unless otherwise noted, is licensed under the [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
