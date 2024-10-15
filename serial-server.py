#!/usr/bin/env python
#
# PySerial RFC 2217 Server
#
# This script creates a server that listens for incoming TCP/IP connections
# and redirects data to a serial port. It is based on the RFC 2217 protocol.
#
# Original author:
#   (C) 2009-2015 Chris Liechti <cliechti@gmx.net>
#
# Modified by Shawn Hymel:
# - Added IP whitelist to restrict access to certain IP addresses
# - Added logging
# - Added graceful exit on keyboard interrupt
# - Added settings for serial and server timeouts
# - Added robust server and serial port restarts
# Date: October 1, 2024
#
# SPDX-License-Identifier:    BSD-3-Clause

import logging
import socket
import time
import threading
import serial
import serial.rfc2217

__version__ = "0.1"

# ------------------------------------------------------------------------------
# Settings

SERIAL_WAIT = 1.0           # Time (seconds) between checking for serial connection
SERIAL_TIMEOUT = 1.0        # Time (seconds) to wait for serial data
SERVER_WAIT = 1.0           # Time (seconds) between checking for server connection
SERVER_TIMEOUT = 1.0        # Time (seconds) to wait for server data
IP_WHITELIST = [            # List of IP addresses that are allowed to connect
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
]  

# ------------------------------------------------------------------------------
# Classes

class Redirector():
    """
    Handle redirecting data between a serial port and a socket.
    """
    
    def __init__(self, serial_instance, socket, debug=False):
        self.serial = serial_instance
        self.socket = socket
        self._write_lock = threading.Lock()
        self.rfc2217 = serial.rfc2217.PortManager(
            self.serial,
            self,
            logger=logging.getLogger("rfc2217.server") if debug else None)
        self.log = logging.getLogger("redirector")

    def statusline_poller(self):
        self.log.debug("Status line poll thread started")
        while self.alive:
            time.sleep(1)
            try:
                self.rfc2217.check_modem_lines()
            except serial.SerialException as e:
                self.log.error(f"Error polling modem lines: {e}")
        self.log.debug("Status line poll thread terminated")

    def shortcircuit(self):
        """
        Connect the serial port to the TCP port by copying everything from one side to the other
        """
        self.alive = True
        self.thread_read = threading.Thread(target=self.reader)
        self.thread_read.daemon = True
        self.thread_read.name = "serial->socket"
        self.thread_read.start()
        self.thread_poll = threading.Thread(target=self.statusline_poller)
        self.thread_poll.daemon = True
        self.thread_poll.name = "status line poll"
        self.thread_poll.start()
        self.writer()

    def reader(self):
        """
        Loop forever and copy serial->socket
        """
        self.log.debug("Reader thread started")
        while self.alive:
            # Read from the serial port
            try:
                data = self.serial.read(self.serial.in_waiting or 1)
                if data:
                    # escape outgoing data when needed (Telnet IAC (0xff) character)
                    self.write(b''.join(self.rfc2217.escape(data)))

            # Catch exceptions, likely a result of the serial port being closed
            except socket.error as msg:
                self.log.error(f"{msg}")
                break
        self.alive = False
        self.log.debug("Reader thread terminated")

    def write(self, data):
        """
        Thread safe socket write with no data escaping. used to send telnet stuff
        """
        with self._write_lock:
            self.socket.sendall(data)

    def writer(self):
        """
        Loop forever and copy socket->serial
        """
        while self.alive:
            # Read from the socket
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                self.serial.write(b''.join(self.rfc2217.filter(data)))

            # Catch non-blocking socket exception, just keep going
            except BlockingIOError:
                pass

            # Catch exceptions, likely a result of the serial port being closed
            except socket.error as msg:
                self.log.error(f"{msg}")
                break
        self.log.debug("Writer thread terminated")
        self.stop()

    def stop(self):
        """
        Stop copying
        """
        self.log.debug("Stopping")
        if self.alive:
            self.alive = False
            self.thread_read.join()
            self.thread_poll.join()

# ------------------------------------------------------------------------------
# Functions

