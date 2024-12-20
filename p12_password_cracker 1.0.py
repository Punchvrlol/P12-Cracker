
import string
import time
import concurrent.futures
import requests
from itertools import product
from threading import Lock
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.hazmat.backends import default_backend
import os

# User-friendly configuration section: Add your webhook URL and custom passcodes below

WEBHOOK_URL = 'YOUR_WEBHOOK_URL_HERE'  # Replace with your actual webhook URL
CUSTOM_PASSCODES = [
    'AppleP12.com', 'AppleP12', 'applep12.com', 'applep12', 'nabzclan.vip',
    'region of tech', '1', '12', '123', '1234', '12345', '123456', '1234567',
    '12345678', '123456789', '1234567890'
]

def download_file(file_link):
    """Download the .p12 file from the given link."""
    try:
        response = requests.get(file_link, stream=True)
        if response.status_code == 200 and response.content:
            print(f"File downloaded successfully: {file_link}")
            return response.content
        else:
            print(f"Failed to download the file: {file_link}, Status code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {file_link}, Error: {e}")
        return None

def check_password(file_data, password):
    """Check if the password works for the .p12 file."""
    try:
        load_key_and_certificates(file_data, password.encode(), backend=default_backend())
        return True
    except ValueError:
        return False
    except Exception:
        return False

def send_to_webhook(file_number, password, webhook_url):
    """Send the found password to a Discord webhook."""
    payload = {
        'content': f'Password found for File {file_number}: {password}'
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            print(f"Password sent to webhook for File {file_number}")
        else:
            print(f"Failed to send to webhook. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending to webhook: {e}")

def brute_force_worker(file_data, file_link, file_number, max_length, start_password, lock, found_password, total_files, custom_passcodes, webhook_url):
    """Brute force worker to try passwords on a single file."""
    characters = string.ascii_lowercase + string.digits + string.ascii_uppercase
    start_found = start_password is None  # Start right away if no start password is provided

    print(f"Processing File {file_number} of {total_files}")

    # First, check custom passcodes
    if custom_passcodes:
        for passcode in custom_passcodes:
            print(f"Trying custom passcode: {passcode} for File {file_number}")
            if check_password(file_data, passcode):
                with lock:
                    if not found_password[0]:
                        found_password[0] = passcode
                        print(f"Password found for File {file_number}: {passcode}")
                        send_to_webhook(file_number, passcode, webhook_url)
                        return True
    
    # If no custom passcode is found, start brute-forcing
    for length in range(1, max_length + 1):
        for password_tuple in product(characters, repeat=length):
            password = ''.join(password_tuple)
            if start_password and not start_found:
                if password == start_password:
                    start_found = True
                continue

            print(f"Trying password: {password} for File {file_number}")

            if check_password(file_data, password):
                with lock:
                    if not found_password[0]:
                        found_password[0] = password
                        print(f"Password found for File {file_number}: {password}")
                        send_to_webhook(file_number, password, webhook_url)  # Send the found password to the webhook
                        return True
    return False

def process_files(file_links, max_length, start_password, num_workers, custom_passcodes, webhook_url):
    """Process a list of .p12 files and attempt brute-forcing passwords."""
    lock = Lock()
    found_password = [None]  # Store found password in a list to allow modification by workers

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []

        for idx, file_link in enumerate(file_links, start=1):
            file_data = download_file(file_link)
            if file_data:
                futures.append(executor.submit(brute_force_worker, file_data, file_link, idx, max_length, start_password, lock, found_password, len(file_links), custom_passcodes, webhook_url))

        for future in concurrent.futures.as_completed(futures):
            future.result()

def main():
    # Configuration
    print("Welcome to the Brute Force P12 Password Cracker!")
    file_links = [
        'ADD YOUR FILE LINK HERE',  # Replace with your actual file links
        'ADD YOUR FILE LINK HERE',  # Replace with your actual file links
        'ADD YOUR FILE LINK HERE'   # Replace with your actual file links
    ]
    
    max_length = 8  # Maximum password length to try
    start_password = input("Enter the starting password (or leave blank to start from the beginning): ").strip()
    start_password = None if start_password == '' else start_password

    num_workers = int(input("Enter the number of workers: "))  # Set number of workers here

    process_files(file_links, max_length, start_password, num_workers, CUSTOM_PASSCODES, WEBHOOK_URL)

if __name__ == "__main__":
    main()
