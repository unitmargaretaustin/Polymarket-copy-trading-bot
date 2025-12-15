import asyncio
import signal
from pathlib import Path

from automation.scheduler import Scheduler
from automation.tasks import CopyTradingTask
from automation.utils.config_loader import load_config
from automation.utils.logger import get_logger

LOG = get_logger("main")


async def _run() -> None:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config(
        settings_path=root / "config" / "settings.yaml",
        env_path=root / "config" / "credentials.env",
    )

    task = CopyTradingTask(cfg)
    scheduler = Scheduler(task, cfg)

    stop_event = asyncio.Event()

    def _handle_stop(*_args):
        LOG.warning("Shutdown signal received; stopping gracefully...")
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    await scheduler.run(stop_event)


def main() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
