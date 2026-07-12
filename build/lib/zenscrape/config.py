from pydantic import BaseModel, Field
from typing import Optional, List, Any

class ZenSecurityConfig(BaseModel):
    # Evasion Settings
    impersonate: str = "chrome110"  # Options: chrome110, edge99, safari15.5
    use_stealth: bool = True
    rotate_headers: bool = True

    use_tor: bool = False
    tor_control_port: int = 9051

    cache_requests: bool = False 
    db_path: str = "zenscrape_data.db"

    # Proxy & Network
    proxy_list: List[str] = []
    dns_over_https: bool = True
    verify_ssl: bool = True
    
    # Privacy
    encrypted_storage: bool = False
    encryption_key: Optional[str] = None

class ZenEngineConfig:
    _config: Optional[ZenSecurityConfig] = None

    @classmethod
    def setup(cls, config: ZenSecurityConfig):
        cls._config = config
        print(f"[ZenScrape] Engine configured with profile: {config.impersonate}")

    @classmethod
    def get(cls) -> ZenSecurityConfig:
        if cls._config is None:
            # Fallback to default secure settings
            cls._config = ZenSecurityConfig()
        return cls._config
