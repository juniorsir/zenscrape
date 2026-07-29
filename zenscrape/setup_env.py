import os
import subprocess
import time
import sys
import socket
from loguru import logger

def ensure_tor_env():
    """Automates Tor environment setups, prints logs in gray, and erases them on success"""
    # 1. Install check
    try:
        subprocess.run(["tor", "--version"], capture_output=True, check=True)
    except Exception:
        logger.warning("Tor not found. Installing...")
        os.system("pkg install tor -y" if os.path.exists("/data/data/com.termux") else "sudo apt install tor -y")

    # 2. Config check
    torrc_path = os.path.expanduser("~/.zenscrape_torrc")
    if not os.path.exists(torrc_path):
        with open(torrc_path, "w") as f:
            f.write("SocksPort 9050\nControlPort 9051\nCookieAuthentication 0\n")

    # 3. Check if Tor is already running and active
    try:
        with socket.create_connection(("127.0.0.1", 9050), timeout=1) as s:
            # If the SOCKS port is already listening, we don't need to do anything
            return
    except Exception:
        pass

    # 4. If offline, close any stale processes and start fresh
    os.system("pkill tor")
    time.sleep(0.5)

    # Start Tor and capture its live output stream
    process = subprocess.Popen(
        ["tor", "-f", torrc_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # ANSI Escape Codes for Terminal UI
    GRAY = "\033[90m"
    RESET = "\033[0m"
    UP_AND_CLEAR = "\033[A\033[K" # Move cursor up one line and delete everything on it

    logger.info("⏳ Bootstrapping Tor circuits...")
    
    lines_printed = 0
    success = False

    # 5. Read Tor's live logs as they happen
    try:
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            clean_line = line.strip()
            if not clean_line:
                continue

            # Print the Tor logs in gray with the "»" pointer
            sys.stdout.write(f"{GRAY}»  {clean_line}{RESET}\n")
            sys.stdout.flush()
            lines_printed += 1

            # Detect successful connection
            if "Bootstrapped 100%" in clean_line:
                success = True
                break
                
            # Detect errors (like address already in use)
            if "Could not bind" in clean_line or "Address already in use" in clean_line:
                break
    except KeyboardInterrupt:
        process.terminate()
        sys.exit()

    # 6. CLEAR LOGS ON SUCCESS
    if success:
        # Move the terminal cursor up and erase every gray line we printed
        # +1 to also erase the "Bootstrapping Tor circuits..." info log
        for _ in range(lines_printed + 1):
            sys.stdout.write(UP_AND_CLEAR)
        sys.stdout.flush()
        
        logger.success("🛡️ Tor circuits fully bootstrapped and active!")
    else:
        logger.warning("⚠️ Tor failed to bootstrap cleanly. Trying to proceed...")
