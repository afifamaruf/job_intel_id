"""
File untuk scraping glints

Name: Afif Alli Ma'ruf
Date: 2025
"""

import os
import time
import json
import csv
import logging
from tqdm import tqdm
from typing import List, Dict, Optional
from scraper.base.scraper_strategy import ScraperBase
from scraper.utils.playwright_helper import PlaywrightHelper
from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeout

# Load variable environment
load_dotenv()

# Membuat logger
log = logging.getLogger(__name__)

# Inisialisasi variable
GLINTS_URL = os.getenv("GLINTS_URL") or "https://glints.com/id/opportunities/jobs/explore?keyword=data"
DEFAULT_DELAY = float(os.getenv("SCRAPE_DELAY", 2))
DEFAULT_USER_AGENT = os.getenv("USER_AGENT", None)

class GlintsScraper(ScraperBase):
    def __init__(self, base_url: str | None = None, headless: bool = True, delay: float | None = None, user_agent: Optional[str] = None):
        self.base_url = base_url or GLINTS_URL
        self.headless = headless
        self.delay = DEFAULT_DELAY if delay is None else delay
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        log.debug(f"GlintsScraper init: {self.base_url}, {self.headless}, {self.delay}, {self.user_agent}")

    def _apply_stealth(self, page) -> None:
        """
        Menerapkan stealth script untuk menghindari deteksi bot.
        """
        page.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['id-ID', 'id', 'en-US', 'en']
            });
        """)

    def _safe_goto(self, page, url: str, max_retries: int = 3) -> bool:
        """
        Navigasi ke URL dengan retry logic

        Args:
            page: Playwright page object
            url: URL tujuan
            max_retries: Maksimal percobaan

        Returns:
        bool: True jika berhasil, False jika gagal
        """
        for attempt in range(max_retries):
            try:
                log.debug(f"Attempt {attempt + 1} to load {url}")

                # Gunakan domcontentloaded
                response = page.goto(
                    url,
                    timeout=90000,
                    wait_until="domcontentloaded"
                )

                # Tunggu network idle dengan timeout terpisah
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeout:
                    log.debug("Network idle timeout, continuing anyway...")
                
                # Cek response status
                if response and response.status >= 400:
                    log.warning(f"HTTP {response.status} for {url}")
                    if attempt < max_retries -1:
                        time.sleep(2 ** attempt)
                        continue
                    return False
                return True
            except PlaywrightTimeout as e:
                log.warning(f"Timeout attemp {attempt + 1}: {e}")
                if attempt < max_retries -1:
                    time.sleep(2 ** attempt)
                else:
                    return False
            except Exception as e:
                log.error(f"Unexpected error: {e}")
                if attempt < max_retries -1:
                    time.sleep(2 ** attempt)
                else:
                    return False
        return False

    def fetch_listings(self, limit: int = 100) -> List[Dict]:
        """
        Mengambil daftar job card dari halaman eksplorasi Glints.
        
        Args:
            limit(int=100): batas pengumpulan daftar lowongan

        Returns:
            List[Dict]: Mengembalikan list dict
        """

        # List kosong untuk menyimpan hasil
        results: List[Dict] = []

        # Start playwright dan buka browser
        with PlaywrightHelper.browser_context(headless=self.headless) as (_, browser):
        
            # Buka tab baru
            page, context = PlaywrightHelper.create_page_with_ua(browser, self.user_agent)
            
            # Terapkan stealth
            self._apply_stealth(page)

            # Navigasi dengan retry
            if not self._safe_goto(page, self.base_url):
                log.error("Failed to load page after retries")
                context.close()
                return results

            time.sleep(self.delay)

            # Jumlah hasil scroll sebelumnya
            prev_count = 0
            # Batas maksimal percobaan scroll
            max_scroll = 30
            # Jumlah percobaan scroll berturut-turut tanpa hasil baru
            scroll_tries = 0

            # Berjalan selama results belum mencapai limit dan percobaan scroll belum melebihi max_scroll
            while len(results) < limit and scroll_tries < max_scroll:
                # Tunggu hingga job cards muncul
                try:
                    page.wait_for_selector('a[href*="/opportunities/jobs/"]', timeout=30000)
                except PlaywrightTimeout:
                    log.warning("Timeout waiting for job cards")
                    break

                # Ambil semua elemen <a> yang hrefnya mengandung /opportunities
                job_cards = page.query_selector_all('div[class*="JobCard"], article, div[class*="OpportunityCard"]')

                if not job_cards:
                    job_cards = page.query_selector_all('a[href*="/opportunities/jobs/"]')
                log.debug(f"Found {len(job_cards)} candidate anchors")

                for card in job_cards:
                    if len(results) >= limit:
                        break

                    # Ekstrak URL
                    anchor = card.query_selector('a[href*="/opportunities/jobs/"]')
                    if not anchor:
                        # Jika card sendiri adalah anchor
                        anchor = card if card.evaluate('el => el.tagName') == 'A' else None
                    if not anchor:
                        continue

                    log.debug(f"Full Anchor HTML: {anchor.evaluate('el => el.outerHTML')}")
                    href = anchor.get_attribute("href")
                    # Normalisasi url
                    if not href:
                        link_elem = anchor.query_selector('a[href*="/opportunities/"]')
                        href = link_elem.get_attribute("href") if link_elem else None
                    if not href:
                        continue
                    url = href if href.startswith("http") else f"https://glints.com/{href}"

                    # Ekstrak title
                    title_elem = card.query_selector(
                        '[data-testid*="title"], '
                        '[class*="JobCardTitle"], '
                        'h3, h2, '
                        'a[href*="/opportunities/jobs/"]'
                    )
                    title = title_elem.inner_text().strip() if title_elem else None

                    # Ekstrak nama perusahaan
                    company_elem = card.query_selector(
                        '[data-testid*="company-name"], '
                        '[class*="CompanyLink"], '
                        '[class*="CompanyName"], '
                        'a[href*="/companies/"]'
                    )
                    company = company_elem.inner_text().strip() if company_elem else None

                    # Ekstrak lokasi
                    location_elem = card.query_selector(
                        '[data-testid*="location"], '
                        '[class*="Location"], '
                        'svg[class*="location"] + span, '
                        '[class*="CityLabel"]'
                    )
                    location = location_elem.inner_text().strip() if location_elem else None

                    # Mencegah duplikasi
                    if any(r["url"] == url for r in results):
                        continue
                    
                    # Fallback: pakai text lines dari seluruh anchor
                    if not (title and company and location):
                        lines = [
                            l.strip()
                            for l in anchor.inner_text().split("\n")
                            if l.strip()
                        ]
                        if not title and len(lines) >= 1:
                            title = lines[0]
                        if not company and len(lines) >=2:
                            company = lines[1]
                        if not location and len(lines) >= 3:
                            location = lines[2]

                    # Add results 1 lowongan ke dalam list
                    results.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url
                        })

                    # Jika results sudah mencapai limit, keluar dari loop
                    if len(results) >= limit:
                        break
                            
                    if len(results) == prev_count:
                        scroll_tries += 1
                        page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                        time.sleep(self.delay + 0.5)
                    else:
                        prev_count = len(results)
                        scroll_tries = 0
                        
            # Tutup context
            context.close()
            log.info(f"Collected {results} listing summaries")
        return results[:limit]
                    
    
    def fetch_job_detail(self, url: str) -> Dict:
        """
        Buka halaman job detail dan ambil deskripsi

        Args:
            url(str): URL halaman yang akan di scraping


        Returns:
            Dict: Mengembalikan Dictionary
        """

        # Data awal
        data = {
            "description": None,
            "salary": None,
            "requirements": None,
            "posted": None,
            "url": url
        }

        # Buka browser
        with PlaywrightHelper.browser_context(headless=self.headless) as (_, browser):
            
            # Buka tab baru
            page, context = PlaywrightHelper.create_page_with_ua(browser, self.user_agent)
            
            # Terapkan stealth
            self._apply_stealth(page)

            # Navigasi dengan retry
            if not self._safe_goto(page, url):
                log.warning(f"Failed to load detail page: {url}")
                context.close()
                return data

            # Ekstrak data deskripsi
            try:
                desc_selectors = [
                    "div[data-testid='job-description']",
                    "div.job-description",
                    "div[class*='JobDescription']",
                    "div[class*='jobDescription']",
                ]
                
                desc = None
                for selector in desc_selectors:
                    if page.query_selector(selector):
                        desc = page.inner_text(selector).strip()
                        break
                
                if not desc:
                    # Fallback ke main content
                    desc = page.inner_text("main").strip()[:5000]
                
                data["description"] = desc
            except Exception as e:
                log.debug(f"Could not extract description: {e}")

            # Ekstrak data gaji
            try:
                salary_selectors = [
                    'span[data-testid="salary-range"]',
                    'div[class*="SalaryRange"] span',
                    'span[class*="salary"]',
                    'div[class*="SalaryJobOverview"] span'
                ]
                
                for selector in salary_selectors:
                    elem = page.query_selector(selector)
                    if elem:
                        data['salary'] = elem.inner_text().strip()
                        break
            except Exception as e:
                log.debug(f"Could not extract salary: {e}")
                
            # Ekstrak data requirements
            try:
                bullets = page.query_selector_all(
                    "div[data-testid='job-description'] ul li"
                )
                if not bullets:
                    bullets = page.query_selector_all("main ul li")
                    
                if bullets:
                    data['requirements'] = [b.inner_text().strip() for b in bullets[:20]]
            except Exception as e:
                log.debug(f"Could not extract requirements: {e}")

            # Ekstrak tanggal posting
            try:
                posted = page.query_selector('span[class*="TopFoldsc__PostedAt"]')
                if posted:
                    data['posted'] = posted.inner_text().strip()
            except Exception as e:
                log.debug(f"Could not extract posted date: {e}")
            context.close()
        return data
    
    def scrape_and_save(self, limit: int = 100, out_path: str | None = None, save_csv: bool = False) -> List[Dict]:
        """
        Method untuk memulai scrape dan menyimpannya ke file json/csv

        Args:
            limit(int=100): Batas minimal data yang di scrape
            out_path(str): Alamat file output
            save_csv(bool): Simpan sebagai csv atau tidak

        
        Returns:
            List[Dict]: List berisi dictionary data pekerjaan
        """

        # Mulai proses scraping
        log.info(f"Start full scrape: limit={limit}")
        listings = self.fetch_listings(limit=limit)
        log.info(f"Jumlah listings didapat: {len(listings)}")

        # Tempat menyimpan full jobs data
        full_jobs = []
        # Ambil detail setiap listing
        for idx, item in tqdm(enumerate(listings, start=1), total=len(listings), desc="Fetching job details"):
            log.info(f"Fetching detail {idx}, {len(listings)}, {item.get('url')}")
            try:
                detail = self.fetch_job_detail(item["url"])
            except Exception as e:
                detail = {}

            # Gabungkan list job dengan detail job
            merged = {**item, **detail}
            full_jobs.append(merged)

            time.sleep(self.delay)
        
        if out_path:
            out_json = out_path if out_path.endswith(".json") else f"{out_path}.json"
            # Buat direktori jika belum ada
            os.makedirs(os.path.dirname(out_json), exist_ok=True)

            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(full_jobs, f, ensure_ascii=False, indent=2)
            log.info(f"Saved Json to {out_json}")
        
        if save_csv:
            csv_path = out_json.replace(".json", ".csv")
            # Buat direktori jika belum ada (meskipun sudah dibuat untuk JSON, tapi aman)
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)

            with open(csv_path, "w", encoding="utf-8", newline="") as cf:
                if full_jobs:
                    headers = list(full_jobs[0].keys())
                    writer = csv.DictWriter(cf, fieldnames=headers)
                    writer.writeheader()
                    for r in full_jobs:
                        row = r.copy()
                        if isinstance(row.get("requirements"), list):
                            row["requirements"] = "; ".join(row["requirements"])
                        writer.writerow(row)
            log.info(f"Saved CSV to {csv_path}")

        return full_jobs