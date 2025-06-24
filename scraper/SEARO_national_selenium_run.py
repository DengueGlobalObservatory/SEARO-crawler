# Extract data from a bar chart (Total cases in "General overview") and line chart (Cases by month in "Trends overview")
# some countries report "total cases" in bar chart only (e.g., Bhutan, Maldives) but line chart often has more historical data
# so extract data from both chart types

import pandas as pd
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, JavascriptException, NoSuchElementException
import undetected_chromedriver as uc
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
driver.get('https://worldhealthorg.shinyapps.io/searo-dengue-dashboard/#')

print(driver.title)
time.sleep(5)

# click the side panel ('country profile')
side_panel = WebDriverWait(driver, 20).until(
    EC.element_to_be_clickable((By.ID, "tab-sidebar_country_profile"))
)
driver.execute_script("arguments[0].scrollIntoView();", side_panel)
driver.execute_script("arguments[0].click();", side_panel)

class CountryDataExtractor:
    """
    Enhanced country data extractor with separate line chart and bar chart extraction
    """

    def __init__(self, driver, line_chart_id="c_trend_cases_country_month_out", bar_chart_id="c_total_case_evolution"):
        self.driver = driver
        self.line_chart_id = line_chart_id
        self.bar_chart_id = bar_chart_id

    def select_country(self, country_name):
        """
        Select a country from the dropdown menu by its name.

        Args:
            country_name (str): The name of the country to select from the dropdown menu.
        """
        print(f"Selecting country: {country_name}")

        # Open the country dropdown menu
        country_filter = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-id='c_country_selection']"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", country_filter)
        self.driver.execute_script("arguments[0].click();", country_filter)

        # Modify the XPath to select the country by its name (within <span class="text">)
        country_xpath = f"//a[contains(@class, 'dropdown-item') and contains(., '{country_name}')]/span[contains(@class, 'text')]"

        # Wait for the country to be clickable and select it
        country_filter = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, country_xpath))
        )
        self.driver.execute_script("arguments[0].scrollIntoView();", country_filter)
        self.driver.execute_script("arguments[0].click();", country_filter)

        # Wait for the page to load and chart to update after selecting the country
        time.sleep(5)  # Increased wait time

        # Check if both charts are available
        self._check_chart_availability()

        # Wait for both charts to be ready
        self._wait_for_chart_update(self.line_chart_id)
        self._wait_for_chart_update(self.bar_chart_id)

    def _check_chart_availability(self):
        """Check if both charts are available and visible"""
        print("Checking chart availability...")

        # Check line chart
        try:
            line_element = self.driver.find_element(By.ID, self.line_chart_id)
            print(f"✅ Line chart found: visible={line_element.is_displayed()}, size={line_element.size}")
        except NoSuchElementException:
            print(f"❌ Line chart element '{self.line_chart_id}' not found!")

        # Check bar chart
        try:
            bar_element = self.driver.find_element(By.ID, self.bar_chart_id)
            print(f"✅ Bar chart found: visible={bar_element.is_displayed()}, size={bar_element.size}")

            # Check if bar chart might be in a different tab or section
            if not bar_element.is_displayed():
                print("Bar chart not visible, checking if it's in a different section...")
                # Try to scroll to it
                self.driver.execute_script("arguments[0].scrollIntoView();", bar_element)
                time.sleep(2)
                print(f"After scroll - Bar chart visible: {bar_element.is_displayed()}")

        except NoSuchElementException:
            print(f"❌ Bar chart element '{self.bar_chart_id}' not found!")

            # Try to find any charts with similar IDs
            all_charts = self.driver.find_elements(By.CSS_SELECTOR, "[id*='chart'], [id*='total'], [id*='case']")
            print(f"Found {len(all_charts)} potential chart elements:")
            for chart in all_charts[:10]:  # Show first 10
                print(f"  - ID: {chart.get_attribute('id')}, Class: {chart.get_attribute('class')}")

    def check_page_structure(self):
        """Debug method to check the overall page structure"""
        print("\n--- Checking page structure for charts ---")

        # Look for all ECharts elements
        echarts_elements = self.driver.find_elements(By.CSS_SELECTOR, ".echarts4r, [class*='echarts'], [id*='chart']")
        print(f"Found {len(echarts_elements)} potential ECharts elements:")

        for i, element in enumerate(echarts_elements):
            element_id = element.get_attribute('id')
            element_class = element.get_attribute('class')
            is_visible = element.is_displayed()
            size = element.size
            print(f"  {i+1}. ID: {element_id}, Class: {element_class}, Visible: {is_visible}, Size: {size}")

        # Check if we need to navigate to a different tab or section
        tabs = self.driver.find_elements(By.CSS_SELECTOR, "[role='tab'], .nav-link, .tab-pane")
        if tabs:
            print(f"\nFound {len(tabs)} potential tab elements:")
            for i, tab in enumerate(tabs[:5]):
                tab_text = tab.text.strip()
                tab_id = tab.get_attribute('id')
                is_active = 'active' in tab.get_attribute('class') if tab.get_attribute('class') else False
                print(f"  {i+1}. Text: '{tab_text}', ID: {tab_id}, Active: {is_active}")

    def _wait_for_chart_update(self, chart_id):
        """Wait for the ECharts to update after country selection"""
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, chart_id))
            )
            # Additional wait for ECharts to re-render
            time.sleep(2)

            # Verify ECharts instance is available
            echarts_ready = self.driver.execute_script("""
                var element = document.getElementById(arguments[0]);
                if (!element) return false;
                var instance = echarts.getInstanceByDom(element);
                return instance !== null && instance !== undefined;
            """, chart_id)

            if not echarts_ready:
                print(f"Warning: ECharts instance not ready for {chart_id}, will attempt extraction anyway")

        except TimeoutException:
            print(f"Warning: Chart element '{chart_id}' not found, continuing anyway")

    def extract_echarts_data_direct(self, chart_id, chart_type="line"):
        """
        Extract data directly from ECharts instance - Enhanced for bar charts
        """
        print(f"Attempting direct ECharts data extraction for {chart_type} chart...")

        js_code = f"""
        try {{
            // Get the chart element
            var chartElement = document.getElementById('{chart_id}');
            if (!chartElement) {{
                return {{error: "Chart element not found"}};
            }}

            // Get ECharts instance
            var echartsInstance = echarts.getInstanceByDom(chartElement);
            if (!echartsInstance) {{
                return {{error: "ECharts instance not found"}};
            }}

            // Get the complete option object
            var option = echartsInstance.getOption();
            if (!option) {{
                return {{error: "ECharts option not available"}};
            }}

            // Extract structured data
            var result = {{
                success: true,
                xAxis: [],
                series: [],
                chartType: '{chart_type}'
            }};

            // Extract X-axis data (months/dates)
            if (option.xAxis && option.xAxis[0] && option.xAxis[0].data) {{
                result.xAxis = option.xAxis[0].data;
            }}

            // Extract series data with detailed logging
            if (option.series) {{
                option.series.forEach(function(series, index) {{
                    var seriesData = {{
                        name: series.name || 'Series_' + index,
                        data: series.data || [],
                        type: series.type || 'unknown',
                        dataLength: series.data ? series.data.length : 0
                    }};

                    // Log the actual data structure for debugging
                    console.log('Series ' + index + ':', seriesData.name, 'Type:', seriesData.type, 'Length:', seriesData.dataLength);
                    if (seriesData.data.length > 0) {{
                        console.log('First 3 data points:', seriesData.data.slice(0, 3));
                    }}

                    result.series.push(seriesData);
                }});
            }}

            return result;

        }} catch (error) {{
            return {{error: "JavaScript execution error: " + error.message}};
        }}
        """

        try:
            result = self.driver.execute_script(js_code)

            if result.get('error'):
                print(f"Direct extraction error for {chart_type}: {result['error']}")
                return None

            if result.get('success'):
                print(f"Raw ECharts data for {chart_type}:")
                print(f"  X-axis length: {len(result.get('xAxis', []))}")
                print(f"  Series count: {len(result.get('series', []))}")
                for i, series in enumerate(result.get('series', [])):
                    print(f"    Series {i}: {series.get('name')} ({series.get('type')}) - {len(series.get('data', []))} points")

                return self._convert_echarts_to_dataframe(result, chart_type)
            else:
                print(f"Unexpected result structure from direct extraction for {chart_type}")
                return None

        except Exception as e:
            print(f"JavaScript execution failed for {chart_type}: {e}")
            return None

    def _convert_echarts_to_dataframe(self, echarts_data, chart_type="line"):
        """Enhanced conversion with better debugging for bar charts"""
        try:
            x_axis_data = echarts_data.get('xAxis', [])
            series_list = echarts_data.get('series', [])

            print(f"Converting {chart_type} data:")
            print(f"  X-axis data: {x_axis_data[:3]}..." if len(x_axis_data) > 3 else f"  X-axis data: {x_axis_data}")
            print(f"  Series count: {len(series_list)}")

            if not x_axis_data or not series_list:
                print(f"No data found in x-axis or series for {chart_type} chart")
                return None

            all_data = []

            for series_idx, series in enumerate(series_list):
                series_name = series.get('name', f'Series_{series_idx}')
                series_data = series.get('data', [])
                series_type = series.get('type', 'unknown')

                print(f"Processing {chart_type} series {series_idx}: {series_name} (type: {series_type}) with {len(series_data)} data points")

                # Debug: Show first few data points
                if len(series_data) > 0:
                    print(f"  Sample data: {series_data[:3]}")

                for i, value in enumerate(series_data):
                    if i >= len(x_axis_data):
                        print(f"  Warning: Data point {i} exceeds x-axis length")
                        break

                    # Handle different data formats with better debugging
                    actual_value = None

                    if isinstance(value, (list, tuple)):
                        if len(value) >= 2:
                            actual_value = value[1]
                            print(f"  Point {i}: Array format, using value[1] = {actual_value}")
                        else:
                            actual_value = value[0] if len(value) > 0 else 0
                            print(f"  Point {i}: Short array, using value[0] = {actual_value}")
                    elif isinstance(value, dict):
                        # Handle the specific bar chart format: {'value': ['Jan-2024', ' 1055']}
                        dict_value = value.get('value', value.get('y', 0))
                        if isinstance(dict_value, (list, tuple)) and len(dict_value) >= 2:
                            # Extract the numeric value (second element)
                            actual_value = dict_value[1]
                            print(f"  Point {i}: Dict with array value, extracted = {actual_value}")
                        else:
                            actual_value = dict_value
                            print(f"  Point {i}: Dict format, extracted = {actual_value}")
                    else:
                        actual_value = value if value is not None else 0
                        print(f"  Point {i}: Direct value = {actual_value}")

                    # Convert to numeric (handle strings with spaces)
                    try:
                        if actual_value is not None:
                            # Clean string values (remove spaces, commas)
                            if isinstance(actual_value, str):
                                cleaned_value = actual_value.strip().replace(',', '')
                                actual_value = float(cleaned_value)
                            else:
                                actual_value = float(actual_value)
                        else:
                            actual_value = 0.0
                    except (ValueError, TypeError):
                        print(f"  Warning: Could not convert '{actual_value}' to float, using 0")
                        actual_value = 0.0

                    # Create data row
                    if chart_type == "bar":
                        all_data.append({
                            'Period': x_axis_data[i],
                            'Series': series_name,
                            'Value': actual_value,
                            'Chart_Type': 'bar'
                        })
                    else:  # line chart
                        all_data.append({
                            'Month': x_axis_data[i],
                            'Year': series_name,
                            'Value': actual_value,
                            'Chart_Type': 'line'
                        })

            if not all_data:
                print(f"No valid data points created for {chart_type}")
                return None

            df = pd.DataFrame(all_data)
            print(f"Created DataFrame with {len(df)} rows")

            # Clean and validate data
            df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
            initial_count = len(df)
            df = df.dropna(subset=['Value'])
            final_count = len(df)

            if initial_count != final_count:
                print(f"Dropped {initial_count - final_count} rows with invalid values")

            print(f"Direct extraction successful for {chart_type}: {len(df)} data points")
            if len(df) > 0:
                print(f"Sample converted data:")
                print(df.head().to_string(index=False))

            return df

        except Exception as e:
            print(f"Error converting ECharts data to DataFrame for {chart_type}: {e}")
            import traceback
            traceback.print_exc()
            return None


    def extract_tooltip_data_fallback(self, chart_id, chart_type="line"):
        """
        Enhanced tooltip extraction specifically for bar charts
        """
        print(f"Using tooltip extraction as fallback method for {chart_type} chart...")

        action = ActionChains(self.driver)

        if chart_type == "bar":
            final_df = pd.DataFrame(columns=['Period', 'Series', 'Value'])
            # Bar charts - try more positions across the width
            x_offsets = list(range(10, 400, 20))  # Every 20px from 10 to 400
            y_offsets = [-10, 0, 10, 20]  # Try different heights
        else:  # line chart
            final_df = pd.DataFrame(columns=['Year', 'Month', 'Value'])
            x_offsets = [600, 500, 400, 300, 200, 100, 0, -100, -200, -300, -400, -500]
            y_offsets = [0]

        try:
            graph = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, chart_id))
            )

            chart_size = graph.size
            print(f"Chart size for {chart_type}: {chart_size}")

            successful_extractions = 0
            tooltip_texts_found = []

            for x_offset in x_offsets:
                for y_offset in y_offsets:
                    try:
                        # Move to position
                        action.move_to_element_with_offset(graph, x_offset, y_offset).perform()
                        time.sleep(0.8)  # Shorter wait

                        # Enhanced tooltip detection
                        tooltip_selectors = [
                            "div[style*='position: absolute'][style*='display: block']:not([style*='display: none'])",
                            "div[style*='z-index'][style*='position: absolute']:not([style*='display: none'])",
                            ".echarts-tooltip",
                            "div[style*='pointer-events: none'][style*='position: absolute']",
                            "div[style*='background'][style*='position: absolute']"
                        ]

                        tooltip = None
                        cases_text = ""

                        for selector in tooltip_selectors:
                            try:
                                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for element in elements:
                                    if element.is_displayed() and element.text.strip():
                                        tooltip = element
                                        cases_text = element.text.strip()
                                        break
                                if cases_text:
                                    break
                            except:
                                continue

                        if not cases_text:
                            continue

                        # Avoid duplicate tooltips
                        if cases_text in tooltip_texts_found:
                            continue
                        tooltip_texts_found.append(cases_text)

                        print(f"Found tooltip at ({x_offset}, {y_offset}): {repr(cases_text)}")

                        # Parse tooltip text
                        lines = [line.strip() for line in cases_text.split('\n') if line.strip()]
                        if len(lines) < 2:
                            continue

                        temp_df = pd.DataFrame()

                        if chart_type == "bar":
                            # Enhanced parsing for bar charts
                            if len(lines) >= 2:
                                # Try different formats
                                period = lines[0]

                                # Look for numeric value in any line
                                value = None
                                series_name = "Total cases"

                                for line in lines[1:]:
                                    extracted_value = self._extract_numeric_value(line)
                                    if extracted_value is not None and extracted_value > 0:
                                        value = extracted_value
                                        # If there are multiple lines, use the previous line as series name
                                        if len(lines) > 2:
                                            line_idx = lines.index(line)
                                            if line_idx > 0:
                                                series_name = lines[line_idx - 1]
                                        break

                                if value is not None:
                                    temp_df = pd.DataFrame({
                                        'Period': [period],
                                        'Series': [series_name],
                                        'Value': [value]
                                    })
                                    print(f"  Parsed: Period={period}, Series={series_name}, Value={value}")
                        else:
                            # Line chart parsing (original)
                            month = lines[0]
                            years = lines[1::2]
                            values = lines[2::2]

                            valid_years = [year for year in years if year.isdigit()]
                            valid_values = [self._extract_numeric_value(val) for val in values[:len(valid_years)]]

                            temp_df = pd.DataFrame({
                                'Year': [int(year) for year in valid_years],
                                'Month': [month] * len(valid_years),
                                'Value': valid_values
                            })

                        # Add valid data
                        if not temp_df.empty:
                            temp_df = temp_df.dropna()
                            if not temp_df.empty:
                                final_df = pd.concat([final_df, temp_df], ignore_index=True)
                                successful_extractions += 1

                    except Exception as e:
                        continue

            # Remove duplicates
            if not final_df.empty:
                final_df = final_df.drop_duplicates().reset_index(drop=True)

            print(f"Tooltip extraction completed for {chart_type}: {len(final_df)} data points from {successful_extractions} successful positions")
            print(f"Unique tooltip texts found: {len(tooltip_texts_found)}")

            return final_df

        except Exception as e:
            print(f"Tooltip extraction failed for {chart_type}: {e}")
            return None

    def _extract_numeric_value(self, value_str):
        """Extract numeric value from string, handling commas and various formats"""
        if not value_str or value_str == 'NaN':
            return None

        # Remove common formatting
        cleaned = value_str.replace(',', '').replace(' ', '').strip()

        # Try to extract number
        import re
        number_match = re.search(r'[\d.]+', cleaned)
        if number_match:
            try:
                return float(number_match.group())
            except ValueError:
                return None
        return None

    def extract_line_chart_data(self, country_name):
        """Extract data from the line chart for a single country"""
        print(f"\\n--- Extracting LINE CHART data for: {country_name} ---")

        # Try direct ECharts method first
        line_data = self.extract_echarts_data_direct(self.line_chart_id, "line")

        # If direct method fails, use tooltip fallback
        if line_data is None or line_data.empty:
            print("Direct method failed for line chart, using tooltip fallback...")
            line_data = self.extract_tooltip_data_fallback(self.line_chart_id, "line")

        # Add country column if data was extracted
        if line_data is not None and not line_data.empty:
            line_data['Country'] = country_name
            print(f"Successfully extracted {len(line_data)} line chart data points for {country_name}")
            return line_data
        else:
            print(f"Failed to extract line chart data for {country_name}")
            return pd.DataFrame()

    def debug_chart_structure(self, chart_id, chart_type):
        """Debug method to understand chart structure and available data"""
        print(f"\n--- DEBUG: Analyzing {chart_type} chart structure ---")

        js_debug_code = f"""
        try {{
            var chartElement = document.getElementById('{chart_id}');
            if (!chartElement) {{
                return {{error: "Chart element not found", chartId: '{chart_id}'}};
            }}

            var echartsInstance = echarts.getInstanceByDom(chartElement);
            if (!echartsInstance) {{
                return {{error: "ECharts instance not found", hasElement: true}};
            }}

            var option = echartsInstance.getOption();
            if (!option) {{
                return {{error: "ECharts option not available", hasInstance: true}};
            }}

            // Extract debug information
            var debugInfo = {{
                success: true,
                hasXAxis: !!option.xAxis,
                hasSeries: !!option.series,
                xAxisCount: option.xAxis ? option.xAxis.length : 0,
                seriesCount: option.series ? option.series.length : 0,
                chartType: chart_id.includes('total') ? 'bar' : 'line'
            }};

            // Get x-axis info
            if (option.xAxis && option.xAxis[0]) {{
                debugInfo.xAxisType = option.xAxis[0].type;
                debugInfo.xAxisDataLength = option.xAxis[0].data ? option.xAxis[0].data.length : 0;
                debugInfo.xAxisSample = option.xAxis[0].data ? option.xAxis[0].data.slice(0, 3) : [];
            }}

            // Get series info
            if (option.series) {{
                debugInfo.seriesInfo = option.series.map(function(series, index) {{
                    return {{
                        index: index,
                        name: series.name || 'unnamed',
                        type: series.type || 'unknown',
                        dataLength: series.data ? series.data.length : 0,
                        sampleData: series.data ? series.data.slice(0, 3) : []
                    }};
                }});
            }}

            return debugInfo;

        }} catch (error) {{
            return {{error: "JavaScript execution error: " + error.message}};
        }}
        """

        try:
            debug_result = self.driver.execute_script(js_debug_code)
            print(f"Debug result for {chart_type}: {debug_result}")
            return debug_result
        except Exception as e:
            print(f"Debug failed for {chart_type}: {e}")
            return None

    def extract_bar_chart_data(self, country_name):
        """Extract data from the bar chart for a single country with enhanced debugging"""
        print(f"\\n--- Extracting BAR CHART data for: {country_name} ---")

        # First, debug the chart structure
        debug_info = self.debug_chart_structure(self.bar_chart_id, "bar")

        # Try direct ECharts method first
        bar_data = self.extract_echarts_data_direct(self.bar_chart_id, "bar")

        # If direct method fails, use tooltip fallback
        if bar_data is None or bar_data.empty:
            print("Direct method failed for bar chart, using tooltip fallback...")
            bar_data = self.extract_tooltip_data_fallback(self.bar_chart_id, "bar")

        # Add country column if data was extracted
        if bar_data is not None and not bar_data.empty:
            bar_data['Country'] = country_name
            print(f"Successfully extracted {len(bar_data)} bar chart data points for {country_name}")
            return bar_data
        else:
            print(f"Failed to extract bar chart data for {country_name}")

            # Additional debugging - check if chart element exists
            try:
                element = self.driver.find_element(By.ID, self.bar_chart_id)
                print(f"Bar chart element found: {element.is_displayed()}")
                print(f"Element size: {element.size}")
                print(f"Element location: {element.location}")
            except NoSuchElementException:
                print(f"Bar chart element with ID '{self.bar_chart_id}' not found!")

            return pd.DataFrame()

    def extract_country_data(self, country_name):
        """
        Extract data for a single country from both line and bar charts
        Returns a tuple: (line_data, bar_data)
        """
        print(f"\\n{'='*60}")
        print(f"EXTRACTING ALL DATA FOR: {country_name}")
        print('='*60)

        # Select the country
        self.select_country(country_name)

        # Extract from both charts
        line_data = self.extract_line_chart_data(country_name)
        bar_data = self.extract_bar_chart_data(country_name)

        return line_data, bar_data

    def extract_data_for_countries(self, countries_list, output_directory, today):
        """
        Extract data for multiple countries from both charts, and save to separate CSV files.

        Args:
            countries_list (list): List of country names to select from the dropdown.
            output_directory (str): The directory where the CSV files will be saved.
            today (str): Today's date string for filename.

        Returns:
            tuple: (line_chart_df, bar_chart_df) - The merged DataFrames for both chart types.
        """
        print(f"Starting data extraction for {len(countries_list)} countries from both charts...")

        # Initialize empty lists to hold data from all countries
        all_line_data = []
        all_bar_data = []
        successful_line_extractions = 0
        successful_bar_extractions = 0
        failed_line_extractions = []
        failed_bar_extractions = []

        # Loop over all countries in the list
        for i, country in enumerate(countries_list, 1):
            print(f"\\n{'='*70}")
            print(f"Processing country {i}/{len(countries_list)}: {country}")
            print('='*70)

            try:
                # Extract data for the current country from both charts
                line_data, bar_data = self.extract_country_data(country)

                # Process line chart data
                if not line_data.empty:
                    all_line_data.append(line_data)
                    successful_line_extractions += 1
                    print(f"✅ {country} LINE: {len(line_data)} records extracted")
                else:
                    failed_line_extractions.append(country)
                    print(f"❌ {country} LINE: No data extracted")

                # Process bar chart data
                if not bar_data.empty:
                    all_bar_data.append(bar_data)
                    successful_bar_extractions += 1
                    print(f"✅ {country} BAR: {len(bar_data)} records extracted")
                else:
                    failed_bar_extractions.append(country)
                    print(f"❌ {country} BAR: No data extracted")

            except Exception as e:
                print(f"❌ {country}: Exception occurred - {e}")
                failed_line_extractions.append(country)
                failed_bar_extractions.append(country)
                continue

        # Summary
        print(f"\\n{'='*70}")
        print("EXTRACTION SUMMARY")
        print('='*70)
        print(f"LINE CHART - Successful: {successful_line_extractions}/{len(countries_list)}")
        if failed_line_extractions:
            print(f"LINE CHART - Failed: {', '.join(failed_line_extractions)}")

        print(f"BAR CHART - Successful: {successful_bar_extractions}/{len(countries_list)}")
        if failed_bar_extractions:
            print(f"BAR CHART - Failed: {', '.join(failed_bar_extractions)}")

        # Process and save line chart data
        final_line_df = pd.DataFrame()
        if all_line_data:
            final_line_df = pd.concat(all_line_data, ignore_index=True)
            line_output_file = f"{output_directory}/SEARO_National_data_{today}.csv"
            final_line_df.to_csv(line_output_file, index=False)
            print(f"\\n📊 LINE CHART dataset: {len(final_line_df)} total records")
            print(f"💾 Line chart data saved to: {line_output_file}")
            self._print_data_summary(final_line_df, "Line Chart")

        # Process and save bar chart data
        final_bar_df = pd.DataFrame()
        if all_bar_data:
            final_bar_df = pd.concat(all_bar_data, ignore_index=True)
            bar_output_file = f"{output_directory}/SEARO_National_data_barchart_{today}.csv"
            final_bar_df.to_csv(bar_output_file, index=False)
            print(f"\\n📊 BAR CHART dataset: {len(final_bar_df)} total records")
            print(f"💾 Bar chart data saved to: {bar_output_file}")
            self._print_data_summary(final_bar_df, "Bar Chart")

        if all_line_data or all_bar_data:
            return final_line_df, final_bar_df
        else:
            print("\\n❌ No data was successfully extracted from any country for either chart")
            return pd.DataFrame(), pd.DataFrame()

    def _print_data_summary(self, df, chart_type):
        """Print a summary of the extracted data"""
        if df.empty:
            return

        print(f"\\n{'='*50}")
        print(f"{chart_type.upper()} DATA SUMMARY")
        print('='*50)
        print(f"Countries: {df['Country'].nunique()}")

        if 'Month' in df.columns and 'Year' in df.columns:
            # Line chart format
            print(f"Months: {df['Month'].nunique()}")
            print(f"Years: {df['Year'].nunique()}")
            print(f"Year range: {df['Year'].min()} - {df['Year'].max()}")
        elif 'Period' in df.columns:
            # Bar chart format
            print(f"Periods: {df['Period'].nunique()}")

        print(f"Value range: {df['Value'].min():.2f} - {df['Value'].max():.2f}")
        print(f"\\nCountries included: {', '.join(sorted(df['Country'].unique()))}")

        print("\\nSample data:")
        print(df.head().to_string(index=False))

