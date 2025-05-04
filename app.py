from bson import ObjectId
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import requests
import json
import os
import time
import datetime
import uuid
from config import Config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from stytch import Client as StytchClient
from stytch.core.response_base import StytchError
from flask_pymongo import PyMongo

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Configure MongoDB
# Configure MongoDB - FIXED VERSION
# Debug logging for MongoDB configuration
# print(f"MongoDB URI configured: {'Yes' if app.config.get('MONGO_URI') else 'No'}")
# if app.config.get('MONGO_URI'):
#     # Only log first few characters to avoid exposing credentials
#     app.logger.info(f"MongoDB URI starts with: {app.config.get('MONGO_URI')[:15]}...")

# Then configure Mon
app.config["MONGO_URI"] = Config.MONGO_URI  # Directly use the Config class
mongo = PyMongo(app)

# Configure API endpoints via Cloudflare AI Gateway
openai_endpoint = f"https://gateway.ai.cloudflare.com/v1/{app.config['CLOUDFLARE_ACCOUNT_ID']}/{app.config['CLOUDFLARE_GATEWAY_ID']}/openai/v1/chat/completions"
replicate_endpoint = f"https://gateway.ai.cloudflare.com/v1/{app.config['CLOUDFLARE_ACCOUNT_ID']}/{app.config['CLOUDFLARE_GATEWAY_ID']}/replicate/v1/predictions"

# Initialize Stytch client
stytch_client = StytchClient(
    project_id=app.config['STYTCH_PROJECT_ID'],
    secret=app.config['STYTCH_SECRET'],
    environment=app.config['STYTCH_ENV']
)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/test_mongo')
def test_mongo():
    try:
        # List all collections in the database
        collections = mongo.db.list_collection_names()
        
        # Get count of bounties in the database
        bounty_count = mongo.db.bounties.count_documents({})
        
        return jsonify({
            'status': 'success',
            'message': 'MongoDB connection working properly',
            'collections': collections,
            'bounty_count': bounty_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'MongoDB connection failed: {str(e)}'
        }), 500

def is_authenticated():
    """Check if the user is authenticated by validating Stytch session"""
    stytch_session_token = session.get('stytch_session_token')
    if not stytch_session_token:
        return False
    
    try:
        # Validate session token with Stytch
        resp = stytch_client.sessions.authenticate(session_token=stytch_session_token)
        return True
    except StytchError as e:
        # Session has expired or is invalid, clear it
        session.pop('stytch_session_token', None)
        app.logger.error(f"Session validation error: {e}")
        return False
    except Exception as e:
        app.logger.error(f"Unexpected error in authentication: {e}")
        return False

def get_user_email():
    """Get the email of the authenticated user"""
    stytch_session_token = session.get('stytch_session_token')
    if not stytch_session_token:
        return None
    
    try:
        # Get user info from Stytch
        resp = stytch_client.sessions.authenticate(session_token=stytch_session_token)
        if resp.user and resp.user.emails and len(resp.user.emails) > 0:
            return resp.user.emails[0].email
        return None
    except Exception as e:
        app.logger.error(f"Error getting user email: {e}")
        return None

