from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import json
import os
import time
from config import Config

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# Configure API endpoints via Cloudflare AI Gateway
openai_endpoint = f"https://gateway.ai.cloudflare.com/v1/{app.config['CLOUDFLARE_ACCOUNT_ID']}/{app.config['CLOUDFLARE_GATEWAY_ID']}/openai/v1/chat/completions"
replicate_endpoint = f"https://gateway.ai.cloudflare.com/v1/{app.config['CLOUDFLARE_ACCOUNT_ID']}/{app.config['CLOUDFLARE_GATEWAY_ID']}/replicate/v1/predictions"

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

@app.route('/')
def index():
    """Render the main page"""
    species_list = [
        "Human", "Twi'lek", "Wookiee", "Rodian", "Trandoshan", 
        "Mon Calamari", "Zabrak", "Bothan", "Togruta", "Gungan"
    ]
    danger_levels = ["Low", "Medium", "High", "Extreme"]
    
    return render_template('index.html', species_list=species_list, danger_levels=danger_levels)

@app.route('/generate_bounty', methods=['POST'])
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
        
        # Store in session for potential later use
        session['bounty'] = target_details
        
        return render_template('bounty.html', bounty=target_details)
    
    return redirect(url_for('index'))


@app.template_filter('format_number')
def format_number_filter(value):
    """Format a number with commas as thousands separators"""
    return "{:,}".format(int(value))


@app.route('/download_bounty')
def download_bounty():
    """Download the bounty as JSON"""
    if 'bounty' in session:
        bounty = session['bounty']
        return jsonify(bounty)
    return redirect(url_for('index'))

@app.route('/get_yoda_advice/<bounty_id>', methods=['GET'])
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

