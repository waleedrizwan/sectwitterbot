# SEC Twitter Bot 

See Twitter Account here(https://twitter.com/sectrades)

# Preface
Section 16 of the Securities Exchange Act of 1934 requires senior executives, directors, and 10%+ shareholders (“insiders”) to make initial and ongoing filings about their company stock holdings, including to report most of their transactions in the company’s stock. The Insider Transactions Data Sets is extracted from the eXtensible Markup Language (XML) based fillable portion of Forms 3, 4 and 5. The data is presented without change from the “as-filed” submissions and in a flattened format to provide the public with readily available data from reporting persons. See(https://www.sec.gov/dera/data/form-345)

# How it works 
The script is running inside of an AWS EC2 Linux instance, being executed  
periodically using the built in Cron task scheduler. 

Each time it executes it first scrapes all filings for a company based on its **CIK** code (Central Index Key (CIK) is used on the SEC's computer systems to identify corporations and individual people who have filed disclosure with the SEC.)
 
Each CIK code has a parent directory containing every SEC filing made, including other kinds of reports. We are specifically looking for Form 4 filings which contain the insider transactions that have been disclosed. Form 4s are in XML format

Every time a transaction is pulled it is converted into a dictionary and added into a dataframe that we prepare for insertion into the AWS RDS MySQL DB. If the transaction doesn't exist in the table a summary of the trade is Tweeted by the bot via the Twitter API.

# Twitter API issues 
Currently there is a 50 requests per day limit on the Twitter API under the free tier. With premium access this bot could be making tweets all day.

# CIK Codes
The SEC provides all CIK codes in a strange format which I have cleaned up and stored in the file: **all_cik_codes.json**
