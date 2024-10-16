import os
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
load_dotenv()

chrome_driver_path = "C:\\path\\chromedriver-win64\\chromedriver.exe"

def create_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    service = Service(chrome_driver_path)
    return webdriver.Chrome(service=service, options=chrome_options)


class ContactInfo:
    def __init__(self, email, name=None, title=None, context=None):
        self.email = email
        self.name = name
        self.title = title
        self.context = context

    def __str__(self):
        parts = [f"Email: {self.email}"]
        if self.name:
            parts.append(f"Name: {self.name}")
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)

def extract_names_and_emails(driver, url):
    try:
        contacts = []
        # Common name patterns
        name_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Basic name pattern
            r'Mr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Ms\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Mrs\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Dr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]

        # Common title patterns
        title_patterns = [
            r'(CEO|Chief Executive Officer)',
            r'(CTO|Chief Technology Officer)',
            r'(CFO|Chief Financial Officer)',
            r'(Manager)',
            r'(Director)',
            r'(President)',
            r'(Vice President)',
            r'(Coordinator)',
            r'(Administrator)',
            r'(Specialist)',
            r'(Associate)',
            r'(Supervisor)',
            r'(Lead)',
            r'(Head of [A-Za-z\s]+)',
        ]

        # Find all elements that might contain contact information
        contact_elements = driver.find_elements(By.CSS_SELECTOR, 
            '.contact-info, .team-member, .staff, .employee, .person, .profile, ' +
            '[class*="contact"], [class*="team"], [class*="staff"], [class*="profile"]'
        )

        for element in contact_elements:
            try:
                context = element.text
                if not context:
                    continue

                # Extract emails
                email_matches = re.finditer(r'[\w\.-]+@[\w\.-]+\.\w+', context)
                
                for email_match in email_matches:
                    email = email_match.group()
                    
                    # Get surrounding context( before and after email)
                    start_pos = max(0, email_match.start() - 45)
                    end_pos = min(len(context), email_match.end() + 45)
                    surrounding_text = context[start_pos:end_pos]

                    # Look for names in surrounding text
                    name = None
                    for pattern in name_patterns:
                        name_match = re.search(pattern, surrounding_text)
                        if name_match:
                            name = name_match.group(1)
                            break

                    # Look for titles in surrounding text
                    title = None
                    for pattern in title_patterns:
                        title_match = re.search(pattern, surrounding_text, re.IGNORECASE)
                        if title_match:
                            title = title_match.group(1)
                            break

                    contact = ContactInfo(
                        email=email,
                        name=name,
                        title=title,
                        context=surrounding_text.strip()
                    )
                    contacts.append(contact)
            
            
            except Exception as e:
                print(f"Error processing contact element: {e}")
                continue

        # Look for structured data
        try:
            structured_data = driver.find_elements(By.CSS_SELECTOR, '[itemtype*="Person"], [itemtype*="Organization"]')
            for data in structured_data:
                name_elem = data.find_element(By.CSS_SELECTOR, '[itemprop="name"]')
                email_elem = data.find_element(By.CSS_SELECTOR, '[itemprop="email"]')
                if name_elem and email_elem:
                    contact = ContactInfo(
                        email=email_elem.text,
                        name=name_elem.text,
                        context="From structured data"
                    )
                    contacts.append(contact)
        except:
            pass

        return contacts

    except Exception as e:
        print(f"Error extracting names and emails from {url}: {e}")
        return []

def extract_business_name(driver, url):
    try:
        # Wait for page load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Common patterns for business names
        patterns = [
            {'selector': 'h1.company-name', 'attr': 'text'},
            {'selector': 'h1.site-title', 'attr': 'text'},
            {'selector': 'meta[property="og:site_name"]', 'attr': 'content'},
            {'selector': '.logo-text', 'attr': 'text'},
            {'selector': '#company-name', 'attr': 'text'},
            {'selector': '.business-name', 'attr': 'text'},
        ]
        
        for pattern in patterns:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, pattern['selector'])
                for element in elements:
                    if pattern['attr'] == 'text':
                        value = element.text
                    else:
                        value = element.get_attribute(pattern['attr'])
                    
                    if value and len(value.strip()) > 0:
                        # Clean the business name
                        name = value.strip()
                        name = re.sub(r'\s+-\s+.*$', '', name)  # Remove everything after dash
                        name = re.sub(r'\s*\|.*$', '', name)    # Remove everything after pipe
                        return name
            except:
                continue
                
        # If no business name found, try to use the title
        try:
            title = driver.title
            if title:
                # Clean the title
                title = re.sub(r'\s+-\s+.*$', '', title)
                title = re.sub(r'\s*\|.*$', '', title)
                return title.strip()
        except:
            pass
    
        return None
    
    except Exception as e:
        print(f"Error extracting business name: {e}")
        return None

