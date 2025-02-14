import tls_client 
import random
import time
import re
import toml
import ctypes
import threading
import string
import uuid
import requests

from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from logmagix import Logger, Home

with open('input/config.toml') as f:
    config = toml.load(f)

DEBUG = config['dev'].get('Debug', False)
log = Logger()

def debug(func_or_message, *args, **kwargs) -> callable:
    if callable(func_or_message):
        @wraps(func_or_message)
        def wrapper(*args, **kwargs):
            result = func_or_message(*args, **kwargs)
            if DEBUG:
                log.debug(f"{func_or_message.__name__} returned: {result}")
            return result
        return wrapper
    else:
        if DEBUG:
            log.debug(f"Debug: {func_or_message}")

def debug_response(response) -> None:
    debug(response.headers)
    debug(response.text)
    debug(response.status_code)

class Miscellaneous:
    @debug
    def get_proxies(self) -> dict:
        try:
            if config['dev'].get('Proxyless', False):
                return None
                
            with open('input/proxies.txt') as f:
                proxies = [line.strip() for line in f if line.strip()]
                if not proxies:
                    log.warning("No proxies available. Running in proxyless mode.")
                    return None
                
                proxy_choice = random.choice(proxies)
                proxy_dict = {
                    "http": f"http://{proxy_choice}",
                    "https": f"http://{proxy_choice}"
                }
                log.debug(f"Using proxy: {proxy_choice}")
                return proxy_dict
        except FileNotFoundError:
            log.failure("Proxy file not found. Running in proxyless mode.")
            return None

    @debug 
    def generate_password(self):
        password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?/", k=16))
        return password
    
    @debug 
    def generate_username(self):
        return ''.join(random.choices(string.ascii_lowercase, k=16))

    @debug 
    def generate_email(self, domain: str = "cybertemp.xyz"):
        username = f"{''.join(random.choices(string.ascii_lowercase + string.digits, k=20))}"
        email = f"{username}@{domain}"
        return email
    
    @debug 
    def randomize_user_agent(self) -> str:
        android_version = f"{random.randint(13, 15)}"
        okhttp_version = f"4.{random.randint(10, 12)}.{random.randint(0, 9)}"
        
        user_agent = f"Crunchyroll/3.74.2 Android/{android_version} okhttp/{okhttp_version}"
        return user_agent
    
    class Title:
        def __init__(self) -> None:
            self.running = False

        def start_title_updates(self, total, start_time) -> None:
            self.running = True
            def updater():
                while self.running:
                    self.update_title(total, start_time)
                    time.sleep(0.5)
            threading.Thread(target=updater, daemon=True).start()

        def stop_title_updates(self) -> None:
            self.running = False

        def update_title(self, total, start_time) -> None:
            try:
                elapsed_time = round(time.time() - start_time, 2)
                title = f'discord.cyberious.xyz | Total: {total} | Time Elapsed: {elapsed_time}s'

                sanitized_title = ''.join(c if c.isprintable() else '?' for c in title)
                ctypes.windll.kernel32.SetConsoleTitleW(sanitized_title)
            except Exception as e:
                log.debug(f"Failed to update console title: {e}")

class AccountCreator:
    def __init__(self, proxy_dict: dict = None) -> None:
        self.session = tls_client.Session("okhttp4_android_12" , random_tls_extension_order=True)
        self.session.headers = {
            'authorization': 'Basic ZG1yeWZlc2NkYm90dWJldW56NXo6NU45aThPV2cyVmtNcm1oekNfNUNXekRLOG55SXo0QU0=',
            'connection': 'Keep-Alive',
            'content-type': 'application/x-www-form-urlencoded',
            'etp-anonymous-id': str(uuid.uuid4()),
            'host': 'www.crunchyroll.com',
            'user-agent': Miscellaneous().randomize_user_agent(),
            'x-datadog-sampling-priority': '0',
        }
        self.session.proxies = proxy_dict

    @debug
    def get_token(self):
        data = f'grant_type=client_id&device_id={str(uuid.uuid4())}&device_name=sdk_gphone64_x86_64&device_type=Google sdk_gphone64_x86_64'

        response = self.session.post('https://www.crunchyroll.com/auth/v1/token', data=data)

        if response.status_code == 200:
            access_token = response.json()['access_token']
            self.session.headers['authorization'] = f"Bearer {access_token}"
            self.session.headers['content-type'] = 'application/json; charset=UTF-8'
            return True
        else:
            log.failure(f"Failed to get token: {response.text}, {response.status_code}")
            return False

    @debug
    def sign_up(self, email: str, password: str):
        json_data = {
            'email': email,
            'password': password,
            'preferred_content_audio_language': 'en-US',
            'preferred_communication_language': 'en-US',
            'preferred_content_subtitle_language': 'en-US',
        }

        response = self.session.post('https://www.crunchyroll.com/accounts/v2', json=json_data)

        json_data = response.json()

        if response.status_code == 201 and json_data.get("account_id"):
            account_id = json_data['account_id']
            external_id = json_data['external_id']
            return account_id, external_id
        else:
            log.failure(f"Failed to sign up: {response.text}, {response.status_code}")
            return None, None
    
    @debug
    def verify_email(self, url: str):
        response = self.session.get(url)
        if response.status_code == 200:
            return True
        else:
            log.failure(f"Failed to verify email: {response.text}, {response.status_code}")
            return False

