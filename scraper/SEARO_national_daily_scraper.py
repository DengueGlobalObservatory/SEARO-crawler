import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time
from io import StringIO

# Function to fetch the date paragraph
def fetch_date_paragraph(url, max_attempts=3, wait_time=20):
    attempt = 0
    while attempt < max_attempts:
        try:
            # Fetch the webpage
            response = requests.get(url)
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
        time.sleep(wait_time)  # Wait before retrying
    
    # If all attempts fail, raise an exception or return None
    print("Maximum attempts reached. Failed to fetch the 'Data as of' paragraph.")
    return None

# URL of the webpage
url = "https://searo-cds-dashboard.shinyapps.io/searo-dengue-dashboard/#"

# Fetch the date paragraph
date_paragraph = fetch_date_paragraph(url)
if date_paragraph:
    print(f"Successfully fetched paragraph: {date_paragraph}")
else:
    print("Failed to fetch the paragraph after maximum retries.")

# Define a regular expression pattern to match the date after "Data reported as of"
pattern = r"\d{1,2}\s+[A-Za-z]+\s+\d{4}"
match = re.search(pattern, date_paragraph)


# Extract the date after "Data reported as of"
# Search for the pattern in the text

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

# if the file already exists, save it to a dataframe and then append to a new one    
# access to CSV in git repo
token = "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"
headers = {'Authorization': f'token {token}'}

response = requests.get("https://raw.githubusercontent.com/ahyoung-lim/SEARO-crawler/refs/heads/main/report_date.csv", headers=headers)

if response.status_code == 200:
    # Read the CSV content into a DataFrame
    csv_content = StringIO(response.text)
    df_main_old = pd.read_csv(csv_content)
    print(df_main_old.head())
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")

df_main_new = pd.concat([df_main_old, df_current])

# save to dataframe and overwrite the old file
df_main_new.to_csv("report_date.csv", index = False)

# Read the last date from the CSV file
df_main_new['Sys_date'] = pd.to_datetime(df_main_new['Sys_date'], format='%Y-%m-%d %H:%M')
df_main_new['Report_date'] = pd.to_datetime(df_main_new['Report_date'], format='%Y-%m-%d')

df_main_new = df_main_new.sort_values(by='Sys_date', ascending=False)

last_report_date = df_main_new['Report_date'].iloc[0]
second_last_date = df_main_new['Report_date'].iloc[1]

if last_report_date == second_last_date: 
   print("No data updates")