def generate_target_details(species, danger_level, bounty_value, special_skills="", known_associates="", last_known_location=""):
    """Generate target details using OpenAI via Cloudflare AI Gateway"""
    # Build a detailed prompt for Star Wars-themed bounty target
    prompt = f"""Generate a Star Wars bounty hunter target with the following details:
    - Species: {species}
    - Danger Level: {danger_level}
    - Bounty Value: {bounty_value} credits
    {f'- Special Skills: {special_skills}' if special_skills else ''}
    {f'- Known Associates: {known_associates}' if known_associates else ''}
    {f'- Last Known Location: {last_known_location}' if last_known_location else ''}
    
    Please provide the following information in JSON format:
    - name: A Star Wars appropriate name for this species
    - title: A short intimidating title or nickname
    - crimes: List of 3-5 notable crimes they've committed
    - backstory: Brief background (2-3 sentences)
    - appearance: Detailed physical description including distinctive features
    - weapons: Their preferred weapons or fighting style
    - cautionNotes: Important warnings for bounty hunters
    - issuer: Who posted this bounty (Empire, Hutt Cartel, etc.)
    - lastSeen: Last known planet or location
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app.config['OPENAI_API_KEY']}"
    }
    
    data = {
        "model": "gpt-4.1",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(openai_endpoint, headers=headers, json=data)
        result = response.json()
        
        # Parse the JSON response
        content = result['choices'][0]['message']['content']
        return json.loads(content)
    except Exception as e:
        app.logger.error(f"Error processing OpenAI response: {e}")
        app.logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return None

def generate_target_image(target_details):
    """Generate target image using Replicate via Cloudflare AI Gateway"""
    # Create a detailed prompt for the image generation
    image_prompt = f"""Star Wars wanted poster of a {target_details['species']} named {target_details['name']}, 
                    {target_details['title']}, {target_details['appearance']}, 
                    dramatic lighting, Star Wars universe, 
                    security hologram style, wanted poster layout"""
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {app.config['REPLICATE_API_KEY']}"
    }
    
    # Using the SD 3.5 medium model that we've confirmed works
    data = {
        "version": "stability-ai/stable-diffusion-3.5-medium",
        "input": {
            "prompt": image_prompt,
            "negative_prompt": "deformed, ugly, bad anatomy, blurry, pixelated",
            "num_inference_steps": 50
        }
    }
    
    try:
        # Initial prediction request
        response = requests.post(replicate_endpoint, headers=headers, json=data)
        prediction_data = response.json()
        
        app.logger.info(f"Initial prediction response: {prediction_data}")
        
        if 'id' not in prediction_data:
            app.logger.error(f"Failed to create prediction: {prediction_data}")
            return None
            
        prediction_id = prediction_data['id']
        
        # Poll for the result
        max_attempts = 30
        for attempt in range(max_attempts):
            app.logger.info(f"Polling attempt {attempt+1}/{max_attempts}")
            
            # Wait before checking
            time.sleep(2)
            
            # Check prediction status
            check_url = f"{replicate_endpoint}/{prediction_id}"
            check_response = requests.get(check_url, headers=headers)
            current_prediction = check_response.json()
            
            app.logger.info(f"Poll response: {current_prediction}")
            
            # If completed successfully, return the output
            if current_prediction.get("status") == "succeeded" and current_prediction.get("output"):
                app.logger.info(f"Image generation succeeded: {current_prediction['output']}")
                return current_prediction["output"][0]
                
            # If failed, log and return None
            elif current_prediction.get("status") == "failed":
                app.logger.error(f"Image generation failed: {current_prediction.get('error')}")
                return None
                
            # If still processing, continue polling
            
        # If we've reached the maximum number of attempts without success
        app.logger.warning(f"Maximum polling attempts reached for prediction {prediction_id}")
        return None
        
    except Exception as e:
        app.logger.error(f"Error generating image: {e}")
        return None

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login requests"""
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Email is required', 'error')
            return render_template('login.html')
        
        try:
            # Send magic link email
            resp = stytch_client.magic_links.email.login_or_create(
                email=email,
                login_magic_link_url=url_for('authenticate', _external=True),
                signup_magic_link_url=url_for('authenticate', _external=True)
            )
            flash('Check your email for a magic link to log in', 'success')
            return render_template('login.html', email_sent=True)
        
        except StytchError as e:
            app.logger.error(f"Stytch error: {e}")
            flash('An error occurred while sending the magic link. Please try again.', 'error')
            return render_template('login.html')
        
    return render_template('login.html')

