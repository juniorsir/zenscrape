import os
import subprocess
import time
from loguru import logger

def ensure_tor_env():
    """Automates Tor installation, configuration, and verifies complete bootstrap"""
    # 1. Check if Tor is installed
    try:
        subprocess.run(["tor", "--version"], capture_output=True, check=True)
    except Exception:
        logger.warning("Tor not found. Installing...")
        os.system("pkg install tor -y" if os.path.exists("/data/data/com.termux") else "sudo apt install tor -y")

    # 2. Setup the custom torrc config
    torrc_path = os.path.expanduser("~/.zenscrape_torrc")
    if not os.path.exists(torrc_path):
        with open(torrc_path, "w") as f:
            f.write("SocksPort 9050\nControlPort 9051\nCookieAuthentication 0\n")

    # 3. Check if Tor is already running and fully bootstrapped
    # We do a fast curl test through the proxy to see if it's already active
    check_cmd = ["curl", "-s", "--socks5-hostname", "127.0.0.1:9050", "https://api.ipify.org"]
    try:
        res = subprocess.run(check_cmd, capture_output=True, timeout=2)
        if res.returncode == 0:
            # Tor is already up and connected! No need to wait or restart.
            return
    except Exception:
        pass

    # 4. If Tor is not running, close any hung instances and start it
    logger.warning("Tor SOCKS5 proxy offline or not ready. Restarting...")
    os.system("pkill tor")
    time.sleep(1) # Give system time to release ports
    
    logger.info("🚀 Starting Tor background process...")
    subprocess.Popen(["tor", "-f", torrc_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. SMART BOOTSTRAP CHECK (Pings Tor every 1.5 seconds until circuit is active)
    logger.info("⏳ Waiting for Tor circuits to finalize (Bootstrapping)...")
    
    for attempt in range(20): # Max 30 seconds
        time.sleep(1.5)
        try:
            # We ping a tiny endpoint to verify Tor is 100% active
            ping = subprocess.run(check_cmd, capture_output=True, timeout=2)
            if ping.returncode == 0:
                logger.success(f"🛡️ Tor circuits fully bootstrapped! Exit IP: {ping.stdout.decode().strip()}")
                return
        except Exception:
            pass
            
    logger.warning("⚠️ Tor is taking longer than usual to connect. Proceeding anyway...")
