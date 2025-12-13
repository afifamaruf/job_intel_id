"""
File yang berisi class PlaywrightHelper.

Name: Afif Alli Ma'ruf
Date: 2025
"""

from playwright.sync_api import sync_playwright, Playwright, Browser
from typing import Generator
from contextlib import contextmanager
import logging


log = logging.getLogger(__name__)

class PlaywrightHelper:
    @staticmethod
    def start_browser(headless: bool = True, user_agent: str | None = None) -> tuple["Playwright", "Browser"]:
        """
        Mulai playwright

        Args:
            headless: Run browser tanpa GUI
            user_agent: User agent custom

        Returns:
            Tuple(playwright, browser)
        
        Note:
            Harus panggil browser.close() dan playwright.stop()
            ketika memanggil method ini
        """

        # Inisialisasi playwright
        playwright = sync_playwright().start()

        try:
            # Buka browser
            browser = playwright.chromium.launch(headless=headless)

            log.debug(
                "Playwright started (headless=%s, user_agent=%s)",
                headless,
                user_agent or "default"
            )

            return playwright, browser
        
        except Exception as e:
            # Cleanup jika gagal
            playwright.stop()
            log.error(f"Failed to launch browser: {e}")

    @staticmethod
    @contextmanager
    def browser_context(
        headless: bool = True,
        user_agent: str | None = None
    ) -> Generator[tuple["Playwright", "Browser"], None, None]:
        """
        Context manager untuk auto-cleanup resources

        Usage:
            with PlaywrightHelper.browser_context() as (pw, browser):
                page = browser.new_page()
                page.goto("https://example.com")
        """

        playwright = None
        browser = None

        try:
            playwright = sync_playwright.start()
            browser = playwright.chromium.launch(headless=headless)

            log.debug(f"Playwright started ({headless})")
            yield playwright, browser

        finally:
            if browser:
                browser.close()
                log.debug("Browser closed")
            if playwright:
                playwright.stop()
                log.debug("Playwright stopped")
    
    @staticmethod
    def create_page_with_ua(browser: "Browser", user_agent: str):
        """
        Membuat halaman baru dengan user-agent custom
        """
        context = browser.new_context(user_agent=user_agent)
        page = context.new_page()
        return page, context