class EmailHandler:
    def __init__(self, api_key: str = None) -> None:
        self.session = requests.Session()

        if api_key:
            self.session.headers = {"X-API-KEY": api_key}

    @debug
    def check_mailbox(self, email: str, max_retries: int = 5) -> list | None:
        debug(f"Checking mailbox for {email}")
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(f'https://www.cybertemp.xyz/api/getMail?email={email}')
                if response.status_code == 200:
                    return response.json()
                else:
                    log.failure(f"Failed to check mailbox: {response.text}, {response.status_code}")
                    debug(response.json(), response.status_code)
                    break
            except Exception as e:
                log.failure(f"Error checking mailbox: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                break
        return None

    @debug
    def get_mail_id(self, email: str) -> str | None:
        attempt = 0
        debug(f"Getting verification message id for {email}")
        while attempt < 40: 
            messages = self.check_mailbox(email)
            if messages:
                for message in messages:
                    if 'Please Confirm Your Account' in message.get("subject", ""):
                        debug(message)
                        return message.get("id")
            attempt += 1
            time.sleep(1.5)
        debug(f"No verification message found after {attempt} attempts")
        return None 

    @debug
    def fetch_message(self, email: str, message_id: str) -> dict | None:
        debug(f"Fetching message {message_id} for {email}")
        messages = self.check_mailbox(email)
        if messages:
            for message in messages:
                if message.get("id") == message_id:
                    return {
                        "text": message.get("text", ""),
                        "html": message.get("html", ""),
                        "subject": message.get("subject", "")
                    }
        return None
    
    @debug
    def get_verification_url(self, email: str) -> str | None:
        debug(f"Getting verification link for {email}")
        
        mail_id = self.get_mail_id(email)
        if mail_id:
            message = self.fetch_message(email, mail_id)
            login_url_match = re.search(r'https://links\.mail\.crunchyroll\.com/ls/click\?upn=[A-Za-z0-9\-\_\.\=\?\&]+', message.get("text"))
            if login_url_match:
                login_url = login_url_match.group(0)
                return login_url
        return None

def create_account(email_verifed) -> bool:
    try:
        account_start_time = time.time()

        Misc = Miscellaneous()
        proxies = Misc.get_proxies()
        Email_Handler = EmailHandler(proxies)
        Account_Generator = AccountCreator(proxies)
        
        email = Misc.generate_email()
        username = Misc.generate_username()
        password = config["data"].get("password") or Misc.generate_password()

        log.info(f"Starting a new account creation process for {email[:8]}...")

        log.info("Getting Authorization token...")
        if Account_Generator.get_token():
            log.info("Successfully got token, singing up...")
            account_id, external_id = Account_Generator.sign_up(email, password)
            
            if account_id:
                if email_verifed:
                    log.info(f"Sent otp email. Verifying email... (This may take around 40 seconds to complete)")
                    url = Email_Handler.get_verification_url(email)

                    if url:
                        if Account_Generator.verify_email(url):
                            log.info(f"Email successfully verified")
                            
                with open("output/accounts.txt", "a") as f:
                    f.write(f"{email}:{password}\n")
                            
                with open("output/full_account_capture.txt", "a") as f:
                    f.write(f"{email}:{password}:{account_id}:{external_id}\n")
                                        
                log.message("Crunchyroll", f"Account created successfully: {email[:8]}... | {password[:8]}... | {username[:6]}... ", account_start_time, time.time())
                return True
                
        return False
    except Exception as e:
        log.failure(f"Error during account creation process: {e}")
        return False


def main() -> None:
    try:
        start_time = time.time()
        
        # Initialize basic classes
        Misc = Miscellaneous()
        Banner = Home("Crunchyroll Generator", align="center", credits="discord.cyberious.xyz")
        
        # Display Banner
        Banner.display()

        total = 0
        thread_count = config['dev'].get('Threads', 1)
        email_verifed = config["data"].get("email_verified")

        # Start updating the title
        title_updater = Misc.Title()
        title_updater.start_title_updates(total, start_time)
        
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            while True:
                futures = [
                    executor.submit(create_account, email_verifed)
                    for _ in range(thread_count)
                ]

                for future in as_completed(futures):
                    try:
                        if future.result():
                            total += 1
                    except Exception as e:
                        log.failure(f"Thread error: {e}")

    except KeyboardInterrupt:
        log.info("Process interrupted by user. Exiting...")
    except Exception as e:
        log.failure(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()