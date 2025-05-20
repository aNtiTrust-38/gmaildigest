#!/usr/bin/env python3
"""
Gmail Digest Assistant - Main entry point
"""
import logging
import sys
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def check_env_file():
    """Check if .env file exists and if it's encrypted"""
    env_path = Path('.env')
    if not env_path.exists():
        logger.error(".env file not found. Please run setup_config.py first")
        sys.exit(1)
        
    # Check if env file is encrypted (first 16 bytes would be salt)
    with open(env_path, 'rb') as f:
        content = f.read(17)  # Read a bit more than 16 bytes
        
    # If file starts with binary data (salt), it's likely encrypted
    is_encrypted = not all(byte in range(32, 127) for byte in content)
    
    if is_encrypted:
        logger.info("Encrypted .env file detected, loading with decryption")
        try:
            # First check if load_env module exists
            load_env_path = Path('load_env.py')
            if not load_env_path.exists():
                logger.error("Encrypted .env file detected but load_env.py not found")
                logger.error("Please run setup_config.py again to recreate it")
                sys.exit(1)
                
            # Try to import and run the load_env module
            try:
                import load_env
                success = load_env.load_encrypted_env()
                if not success:
                    logger.error("Failed to decrypt .env file. Check your password")
                    sys.exit(1)
            except ImportError:
                logger.error("Could not import load_env module")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error loading encrypted environment: {e}")
            sys.exit(1)
    else:
        # Regular .env file, load with dotenv
        from dotenv import load_dotenv
        load_dotenv()
        logger.info(".env file loaded")

def main():
    """Main entry point for the Gmail Digest Assistant"""
    try:
        # Check and load environment variables
        check_env_file()
        logger.info("Starting Gmail Digest Assistant...")
        
        # Ensure required environment variables are set
        required_vars = ['TELEGRAM_BOT_TOKEN', 'CREDENTIALS_PATH', 'FORWARD_EMAIL']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            logger.error("Please run setup_config.py to configure the application")
            sys.exit(1)
        
        # Import here to avoid circular imports
        from gmaildigest.telegram_bot import GmailDigestBot
        
        # Start the bot
        bot = GmailDigestBot()
        logger.info("Bot initialized, starting polling...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
