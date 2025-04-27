"""
Enhanced Indeed Job Scraper with AI-Based Job Matching

Features:
- Robust Cloudflare CAPTCHA bypass
- AI-based job matching using Groq/DeepSeek
- Excel-based data storage with proper error handling
- Configurable job limits per company
- Duplicate prevention
"""
from pathlib import Path
import time
import re
import json
import random
import traceback
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from twocaptcha import TwoCaptcha
from openpyxl import load_workbook, Workbook
from groq import Groq


# Constants
CAPTCHA_API_KEY = "31300b1641332536703a487a87b3f4f7"  # Replace with your actual API key
DEEPSEEK_API_KEY = "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"  # Replace with your actual API key
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.77 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 12; SM-G996U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Mobile Safari/537.36"
]
TEST_SITES = [
    "https://1.1.1.1",
    "https://www.cloudflare.com",
    "https://example.com",
    "https://www.bing.com"
]

class IndeedJobScraper:
    def __init__(self):
        self.driver = None
        self.wb = None
        self.sheet = None
        self.total_saved = 0
        self.solver = TwoCaptcha(CAPTCHA_API_KEY)
        # Get the directory where scrapper.py is located
        current_dir = Path(__file__).parent  # Points to scrapapply\indeed
        self.EXCEL_PATH = current_dir / "static" / "indeed" / "download" / "indeed_jobs.xlsx"
    
    def check_internet_connection(self):
        """Verify internet connectivity by testing multiple reliable websites."""
        for site in TEST_SITES:
            try:
                response = requests.get(site, timeout=10)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                continue
        return False
    
    def initialize_browser(self, headless=True):
        """Configure and initialize Chrome WebDriver with specified options."""
        print("\n[+] Initializing browser instance")
        
        options = Options()
        service = Service(ChromeDriverManager().install())
        
        if headless:
            options.add_argument("--headless")
        
        # Browser configuration
        options.add_argument("window-size=1920x1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--lang=en-US")
        options.set_capability("goog:loggingPrefs", {"browser": "INFO"})
        options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
        
        self.driver = webdriver.Chrome(options=options, service=service)
        self.driver.implicitly_wait(4)
        return self.driver
    

        
    # CLOUDFLARE BYPASS LOGIC

    def initialize_workbook(self):
        """Initialize or load the Excel workbook."""
        try:
            self.wb = Workbook()
            self.sheet = self.wb.active
            header = ["Company", "Position", "Location", "Link", "Match %"]
            self.sheet.append(header)
            self.wb.save(self.EXCEL_PATH)
            print("[+] Workbook initialized successfully")
            return True
        except Exception as e:
            print(f"[-] Error initializing workbook: {e}")
            return False
    
    def extract_jobs(self, about_me, job_urls_list, ignore_companies_list, jobs_per_company=3, max_items=50):
        """Main function to orchestrate job extraction process."""
        if not self.initialize_workbook():
            return False
        
        self.about_me = about_me
        self.ignore_companies = [comp.strip().lower() for comp in ignore_companies_list] if ignore_companies_list else []
        self.jobs_per_company = jobs_per_company
        self.max_items = max_items
        
        try:
            self.driver = self.initialize_browser(headless=False)  # Start with visible browser for debugging
            
            for link in job_urls_list:
                if self.total_saved >= self.max_items:
                    break                    
                link = link.strip()
                if not link:
                    continue
                    
                print(f"\n[+] Processing URL: {link}")
                try:
                    self._crawl_job_listings(link)
                except Exception as e:
                    print(f"[-] Error processing {link}: {e}")
                    traceback.print_exc()
                    continue
        
        except Exception as e:
            print(f"[-] Unexpected error in job extraction: {e}")
            traceback.print_exc()
        finally:
            if self.driver:
                self.driver.quit()
            if self.wb:
                self.wb.save(self.EXCEL_PATH)
            print(f"\n[+] Job extraction complete. Saved {self.total_saved} jobs")
            return self.total_saved > 0
    
    def _crawl_job_listings(self, link):
        """Extract and process job listings from current page."""
        # Track jobs per company
        company_counts = {}
        unique_jobs = set()
        
        # Navigate to initial page
        self._safe_get(link)
        
        page_number = 1
        while self.total_saved < self.max_items:
            # Handle CAPTCHA if present
            if "Additional Verification Required" in self.driver.page_source:
                time.sleep(5)
                try:
                    self.bypass_cloudflare()
                except Exception as captcha_error:
                    print(f"CAPTCHA handling error for {link}: {captcha_error}")  
                    continue
            
            # Wait for page to load
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'jobsearch-LeftPane')]"))
                )
            except:
                print("[-] Page load timeout")
                break
            
            # Scroll to load all elements
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Extract job elements
            try:
                job_cards = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'job_seen_beacon')]")
                print(f"[+] Found {len(job_cards)} jobs on page {page_number}")
                
                for card in job_cards:
                    if self.total_saved >= self.max_items:
                        break
                        
                    try:
                        company_elem = card.find_element(By.XPATH, ".//span[@data-testid='company-name']")
                        title_elem = card.find_element(By.XPATH, ".//h2[contains(@class, 'jobTitle')]/a")
                        location_elem = card.find_element(By.XPATH, ".//div[@data-testid='text-location']")
                        
                        company = company_elem.text.strip()
                        position = title_elem.text.strip()
                        location = location_elem.text.strip()
                        job_url = title_elem.get_attribute("href")
                        job_id = self._extract_job_id(job_url)
                        
                        # Skip conditions
                        if (not job_id or job_id in unique_jobs or 
                            company.lower() in self.ignore_companies or 
                            company_counts.get(company.lower(), 0) >= self.jobs_per_company):
                            continue
                            
                        # Process this job
                        match_percentage = self._get_job_match(position)
                        if match_percentage > 30:  # Only save if match is above threshold
                            self._save_job(company, position, location, job_url, match_percentage)
                            unique_jobs.add(job_id)
                            company_counts[company.lower()] = company_counts.get(company.lower(), 0) + 1
                            self.total_saved += 1
                            
                    except Exception as e:
                        print(f"[-] Error processing job card: {e}")
                        continue
                        
            except Exception as e:
                print(f"[-] Error extracting jobs: {e}")
                break
            
            # Pagination - try to go to next page
            try:
                next_button = self.driver.find_element(By.XPATH, f"//a[@data-testid='pagination-page-{page_number + 1}']")
                if next_button:
                    next_button.click()
                    page_number += 1
                    time.sleep(random.uniform(3, 6))
                else:
                    break
            except:
                print("[+] No more pages found")
                break
    
    def _safe_get(self, url, max_retries=3):
        """Safely navigate to URL with retries and connection checks."""
        retries = 0
        while retries < max_retries:
            try:
                if not self.check_internet_connection():
                    print("[-] Waiting for internet connection...")
                    time.sleep(10)
                    continue
                    
                self.driver.get(url)
                time.sleep(random.uniform(3, 6))
                return True
            except Exception as e:
                retries += 1
                print(f"[-] Navigation failed (attempt {retries}): {e}")
                time.sleep(5)
        return False
    
    def _extract_job_id(self, url):
        """Extract job ID from URL."""
        if not url:
            return None
        try:
            if "/viewjob" in url:
                return url.split("/viewjob/")[1].split("?")[0]
            elif "jk=" in url:
                return url.split("jk=")[1].split("&")[0]
            elif "/view/" in url:
                return url.split("/view/")[1].split("/")[0]
        except:
            return None
        return None
    
    def _get_job_match(self, position):
        """Get job match percentage from AI."""
        prompt = f"""
        Analyze how well this job position matches the candidate's profile.
        Candidate profile: {self.about_me}
        Job position: {position}
        
        Return only a single number between 0-100 representing the match percentage.
        """
        
        try:
            client = Groq(api_key=DEEPSEEK_API_KEY)
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=10,
                top_p=1
            )
            
            # Extract the first number found in response
            match = re.search(r'\b\d{1,3}\b', response.choices[0].message.content)
            if match:
                percentage = min(100, max(0, int(match.group())))  # Ensure it's 0-100
                print(f"[AI] Match for '{position}': {percentage}%")
                return percentage
        except Exception as e:
            print(f"[-] AI assessment failed: {e}")
        return 0  # Default to 0 if error occurs
    
    def _save_job(self, company, position, location, url, match):
        """Save job to Excel workbook."""
        try:
            self.sheet.append([company, position, location, url, match])
            self.wb.save(self.EXCEL_PATH)
            print(f"[+] Saved: {company} - {position} ({match}% match)")
        except Exception as e:
            print(f"[-] Error saving job: {e}")