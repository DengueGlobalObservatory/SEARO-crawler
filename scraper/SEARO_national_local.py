import undetected_chromedriver as uc
from selenium import webdriver
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
from dateutil.relativedelta import relativedelta

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

# set chrome download directory
chrome_options = uc.ChromeOptions()
prefs = {"download.default_directory": os.getcwd()}
chrome_options.add_experimental_option("prefs", prefs)


driver = uc.Chrome(headless=True, use_subprocess=False, options = chrome_options, version_main=chrome_version)
driver.get('https://worldhealthorg.shinyapps.io/searo-dengue-dashboard/#')

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


def extract_bar_graph_data():
        """
        Extracts tooltip data for multiple x-offsets and returns a DataFrame.

        Returns:
            A pandas DataFrame containing 'Month', 'Year', and 'Value' columns.
        """

        # Initialize ActionChains and the final DataFrame
        action = ActionChains(driver)
        final_df = pd.DataFrame(columns=[ 'Year', 'Month', 'Value'])
        x_offsets =  [140, 120, 100, 60, 30, 10, -30, -60, -90, -120]

        # interactive line graph element
        graph = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "c_total_case_evolution")))

        # Loop to extract tooltip data for each x_offset
        for x_offset in x_offsets:
            action.move_to_element_with_offset(graph, x_offset, 0).perform()
            time.sleep(2)  # Wait for the tooltip to appear

            try:
                # Extract the pop-up text (assuming a specific CSS selector)
                tooltip = driver.find_element(By.CSS_SELECTOR, "div[style*='z-index: 9999999']")
                cases_text = driver.execute_script("return arguments[0].innerText;", tooltip)

                # Split the text by lines
                lines = cases_text.split('\n')

                # Extract the month from the first line
                month = lines[0].split('-')[0]

                # Extract years and values from the remaining lines
                values = lines[2::2]

                # Create a temporary DataFrame
                temp_df = pd.DataFrame({
                    'Year': 2024,
                    'Month': month ,
                    'Value': values
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
        country_data = extract_bar_graph_data()

        # Add a new column to identify the country for each row
        country_data['Country'] = country

        # Append the country's data to the all_data list
        all_data.append(country_data)

    # Concatenate all DataFrames into a single DataFrame
    final_df = pd.concat(all_data, ignore_index=True)

    # Save the merged DataFrame to a CSV file

    output_file = f"{output_directory}/SEARO_National_data_barchart_{today}.csv"
    final_df.to_csv(output_file, index=False)

    print(f"Data for all countries saved to {output_file}")
    return final_df

countries_list = ["India", "Maldives", "Myanmar", "Nepal", "Indonesia", "Thailand", "Sri Lanka", "Timor-Leste", "Bangladesh", "Bhutan"]
output_directory = "C:/Users/AhyoungLim/Dropbox/WORK/OpenDengue/SEARO-crawler/output"
today = datetime.now().strftime('%Y%m%d%H%m')

# Run the extraction for all countries
extract_data_for_countries(countries_list, output_directory, today)