def is_socket_connected(sock):
    """
    Check if a client socket is still connected. Only works with nonblocking sockets.
    """
    if sock is None:
        return False
    try:
        data = sock.recv(1)
        if data == b"":
            return False
        return True
    except socket.error:
        return True

# ------------------------------------------------------------------------------
# Main

if __name__ == "__main__":

    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="RFC 2217 Serial to Network (TCP/IP) redirector.",
        epilog="""\
NOTE: no security measures are implemented. Anyone can remotely connect
to this service over the network.

Only one connection at once is supported. When the connection is terminated
it waits for the next connect.
""")

    # Configure command line arguments
    parser.add_argument("SERIALPORT")
    parser.add_argument(
        "-p", "--localport",
        type=int,
        help="local TCP port, default: %(default)s",
        metavar="TCPPORT",
        default=2217)
    parser.add_argument(
        "-v", "--verbose",
        dest="verbosity",
        action="count",
        help="print more diagnostic messages (option can be given multiple times)" \
             ", -v: warning, -vv: info, -vvv: debug",
        default=0)
    args = parser.parse_args()

    # Set logging level
    if args.verbosity > 3:
        args.verbosity = 3
    levels = (
        logging.NOTSET,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
    )
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("rfc2217").setLevel(levels[args.verbosity])
    logging.getLogger("redirector").setLevel(levels[args.verbosity])

    # Create the serial port
    ser = serial.serial_for_url(args.SERIALPORT, do_not_open=True)
    ser.timeout = SERIAL_TIMEOUT
    ser.write_timeout = SERIAL_TIMEOUT
    ser.dtr = False
    ser.rts = False

    # Create the server socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", args.localport))
    srv.listen(1)
    srv.settimeout(SERVER_TIMEOUT)
    logging.info(f"The server is listening on port {args.localport}")

    # Welcome message
    logging.info("RFC 2217 TCP/IP to Serial redirector - type Ctrl-C / BREAK to quit")

    # Main loop
    while True:
        try:

            # Wait for a client connection
            client = None
            while not is_socket_connected(client):
                try:
                    client, addr = srv.accept()
                    logging.info(f"Connection request from {addr[0]}:{addr[1]}")

                # Catch timeout exception, just keep going
                except socket.timeout:
                    logging.info("Waiting for client connection...")
                    time.sleep(SERVER_WAIT)
                    continue

            # Check if client IP is in whitelist
            if addr[0] not in IP_WHITELIST:
                logging.warning(f"Connection request from {addr[0]} denied")
                client.close()
                continue

            # Set TCP_NODELAY to disable Nagle's algorithm
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # Set non-blocking mode
            client.setblocking(False)

            # Wait for serial connection
            while not ser.is_open:
                try:
                    ser.open()
                except serial.SerialException as e:
                    
                    # If serial port is already open, close it and try again
                    if "Port is already open" in str(e):
                        ser.close()

                    # Let the user know if the port is already in use
                    elif "PermissionError" in str(e):
                        logging.error(f"Port {ser.name} is already in use")

                    # Otherwise, wait and try again
                    else:
                        logging.info(f"Waiting for serial connection on {ser.name}...")

                    # Wait and try again
                    time.sleep(SERIAL_WAIT)
                    continue

            # Print connection information
            logging.info(f"Connected to {ser.name}")

            # Save serial port settings
            settings = ser.get_settings()

            # Set DTR and RTS to True to simulate a terminal being connected
            ser.dtr = True
            ser.rts = True

            # Create a redirector object
            r = Redirector(
                ser,
                client,
                args.verbosity > 0
            )

            # Start the redirector
            try:
                r.shortcircuit()

            # Any exceptions, stop the redirector
            finally:

                # Stop the redirector and the client socket
                logging.info("Disconnected")
                r.stop()
                client.close()

                # Reset serial port settings
                ser.dtr = False
                ser.rts = False
                ser.apply_settings(settings)
                ser.close()

        # Catch keyboard interrupt
        except KeyboardInterrupt:
            logging.info("Exiting...")
            break

        # Catch socket errors
        except socket.error as e:
            logging.error(f"Socket error: {e}")
