import json
import traceback

import requests
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PASSWORD = 'wordpass12'

driver = webdriver.Firefox()

def switch(window: int) -> None:
    """Helper function to switch to a tab"""
    driver.switch_to.window(driver.window_handles[window])

# create two extra tabs
driver.execute_script(f"window.open('about:blank');")
driver.execute_script(f"window.open('about:blank');")

# open each tab on its page
urls = [
    'https://account.mihoyo.com/#/register/email',
    'https://account.mihoyo.com/#/login',
    'https://temp-mail.org/en/'
]
for handle,url in zip(driver.window_handles, urls):
    driver.switch_to.window(handle)
    driver.get(url)

def get_email_address() -> str:
    """Gets the current mail address"""
    switch(2)
    print('getting email adress')
    while True:
        mail = driver.execute_script("return document.getElementById('mail').value")
        if mail and '@' in mail:
            return mail
        
        driver.implicitly_wait(.1)

def wait_for_confirmation() -> str:
    """Waits for a confirmation email and returns its code"""
    switch(2)
    print('waiting for confirmation email')
    element = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(('xpath', '//*[@id="tm-body"]/main/div[1]/div/div[2]/div[2]/div/div[1]/div/div[4]/ul/li[2]/div[2]/span/a'))
    )
    text = element.get_attribute('textContent')
    driver.find_element_by_id('click-to-delete').click() # email is no longer needed so we can delete it
    return text.strip().split(' ')[0]


def fill_out_register_form(email: str, password: str) -> None:
    """Fills out the registration form"""
    switch(0)
    driver.get('https://account.mihoyo.com/#/register/email')
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
    switch(0)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[2]/div/input').send_keys(code)
    for _ in range(5): # just click it a few times to be sure, idk wtf is going on with mihoyo
        driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[6]/button').click()
        driver.implicitly_wait(.2)
    driver.refresh() # clear out the fields
    print(f'registered email: {email} password: {password} code: {code}')

def register_account() -> tuple[str, str]:
    """Registers a new account, returns its email and password"""
    email = get_email_address()
    fill_out_register_form(email, PASSWORD)
    return (email, PASSWORD)


def login(email: str, password: str) -> None:
    """Logs into a mihoyo account, returns the cookies"""
    if driver.get_cookie('login_ticket') is not None:
        return # already logged in
    switch(1)
    print('logging in')
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[1]/div/input').send_keys(email)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[2]/div/input').send_keys(password)
    driver.find_element_by_xpath('//*[@id="root"]/div[1]/div[2]/form/div[3]/button').click()
    print('waiting for captcha to be solved')
    WebDriverWait(driver, 60).until(
        EC.text_to_be_present_in_element(('tag name', 'body'), 'Account Information')
    )

def logout():
    """Logs out of a mihoyo acccount"""
    print('logging out of account')
    switch(1)
    driver.delete_all_cookies()
    driver.get('https://account.mihoyo.com/#/login')

def get_cookies() -> dict[str, str]:
    """Returns a list of old-style """
    print('fetching login cookies')
    login_ticket = driver.get_cookie('login_ticket')['value'] # type: ignore
    r = requests.get(f"https://webapi-os.account.mihoyo.com/Api/cookie_accountinfo_by_loginticket?login_ticket={login_ticket}")
    return dict(r.cookies)


def run() -> list[dict]:
    accounts = []
    try:
        while True:
            print('='*50)
            email, password = register_account()
            login(email, password)
            accounts.append({
                'email': email,
                'password': password,
                'cookies': get_cookies()
            })
            logout()
    except Exception as e:
        traceback.print_exc()
    finally:
        return accounts
    
if __name__ == '__main__':
    accounts = run()
    with open('accounts.json', 'r') as file:
        data = json.load(file)
    data.extend(accounts)
    with open('accounts.json', 'w') as file:
        json.dump(data, file, indent=4)
    