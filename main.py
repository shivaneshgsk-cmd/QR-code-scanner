"""
main.py — Entry Point for Advanced QR Code Detector & Decoder

Initializes logging, creates required directories,
and launches the main Dashboard application.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime


def setup_logging():
    """Configure application logging."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"qr_scanner_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("  Advanced QR Code Detector & Decoder")
    logger.info("  Starting application...")
    logger.info("=" * 60)
    return logger


def setup_directories():
    """Create required application directories."""
    base = Path(__file__).parent
    dirs = [
        base / "assets",
        base / "logs",
    ]
    for d in dirs:
        d.mkdir(exist_ok=True)


def main():
    """Main entry point."""
    # Setup
    logger = setup_logging()
    setup_directories()

    try:
        # Import and launch dashboard
        from ui.dashboard import Dashboard

        logger.info("Launching dashboard...")
        app = Dashboard()
        app.mainloop()

    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error(
            "Please install dependencies: pip install -r requirements.txt"
        )
        print(f"\n❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        sys.exit(1)

    finally:
        logger.info("Application closed")


if __name__ == "__main__":
    main()
