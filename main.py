import argparse
import hashlib
import json
import random
import string
import time
import traceback
from typing import Any, Collection

import requests
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', metavar="PATH", default="accounts.json", help="The output json file")
parser.add_argument('--amount', type=int, metavar="INT", help="The amount of accounts to create")
parser.add_argument('--password', help="The pasword for all accounts, if not provided will be made randomly")
parser.add_argument('--cookies', action='store_true', help="Only outputs a list of cookies instead of entire accounts")
args = parser.parse_args()

driver = webdriver.Firefox()

def _generate_password() -> str:
    """Generate a new password that's at least medium for mihoyo"""
    while True:
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        if any(i.isdigit() for i in password) and not all(i.isdigit() for i in password):
            return password

def switch_window(window: int) -> None:
    """Helper function to switch to a tab"""
    driver.switch_to.window(driver.window_handles[window])

def init_windows(start: int = 0) -> None:
    """Initialize windows with required sites"""
    switch_window(start)
    driver.get('https://account.mihoyo.com/#/register/email')
    driver.execute_script(f"window.open('about:blank');")
    switch_window(start + 1)
    driver.execute_script(f"window.open('about:blank');")
    driver.get('https://www.hoyolab.com/genshin/')
    switch_window(start + 2)
    driver.get('https://temp-mail.org/en/')

def get_email_address() -> str:
    """Gets the current mail address from temp-mail
    
    Will wait for the address to be generated if not avalible
    """
    switch_window(2)
    print('getting email adress')
    while True:
        try:
            mail = driver.find_element_by_id('mail').get_attribute('value')
        except:
            driver.refresh() # there's a ddos protection that sometimes locks you out
            mail = ''
        if mail and '@' in mail:
            return mail
        
        time.sleep(.1)

def wait_for_confirmation(delete_after: bool = True) -> str:
    """Waits for a confirmation email and returns its code"""
    switch_window(2)
    print('waiting for confirmation email (may take up to a minute!)')
    element = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(('xpath', '//*[@id="tm-body"]/main/div[1]/div/div[2]/div[2]/div/div[1]/div/div[4]/ul/li[2]/div[2]/span/a'))
    )
    text = element.get_attribute('textContent')
    
    if delete_after:
        # this causes tempmail to trigger its antibot protection
        # we either need to solve that or reload sometime later when we have time
        # there's however not a clean way to transition from captcha to reloading 
        # so we sacrifice like 2s to this
        driver.find_element_by_id('click-to-delete').click()
    
    return text.strip().split(' ')[0]


def register(email: str, password: str) -> None:
    """Fills out the registration form 
    
    In the rare case that the user is not logged in after registering
    they will be redirected to the login page.
    """
    switch_window(0)
    driver.get('https://account.mihoyo.com/#/register/email')
    # wait until reloaded
    WebDriverWait(driver, 2).until(EC.text_to_be_present_in_element(('tag name', 'body'), "Register"))
    # fill out form
    print(f'filling out registration form for {email}')
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[1]/div/input').send_keys(email)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[3]/div/input').send_keys(password)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[4]/div/input').send_keys(password)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[5]/div/div/i').click()
    # click "Send Code"
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[2]/div/div').click()
    # wait for the user to solve the captcha
    print('waiting for captcha to be solved')
    WebDriverWait(driver, 60).until(
        EC.text_to_be_present_in_element(('xpath', '//*[@id="root"]/div[1]/div[2]/form/div[2]/div/div'), 'Sent')
    )
    code = wait_for_confirmation()
    switch_window(0)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[2]/div/input').send_keys(code)
    try:
        # sometimes the button just doesn't work, so do it 3 extra times than needed
        for _ in range(5):
            driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[6]/button').click()
            time.sleep(.2)
    except:
        pass
    
    driver.refresh() # clear out the fields
    print(f'registered email: {email} password: {password} code: {code}')
    
    if 'Register' in driver.find_element_by_tag_name('body').text: # still not logged in
        login(email, password)

