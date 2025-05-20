"""
Unit tests for Gmail Service component
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import unittest
from unittest.mock import MagicMock, patch
import datetime
import pytest
from gmaildigest.gmail_service import GmailService

class TestGmailService(unittest.TestCase):
    """Test cases for Gmail Service functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a mock credentials object
        self.mock_credentials = MagicMock()
        
        # Create the GmailService instance with mock credentials
        self.gmail_service = GmailService(self.mock_credentials)
        
        # Replace the actual build function with a mock
        self.gmail_api_mock = MagicMock()
        self.gmail_service.service = self.gmail_api_mock
        
    def test_initialization(self):
        """Test service initialization"""
        self.assertIsNotNone(self.gmail_service)
        self.assertEqual(self.gmail_service.credentials, self.mock_credentials)
        
    @patch('gmaildigest.gmail_service.build')
    def test_build_service(self, mock_build):
        """Test building the Gmail service"""
        # Create a new instance to test the build process
        mock_credentials = MagicMock()
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        service = GmailService(mock_credentials)
        
        # Verify build was called with correct parameters
        mock_build.assert_called_once_with('gmail', 'v1', credentials=mock_credentials)
        self.assertEqual(service.service, mock_service)
        
    def test_get_messages_empty(self):
        """Test fetching messages when none are available"""
        # Mock API response for no messages
        users_mock = MagicMock()
        messages_mock = MagicMock()
        list_mock = MagicMock()
        
        self.gmail_api_mock.users.return_value = users_mock
        users_mock.messages.return_value = messages_mock
        messages_mock.list.return_value = list_mock
        
        # Empty response (no messages)
        list_mock.execute.return_value = {}
        
        result = self.gmail_service.get_messages()
        self.assertEqual(result, [])
        
    def test_get_messages_with_data(self):
        """Test fetching messages with sample data"""
        # Mock the Gmail API responses
        users_mock = MagicMock()
        messages_mock = MagicMock()
        list_mock = MagicMock()
        get_mock = MagicMock()
        
        self.gmail_api_mock.users.return_value = users_mock
        users_mock.messages.return_value = messages_mock
        messages_mock.list.return_value = list_mock
        messages_mock.get.return_value = get_mock
        
        # Sample list response with message IDs
        list_mock.execute.return_value = {
            'messages': [
                {'id': 'msg1'}, 
                {'id': 'msg2'}
            ]
        }
        
        # Sample message data for first message
        get_mock.execute.side_effect = [
            {
                'id': 'msg1',
                'snippet': 'Message 1 content',
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': 'sender1@example.com'},
                        {'name': 'Subject', 'value': 'Test Subject 1'},
                        {'name': 'Date', 'value': 'Mon, 01 Jan 2023 12:00:00 +0000'}
                    ],
                    'body': {'data': 'SGVsbG8gV29ybGQ='}  # Base64: "Hello World"
                }
            },
            {
                'id': 'msg2',
                'snippet': 'Message 2 content',
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': 'sender2@example.com'},
                        {'name': 'Subject', 'value': 'Test Subject 2'},
                        {'name': 'Date', 'value': 'Tue, 02 Jan 2023 13:00:00 +0000'}
                    ],
                    'body': {'data': 'VGVzdCBNZXNzYWdl'}  # Base64: "Test Message"
                }
            }
        ]
        
        # Call the method under test
        result = self.gmail_service.get_messages(max_results=2)
        
        # Verify the results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'msg1')
        self.assertEqual(result[0]['from'], 'sender1@example.com')
        self.assertEqual(result[0]['subject'], 'Test Subject 1')
        self.assertEqual(result[1]['id'], 'msg2')
        self.assertEqual(result[1]['from'], 'sender2@example.com')
        self.assertEqual(result[1]['subject'], 'Test Subject 2')
        
    def test_mark_sender_important(self):
        """Test marking a sender as important"""
        # Set up mocks for storing important senders
        self.gmail_service._load_important_senders = MagicMock()
        self.gmail_service._save_important_senders = MagicMock()
        self.gmail_service.important_senders = set()
        
        # Test marking a new sender
        result = self.gmail_service.mark_sender_important('test@example.com')
        
        # Verify results
        self.assertTrue(result)
        self.assertIn('test@example.com', self.gmail_service.important_senders)
        self.gmail_service._save_important_senders.assert_called_once()
        
    def test_is_sender_important(self):
        """Test checking if a sender is important"""
        # Set up test data
        self.gmail_service.important_senders = {'important@example.com'}
        
        # Test with important and non-important senders
        self.assertTrue(self.gmail_service.is_sender_important('important@example.com'))
        self.assertFalse(self.gmail_service.is_sender_important('notimportant@example.com'))
        
    @patch('gmaildigest.gmail_service.base64.urlsafe_b64encode')
    def test_forward_email(self, mock_encode):
        """Test email forwarding functionality"""
        # Set up mocks
        users_mock = MagicMock()
        messages_mock = MagicMock()
        get_mock = MagicMock()
        send_mock = MagicMock()
        
        self.gmail_api_mock.users.return_value = users_mock
        users_mock.messages.return_value = messages_mock
        messages_mock.get.return_value = get_mock
        messages_mock.send.return_value = send_mock
        
        # Mock email retrieval
        get_mock.execute.return_value = {
            'id': 'msg1',
            'snippet': 'Original message',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Original Subject'},
                    {'name': 'Date', 'value': 'Mon, 01 Jan 2023 12:00:00 +0000'}
                ],
                'body': {'data': 'SGVsbG8gV29ybGQ='}  # Base64: "Hello World"
            }
        }
        
        # Mock base64 encoding (for raw email)
        mock_encode.return_value = b'encoded_email_data'
        
        # Mock send response
        send_response = MagicMock()
        send_mock.execute.return_value = {'id': 'fwd1'}
        
        # Call the method under test
        result = self.gmail_service.forward_email(
            'msg1', 
            'forward@example.com', 
            'Forwarded: Original Subject'
        )
        
        # Verify results
        self.assertEqual(result, 'fwd1')
        
        # Verify the original message was retrieved
        messages_mock.get.assert_called_once()
        
        # Verify a new message was sent
        messages_mock.send.assert_called_once()
        
    def test_search_email(self):
        """Test searching emails by query"""
        # Mock API response
        users_mock = MagicMock()
        messages_mock = MagicMock()
        list_mock = MagicMock()
        get_mock = MagicMock()

        self.gmail_api_mock.users.return_value = users_mock
        users_mock.messages.return_value = messages_mock
        messages_mock.list.return_value = list_mock
        messages_mock.get.return_value = get_mock

        # Sample search results
        list_mock.execute.return_value = {
            'messages': [
                {'id': 'msg1'}, 
                {'id': 'msg2'}
            ]
        }
        # Return actual message dicts for get
        get_mock.execute.side_effect = [
            {
                'id': 'msg1',
                'threadId': 't1',
                'labelIds': [],
                'snippet': 'Message 1 content',
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': 'sender1@example.com'},
                        {'name': 'Subject', 'value': 'Test Subject 1'},
                        {'name': 'Date', 'value': 'Mon, 01 Jan 2023 12:00:00 +0000'}
                    ],
                    'body': {'data': 'SGVsbG8gV29ybGQ='}
                }
            },
            {
                'id': 'msg2',
                'threadId': 't2',
                'labelIds': [],
                'snippet': 'Message 2 content',
                'payload': {
                    'headers': [
                        {'name': 'From', 'value': 'sender2@example.com'},
                        {'name': 'Subject', 'value': 'Test Subject 2'},
                        {'name': 'Date', 'value': 'Tue, 02 Jan 2023 13:00:00 +0000'}
                    ],
                    'body': {'data': 'VGVzdCBNZXNzYWdl'}
                }
            }
        ]

        # Call the method with a search query
        result = self.gmail_service.search_emails('from:example.com')

        # Verify search was called with correct parameters
        messages_mock.list.assert_called_with(userId='me', q='from:example.com')

        # Verify results
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'msg1')
        self.assertEqual(result[1]['id'], 'msg2')
        
    def test_error_handling(self):
        """Test error handling during API calls"""
        # Mock API failure
        users_mock = MagicMock()
        messages_mock = MagicMock()
        list_mock = MagicMock()
        
        self.gmail_api_mock.users.return_value = users_mock
        users_mock.messages.return_value = messages_mock
        messages_mock.list.return_value = list_mock
        
        # Simulate an API error
        list_mock.execute.side_effect = Exception("API Error")
        
        # Call the method and verify error handling
        result = self.gmail_service.get_messages()
        
        # Should return an empty list on error
        self.assertEqual(result, [])
        
if __name__ == '__main__':
    unittest.main() 