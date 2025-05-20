from setuptools import setup, find_packages

setup(
    name="gmaildigest",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'google-auth-oauthlib>=1.0.0',
        'google-auth-httplib2>=0.1.0',
        'google-api-python-client>=2.0.0',
        'python-telegram-bot>=20.0',
        'python-dotenv>=1.0.0',
        'aiohttp>=3.8.0',
        'dateparser>=1.1.0',
        'pytz>=2023.3'
    ],
) 