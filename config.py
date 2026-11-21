import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    database_url = os.environ.get('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url or 'sqlite:///maintenance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = (
        os.environ.get('UPLOAD_FOLDER')
        or os.path.join('/tmp' if os.environ.get('VERCEL') else os.path.dirname(os.path.abspath(__file__)), 'uploads')
    )
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')