@app.route('/authenticate')
def authenticate():
    """Handle magic link authentication"""
    token = request.args.get('token')
    if not token:
        flash('Invalid authentication request', 'error')
        return redirect(url_for('login'))
    
    try:
        # Verify the magic link token
        auth_resp = stytch_client.magic_links.authenticate(
            token=token,
            session_duration_minutes=60 * 24  # 24 hours
        )
        
        # Store the session token
        session['stytch_session_token'] = auth_resp.session_token
        session['user_id'] = auth_resp.user_id
        
        flash('You have successfully logged in!', 'success')
        return redirect(url_for('index'))
    
    except StytchError as e:
        app.logger.error(f"Authentication error: {e}")
        flash('Invalid or expired magic link. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Handle logout requests"""
    stytch_session_token = session.get('stytch_session_token')
    if stytch_session_token:
        try:
            # Revoke the session
            stytch_client.sessions.revoke(session_token=stytch_session_token)
        except Exception as e:
            app.logger.error(f"Error revoking session: {e}")
    
    # Clear the session
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/account')
@login_required
def account():
    """Display user account information"""
    user_email = get_user_email()
    
    # Get user's bounties from MongoDB
    user_bounties = list(mongo.db.bounties.find({"user_email": user_email}).sort("created_at", -1))
    
    return render_template('account.html', 
                          email=user_email, 
                          bounties=user_bounties)
@app.route('/')
def index():
    """Render the main page"""
    species_list = [
        "Human", "Twi'lek", "Wookiee", "Rodian", "Trandoshan", 
        "Mon Calamari", "Zabrak", "Bothan", "Togruta", "Gungan"
    ]
    danger_levels = ["Low", "Medium", "High", "Extreme"]
    
    user_email = get_user_email() if is_authenticated() else None
    
    return render_template('index.html', 
                          species_list=species_list, 
                          danger_levels=danger_levels,
                          is_authenticated=is_authenticated(),
                          user_email=user_email)

def convert_mongo_doc_for_session(doc):
    """Convert MongoDB document to be JSON serializable"""
    if isinstance(doc, dict):
        return {k: convert_mongo_doc_for_session(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [convert_mongo_doc_for_session(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    else:
        return doc

@app.route('/generate_bounty', methods=['POST'])
@login_required
def generate_bounty():
    """Generate a bounty target based on form data"""
    if request.method == 'POST':
        # Get form data
        species = request.form.get('species')
        danger_level = request.form.get('danger_level')
        bounty_value = request.form.get('bounty_value')
        special_skills = request.form.get('special_skills')
        known_associates = request.form.get('known_associates')
        last_known_location = request.form.get('last_known_location')
        
        # Generate target details
        target_details = generate_target_details(
            species, 
            danger_level, 
            bounty_value, 
            special_skills,
            known_associates,
            last_known_location
        )
        
        if not target_details:
            return render_template('index.html', error="Failed to generate bounty details. Please try again.")
        
        # Add species to the target details
        target_details['species'] = species
        target_details['bounty_value'] = bounty_value
        target_details['danger_level'] = danger_level
        
        # Generate target image
        image_url = generate_target_image(target_details)
        
        # Add a fallback image if generation fails
        if not image_url:
            app.logger.warning("Using fallback image")
            # Create a species-specific fallback
            species_fallbacks = {
                "Human": "/static/img/fallback_human.jpg",
                "Rodian": "/static/img/fallback_rodian.jpg",
                # Add more as needed
            }
            
            # Use species-specific fallback if available, otherwise use generic
            image_url = species_fallbacks.get(species, "/static/img/fallback_wanted.jpg")
            
        target_details['image_url'] = image_url
        
        # Add metadata for MongoDB
        user_email = get_user_email()
        bounty_id = str(uuid.uuid4())
        target_details['bounty_id'] = bounty_id
        target_details['user_email'] = user_email
        
        # Fix: Use timezone-aware datetime
        target_details['created_at'] = datetime.datetime.now(datetime.UTC)
        
        # Save the bounty to MongoDB
        result = mongo.db.bounties.insert_one(target_details)
        
        # Fix: Store a JSON-serializable version of the document in session
        # Convert ObjectId to string
        session_safe_target = target_details.copy()
        session_safe_target['_id'] = str(result.inserted_id)
        
        # Store in session for potential later use
        session['bounty'] = session_safe_target
        
        return render_template('bounty.html', 
                              bounty=target_details, 
                              is_authenticated=is_authenticated(),
                              user_email=user_email)
    
    return redirect(url_for('index'))

@app.template_filter('format_number')
def format_number_filter(value):
    """Format a number with commas as thousands separators"""
    return "{:,}".format(int(value))


@app.route('/download_bounty')
@login_required
def download_bounty():
    """Download the bounty as JSON"""
    if 'bounty' in session:
        bounty = session['bounty']
        return jsonify(bounty)
    return redirect(url_for('index'))


@app.route('/view_bounty/<bounty_id>')
@login_required
def view_bounty(bounty_id):
    """View a specific bounty from user's collection"""
    user_email = get_user_email()
    
    # Find the bounty in MongoDB
    bounty = mongo.db.bounties.find_one({
        "bounty_id": bounty_id,
        "user_email": user_email
    })
    
    if not bounty:
        flash("Bounty not found or you don't have permission to view it", "error")
        return redirect(url_for('account'))
    
    # Convert MongoDB document to be JSON serializable for session storage
    session_safe_bounty = {}
    for key, value in bounty.items():
        if key == '_id':
            session_safe_bounty[key] = str(value)  # Convert ObjectId to string
        elif isinstance(value, datetime.datetime):
            session_safe_bounty[key] = value.isoformat()  # Convert datetime to string
        else:
            session_safe_bounty[key] = value
    
    # Store in session for potential later use (like download)
    session['bounty'] = session_safe_bounty
    
    return render_template('bounty.html', 
                          bounty=bounty, 
                          is_authenticated=is_authenticated(),
                          user_email=user_email,
                          from_collection=True)


@app.route('/delete_bounty/<bounty_id>', methods=['POST'])
@login_required
def delete_bounty(bounty_id):
    """Delete a bounty from user's collection"""
    user_email = get_user_email()
    
    # Delete the bounty from MongoDB
    result = mongo.db.bounties.delete_one({
        "bounty_id": bounty_id,
        "user_email": user_email
    })
    
    if result.deleted_count == 1:
        flash("Bounty successfully deleted from your collection", "success")
    else:
        flash("Failed to delete bounty or bounty not found", "error")
    
    return redirect(url_for('account'))

@app.route('/get_yoda_advice/<bounty_id>', methods=['GET'])
@login_required
def get_yoda_advice(bounty_id):
    """Generate Yoda's advice for the bounty hunter"""
    # Get the bounty details from session
    bounty = session.get('bounty')
    
    if not bounty:
        return jsonify({"error": "Bounty not found"}), 404
    
    # Generate Yoda's advice using OpenAI
    yoda_prompt = f"""You are Master Yoda from Star Wars. Provide advice to a bounty hunter about capturing {bounty['name']}, who is a {bounty['species']} with the following characteristics:

Species: {bounty['species']}
Known Crimes: {bounty.get('crimes', '')}
Last Seen: {bounty.get('lastSeen', '')}
Weapons: {bounty.get('weapons', '')}
Special Caution: {bounty.get('cautionNotes', '')}

Write in Yoda's distinctive speaking style and give tactical advice on how to approach and capture this target. Include 4-5 specific pieces of wisdom. Keep your response complete and end with an encouraging Yoda-style phrase."""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {app.config['OPENAI_API_KEY']}"
    }
    
    data = {
        "model": "gpt-4.1",  # Use a more recent model
        "messages": [{"role": "user", "content": yoda_prompt}],
        "temperature": 0.8,
        "max_tokens": 500  # Increased from 300 to ensure complete response
    }
    
    try:
        response = requests.post(openai_endpoint, headers=headers, json=data)
        result = response.json()
        advice_text = result['choices'][0]['message']['content']
        
        # Ensure the response is complete
        if not advice_text.endswith(('.', '!', '?', 'hmmm', 'yes', 'mmm')):
            # Add a proper ending if the response was truncated
            advice_text += " May the Force be with you, young bounty hunter. Hmmm."
        
        return jsonify({"advice": advice_text})
        
    except Exception as e:
        app.logger.error(f"Error getting Yoda advice: {e}")
        return jsonify({"error": "Failed to get Yoda's advice"}), 500
    
@app.route('/email_bounty', methods=['POST'])
@login_required
def email_bounty():
    """Email the bounty details to the specified email address"""
    try:
        recipient_email = request.form.get('email')
        if not recipient_email:
            return jsonify({"error": "Email address is required"}), 400
        
        bounty = session.get('bounty')
        if not bounty:
            return jsonify({"error": "No bounty found"}), 404
        
        # Create email message
        message = MIMEMultipart()
        message['From'] = app.config['SENDER_EMAIL']
        message['To'] = recipient_email
        message['Subject'] = f"WANTED: {bounty['name']} - Bounty Worth {bounty['bounty_value']} Credits"
        
        # Create HTML content for the email
        image_html = ""
        if bounty.get('image_url'):
            image_html = f'<div style="text-align: center; margin-bottom: 30px;"><img src="{bounty["image_url"]}" alt="{bounty["name"]}" style="max-width: 400px; border: 2px solid #FFD700; border-radius: 5px;"></div>'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #000; color: #FFD700; padding: 20px; }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .header h1 {{ color: #FF0000; font-size: 48px; letter-spacing: 8px; text-shadow: 0 0 10px #FF0000; }}
                .header h2 {{ font-size: 36px; margin-bottom: 5px; }}
                .header h3 {{ font-size: 24px; color: #AAA; margin-bottom: 20px; }}
                .reward {{ font-size: 32px; color: #FFD700; margin: 20px 0; font-weight: bold; }}
                .bounty-info {{ background-color: #111; border: 2px solid #FFD700; padding: 30px; margin-bottom: 20px; }}
                .info-label {{ color: #FFD700; font-weight: bold; font-size: 18px; }}
                .info-value {{ color: #FFF; font-size: 16px; line-height: 1.5; margin-bottom: 15px; }}
                .footer {{ text-align: center; font-style: italic; color: #AAA; margin-top: 30px; font-size: 16px; }}
                .warning {{ background-color: #330000; border: 2px solid #FF0000; color: #FF0000; padding: 15px; margin-top: 30px; text-align: center; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>WANTED</h1>
                    <h2>{bounty['name']}</h2>
                    <h3>AKA: {bounty['title']}</h3>
                    <div class="reward">Reward: {'{:,}'.format(int(bounty['bounty_value']))} Credits</div>
                </div>
                
                {image_html}

                <div class="header">
                <h3>Created by Replicate</h3>
                 </div>
                <div class="bounty-info">
                    <p><span class="info-label">Species:</span> <span class="info-value">{bounty['species']}</span></p>
                    <p><span class="info-label">Last Seen:</span> <span class="info-value">{bounty['lastSeen']}</span></p>
                    <p><span class="info-label">Known Crimes:</span> <span class="info-value">{bounty['crimes']}</span></p>
                    <p><span class="info-label">Weapons:</span> <span class="info-value">{bounty['weapons']}</span></p>
                    <p><span class="info-label">Special Caution:</span> <span class="info-value">{bounty['cautionNotes']}</span></p>
                    <p><span class="info-label">Background:</span> <span class="info-value">{bounty['backstory']}</span></p>
                </div>
                
                <div class="warning">APPROACH WITH EXTREME CAUTION - ARMED AND DANGEROUS</div>
                
                <div class="footer">Bounty posted by: {bounty['issuer']}</div>
            </div>
        </body>
        </html>
        """
        
        message.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT']) as server:
            server.starttls()
            server.login(app.config['SENDER_EMAIL'], app.config['SENDER_PASSWORD'])
            server.send_message(message)
        
        return jsonify({"success": "Bounty transmitted successfully!"})
        
    except Exception as e:
        app.logger.error(f"Error sending email: {e}")
        return jsonify({"error": "Failed to send email"}), 500

if __name__ == '__main__':
    app.run(debug=True, port="3000")