def create_hoyolab_account(email: str, password: str) -> str:
    """Creates a hoyolab account on the hoyolab website, returns the username and cookies"""
    driver.refresh() # since we cannot refresh after registering the account we gotta do it now
    print('creating a hoyolab account')
    switch_window(1)
    # wait until reloaded
    element = WebDriverWait(driver, 5).until(EC.presence_of_element_located(('xpath', '//*[@id="__layout"]/div/div[1]/div/div[2]/div[1]/div/div/img')))
    element.click()
    
    driver.find_element_by_xpath('//*[@id="__layout"]/div/div[4]/div/div[2]/div/form/div[1]/div/input').send_keys(email)
    driver.find_element_by_xpath('//*[@id="__layout"]/div/div[4]/div/div[2]/div/form/div[2]/div/input').send_keys(password)
    driver.find_element_by_xpath('//*[@id="__layout"]/div/div[4]/div/div[2]/div/form/button').click()
    
    print('waiting for captcha to be solved')
    element = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located(('xpath', '//*[@id="__layout"]/div/div[4]/div/div[2]/div[2]/div[1]/div[1]/input'))
    )
    username = email[:20]
    element.send_keys(username)
    driver.find_element_by_xpath('//*[@id="__layout"]/div/div[4]/div/div[2]/div[2]/div[2]/div/div/i').click()
    driver.find_element_by_xpath('//*[@id="__layout"]/div/div[4]/div/div[2]/div[2]/div[3]/button').click()
    # there used to be a bug where you would get a tos agreement form twice
    
    return username

def login(email: str, password: str) -> None:
    """Logs into a mihoyo account using the login page
    
    Uses the same window as the registration.
    """
    if driver.get_cookie('login_ticket') is not None:
        return # already logged in
    
    print('logging in')
    switch_window(0)
    driver.get('https://account.mihoyo.com/#/login')
    
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[1]/div/input').send_keys(email)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[2]/div/input').send_keys(password)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[3]/button').click()
    
    print('waiting for captcha to be solved')
    WebDriverWait(driver, 60).until(
        EC.text_to_be_present_in_element(('tag name', 'body'), 'Account Information')
    )
    driver.get('https://account.mihoyo.com/#/register/email')

def create_account(password: str = None) -> tuple[str, str]:
    """Creates a new mihoyo account
    
    This is done by creating an email address, registering the user and possibly logging in.
    """
    password = password or _generate_password()
    
    email = get_email_address()
    register(email, password)
    return email, password

def get_cookies(url: str = "https://api-os-takumi.mihoyo.com/", allowed: Collection[str] = {'ltoken', 'ltuid'}) -> dict[str, str]:
    """Returns a list of cookies from a url"""
    print('fetching login cookies')
    # new tab
    switch_window(-1)
    driver.execute_script(f"window.open('about:blank');")
    switch_window(-1)

    driver.get(url)
    cookies = {c['name']: c['value'] for c in driver.get_cookies() if c['name'] in allowed}
    driver.delete_all_cookies()
    driver.close()
    
    return cookies

def _generate_ds_token(salt: str = "6cqshh5dhw73bzxn20oexa9k516chk7s") -> str:
    t = int(time.time())
    r = ''.join(random.choices(string.ascii_letters, k=6))
    h = hashlib.md5(f"salt={salt}&t={t}&r={r}".encode()).hexdigest()
    return f'{t},{r},{h}'

def verify_cookies(cookies: dict[str, str]):
    print(f"testing cookies: {cookies}")
    headers = {
        "x-rpc-app_version": "1.5.0",
        "x-rpc-client_type": "4",
        "x-rpc-language": "en-us",
        "ds": _generate_ds_token()
    }
    
    # random user I picked
    r = requests.get("https://api-os-takumi.mihoyo.com/game_record/genshin/api/index?server=os_euro&role_id=707818186", cookies=cookies, headers=headers)
    data = r.json()
    if data['retcode'] != 0:
        return False
    
    return True

def clear_cookies() -> None:
    """Deletes cookies from all windows"""
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        driver.delete_all_cookies()

def run() -> list[dict[str, Any]]:
    """Creates accounts until an error is encountered"""
    init_windows()
    accounts = []
    try:
        while args.amount is None or len(accounts) < args.amount:
            print('='*50)
            email, password = create_account(args.password)
            # keep making hoyolab account until it works
            username = create_hoyolab_account(email, password)
            cookies = get_cookies()
            
            if not verify_cookies(cookies):
                print("Cookies have not been created properly, skipping account")
                continue
            
            if args.cookies:
                accounts.append(cookies)
            else:
                accounts.append({
                    'email': email,
                    'password': password,
                    'username': username,
                    'account_id': int(cookies['ltuid']),
                    'cookies': cookies
                })
            
            clear_cookies()
    except Exception as e:
        traceback.print_exc()
    finally:
        return accounts
    
if __name__ == '__main__':
    accounts = run()
    try:
        with open(args.output) as file:
            data = json.load(file)
            accounts = data + accounts
    except FileNotFoundError:
        pass
    except Exception as e:
        print("error reading file: ", e)
    
    with open(args.output, 'w') as file:
        json.dump(accounts, file, indent=4)
    