import os
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv

load_dotenv()

chrome_driver_path = "C:\\path\\chromedriver-win64\\chromedriver.exe"

# Set up the Chrome driver
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service)

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
            "temperature": 0.5,
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
    Focus on:
    1. Adding relevant keywords that might help find contact information
    2. Using advanced search operators if appropriate
    3. Making the query more specific and targeted
    Please provide only the enhanced query without any explanation.
    For example: "keyword" "keyword" "keyword" "email:info"
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

        # Navigate to Google
        driver.get("https://www.google.com")

        # Find the search box
        search_box = driver.find_element(By.NAME, "q")
        
        # Enter the enhanced search query and submit
        search_box.send_keys(enhanced_query)
        search_box.send_keys(Keys.RETURN)
        print("[DEBUG] Searching with enhanced query")
        # Wait for search results to load
        time.sleep(2)

        # Get the search results
        results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
        print("[DEBUG] Processing goog results. ")

        # Print titles and URLs of the search results
        links = []
        print("[DEBUG] Getting links and urls.")
        for result in results:
            title_element = result.find_element(By.TAG_NAME, 'h3')
            link_element = result.find_element(By.TAG_NAME, 'a')
            title = title_element.text
            url = link_element.get_attribute('href')
            links.append(url)
            print(f"[OUTPUT] Title: {title}\nURL: {url}\n")
        extracted_links = list(set(links))
        print("[DEBUG] Extracted Links:", extracted_links)

        print("[DEBUG] Extracting emails. ")
        all_emails = []
        for url in links:
            emails = extract_emails_from_url(url)
            all_emails.extend(emails)
        
        print("[DEBUG] Total emails loaded:", len(all_emails))
        
        print("[DEBUG] Printing emails:")
        for i, email in enumerate(all_emails):
            print(f'{i + 1}: {email}')

    except Exception as e:
        print(f"[DEBUG] An error occurred: {e}")
    finally:
        driver.quit()


def extract_emails_from_url(url):
    try:
        # Get the url from links for email extraction
        driver.get(url)
        time.sleep(2)
        page_source = driver.page_source
        print("[DEBUG] Page Source Loaded.")
        EMAIL_REGEX = r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9]))\.){3}(?:(2(5[0-5]|[0-4][0-9])|1[0-9][0-9]|[1-9]?[0-9])|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""
        print("[DEBUG] Regexing Page Source for Email")

        return [match.group() for match in re.finditer(EMAIL_REGEX, page_source)]
        
    except Exception as e:
        print(f"Error extracting emails from {url}: {e}")
        return []

if __name__ == "__main__":
    query = input("Enter your search query: ")
    google_search(query)