# If the date has been updated then run Selenium and download data
else: 
   print("Start data scraping...")
   import undetected_chromedriver as uc
   from selenium.webdriver.common.by import By
   from selenium.webdriver.support.ui import WebDriverWait
   from selenium.webdriver.support import expected_conditions as EC
   from selenium.webdriver.common.by import By
   from selenium.webdriver.common.action_chains import ActionChains

   import pandas as pd
   import time
   import os
   from datetime import datetime
   import subprocess
   import re
   import sys

   def get_chrome_version():
        try:
            if sys.platform == "win32":
                # Command to retrieve Chrome version from Windows registry
                output = subprocess.check_output(
                    r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version',
                    shell=True, 
                    text=True
                )
                version = re.search(r'\s+version\s+REG_SZ\s+(\d+)\.', output)
            else:  # Assuming Linux or other Unix-like systems
                # Try different commands to retrieve Chrome version on Linux
                for command in ['google-chrome --version', 'google-chrome-stable --version', 'chromium-browser --version']:
                    try:
                        output = subprocess.check_output(command, shell=True, text=True)
                        version = re.search(r'\b(\d+)\.', output)
                        if version:
                            break
                    except subprocess.CalledProcessError:
                        continue
                else:
                    raise RuntimeError("Could not determine Chrome version")

            if version:
                return int(version.group(1))
            else:
                raise ValueError("Could not parse Chrome version")
        except Exception as e:
            raise RuntimeError("Failed to get Chrome version") from e

    # Get the major version of Chrome installed
   chrome_version = get_chrome_version()

   # Set the download directory to the GitHub repository folder
   github_workspace = os.getenv('GITHUB_WORKSPACE')
   download_directory = os.path.join(github_workspace, 'output')

   prefs = {"download.default_directory": download_directory,}
   
   # set chrome download directory
   chrome_options = uc.ChromeOptions()
   chrome_options.add_experimental_option("prefs", prefs)

   driver = uc.Chrome(headless=True, use_subprocess=False, options = chrome_options, version_main=chrome_version)     
   driver.get('https://searo-cds-dashboard.shinyapps.io/searo-dengue-dashboard/#') 

   print(driver.title)
   time.sleep(5)

   # click the side panel ('country profile')
   side_panel = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "tab-sidebar_country_profile"))
    )
   driver.execute_script("arguments[0].scrollIntoView();", side_panel)
   driver.execute_script("arguments[0].click();", side_panel)

   def select_country(country_name):
        """
        Select a country from the dropdown menu by its name.
        
        Args:
            country_name (str): The name of the country to select from the dropdown menu.
        """
        # Open the country dropdown menu
        country_filter = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-id='c_country_selection']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", country_filter)
        driver.execute_script("arguments[0].click();", country_filter)

        # Modify the XPath to select the country by its name (within <span class="text">)
        country_xpath = f"//a[contains(@class, 'dropdown-item') and contains(., '{country_name}')]/span[contains(@class, 'text')]"
        
        # Wait for the country to be clickable and select it
        country_filter = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, country_xpath))
        )
        driver.execute_script("arguments[0].scrollIntoView();", country_filter)
        driver.execute_script("arguments[0].click();", country_filter)

        time.sleep(5)  # Wait for the page to load after selecting the country


   # Find an approximate location on the graph to hover over
   # and repeat the action with different x-offsets
   def extract_tooltip_data():
        """
        Extracts tooltip data for multiple x-offsets and returns a DataFrame.

        Returns:
            A pandas DataFrame containing 'Month', 'Year', and 'Value' columns.
        """

        # Initialize ActionChains and the final DataFrame
        action = ActionChains(driver)
        final_df = pd.DataFrame(columns=[ 'Year', 'Month', 'Value'])
        x_offsets = [600, 500, 400, 300, 200, 100, 0, -100, -200, -300, -400, -500]
        # interactive line graph element
        graph = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "c_trend_cases_country_month_out")))

        # Loop to extract tooltip data for each x_offset
        for x_offset in x_offsets:
            action.move_to_element_with_offset(graph, x_offset, 0).perform()
            time.sleep(2)  # Wait for the tooltip to appear

            try:
                # Extract the pop-up text (assuming a specific CSS selector)
                tooltip = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div[style*='z-index: 9999999']"))
                )
                cases_text = tooltip.text

                # Split the text by lines
                lines = cases_text.split('\n')

                # Extract the month from the first line
                month = lines[0]

                # Extract years and values from the remaining lines
                years = lines[1::2]
                values = lines[2::2]

                # Create a temporary DataFrame
                temp_df = pd.DataFrame({
                    'Year': [int(year) for year in years],
                    'Month': [month] * len(years),
                    'Value': [float(value) if value != 'NaN' else 'NA' for value in values]
                })

                # Append the temporary DataFrame to the final DataFrame
                final_df = pd.concat([final_df, temp_df], ignore_index=True)

            except Exception as e:
                print(f"Error at x_offset {x_offset}: {e}")

        return final_df


   def extract_data_for_countries(countries_list, output_directory, today):
        """
        Extract data for multiple countries, merge them into one DataFrame, and save to CSV.

        Args:
            countries_list (list): List of country names to select from the dropdown.
            output_directory (str): The directory where the CSV file will be saved.
        
        Returns:
            pd.DataFrame: The merged DataFrame containing data for all countries.
        """
        # Initialize an empty list to hold data from all countries
        all_data = []

        # Loop over all countries in the list
        for country in countries_list:
            # Select the country from the dropdown
            select_country(country)

            # Extract the tooltip data for the selected country
            country_data = extract_tooltip_data()

            # Add a new column to identify the country for each row
            country_data['Country'] = country
            
            # Append the country's data to the all_data list
            all_data.append(country_data)

        # Concatenate all DataFrames into a single DataFrame
        final_df = pd.concat(all_data, ignore_index=True)

        # Save the merged DataFrame to a CSV file
        
        output_file = f"{output_directory}/SEARO_National_data_{today}.csv"
        final_df.to_csv(output_file, index=False)
        
        print(f"Data for all countries saved to {output_file}")
        return final_df

   countries_list = ["India", "Maldives", "Myanmar", "Nepal", "Indonesia", "Thailand", "Sri Lanka", "Timor-Leste", "Bangladesh", "Bhutan"]
   today = datetime.now().strftime('%Y%m%d%H%m')

   # Run the extraction for all countries
   extract_data_for_countries(countries_list, download_directory, today)
