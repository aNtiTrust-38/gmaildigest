#!/usr/bin/env python3
"""
Gmail Digest Assistant - Configuration GUI
This utility helps users set up the .env configuration file with a user-friendly interface.
"""
import os
import sys
import json
import base64
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path
import stat
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SetupConfig:
    """GUI configuration tool for Gmail Digest Assistant"""
    
    def __init__(self, root):
        """Initialize the configuration tool"""
        self.root = root
        self.root.title("Gmail Digest Assistant - Setup")
        # Load previous window size if available
        self._load_window_size()
        self.root.resizable(True, True)
        
        # Set application icon if available
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass  # Icon not found, use default
            
        # Configuration variables
        self.credentials_path = tk.StringVar()
        self.telegram_token = tk.StringVar()
        self.forward_email = tk.StringVar()
        self.check_interval = tk.StringVar(value="15")
        self.anthropic_api_key = tk.StringVar()
        
        # Salt for encryption (fixed per installation)
        self.salt = os.urandom(16)
        
        self.create_widgets()
        # Bind window close to save size
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
    def _load_window_size(self):
        import json
        import os
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.gui_config.json')
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            self.root.geometry(f"{cfg['width']}x{cfg['height']}")
        except Exception:
            self.root.geometry("550x450")

    def _on_close(self):
        import json
        import os
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.gui_config.json')
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        try:
            with open(config_path, 'w') as f:
                json.dump({'width': width, 'height': height}, f)
        except Exception:
            pass
        self.root.destroy()
        
    def create_widgets(self):
        """Create the UI widgets"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Gmail Digest Assistant Configuration", 
            font=("Helvetica", 16)
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky=tk.W)
        
        # Credentials file selector
        ttk.Label(main_frame, text="Google Credentials File:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        
        credentials_entry = ttk.Entry(
            main_frame, 
            textvariable=self.credentials_path,
            width=40
        )
        credentials_entry.grid(row=1, column=1, pady=5)
        
        browse_button = ttk.Button(
            main_frame,
            text="Browse",
            command=self.browse_credentials
        )
        browse_button.grid(row=1, column=2, padx=5, pady=5)
        
        # Telegram token input
        ttk.Label(main_frame, text="Telegram Bot Token:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        
        ttk.Entry(
            main_frame,
            textvariable=self.telegram_token,
            width=40
        ).grid(row=2, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Help text for Telegram token
        token_help = ttk.Label(
            main_frame,
            text="Get this from @BotFather on Telegram",
            font=("Helvetica", 9),
            foreground="gray"
        )
        token_help.grid(row=3, column=1, columnspan=2, sticky=tk.W)
        
        # Anthropic API key input (optional)
        ttk.Label(main_frame, text="Anthropic API Key (optional):").grid(
            row=3, column=0, sticky=tk.W, pady=5
        )
        ttk.Entry(
            main_frame,
            textvariable=self.anthropic_api_key,
            width=40
        ).grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5)
        # Help label with clickable link
        def open_anthropic_link(event):
            import webbrowser
            webbrowser.open_new("https://console.anthropic.com/")
        anthropic_help = ttk.Label(
            main_frame,
            text="Optional: For advanced AI summarization. If omitted, local summarization will be used. Get your API key from the Anthropic dashboard, here.",
            font=("Helvetica", 9),
            foreground="gray",
            cursor="hand2"
        )
        anthropic_help.grid(row=4, column=1, columnspan=2, sticky=tk.W)
        # Make 'here' clickable
        def on_enter(event):
            anthropic_help.config(foreground="blue", font=("Helvetica", 9, "underline"))
        def on_leave(event):
            anthropic_help.config(foreground="gray", font=("Helvetica", 9))
        anthropic_help.bind("<Button-1>", open_anthropic_link)
        anthropic_help.bind("<Enter>", on_enter)
        anthropic_help.bind("<Leave>", on_leave)
        
        # Forward email input
        ttk.Label(main_frame, text="Forward Email Address:").grid(
            row=5, column=0, sticky=tk.W, pady=5
        )
        
        ttk.Entry(
            main_frame,
            textvariable=self.forward_email,
            width=40
        ).grid(row=5, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        # Default email help text
        email_help = ttk.Label(
            main_frame, 
            text="Important emails will be forwarded to this address",
            font=("Helvetica", 9),
            foreground="gray"
        )
        email_help.grid(row=6, column=1, columnspan=2, sticky=tk.W)
        
        # Check interval selection
        ttk.Label(main_frame, text="Check Interval:").grid(
            row=7, column=0, sticky=tk.W, pady=5
        )
        
        interval_combo = ttk.Combobox(
            main_frame,
            textvariable=self.check_interval,
            width=10,
            state="readonly"
        )
        interval_combo["values"] = ["15", "30", "60", "1H"]
        interval_combo.current(0)
        interval_combo.grid(row=7, column=1, sticky=tk.W, pady=5)
        
        # Minutes label
        minutes_label = ttk.Label(main_frame, text="minutes")
        minutes_label.grid(row=7, column=1, padx=(70, 0), sticky=tk.W)
        
        # Encryption option
        self.encrypt_var = tk.BooleanVar(value=True)
        encrypt_check = ttk.Checkbutton(
            main_frame,
            text="Encrypt .env file (recommended)",
            variable=self.encrypt_var
        )
        encrypt_check.grid(row=8, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
        
        encryption_note = ttk.Label(
            main_frame,
            text="Note: You'll need to provide a password to encrypt your configuration",
            font=("Helvetica", 9),
            foreground="gray"
        )
        encryption_note.grid(row=9, column=0, columnspan=3, sticky=tk.W)
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=10, column=0, columnspan=3, pady=20)
        
        save_button = ttk.Button(
            button_frame,
            text="Save Configuration",
            command=self.save_config,
            width=20
        )
        save_button.pack(side=tk.LEFT, padx=5)
        
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.root.destroy,
            width=10
        )
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var,
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def browse_credentials(self):
        """Open file browser to select credentials.json"""
        filename = filedialog.askopenfilename(
            title="Select Google Credentials JSON File",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if filename:
            self.credentials_path.set(filename)
            self.status_var.set(f"Selected: {filename}")
            
            # Validate that it's a proper credentials file
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                if 'installed' in data and 'client_id' in data['installed']:
                    self.status_var.set("Valid credentials file selected")
                else:
                    self.status_var.set("Warning: This doesn't appear to be a valid Google credentials file")
            except:
                self.status_var.set("Warning: Unable to parse the selected file")
                
    def _get_encryption_key(self, password):
        """Generate an encryption key from password"""
        if not password:
            return None
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
                
    def save_config(self):
        """Save the configuration to .env file"""
        # Validate inputs
        if not self.credentials_path.get():
            messagebox.showerror("Error", "Please select a credentials file")
            return
            
        if not self.telegram_token.get():
            messagebox.showerror("Error", "Please enter your Telegram bot token")
            return
            
        if not self.forward_email.get():
            messagebox.showerror("Error", "Please enter a forwarding email address")
            return
            
        # Adjust interval for 1H
        check_interval = self.check_interval.get()
        if check_interval == "1H":
            check_interval = "60"
            
        # Get encryption password if enabled
        encryption_key = None
        if self.encrypt_var.get():
            password = self.prompt_for_password()
            if not password:  # User canceled
                return
                
            encryption_key = self._get_encryption_key(password)
            
        # Create .env content
        env_content = f"""# Gmail Digest Assistant Configuration\n# Created by setup tool on {import_time()}\n\n# === Google API Credentials ===\nCREDENTIALS_PATH={os.path.basename(self.credentials_path.get())}\n\n# === Telegram Bot ===\nTELEGRAM_BOT_TOKEN={self.telegram_token.get()}\n\n# === Anthropic API (optional) ===\nANTHROPIC_API_KEY={self.anthropic_api_key.get()}\n\nFORWARD_EMAIL={self.forward_email.get()}\nCHECK_INTERVAL_MINUTES={check_interval}\n"""
        
        try:
            # Copy the credentials file to the application directory if it's not already there
            target_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                            os.path.basename(self.credentials_path.get()))
            
            if self.credentials_path.get() != target_creds_path:
                with open(self.credentials_path.get(), 'r') as src_file:
                    with open(target_creds_path, 'w') as dest_file:
                        dest_file.write(src_file.read())
                        
                # Set restrictive permissions on the credentials file
                os.chmod(target_creds_path, stat.S_IRUSR | stat.S_IWUSR)
                
            # Save .env file (encrypted or plaintext)
            env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
            
            if encryption_key:
                # Save encrypted
                fernet = Fernet(encryption_key)
                encrypted_content = fernet.encrypt(env_content.encode())
                
                # Save salt and encrypted content
                with open(env_path, 'wb') as f:
                    f.write(self.salt)  # First 16 bytes are the salt
                    f.write(encrypted_content)
                    
                # Create a loader script if encrypted
                self.create_env_loader(env_path)
                
            else:
                # Save plaintext
                with open(env_path, 'w') as f:
                    f.write(env_content)
                    
            # Set restrictive permissions on .env file
            os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
            
            messagebox.showinfo(
                "Success", 
                "Configuration saved successfully!\n\nYou can now run the application."
            )
            self.root.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            
    def prompt_for_password(self):
        """Prompt user for encryption password"""
        password_window = tk.Toplevel(self.root)
        password_window.title("Set Encryption Password")
        password_window.geometry("400x200")
        password_window.transient(self.root)
        password_window.grab_set()
        
        ttk.Label(
            password_window,
            text="Enter a password to encrypt your configuration:",
            font=("Helvetica", 11)
        ).pack(pady=(20, 10))
        
        password = tk.StringVar()
        confirm_password = tk.StringVar()
        
        ttk.Entry(
            password_window,
            textvariable=password,
            show="●",
            width=30
        ).pack(pady=5)
        
        ttk.Label(
            password_window,
            text="Confirm password:"
        ).pack(pady=(10, 5))
        
        ttk.Entry(
            password_window,
            textvariable=confirm_password,
            show="●",
            width=30
        ).pack(pady=5)
        
        result = [None]  # Use list for nonlocal access
        
        def on_ok():
            if password.get() != confirm_password.get():
                messagebox.showerror("Error", "Passwords do not match")
                return
                
            if not password.get():
                messagebox.showerror("Error", "Password cannot be empty")
                return
                
            result[0] = password.get()
            password_window.destroy()
            
        def on_cancel():
            password_window.destroy()
            
        button_frame = ttk.Frame(password_window)
        button_frame.pack(pady=15)
        
        ttk.Button(
            button_frame,
            text="OK",
            command=on_ok,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        self.root.wait_window(password_window)
        return result[0]
        
    def create_env_loader(self, env_path):
        """Create a utility to load the encrypted .env file"""
        loader_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'load_env.py')
        
        loader_content = '''#!/usr/bin/env python3
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
'''
        
        with open(loader_path, 'w') as f:
            f.write(loader_content)
            
        # Make it executable
        os.chmod(loader_path, stat.S_IRWXU)

def import_time():
    """Get current time for .env file comment"""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def main():
    """Run the configuration tool"""
    # Check for dependencies
    try:
        import cryptography
    except ImportError:
        print("Missing dependencies. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
        
    root = tk.Tk()
    app = SetupConfig(root)
    root.mainloop()

if __name__ == "__main__":
    main() 