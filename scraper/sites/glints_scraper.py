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
    def __init__(self, base_url: str | None = None, headless: bool = True, delay: float | None = None, user_aget: Optional[str] = None):
        self.base_url = base_url or GLINTS_URL
        self.headless = headless
        self.delay = DEFAULT_DELAY if delay is None else delay
        self.user_agent = user_aget or DEFAULT_USER_AGENT
        log.debug(f"GlintsScraper init: {self.base_url}, {self.headless}, {self.delay}, {self.user_aget}")

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
        with PlaywrightHelper.browser_context() as (pw, browser):
            try:
                # Buka tab baru
                page, context = PlaywrightHelper.create_page_with_ua(browser, self.user_agent)
                page.goto(self.base_url, timeout=60000)
                time.sleep(self.delay)

                # Jumlah hasil scroll sebelumnya
                prev_count = 0
                # Batas maksimal percobaan scroll
                max_scroll = 30
                # Jumlah percobaan scroll berturut-turut tanpa hasil baru
                scroll_tries = 0

                # Berjalan selama results belum mencapai limit dan percobaan scroll belum melebihi max_scroll
                while len(results) < limit and scroll_tries < max_scroll:
                    # Ambil semua elemen <a> yang hrefnya mengandung /opportunities
                    job_cards = page.query_selector_all("a[href*='/opportunities/']")
                    log.debug(f"Found {len(job_cards)} candidate anchors")

                    for anchor in job_cards:
                        try:
                            href = anchor.get_attribute("href")
                            # Normalisasi url
                            if not href:
                                continue
                            url = href if href.startswith("http") else f"https://glints.com/{href}"

                            # Ekstrak title
                            title_elem = anchor.query_selector("h3") or anchor.query_selector("h2")
                            title = title_elem.inner_text().strip() if title_elem else None

                            # Ekstrak nama perusahaan
                            company_elem = anchor.query_selector("div:has(span.company)") or anchor.query_selector("p:has(span)")
                            company = company_elem.inner_text().strip() if company_elem else None

                            # Ekstrak lokasi
                            location_elem = anchor.query_selector("p span")
                            location = location_elem.inner_text().strip() if location_elem else None

                            # Mencegah duplikasi
                            if any(r["url"] == url for r in results):
                                continue

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
                            
                        except Exception as e:
                            log.debug(f"Error parsing anchor: {e}")
                            continue

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
                    
            finally:
                browser.close()
                pw.stop()
    
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
        with PlaywrightHelper.browser_context() as (pw, browser):
            try:
                # Buka tab baru
                page, context = PlaywrightHelper.create_page_with_ua(browser, self.user_agent)
                try:
                    page.goto(url, timeout=60000)
                except PlaywrightTimeout:
                    log.warning(f"Timeout opening {url}")
                    return data
                
                # Jeda agar halaman termuat
                page.wait_for_load_state('networkidle')

                # Ekstrak data deskripsi
                try:
                    if page.query_selector("div[data-testid='job-description']"):
                        desc = page.inner_text("div[data-testid='job-description']").strip()
                    elif page.query_selector("div.job-description"):
                        desc = page.inner_text("div.job-description").strip()
                    else:
                        desc = page.inner_text("main").strip()[:5000]
                    
                    data["description"] = desc
                except Exception as e:
                    log.debug(f"Could not extract description: {e}")

                # Ekstrak data gaji
                try:
                    if page.query_selector("span[data-testid='salary-range']"):
                        data['salary'] = page.inner_text("span[data-testid='salary-range']").strip()
                    elif page.query_selector("div:has(span.salary)"):
                        data['salary'] = page.inner_text("div:has(span.salary)")
                except Exception:
                    pass
                
                # Ekstrak data requirements
                try:
                    bullets = page.query_selector_all("div[data-testid='job-description'] ul li")

                    if not bullets:
                        bullets = page.query_selector_all("main ul li")
                    reqs = [b.inner_text().strip() for b in bullets] if bullets else None
                    data['requirements'] = reqs
                except Exception:
                    data['requirements'] = None

                # Ekstrak tanggal posting
                try:
                    if page.query_selector("time"):
                        data['posted'] = page.query_selector("time").get_attribute("datetime")
                except Exception:
                    data['posted'] = None

                return data
            finally:
                context.close()
                browser.close()
                pw.stop()
    
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

        # Tempat menyimpan full jobs data
        full_jobs = []
        # Ambil detail setiap listing
        for idx, item in enumerate(listings, start=1):
            log.info(f"Fetching detail {idx}, {len(listings)}, {item.get("url")}")
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
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(full_jobs, f, ensure_ascii=False, indent=2)
            log.info(f"Saved Json to {out_json}")
        
        if save_csv:
            csv_path = out_json.replace(".json", ".csv")
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
    
    def get_site_name(self) -> str:
        return "Glints"