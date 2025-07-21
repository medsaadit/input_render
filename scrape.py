# --- External Libraries ---
import undetected_chromedriver as uc  # Anti-detection Chrome driver to avoid bot detection
from selenium.webdriver.chrome.options import Options  # Chrome browser configuration options
from selenium.webdriver.common.by import By  # Element locator strategies
from selenium.webdriver.support.ui import WebDriverWait  # Wait functionality for Selenium
from selenium.webdriver.support import expected_conditions as EC  # Conditions to wait for
import requests  # HTTP requests library
import time  # Time-related functions
import os  # OS-level operations (file paths, env vars)
import re  # Regular expressions for pattern matching
import json  # JSON processing
from telethon.sync import TelegramClient  # Telegram API client
import asyncio  # Async IO operations
from flask import Flask, request, jsonify
import scrape
import sys

# --- Constants ---
MOBULA_API = "05af5fe9-c6a2-4677-8491-fa1bea364fc1"

# Telegram API credentials
API_ID = 20445291 
API_HASH = 'f85a52ec518d7d9376ab3b99b5fd3fc5'  

# Target chat ID to send messages to
# TARGET_CHAT_ID = -1001326481918  # Commented out alternative chat ID
TARGET_CHAT_ID = -1002670598744  # Commented out alternative chat ID



async def send_telegram_message(driver, message):
    """
    Send alert messages to Telegram using the Telethon client.
    
    Args:
        driver: Selenium WebDriver instance (unused but kept for compatibility)
        messages (list): List of messages to send
    """
    print("Sending Message ...")
    
    async with TelegramClient('telegram_session', API_ID, API_HASH) as client:
        try:
            await client.send_message(TARGET_CHAT_ID, message)
            print("Message sent successfully!")
        except Exception as e:
            print(f"Error while sending message: {e}")
# --- Selenium Setup ---
def initialize_selenium_driver(headless=False):
    """
    Initialize and configure the Selenium web driver with undetected-chromedriver.
    
    Args:
        headless (bool): Whether to run Chrome in headless mode
        
    Returns:
        WebDriver: Configured Chrome WebDriver instance
        
    Raises:
        Exception: If driver initialization fails
    """
    try:
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        
        # Add user data directory and profile directory arguments
        # This is the typical path for Chrome profiles on Windows
        # For macOS, use: ~/Library/Application Support/Google/Chrome
        # For Linux, use: ~/.config/google-chrome
        
        # Get user home directory
        user_home = os.path.expanduser("~")
        
        # Set up the user data directory path based on OS
        if os.name == 'nt':  # Windows
            user_data_dir = os.path.join(user_home, 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
        elif os.name == 'posix':  # macOS or Linux
            if os.path.exists(os.path.join(user_home, 'Library')):  # macOS
                user_data_dir = os.path.join(user_home, 'Library', 'Application Support', 'Google', 'Chrome')
            else:  # Linux
                user_data_dir = os.path.join(user_home, '.config', 'google-chrome')
        
        # Add the user data directory and profile arguments
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--profile-directory=Default")  # Use Profile 1
        
        # Security and performance settings
        chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
        chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
        
        # Use undetected-chromedriver to bypass detection
        driver = uc.Chrome(options=chrome_options)
        driver.maximize_window()
        print("✅ Selenium WebDriver initialized successfully")
        return driver
    except Exception as e:
        print(f"[X] Error initializing Selenium WebDriver: {e}")
        raise

def extract_all_existing_addresses():
    """
    Extract previously processed URLs from storage file to avoid duplicates.
    
    Returns:
        list: List of previously processed URLs
    """
    if os.path.exists("existing_urls.txt"):
        with open("existing_urls.txt", "r") as file:
            existing_urls = file.read().splitlines()
    else:
        existing_addresses = []
    return existing_addresses

def extract_info_from_dexscreener(driver ,address):
# Opening new tab and getting additional JSON data directly from DexScreener's internal API
    tab_url = f"https://io.dexscreener.com/dex/pair-details/v2/solana/{address}"
    original_window = driver.current_window_handle
    data_dict = None
    
    try:
        # Open new tab and navigate to internal API endpoint
        driver.switch_to.new_window('tab')
        driver.get(tab_url)

        # Wait for the <pre> tag containing JSON data to be present
        try:
            pre_tag = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "pre"))
            )
            pre_text = pre_tag.text
            data_dict = json.loads(pre_text)  # Parse JSON from the page
            return data_dict
        except Exception as e:
            print(f"Error finding or parsing tab content: {e}")
        finally:
            # Clean up by closing the tab and returning to original window
            driver.close()
            driver.switch_to.window(original_window)
    except Exception as e:
        print(f"Error managing browser tabs: {e}")
        # Try to return to original window if possible
        try:
            driver.switch_to.window(original_window)
        except:
            pass

