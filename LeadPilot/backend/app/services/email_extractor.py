import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
from fake_useragent import UserAgent
import validators
import dns.resolver
from typing import List, Tuple

class EmailExtractorService:
    def __init__(self):
        self.ua = UserAgent()
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.common_prefixes = ['info', 'contact', 'hello', 'support', 'sales', 'inquiry']
    
    def extract_domain(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            return domain.replace('www.', '')
        except:
            return None
    
    def fetch_page(self, url: str, timeout: int = 10) -> str:
        try:
            headers = {'User-Agent': self.ua.random}
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text
        except:
            return None
    
    def find_emails_in_text(self, text: str) -> List[str]:
        if not text:
            return []
        emails = re.findall(self.email_pattern, text)
        emails = [email.lower() for email in emails if not email.endswith(('.png', '.jpg', '.gif'))]
        return list(set(emails))
    
    def find_contact_pages(self, base_url: str, soup) -> List[str]:
        contact_keywords = ['contact', 'about', 'connect', 'reach']
        contact_urls = []
        
        if soup:
            for link in soup.find_all('a', href=True):
                href = link['href'].lower()
                text = link.get_text().lower()
                if any(kw in href or kw in text for kw in contact_keywords):
                    full_url = urljoin(base_url, link['href'])
                    if full_url not in contact_urls:
                        contact_urls.append(full_url)
        
        domain = base_url.rstrip('/')
        for page in [f"{domain}/contact", f"{domain}/about"]:
            if page not in contact_urls:
                contact_urls.append(page)
        
        return contact_urls[:3]
    
    def extract_emails_from_website(self, website_url: str) -> Tuple[List[str], int]:
        all_emails = set()
        
        if not website_url or not validators.url(website_url):
            return list(all_emails), 0
        
        html = self.fetch_page(website_url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            
            for link in soup.find_all('a', href=True):
                if link['href'].startswith('mailto:'):
                    email = link['href'].replace('mailto:', '').split('?')[0]
                    all_emails.add(email.lower())
            
            page_emails = self.find_emails_in_text(html)
            all_emails.update(page_emails)
            
            contact_pages = self.find_contact_pages(website_url, soup)
            for contact_url in contact_pages:
                contact_html = self.fetch_page(contact_url)
                if contact_html:
                    contact_emails = self.find_emails_in_text(contact_html)
                    all_emails.update(contact_emails)
        
        confidence = 100 if all_emails else 0
        return list(all_emails), confidence
    
    def generate_email_guesses(self, website_url: str) -> List[str]:
        domain = self.extract_domain(website_url)
        if not domain:
            return []
        return [f"{prefix}@{domain}" for prefix in self.common_prefixes]
    
    def validate_email_dns(self, email: str) -> bool:
        try:
            domain = email.split('@')[1]
            dns.resolver.resolve(domain, 'MX')
            return True
        except:
            return False
