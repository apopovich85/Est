import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()

class Config:
    SECRET_KEY = 'dev-secret-key-change-in-production'
    
    # Put database in project root (OneDrive fix)
    database_file = basedir / 'estimates.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{database_file}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

config = {
    'default': Config
}