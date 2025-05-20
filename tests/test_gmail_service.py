"""
Test suite for Gmail service functionality
"""
import os
import unittest
from datetime import datetime, timedelta
from dotenv import load_dotenv
from gmaildigest.auth import GmailAuthenticator
from gmaildigest.gmail_service import GmailService

# Load environment variables
load_dotenv()

class TestGmailService(unittest.TestCase):
    """Test cases for GmailService class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        print("\nInitializing Gmail service tests...")
        try:
            # Initialize authenticator
            auth = GmailAuthenticator()
            credentials = auth.get_credentials()
            if not credentials:
                raise Exception("Failed to obtain credentials")
            
            # Initialize service
            cls.service = GmailService(credentials)
            print("✓ Successfully authenticated with Gmail")
        except Exception as e:
            print(f"✗ Setup failed: {e}")
            raise
    
    def setUp(self):
        """Setup before each test"""
        print(f"\nRunning: {self._testMethodName}")
    
    def test_1_authentication(self):
        """Test if authentication is working"""
        self.assertIsNotNone(self.service.service, "Gmail service should be initialized")
        print("✓ Authentication test passed")
    
    def test_2_fetch_messages(self):
        """Test message fetching functionality"""
        # Test with small result set
        messages = self.service.get_messages(max_results=5)
        self.assertIsInstance(messages, list, "Should return a list")
        self.assertLessEqual(len(messages), 5, "Should respect max_results parameter")
        
        # Verify message structure
        if messages:
            message = messages[0]
            required_fields = ['id', 'thread_id', 'subject', 'from', 'to', 'date', 'body', 'labels']
            for field in required_fields:
                self.assertIn(field, message, f"Message should contain {field}")
        
        print(f"✓ Successfully fetched {len(messages)} messages")
    
    def test_3_search_messages(self):
        """Test message search functionality"""
        # Search for recent messages (last 24 hours)
        date = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')
        query = f'after:{date}'
        
        messages = self.service.get_messages(max_results=5, query=query)
        self.assertIsInstance(messages, list, "Should return a list")
        
        print(f"✓ Successfully tested search with {len(messages)} results")
    
    def test_4_sender_importance(self):
        """Test sender importance marking functionality"""
        # Use a test email address
        test_sender = "test@example.com"
        
        # Test marking as important
        success = self.service.mark_sender_important(test_sender, True)
        self.assertTrue(success, "Should successfully mark sender as important")
        
        # Verify importance status
        is_important = self.service.get_sender_importance(test_sender)
        self.assertTrue(is_important, "Sender should be marked as important")
        
        # Test cache
        is_important_cached = self.service.get_sender_importance(test_sender)
        self.assertTrue(is_important_cached, "Should return cached importance status")
        
        print("✓ Successfully tested sender importance functionality")
    
    def test_5_email_forwarding(self):
        """Test email forwarding functionality"""
        # Get a test message
        messages = self.service.get_messages(max_results=1)
        if not messages:
            self.skipTest("No messages available for forwarding test")
        
        test_message = messages[0]
        forward_to = os.getenv('TEST_FORWARD_EMAIL', 'kai@peacefamily.us')
        
        # Test forwarding
        success = self.service.forward_email(test_message['id'], forward_to)
        self.assertTrue(success, "Should successfully forward email")
        
        print("✓ Successfully tested email forwarding")
    
    def test_6_error_handling(self):
        """Test error handling"""
        # Test with invalid message ID
        success = self.service.forward_email('invalid_id', 'test@example.com')
        self.assertFalse(success, "Should handle invalid message ID gracefully")
        
        # Test with invalid query
        messages = self.service.get_messages(query='invalid:query')
        self.assertEqual(len(messages), 0, "Should handle invalid query gracefully")
        
        print("✓ Successfully tested error handling")

if __name__ == '__main__':
    unittest.main(verbosity=2) 