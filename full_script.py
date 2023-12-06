import requests                  # Import the requests library for making HTTP requests
from bs4 import BeautifulSoup    # Import BeautifulSoup for parsing HTML content
import time                      # Import the time library for timing the script
import pandas as pd              # Import pandas library for creating a DataFrame and writing to Excel                       # sys module provides access to any command-line arguments
import json 
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
import tweepy
import re

folder_count = 25

with open('creds.json', 'r') as file:
    data = json.load(file)

consumer_key = data["consumer_key"]
consumer_secret = data["consumer_secret"]
access_token = data["access_token"]
access_token_secret =  data["access_token_secret"]
table_name = data["table_name"]
host = data["host"]
user = data["username"]
password = data["dbpass"]
database = data["database"]

# Define the company CIK codes
companies = {
   "T-Mobile US, Inc.": 1283699

}

# Define the base URL and headers
base_url = "https://www.sec.gov/Archives/edgar/data/"
headers = {
    "Connection": "close",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
}

form_data = [] # Initialize an empty list to hold extracted data from SEC filings

def scrape_all_company_data(companies):
    # Loop through the companies
    for company, cik in companies.items():
        scrape_data_for_company(company, cik)
        
def scrape_data_for_company(company, cik):      
    print(f"Scraping company {company} with CIK {cik}")
    url = base_url + str(cik) + "/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error accessing company {company} at URL {url}: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    folders = soup.find("table").find_all("a", {"href": True, "id": False})[:folder_count]

    for folder in folders:
        scrape_all_filing_folders(company, url, folder)
                   
def scrape_all_filing_folders(company, url, folder):                            
    # Get the text for the folder
    folder_text = folder.get_text()
    
    try:
        # Construct the URL for the folder
        folder_url = url + folder_text
        
        # Access the folder URL and get its content
        response = requests.get(folder_url, headers=headers)
        response.raise_for_status()
        folder_content = BeautifulSoup(response.text, "html.parser")
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing folder {folder_url} for company {company}: {e}")
        return
    
    for link in folder_content.find("table").find_all("a", href=True):
            process_folder_content_link(company, folder_url, link)

def process_folder_content_link(company, folder_url, link):
    if "index.html" not in link.get_text():
        return      
    # contains link to folder containing form 4
    filing_detail_folder = folder_url + "/"  + link.get_text()               
    response = requests.get(filing_detail_folder, headers=headers)
    response.raise_for_status()
    filing_detail_content = BeautifulSoup(response.text, "html.parser")

    for link in filing_detail_content.find_all("a", href=True):
        process_filing_detail(company, folder_url, link)

def process_filing_detail(company, folder_url, link):
    link_title = link.get_text() 
    should_process = ".xml" in link_title and ("doc4" in link_title or "form4" in link_title)
    if not should_process:
        return
                                                                                                
    form4_url = folder_url + "/" + link.get_text()
    
    try:
        response = requests.get(form4_url, headers=headers)
        response.raise_for_status()
        form_4_content = BeautifulSoup(response.text, "xml")
        non_derivative_table = form_4_content.find('nonDerivativeTable')
        non_derivative_transactions = non_derivative_table.find_all('nonDerivativeTransaction')
        current_transaction = {}

        for transaction in non_derivative_transactions:
            transaction_amounts = transaction.find('transactionAmounts') 
            security_title = transaction.find('securityTitle').find('value').get_text()
            transaction_date = transaction.find('transactionDate').find('value').get_text()            
            transaction_code = transaction.find('transactionCoding').find('transactionCode').get_text()
            transaction_shares = transaction_amounts.find('transactionShares').find('value').get_text()            
            transaction_price_per_share = transaction_amounts.find("transactionPricePerShare").find("value")

            if transaction_price_per_share is not None:
                transaction_price_per_share = transaction_price_per_share.get_text()

            else:
                transaction_price_per_share = ""

            if form_4_content.find("officerTitle") is not None:
                current_transaction["insiderTitle"] = form_4_content.find("officerTitle").get_text()
            else:
                current_transaction["insiderTitle"] = ""
            current_transaction["ticker"] = company 
            current_transaction["insiderName"] = form_4_content.find("rptOwnerName").get_text()                            
            current_transaction["securityType"] = security_title
            current_transaction["purchaseDate"] = transaction_date
            current_transaction["transactionCode"] = transaction_code
            current_transaction["numShares"] = transaction_shares
            current_transaction["pricePerShare"] = transaction_price_per_share
            current_transaction["formURL"] = form4_url

            if len(current_transaction) > 2:
                form_data.append(current_transaction) 
    except:  
        pass

def format_string(s):
    # Function to add commas to numbers
    def format_number(match):
        # Use Python's string formatting to add commas to numbers
        return f"{int(match.group()):,}"

    # Function to convert subsequent uppercase letters to lowercase
    def lowercase_except_first(match):
        word = match.group()
        if len(word) > 1:
            return word[0] + word[1:].lower()
        else:
            return word

    # Replace numbers with formatted numbers
    formatted_s = re.sub(r'\d+', format_number, s)

    # Convert only subsequent uppercase letters of each word to lowercase
    formatted_s = re.sub(r'\b\w+\b', lowercase_except_first, formatted_s)

    return formatted_s
def send_tweet(data):
    client = tweepy.Client(
            consumer_key = consumer_key, consumer_secret=consumer_secret,
            access_token=access_token, access_token_secret=access_token_secret)

    # Write your tweet message
    tweet = "{}, {} has purchased {} of {}, {} on {} for {} per share. View here {} ".format( format_string(data["insiderName"]), format_string(data["insiderTitle"]), format_string(data["numShares"]), data["ticker"], data["securityType"],data["purchaseDate"], format_string(data["pricePerShare"]) , data["formURL"])
    response = client.create_tweet(text = tweet)

def write_to_mysql(data, table_name, host, user, password, database):
    # Create a pandas DataFrame from the extracted data
    df = pd.DataFrame(data)

    if df.empty or len(df.columns) == 0:
        print("DataFrame is empty or has no columns")
        return 
    df = df[['purchaseDate', 'ticker', 'insiderName', 'insiderTitle', 'securityType', 'transactionCode', 'numShares', 'pricePerShare', "formURL"]]
    df = df.drop_duplicates()
    engine = create_engine(f'mysql+pymysql://{user}:{password}@{host}/{database}')
    
    with engine.connect() as connection:
        for index, row in df.iterrows():
            try:
                # Attempt to insert each row. If a record already exists, an IntegrityError should be raised.
                row.to_frame().T.to_sql(name=table_name, con=connection, index=False, if_exists='append')
                time.sleep(30)
                send_tweet(row.to_dict())
                print(f"Data written successfully to MySQL table {table_name}")
            except IntegrityError:
                # This block is executed if the record already exists. You can log this or pass.
                print(f"Record already exists in table {table_name}: {row}")
                pass

if __name__ == "__main__":
    start = time.time()
    scrape_all_company_data(companies)
    write_to_mysql(form_data, table_name, host, user, password, database)
    end = time.time()
    #Subtract Start Time from The End Time
    total_time = end - start
    print("\n Total Runtime "+ str(total_time//60), " Minutes")