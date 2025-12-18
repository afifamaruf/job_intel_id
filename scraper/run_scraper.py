"""
Script untuk menjalankan Scraper dari command line.

Name: Afif Alli Ma'ruf
Date: 2025
"""

import argparse
import logging

from scraper.sites.glints_scraper import GlintsScraper
from scraper.scraper_factory import ScraperFactory


def parse_args() -> argparse.Namespace:
    """Parsing argumen dari command line."""

    parser = argparse.ArgumentParser(
        description="Run the scraper and save the results."
    )

    parser.add_argument(
        "--site",
        type=str,
        choices=ScraperFactory.list_available(),
        default="glints",
        help="Name of the site to scrape (default: glints)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of vacancies taken (default: 100)"
    )

    parser.add_argument(
        "--out",
        type=str,
        default="glints_jobs",
        help="Output file path (without extension, default: glints_jobs)"
    )

    parser.add_argument(
        "--csv",
        action="store_true",
        help="If set, results are also saved as CSV."
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser headless (without GUI display)"
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override GLINTS_URL from .env (opsional)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Level log: DEBUG, INFO, WARNING, ERROR (default: INFO)"
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log = logging.getLogger(__name__)

    # Susun kwargs untuk dikirim ke factory
    kwargs = {
        "base_url": args.base_url,
        "headless": args.headless
    }

    if args.user_agent:
        kwargs["user_agent"] = args.user_agent

    # inisialisasi scraper
    scraper = ScraperFactory.create_scraper(args.site, **kwargs)

    log.info(f"Running scraper {args.site} with limit={args.limit}")

    scraper.scrape_and_save(
        limit=args.limit,
        out_path=args.out,
        save_csv=args.csv
    )

    if __name__ == "__main__":
        main()