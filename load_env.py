#!/usr/bin/env python3
"""
Gmail Digest Assistant - Environment Loader
This utility decrypts and loads the encrypted .env file
"""
import os
import base64
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from dotenv import load_dotenv

def load_encrypted_env():
    """Decrypt and load the encrypted .env file"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    try:
        with open(env_path, 'rb') as f:
            file_content = f.read()
            
        # First 16 bytes are the salt
        salt = file_content[:16]
        encrypted_data = file_content[16:]
        
        # Get password from user
        password = getpass.getpass("Enter encryption password: ")
        
        # Generate key from password and salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        # Decrypt the data
        fernet = Fernet(key)
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        
        # Write to temporary file and load with dotenv
        temp_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env.temp')
        with open(temp_env_path, 'w') as f:
            f.write(decrypted_data)
            
        # Load environment variables
        load_dotenv(temp_env_path)
        
        # Remove temporary file
        os.unlink(temp_env_path)
        
        print("Environment variables loaded successfully")
        return True
        
    except Exception as e:
        print(f"Error loading environment: {str(e)}")
        return False

if __name__ == "__main__":
    load_encrypted_env()
