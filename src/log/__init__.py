import logging
import os
from datetime import date

def setup_logging():
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"sync_{date.today().isoformat()}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return logging.getLogger("aw-sync")
