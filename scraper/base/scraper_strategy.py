"""
File yang berisi class ScraperBase 
yang berfungsi sebagai interface untuk semua scraper

Name: Afif Alli Ma'ruf
Date: 2025
"""

from abc import ABC, abstractmethod

class ScraperBase(ABC):

    @abstractmethod
    def fetch_listings(self) -> list[dict]:
        """
        Return:
            [
                {
                    "title": "...",
                    "company": "...",
                    "detail_url": "..."
                },
                ...
            ]
        """
        pass

    @abstractmethod
    def fetch_job_detail(self, url:str) -> dict:
        """
        Return:
            {
                "title": "...",
                "company": "...",
                "location": "...",
                "salary": "...",
                "description": "...",
                "requirements": [...]
            }
        """
        pass
    @abstractmethod
    def get_site_name(self) -> str:
        """
        Mengembalikan nama situs.
        """
        pass