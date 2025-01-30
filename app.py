import os
from flask import Flask, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from requests_oauthlib import OAuth2Session
from flask_session import Session

# Flask-Konfiguration
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Fitbit API-Konfiguration
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")
AUTHORIZATION_BASE_URL = 'https://www.fitbit.com/oauth2/authorize'
TOKEN_URL = 'https://api.fitbit.com/oauth2/token'

# Scopes für Fitbit API
SCOPES = ['activity', 'heartrate', 'profile', 'nutrition', 'location', 'settings', 'sleep',
          'social', 'weight', 'temperature', 'respiratory_rate']

# SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy & Migrations-Setup
db = SQLAlchemy(app)

# Flask-Session-Konfiguration
app.config['SESSION_TYPE'] = 'filesystem'  # Oder 'sqlalchemy' für DB-Sessions
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session/'  # Falls 'filesystem' genutzt wird

Session(app)

# Datenbankmodell für Tokens

class Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String(512), nullable=False)
    refresh_token = db.Column(db.String(512), nullable=False)
    scope = db.Column(db.String(256), nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, access_token, refresh_token, scope, expires_at):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.scope = scope
        self.expires_at = expires_at

@app.route('/')
def home():
    """Homepage mit Login-Link."""
    return '<a href="/login">Mit Fitbit verbinden</a>'

@app.route('/login')
def login():
    """Start der OAuth2-Authentifizierung."""
    fitbit = OAuth2Session(CLIENT_ID, scope=SCOPES, redirect_uri=REDIRECT_URI)
    authorization_url, state = fitbit.authorization_url(AUTHORIZATION_BASE_URL)

    # State merken
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    """Callback von Fitbit nach Einverständniserklärung."""
    fitbit = OAuth2Session(CLIENT_ID, state=session['oauth_state'], redirect_uri=REDIRECT_URI)
    token = fitbit.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET,
                               authorization_response=request.url)


    # Access-Token speichern
    save_token_to_db(token)

    return "Vielen Dank! Ihre Angaben wurden erfolgreich gespeichert."

def save_token_to_db(token):
    # Speichert den Token in der PostgresSQL-Datenbank
    new_token = Token(
        access_token=token.get('access_token'),
        refresh_token=token.get('refresh_token'),
        scope=','.join(token.get('scope',[])),
        expires_at=token.get('expires_at')
    )

    db.session.add(new_token)
    db.session.commit()