def wallet_info(address):
    """
    Query the Mobula API to get wallet portfolio information.
    
    Args:
        address (str): Wallet address to check
        
    Returns:
        dict: Wallet portfolio data or None if request fails
    """
    try:
        url = f"https://api.mobula.io/api/1/wallet/portfolio?wallet={address}"
        headers = {
            "Authorization": MOBULA_API
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data  # Return the actual data object, not the string
        else:
            print(f"Error fetching wallet info: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception in wallet_info: {e}")
        return None


def make_output(cmc_output , dex_output):
    # getting all the fields from the cmc output
    token_symbol = cmc_output["token_symbol"]
    token_name = cmc_output["token_name"]
    token_liquidity = cmc_output["token_liquidity"]
    token_total_supply = cmc_output["token_total_supply"]
    # token_price = cmc_output["token_price"]
    token_exchange = cmc_output["token_exchange"]
    token_market_cap = cmc_output["token_market_cap"]
    token_blockchain = "solana"

    #initializing to n/a in case we don't get data 
    total_holders = "N/A"
    percentage_output = "N/A"
    token_total_supply = "N/A"
    freeze_revoked = "N/A"
    c_total_balance = "N/A"
    c_sol_balance = "N/A"
    c_decent_money = "N/A"
    c_decent_history = "N/A"

    # Extract holders information if available
    if dex_output and isinstance(dex_output.get("holders"), dict):
        holders_info = dex_output["holders"]
        total_holders = holders_info.get("count", "N/A")

        # Process top holders data
        if isinstance(holders_info.get("holders"), list) and holders_info["holders"]:
            holders = holders_info["holders"]
            percentages = [holder.get("percentage", 0) for holder in holders]
            percentage_output = " | ".join([f"{p}%" for p in percentages])
            # token_total_supply = holders_info.get("totalSupply", "N/A") 

    # Check Solana-specific token attributes (freeze authority)
    if dex_output and isinstance(dex_output.get("ta"), dict):
        token_attributes = dex_output["ta"]
        if token_blockchain.lower() == "solana" and isinstance(token_attributes.get("solana"), dict):
            freeze_status = token_attributes["solana"].get("isFreezable", False)
            freeze_revoked = "❌" if freeze_status else "✅"
    

    # Only attempt to get creator info if we have holders data - with proper type checking
    holders_exist = (dex_output and 
                    isinstance(dex_output.get("holders"), dict) and 
                    isinstance(dex_output["holders"].get("holders"), list) and 
                    dex_output["holders"]["holders"])

# Process creator wallet information if available
    if holders_exist:
        try:
            # Assume first holder is creator (most common case for new tokens)
            creator_id = dex_output["holders"]["holders"][0].get("id")
            if creator_id:
                creator_info_str = wallet_info(creator_id)
                # Check if creator_info is valid JSON string and parse it
                if creator_info_str:
                    if isinstance(creator_info_str, str):
                        try:
                            creator_info = json.loads(creator_info_str)
                        except json.JSONDecodeError:
                            creator_info = None
                    else:
                        creator_info = creator_info_str
                        
                    # Extract wallet data if properly structured
                    if isinstance(creator_info, dict) and "data" in creator_info:
                        c_total_balance = creator_info["data"].get("total_wallet_balance", "N/A")
                        
                        # Look for Solana in assets list (typically at index 21)
                        assets = creator_info["data"].get("assets", [])
                        if isinstance(assets, list) and len(assets) > 21:
                            c_sol_balance = assets[21].get("token_balance", "N/A")
                        
                        # Analyze wallet quality indicators
                        try:
                            total_balance_float = float(c_total_balance) if c_total_balance != "N/A" else 0
                            c_decent_money = "✅" if total_balance_float > 1000 else "❌"
                        except (ValueError, TypeError):
                            c_decent_money = "❓"
                            
                        # Check for wallet history - more assets indicate more history
                        c_decent_history = "✅" if isinstance(assets, list) and len(assets) > 3 else "❌"
        except Exception as e:
            print(f"Error processing creator info: {e}")




    



    message = f"""
        {token_name} ON {token_blockchain}({token_symbol})

        Exchange: {token_exchange}
        Market Cap: {token_market_cap}
        Liquidity: {token_liquidity}
        Token Price: "not done yet"
        Total Supply: {token_total_supply}
        Holders: {total_holders}
        Top Holders: {percentage_output}

        Freeze authority revoked: {freeze_revoked}

        Creator Info:
        . Balance SOL: {c_sol_balance}
        . Balance USD: {c_total_balance}
        . Dev Wallet has enough money: {c_decent_money}
        . Dev Wallet has decent history: {c_decent_history}
        """

    print(message)
    return message
def extract_info_from_cmc(driver , url): #get address from the callback

    x_paths = {}
    x_paths["token_symbol"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[2]/div[1]/div/div/h1/span[1]/div/div/span" 
    x_paths["token_name"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[2]/div[1]/div/div/div/div[1]/span"
    x_paths["token_liquidity"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[6]/dd/div[1]/div/span"
    x_paths["token_total_supply"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/div[8]/div/div[1]/dl[2]/span/span/dd/span"
    x_paths["token_price"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[1]/dd/div[1]/div/span"
    x_paths["token_exchange"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[1]/div[1]/a[2]/div/div"
    x_paths["token_market_cap"] = "/html/body/div[1]/div[3]/div/div[2]/div/aside/div/div[2]/dl/div[3]/dd/div[1]/div/span"

    output = {}
    try: 
        driver.get(url)
        time.sleep(10)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        for key, path in x_paths.items():
            if key == "token_price":
                continue  # skip token_price for now

            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, path))
                )
                # print(f"{key}: {element.text}")
                output[key] = element.text
            except Exception as e:
                print(f"Failed to get {key}: {e}")
        return output

    except Exception as e:
        print(f"Error loading page: {e}")


def scrape(driver , pool_address , mint_address):
    existing_addresses = extract_all_existing_addresses()
    if pool_address not in existing_addresses:
        url = f"https://coinmarketcap.com/dexscan/solana/{pool_address}/"
        x_paths = {}
        output1 = extract_info_from_cmc(driver, url)
        output2 = extract_info_from_dexscreener(driver, mint_address)

        message = make_output(output1,output2)
        asyncio.run(send_telegram_message(driver, message))  # Run the async function



def main(pool_address , mint_address):
    driver = initialize_selenium_driver()
    scrape(driver , pool_address , mint_address)


# main("F86Rm73qaX7S38ZoocjzTZkLzQe6a1X575BcnjUtQzor", "2uhxAa6yag3zHtahLj4Cqn23fu9giheWj9c7DMwRjFvq" )