def generate_response_with_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    endpoint = os.getenv("GEMINI_ENDPOINT")

    headers = {
        "Content-Type": "application/json",
    }
    params = {
        "key": api_key
    }
    
    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "topP": 0.8,
            "topK": 40,
            "candidateCount": 1,
            "maxOutputTokens": 100,
            "stopSequences": ["\n", "Note:", "Example:"],
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
    }

    response = requests.post(endpoint, headers=headers, params=params, json=request_body)
    try:
        response_data = response.json()
        print("Response from Gemini API:", response_data)  # Debug logging

        if 'candidates' in response_data and len(response_data['candidates']) > 0:
            candidate = response_data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                return candidate['content']['parts'][0]['text']
            else:
                raise KeyError("Expected content not found in Gemini API response.")
        else:
            raise KeyError("Expected candidates not found in Gemini API response.")
    except ValueError:
        raise ValueError("Invalid response received from Gemini API")

def enhance_search_query(query):
    prompt = f"""
    Please enhance this search query to make it more effective for finding private businesses on Google Search: "{query}"
    Do not contain the query in inverted commas.
    Focus on:
    1. Adding relevant keywords that might help find contact information(do not use "contact information" itself rather use 'info:' tags)
    2. Using advanced search operators if appropriate
    3. Making the query more specific and targeted
    Please provide only the enhanced query without any explanation.
    For example: keyword keyword keyword "location" "info:email" "info:contact"
    """
    try:
        print(f"[DEBUG] Enhancing Query: \n\t{query} with  \n\t{prompt}")
        enhanced_query = generate_response_with_gemini(prompt)
        print(f"[DEBUG] Original query: {query}")
        print(f"[DEBUG] Enhanced query: {enhanced_query}")
        return enhanced_query
    except Exception as e:
        print(f"[DEBUG] Error enhancing query: {e}")
        return query  # Return original query if enhancement fails

def google_search(query):
    try:
        # Enhance the query using Gemini
        print("[DEBUG] Searching: ", query)
        enhanced_query = enhance_search_query(query)
        print("[DEBUG] Searching enhanced query: ", enhanced_query)

        # Create main driver for Google search
        main_driver = create_driver()
        main_driver.get("https://www.google.com")
        
        # Find and use the search box
        search_box = main_driver.find_element(By.NAME, "q")
        search_box.send_keys(enhanced_query)
        search_box.send_keys(Keys.RETURN)
        
        # Wait for results
        time.sleep(2)
        
        # Get search results
        results = main_driver.find_elements(By.CSS_SELECTOR, 'div.g')
        print(f"[DEBUG] Found {len(results)} search results")
        
        processed_results = []
        
        for index, result in enumerate(results):
            try:
                # Extract basic information from search result
                title_element = result.find_element(By.CSS_SELECTOR, 'h3')
                link_element = result.find_element(By.CSS_SELECTOR, 'a')
                title = title_element.text
                url = link_element.get_attribute('href')
                
                print(f"\n[DEBUG] Processing result {index + 1}/{len(results)}: {url}")
                
                # Create a new driver instance for each URL
                with create_driver() as page_driver:
                    try:
                        page_driver.set_page_load_timeout(20)
                        page_driver.get(url)
                        
                        business_name = extract_business_name(page_driver, url)
                        if business_name:
                            print(f"[SUCCESS] Found business name: {business_name}")
                        
                        contacts = extract_names_and_emails(page_driver, url)
                        if contacts:
                            print(f"[SUCCESS] Found {len(contacts)} contacts")
                        
                        result_data = {
                            'business_name': business_name,
                            'title': title,
                            'url': url,
                            'contacts': contacts
                        }
                        processed_results.append(result_data)
                        
                        print(f"[OUTPUT] Business: {business_name}")
                        print(f"Title: {title}")
                        print(f"URL: {url}")
                        if contacts:
                            print("Contacts:")
                            for contact in contacts:
                                print(f"  {contact}")
                        print("-" * 50)
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to process page {url}: {e}")
                        continue
                        
            except Exception as e:
                print(f"[ERROR] Failed to process search result: {e}")
                continue

        # Print summary
        print("\n[SUMMARY]")
        print(f"Total results found: {len(results)}")
        print(f"Successfully processed: {len(processed_results)}")
        print(f"Results with business names: {len([r for r in processed_results if r['business_name']])}")
        print(f"Total contacts found: {sum(len(r['contacts']) for r in processed_results)}")

    except Exception as e:
        print(f"[ERROR] An error occurred in main search process: {e}")
    finally:
        if main_driver:
            try:
                main_driver.quit()
            except:
                pass

if __name__ == "__main__":
    query = input("Enter your search query: ")
    start_time = time.time()

    google_search(query)

    end_time = time.time()
    runtime = end_time-start_time
    print(f"Script executed in {runtime} seconds.")