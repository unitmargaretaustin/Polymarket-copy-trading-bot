import asyncio
import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from automation.utils.logger import get_logger
from automation.utils.proxy_manager import ProxyManager

LOG = get_logger("tasks")


@dataclass(frozen=True)
class LeaderTrade:
    """
    Normalized representation of a leader trade event.
    """
    leader_wallet: str
    event_id: str                  # unique idempotency key for this leader trade
    market_id: str
    market_title: str
    side: str                      # "BUY" or "SELL"
    outcome: str                   # e.g., "YES" / "NO"
    price: float                   # observed price
    size: float                    # observed size (shares or $ - depends on your normalization)
    ts: float                      # epoch seconds


@dataclass(frozen=True)
class ExecutionDecision:
    allow: bool
    reason: str
    copy_size: float
    limit_price: float
    mode: str                      # "MIRROR" or "INDEPENDENT"


class CopyTradingTask:
    """
    Browser automation skeleton for Polymarket copy trading.

    Notes:
    - This implementation focuses on orchestration, risk gating, state, and logging.
    - You must implement the Polymarket-specific trade discovery and order placement details.
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.root = Path(__file__).resolve().parents[2]
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.state_path = self.output_dir / "state.json"
        self.results_path = self.output_dir / "results.json"
        self.report_path = self.output_dir / "report.csv"

        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.proxy_manager = ProxyManager(self.cfg)

        self.state = self._load_state()
        self._ensure_report_header()

        self._circuit_breaker_failures = 0
        self._max_failures_before_pause = int(self.cfg["runtime"].get("circuit_breaker_failures", 8))
        self._pause_seconds = int(self.cfg["runtime"].get("circuit_breaker_pause_seconds", 60))

    async def start(self) -> None:
        LOG.info("Starting CopyTradingTask...")

        self.playwright = await async_playwright().start()

        proxy = self.proxy_manager.get_proxy_for_worker()
        browser_args = {
            "headless": bool(self.cfg["browser"].get("headless", True)),
        }
        if proxy:
            browser_args["proxy"] = proxy

        self.browser = await self.playwright.chromium.launch(**browser_args)

        storage_state_path = self.cfg["browser"].get("storage_state_path")
        context_args = {}
        if storage_state_path and Path(storage_state_path).exists():
            context_args["storage_state"] = storage_state_path

        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()

        await self._maybe_login()
        LOG.info("Task started.")

    async def stop(self) -> None:
        LOG.info("Stopping CopyTradingTask...")

        try:
            if self.context:
                # Save storage state for session persistence (optional)
                storage_state_path = self.cfg["browser"].get("storage_state_path")
                if storage_state_path:
                    await self.context.storage_state(path=storage_state_path)
        except Exception:
            LOG.exception("Failed to save storage_state.")

        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self._persist_state()
        LOG.info("Task stopped.")

    async def step(self) -> None:
        """
        One polling/processing cycle:
        - fetch leader trades since last checkpoint
        - dedupe
        - evaluate risk rules
        - place orders
        - persist state + output
        """
        if self._circuit_breaker_failures >= self._max_failures_before_pause:
            LOG.warning(
                "Circuit breaker active (failures=%d). Pausing for %ds",
                self._circuit_breaker_failures,
                self._pause_seconds,
            )
            await asyncio.sleep(self._pause_seconds)
            self._circuit_breaker_failures = 0

        assert self.page is not None, "Page not initialized"

        leaders = self.cfg["leaders"]["wallets"]
        LOG.debug("Polling leaders=%d", len(leaders))

        try:
            new_trades = await self._discover_new_leader_trades(leaders)
            if not new_trades:
                return

            executed = 0
            for trade in new_trades:
                if self._is_duplicate(trade):
                    continue

                decision = await self._evaluate_trade(trade)
                self._record_seen(trade)

                if not decision.allow:
                    self._append_result(trade, decision, status="SKIPPED")
                    self._append_report_row(trade, decision, status="SKIPPED")
                    continue

                ok, details = await self._place_copy_order(trade, decision)
                status = "FILLED" if ok else "FAILED"

                self._append_result(trade, decision, status=status, extra=details)
                self._append_report_row(trade, decision, status=status, extra=details)

                if ok:
                    executed += 1

            if executed:
                LOG.info("Executed %d copy orders this cycle.", executed)

            self._persist_state()
        except Exception:
            self._circuit_breaker_failures += 1
            raise

    # -----------------------------
    # Leader trade discovery (TODO)
    # -----------------------------
    async def _discover_new_leader_trades(self, leaders: List[str]) -> List[LeaderTrade]:
        """
        Return a list of leader trades newer than our checkpoint.

        You must implement this based on how you want to observe leader activity:
        - UI-based: visit leader profile pages and parse recent trades
        - API-based: if you have a stable endpoint and auth model (not provided here)

        This skeleton uses UI-based placeholders.
        """
        since_ts = float(self.state.get("checkpoint", 0.0))
        now = time.time()

        trades: List[LeaderTrade] = []

        # TODO: Implement for Polymarket
        # Suggested approach:
        # 1) For each leader wallet:
        #    - Navigate to a "recent activity" view for that wallet
        #    - Parse entries (market, side, outcome, size, price, timestamp)
        #    - Convert to LeaderTrade with a stable event_id
        #
        # For now, we return an empty list unless demo mode is enabled.
        if bool(self.cfg["runtime"].get("demo_mode", False)):
            # Create one fake trade occasionally to test pipeline end-to-end.
            if random.random() < 0.15:
                leader = random.choice(leaders)
                event_id = f"demo:{leader}:{int(now)}"
                trades.append(
                    LeaderTrade(
                        leader_wallet=leader,
                        event_id=event_id,
                        market_id="demo-market-123",
                        market_title="Demo Market",
                        side="BUY",
                        outcome="YES",
                        price=0.52,
                        size=10.0,
                        ts=now,
                    )
                )

        # Update checkpoint optimistically to "now" (safer: to max(trade.ts) after sorting)
        self.state["checkpoint"] = max(since_ts, now)
        return [t for t in trades if t.ts > since_ts]

    # -----------------------------
    # Risk gating / sizing
    # -----------------------------
    async def _evaluate_trade(self, trade: LeaderTrade) -> ExecutionDecision:
        """
        Validate and compute follower order parameters.
        """
        risk = self.cfg["risk"]
        copy = self.cfg["copy_mode"]

        # Exposure checks
        if not self._within_exposure_limits(trade):
            return ExecutionDecision(False, "Exposure limit reached", 0.0, 0.0, mode="MIRROR")

        # Liquidity/spread/slippage check (placeholder)
        liquidity_ok, reason = await self._check_liquidity_and_slippage(trade)
        if not liquidity_ok:
            return ExecutionDecision(False, reason, 0.0, 0.0, mode="MIRROR")

        # Compute size
        copy_size = self._compute_copy_size(trade)
        if copy_size <= 0:
            return ExecutionDecision(False, "Computed copy size is zero", 0.0, 0.0, mode="MIRROR")

        # Compute limit price with slippage cap
        limit_price = self._compute_limit_price(trade)

        # Exit mode selection
        mode = "MIRROR" if bool(risk.get("mirror_exits", True)) else "INDEPENDENT"

        return ExecutionDecision(True, "OK", copy_size, limit_price, mode=mode)

    def _compute_copy_size(self, trade: LeaderTrade) -> float:
        mode = self.cfg["copy_mode"]["mode"].lower()  # "proportional" or "fixed"
        if mode == "fixed":
            return float(self.cfg["copy_mode"].get("fixed_amount", 5.0))

        # proportional
        leader_unit = float(self.cfg["copy_mode"].get("leader_unit", 1.0))
        follower_unit = float(self.cfg["copy_mode"].get("follower_unit", 1.0))
        ratio = follower_unit / max(leader_unit, 1e-9)
        return float(max(0.0, trade.size * ratio))

    def _compute_limit_price(self, trade: LeaderTrade) -> float:
        """
        Applies slippage cap around observed trade price.
        BUY: limit <= price + cap
        SELL: limit >= price - cap
        """
        cap = float(self.cfg["risk"].get("max_slippage", 0.02))
        if trade.side.upper() == "BUY":
            return min(0.999, trade.price + cap)
        return max(0.001, trade.price - cap)

    async def _check_liquidity_and_slippage(self, trade: LeaderTrade) -> Tuple[bool, str]:
        """
        Placeholder checks. Replace with market depth / spread checks.
        """
        min_liquidity = float(self.cfg["risk"].get("min_liquidity", 100.0))
        max_spread = float(self.cfg["risk"].get("max_spread", 0.05))

        # TODO: Implement real market checks by reading the market page / order book UI.
        # For now, accept in demo mode only, otherwise allow but mark as TODO.
        if bool(self.cfg["runtime"].get("strict_market_checks", False)):
            return False, "Market checks not implemented (strict_market_checks enabled)"

        return True, "OK"

    def _within_exposure_limits(self, trade: LeaderTrade) -> bool:
        """
        Enforces per-market and per-category exposure limits.
        Categories are a config-time mapping (market_id -> category), since scraping categories is brittle.
        """
        limits = self.cfg["risk"]["exposure_limits"]
        per_market_cap = float(limits.get("per_market", 50.0))
        per_category_cap = float(limits.get("per_category", 150.0))

        exposures = self.state.setdefault("exposures", {"markets": {}, "categories": {}})

        market_exposure = float(exposures["markets"].get(trade.market_id, 0.0))
        if market_exposure >= per_market_cap:
            return False

        category = self.cfg.get("market_categories", {}).get(trade.market_id, "uncategorized")
        category_exposure = float(exposures["categories"].get(category, 0.0))
        if category_exposure >= per_category_cap:
            return False

        return True

    # -----------------------------
    # Order execution (TODO)
    # -----------------------------
    async def _place_copy_order(self, trade: LeaderTrade, decision: ExecutionDecision) -> Tuple[bool, Dict[str, Any]]:
        """
        Place the follower limit order.

        You must implement:
        - navigate to market page
        - select YES/NO outcome
        - choose BUY/SELL
        - set limit price and size
        - submit and wait for confirmation
        - reconcile filled/partial/failed

        Returns (ok, details)
        """
        assert self.page is not None

        t0 = time.perf_counter()
        details: Dict[str, Any] = {
            "latency_ms": None,
            "order_id": None,
            "note": None,
        }

        # TODO: Implement with real selectors and flow
        if bool(self.cfg["runtime"].get("demo_mode", False)):
            await asyncio.sleep(random.uniform(0.2, 0.6))
            elapsed = (time.perf_counter() - t0) * 1000.0
            details["latency_ms"] = round(elapsed, 2)
            details["order_id"] = f"demo-order:{trade.event_id}"
            self._apply_exposure(trade, decision.copy_size)
            return True, details

        details["note"] = "Order placement not implemented. Enable demo_mode to test pipeline."
        elapsed = (time.perf_counter() - t0) * 1000.0
        details["latency_ms"] = round(elapsed, 2)
        return False, details

    def _apply_exposure(self, trade: LeaderTrade, amount: float) -> None:
        exposures = self.state.setdefault("exposures", {"markets": {}, "categories": {}})
        exposures["markets"][trade.market_id] = float(exposures["markets"].get(trade.market_id, 0.0)) + float(amount)

        category = self.cfg.get("market_categories", {}).get(trade.market_id, "uncategorized")
        exposures["categories"][category] = float(exposures["categories"].get(category, 0.0)) + float(amount)

    # -----------------------------
    # Login/session handling (TODO)
    # -----------------------------
    async def _maybe_login(self) -> None:
        """
        If storage_state is provided and valid, you might already be logged in.
        Otherwise, implement login steps here.

        Keep credentials in config/credentials.env and avoid hardcoding.
        """
        base_url = self.cfg["polymarket"]["base_url"]
        assert self.page is not None
        await self.page.goto(base_url, wait_until="domcontentloaded")

        # TODO: Implement a robust login check and flow.
        # Example pattern:
        # - if page shows "Connect Wallet" or login button, perform steps
        # - save storage_state on stop()
        #
        # For now: no-op.
        await asyncio.sleep(0.3)

    # -----------------------------
    # State, results, reporting
    # -----------------------------
    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                LOG.exception("Failed to load state.json; starting with empty state.")
        return {
            "checkpoint": 0.0,
            "seen_events": {},
            "exposures": {"markets": {}, "categories": {}},
        }

    def _persist_state(self) -> None:
        try:
            self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception:
            LOG.exception("Failed to persist state.json")

    def _is_duplicate(self, trade: LeaderTrade) -> bool:
        seen = self.state.setdefault("seen_events", {})
        return trade.event_id in seen

    def _record_seen(self, trade: LeaderTrade) -> None:
        seen = self.state.setdefault("seen_events", {})
        seen[trade.event_id] = {
            "leader_wallet": trade.leader_wallet,
            "market_id": trade.market_id,
            "side": trade.side,
            "ts": trade.ts,
        }

        # Optional pruning
        max_seen = int(self.cfg["runtime"].get("max_seen_events", 5000))
        if len(seen) > max_seen:
            # prune oldest by ts
            items = sorted(seen.items(), key=lambda kv: kv[1].get("ts", 0.0))
            for k, _v in items[: len(seen) - max_seen]:
                del seen[k]

    def _append_result(self, trade: LeaderTrade, decision: ExecutionDecision, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        record = {
            "status": status,
            "trade": {
                "leader_wallet": trade.leader_wallet,
                "event_id": trade.event_id,
                "market_id": trade.market_id,
                "market_title": trade.market_title,
                "side": trade.side,
                "outcome": trade.outcome,
                "price": trade.price,
                "size": trade.size,
                "ts": trade.ts,
            },
            "decision": {
                "allow": decision.allow,
                "reason": decision.reason,
                "copy_size": decision.copy_size,
                "limit_price": decision.limit_price,
                "mode": decision.mode,
            },
            "extra": extra or {},
        }

        # Append to results.json as a list (simple approach)
        try:
            if self.results_path.exists():
                data = json.loads(self.results_path.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    data = []
            else:
                data = []
            data.append(record)
            self.results_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            LOG.exception("Failed to append to results.json")

    def _ensure_report_header(self) -> None:
        if self.report_path.exists():
            return
        try:
            with self.report_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    "ts",
                    "leader_wallet",
                    "event_id",
                    "market_id",
                    "market_title",
                    "side",
                    "outcome",
                    "leader_price",
                    "leader_size",
                    "copy_size",
                    "limit_price",
                    "mode",
                    "status",
                    "reason",
                    "latency_ms",
                    "order_id",
                    "note",
                ])
        except Exception:
            LOG.exception("Failed to create report.csv")

    def _append_report_row(self, trade: LeaderTrade, decision: ExecutionDecision, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        extra = extra or {}
        try:
            with self.report_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([
                    int(trade.ts),
                    trade.leader_wallet,
                    trade.event_id,
                    trade.market_id,
                    trade.market_title,
                    trade.side,
                    trade.outcome,
                    trade.price,
                    trade.size,
                    decision.copy_size,
                    decision.limit_price,
                    decision.mode,
                    status,
                    decision.reason,
                    extra.get("latency_ms"),
                    extra.get("order_id"),
                    extra.get("note"),
                ])
        except Exception:
            LOG.exception("Failed to append row to report.csv")
