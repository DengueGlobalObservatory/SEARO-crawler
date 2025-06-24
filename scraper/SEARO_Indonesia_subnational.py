# Extract Indonesia subnational data (country profile>Indonesia>Provinces Data)
# Run locally upon updates

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


driver = uc.Chrome(headless=False, use_subprocess=False, options = chrome_options, version_main=chrome_version)
driver.get('https://worldhealthorg.shinyapps.io/searo-dengue-dashboard/#')

print(driver.title)
time.sleep(5)

# click the side panel ('country profile')
side_panel = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.ID, "tab-sidebar_country_profile"))
)
driver.execute_script("arguments[0].scrollIntoView();", side_panel)
driver.execute_script("arguments[0].click();", side_panel)


# country drop down menu
country_filter = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@data-id='c_country_selection']"))
)

driver.execute_script("arguments[0].scrollIntoView();", country_filter)
driver.execute_script("arguments[0].click();", country_filter)

# select Indonesia
indonesia_filter = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[@id='bs-select-2-3' and contains(@class, 'dropdown-item')]"))
)

driver.execute_script("arguments[0].scrollIntoView();", indonesia_filter)
driver.execute_script("arguments[0].click();", indonesia_filter)

time.sleep(15)

data = []

def scrape_table():
    rows = driver.find_elements(By.XPATH, "//div[@id='c_map_in_overview_table']//div[@role='row']")
    table_data = []
    # Check if rows exist
    if not rows:
        return None  # Return None if no rows are found

    # Loop through the rows and extract the text for each cell
    for row in rows:
        cells = row.find_elements(By.XPATH, ".//div[@role='cell']")
        row_data = [cell.text for cell in cells]
        table_data.append(row_data)

    return table_data  # Return the data after scraping

# Call the scrape_table function
data = scrape_table() # save table for the first month

# Check if data is None or empty
if not data:
    print("No data found. Exiting.")
    driver.quit()
else:
    print(data)

# Locate the slider handle
slider_handle = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "#c_map_month_picker_in_overview .irs-handle.single"))
)
# Locate the month display with a wait until it's visible
month_display = WebDriverWait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#c_map_month_picker_in_overview .irs-single")))
max_month_text = driver.execute_script("return arguments[0].innerText;", month_display[0])
print(f"Current month: {max_month_text}")

def move_slider_left_until_target_month(target_month):
    global data
    actions = ActionChains(driver)

    while True:
        # Check the current month display
        current_month = driver.execute_script("return arguments[0].innerText;", month_display[0])
        # print(f"Current month: {current_month}")

        # If the current month matches the target, stop
        if current_month == target_month:
            print(f"Target month '{target_month}' reached!")
            time.sleep(3)
            table_data = scrape_table()
            data.extend(table_data)
            break

        else:
            # Move the slider handle left by a small amount
            actions.click_and_hold(slider_handle).move_by_offset(-3, 0).release().perform()
            time.sleep(5)  # Pause to let the slider update

    return data



# Extract the start and end month text
min_month = driver.find_element(By.CSS_SELECTOR, "#c_map_month_picker_in_overview .irs-min")

# Retrieve the inner text of the start and end months using JavaScript
min_month_text = driver.execute_script("return arguments[0].innerText;", min_month)

# Parse the start and end dates
start_date = datetime.strptime(min_month_text, "%b-%Y")
end_date = datetime.strptime(max_month_text, "%b-%Y")

# Generate the monthly sequence
current_date = end_date
monthly_sequence = []

while current_date >= start_date:
    # Add the current date to the sequence in the desired format
    monthly_sequence.append(current_date.strftime("%b-%Y"))
    # Move to the next month
    current_date -= relativedelta(months=1)  # Move one month backward

monthly_sequence = monthly_sequence[0:11]



# Move the slider for each month in the sequence
for target_month in monthly_sequence:
    print(f"Moving slider to: {target_month}")
    move_slider_left_until_target_month(target_month)
    print(f"Target month '{target_month}' completed")


# Create a DataFrame from the extracted data
df = pd.DataFrame(data, columns=['Region', 'Date', 'Cases'])

# Print the DataFrame
print(df)

df.to_csv("C:/Users/AhyoungLim/Dropbox/WORK/OpenDengue/SEARO-crawler/output/Indonesia_subnational_Feb2024_Dec2024.csv", index=False)

driver.quit()
