import random
from typing import Any, Dict, Optional

from automation.utils.logger import get_logger

LOG = get_logger("proxy_manager")


class ProxyManager:
    """
    Handles optional proxy selection. For Playwright, proxy dict typically looks like:
    {"server": "http://host:port", "username": "...", "password": "..."}
    """

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.proxies = cfg.get("proxies", {}).get("pool", []) or []
        self.mode = (cfg.get("proxies", {}).get("mode", "none") or "none").lower()

    def get_proxy_for_worker(self) -> Optional[Dict[str, str]]:
        if self.mode == "none" or not self.proxies:
            return None

        if self.mode == "random":
            p = random.choice(self.proxies)
            LOG.debug("Selected proxy (random): %s", p.get("server"))
            return p

        if self.mode == "sticky":
            # Sticky can be implemented by pinning to first proxy or hashing by worker id.
            p = self.proxies[0]
            LOG.debug("Selected proxy (sticky): %s", p.get("server"))
            return p

        LOG.warning("Unknown proxy mode=%s. Disabling proxies.", self.mode)
        return None
