import logging
import sys

from .bot import run
from .config import Config, ConfigError


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        config = Config.from_env()
    except ConfigError as e:
        logging.getLogger(__name__).error("設定エラー: %s", e)
        return 2
    run(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
