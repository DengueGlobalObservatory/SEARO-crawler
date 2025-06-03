# Data scraper for WHO SEARO dengue data
This repository contains scripts to scrape dengue data for WHO SEARO using Python. The workflows are automated using GitHub Actions.

## Structure
### `scraper`
- **`SEARO_national_daily_scraper.py`**: A Python script that runs Selenium to download monthly historical dengue case data from the [WHO SEARO Dengue Dashboard](https://worldhealthorg.shinyapps.io/searo-dengue-dashboard/#). Datasets will be added automatically to the output folder only if the data reporting date has been updated on the website. 

### `.github/workflows`
- **`All-Action.yaml`**: A GitHub Actions workflow file to run the `SEARO_national_daily_scraper.py` script. The workflow runs every day at 8 AM UTC or when manually triggered via the GitHub UI.

