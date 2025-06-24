import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
from io import StringIO
import os
import sys

# Function to fetch the date paragraph
def fetch_date_paragraph(url, max_attempts=3, wait_time=20):
    attempt = 0
    while attempt < max_attempts:
        try:
            # Fetch the webpage
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for bad status codes
            soup = BeautifulSoup(response.text, 'html.parser')

            # Select the paragraph containing the date
            date_paragraph = soup.find('p', string=lambda t: t and "Data as of" in t)
            if date_paragraph:
                return date_paragraph.get_text(strip=True)
            else:
                print(f"Attempt {attempt + 1}: 'Data as of' paragraph not found. Retrying...")
        except Exception as e:
            print(f"Attempt {attempt + 1}: Encountered an error: {e}. Retrying...")

        attempt += 1
        if attempt < max_attempts:
            time.sleep(wait_time)  # Wait before retrying

    # If all attempts fail, raise an exception or return None
    print("Maximum attempts reached. Failed to fetch the 'Data as of' paragraph.")
    return None

# URL of the webpage
url = "https://worldhealthorg.shinyapps.io/searo-dengue-dashboard/#"

# Fetch the date paragraph
date_paragraph = fetch_date_paragraph(url)
if not date_paragraph:
    print("Failed to fetch the paragraph after maximum retries.")
    sys.exit(1)

print(f"Successfully fetched paragraph: {date_paragraph}")

# Define a regular expression pattern to match the date after "Data reported as of"
pattern = r"\d{1,2}\s+[A-Za-z]+\s+\d{4}"
match = re.search(pattern, date_paragraph)

if not match:
    print("No date pattern found in the paragraph.")
    sys.exit(1)

# Extract the matched date
date_string = match.group()
# Parse the input date string into a datetime object
date_string = datetime.strptime(date_string, "%d %b %Y")
# Format the datetime object into the desired format
formatted_date = date_string.strftime("%Y-%m-%d")

print(f"Extracted Date: {formatted_date}")

# Create a new DataFrame with today's date and the extracted report date
now = datetime.now() # current date and time

table = [{'Sys_date': now.strftime('%Y-%m-%d %H:%M'), 'Report_date': formatted_date}]
df_current = pd.DataFrame(table)
print(df_current)

# Append the new data to the existing CSV file
# Use GitHub token from environment variable
token = os.getenv('GITHUB_TOKEN')
if not token:
    print("GitHub token not found in environment variables")
    sys.exit(1)

headers = {'Authorization': f'token {token}'}

response = requests.get("https://raw.githubusercontent.com/DengueGlobalObservatory/SEARO-crawler/refs/heads/main/report_date.csv", headers=headers)

if response.status_code == 200:
    # Read the CSV content into a DataFrame
    csv_content = StringIO(response.text)
    df_main_old = pd.read_csv(csv_content)
    print("Existing data loaded:")
    print(df_main_old.head())
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")
    # Create empty DataFrame if file doesn't exist
    df_main_old = pd.DataFrame(columns=['Sys_date', 'Report_date'])

df_main_new = pd.concat([df_main_old, df_current], ignore_index=True)

# Save to CSV file
df_main_new.to_csv("report_date.csv", index=False)

# Convert date columns to datetime
df_main_new['Sys_date'] = pd.to_datetime(df_main_new['Sys_date'], format='%Y-%m-%d %H:%M')
df_main_new['Report_date'] = pd.to_datetime(df_main_new['Report_date'], format='%Y-%m-%d')

# Sort by system date
df_main_new = df_main_new.sort_values(by='Sys_date', ascending=False)

# Check if we have at least 2 entries
if len(df_main_new) < 2:
    print("Not enough data to compare dates. Running scraper...")
    should_scrape = True
else:
    last_report_date = df_main_new['Report_date'].iloc[0]
    second_last_date = df_main_new['Report_date'].iloc[1]

    if last_report_date == second_last_date:
        print("No data updates")
        should_scrape = False
    else:
        print("Data has been updated. Start data scraping...")
        should_scrape = True

# If the date has been updated then run Selenium and download data
if should_scrape:
    try:
        # Check if the scraper file exists
        scraper_path = "scraper/SEARO_national_selenium_run.py"
        # this will extract data from the bart chart (Total cases in General Overview section) and line chart (cases by month in "Trend overview")
        if not os.path.exists(scraper_path):
            print(f"Scraper file not found at: {scraper_path}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Files in current directory: {os.listdir('.')}")
            if os.path.exists('scraper'):
                print(f"Files in scraper directory: {os.listdir('scraper')}")
            sys.exit(1)

        import runpy
        print(f"Running scraper from: {scraper_path}")
        runpy.run_path(scraper_path)
        print("Scraper completed successfully")

    except Exception as e:
        print(f"Error running scraper: {e}")
        sys.exit(1)
