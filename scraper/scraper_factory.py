"""
File berisi Scraper Factory
untuk membuat object scraper

Name: Afif Alli Ma'ruf
Date: 2025
"""

from scraper.sites.glints_scraper import GlintsScraper

class ScraperFactory:
    
    """
    Factory untuk memilih scraper berdasarkan nama situs.
    """

    # Registrasi situs
    registry = {
        "glints": GlintsScraper,
    }

    @staticmethod
    def create_scraper(site: str, **kwargs):
        """
        Args:
            site(str): nama website yang akan di scrape
            **kwargs: keyword arguments
        """
        
        # Normalisasi input
        site = site.lower()

        if site not in ScraperFactory.registry:
            available = ", ".join(ScraperFactory.registry.keys())
            raise ValueError(
                f"Scraper '{site}' not found. "
                f"Choices: {available}"
            )
        
        return ScraperFactory.registry[site](**kwargs)