# Main execution function
def main(driver, download_directory):
    """
    Main execution function to extract data for all countries from both charts

    Args:
        driver: Selenium WebDriver instance
        download_directory: Directory to save the output files
    """

    # Initialize the extractor
    extractor = CountryDataExtractor(driver)

    # Countries list
    countries_list = [
        "India", "Maldives", "Myanmar", "Nepal", "Indonesia",
        "Thailand", "Sri Lanka", "Timor-Leste", "Bangladesh", "Bhutan"
    ]

    # Generate timestamp for filename
    today = datetime.now().strftime('%Y%m%d_%H%M')

    # Run the extraction for all countries and both chart types
    final_line_df, final_bar_df = extractor.extract_data_for_countries(countries_list, download_directory, today)

    return final_line_df, final_bar_df

# Usage example with debugging (assuming you have driver and download_directory defined):
def debug_first_country(driver, download_directory):
    """Test function to debug extraction for the first country only"""
    print("=== DEBUGGING MODE: Testing first country only ===")

    extractor = CountryDataExtractor(driver)

    # Check page structure first
    extractor.check_page_structure()

    # Test with first country
    test_country = "Bangladesh"  # Start with Bangladesh as it's shown in your HTML
    print(f"\n=== Testing extraction for {test_country} ===")

    # Select country and check availability
    extractor.select_country(test_country)

    # Extract line chart data
    print("\n--- Testing Line Chart Extraction ---")
    line_data = extractor.extract_line_chart_data(test_country)
    print(f"Line chart result: {len(line_data) if not line_data.empty else 0} records")

    # Extract bar chart data
    print("\n--- Testing Bar Chart Extraction ---")
    bar_data = extractor.extract_bar_chart_data(test_country)
    print(f"Bar chart result: {len(bar_data) if not bar_data.empty else 0} records")

    # Save test results
    if not line_data.empty:
        line_data.to_csv(f"{download_directory}/DEBUG_line_data.csv", index=False)
        print(f"Debug line data saved to: {download_directory}/DEBUG_line_data.csv")

    if not bar_data.empty:
        bar_data.to_csv(f"{download_directory}/DEBUG_bar_data.csv", index=False)
        print(f"Debug bar data saved to: {download_directory}/DEBUG_bar_data.csv")

    return line_data, bar_data

# Run debug mode first
debug_line, debug_bar = debug_first_country(driver, download_directory)

# Only run full extraction if debug is successful
if not debug_bar.empty:
    print("\n=== Debug successful, running full extraction ===")
    final_line_data, final_bar_data = main(driver, download_directory)
else:
    print("\n=== Debug failed for bar chart, check the debug output above ===")
    print("The bar chart might be:")
    print("1. In a different tab/section that needs to be clicked")
    print("2. Have a different ID than 'c_total_case_evolution'")
    print("3. Not be an ECharts instance")
    print("4. Be loaded dynamically after additional user interaction")

# Alternative: Use the class directly
# extractor = CountryDataExtractor(driver)
# line_data, bar_data = extractor.extract_data_for_countries(countries_list, output_dir, timestamp)
