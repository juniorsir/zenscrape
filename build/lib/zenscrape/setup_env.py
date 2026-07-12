import os
import subprocess
import time
from loguru import logger

def ensure_tor_env():
    """Automates Tor installation and configuration for the user"""
    # 1. Check if Tor is installed
    try:
        subprocess.run(["tor", "--version"], capture_output=True, check=True)
    except:
        logger.warning("Tor not found. Attempting to install...")
        os.system("pkg install tor -y" if os.path.exists("/data/data/com.termux") else "sudo apt install tor -y")

    # 2. Create the internal Tor config
    torrc_path = os.path.expanduser("~/.zenscrape_torrc")
    if not os.path.exists(torrc_path):
        with open(torrc_path, "w") as f:
            f.write("SocksPort 9050\nControlPort 9051\nCookieAuthentication 0\n")
    
    # 3. Start Tor if not running
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 9050))
        s.close()
    except:
        logger.info("🚀 Starting Tor background process...")
        subprocess.Popen(["tor", "-f", torrc_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5) # Wait for bootstrap
