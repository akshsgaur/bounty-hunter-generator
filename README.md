


## Star Wars Bounty Hunter Generator 🚀

A Flask-based web application that generates detailed Star Wars bounty targets using AI. Create custom bounties with backstories, images, and even get tactical advice from Master Yoda!

## Features ✨

- **AI-Powered Target Generation**: Uses GPT-4.1 to create detailed bounty descriptions and backstories
- **AI Image Generation**: Creates unique target images using Replicate's Stable Diffusion
- **Secure Authentication**: Passwordless login via Stytch magic links
- **Personal Bounty Collection**: Save and manage your generated bounties
- **Master Yoda's Wisdom**: Get tactical advice from Master Yoda for each bounty
- **Email Sharing**: Share bounties with other hunters
- **MongoDB Integration**: Persistent storage for bounty collections
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites 🛠️

Before installation, ensure you have:
- Python 3.8 or higher
- MongoDB installed and running
- Account credentials for:
  - OpenAI API
  - Replicate API
  - Stytch
  - Cloudflare AI Gateway
  - Gmail (for sending emails)
  - MongoDB Atlas (or local MongoDB)

## Installation Guide 📝

1. **Clone the Repository**
   ```bash
   git clone https://github.com/akshsgaur/bounty-hunter-generator.git
   cd bounty-hunter-generator
   ```

2. **Create and Activate Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Unix/MacOS
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create Environment File**
   Create a `.env` file in the root directory with the following variables:
   ```env
   SECRET_KEY=your-secret-key
   OPENAI_API_KEY=your-openai-key
   REPLICATE_API_KEY=your-replicate-key
   CLOUDFLARE_ACCOUNT_ID=your-cloudflare-account-id
   CLOUDFLARE_GATEWAY_ID=your-cloudflare-gateway-id
   
   # Email Configuration
   SENDER_EMAIL=your-gmail-address
   SENDER_PASSWORD=your-gmail-app-password
   
   # Stytch Authentication
   STYTCH_PROJECT_ID=your-stytch-project-id
   STYTCH_SECRET=your-stytch-secret
   STYTCH_ENV=test  # or 'live' for production
   
   # MongoDB Configuration
   MONGO_USERNAME=your-mongo-username
   MONGO_PASSWORD=your-mongo-password
   MONGO_CLUSTER=your-cluster-address
   MONGO_DBNAME=bounty_hunter
   ```

5. **Configure MongoDB**
   - Create a MongoDB database (local or Atlas)
   - Update the MongoDB connection details in your `.env` file
   - Ensure your IP address is whitelisted in MongoDB Atlas (if using Atlas)

6. **Run the Application**
   ```bash
   python app.py
   ```
   The application will be available at `http://localhost:3000`

## Usage Guide 🎮

1. **Authentication**
   - Visit the homepage and click "Log In"
   - Enter your email address
   - Click the magic link sent to your email

2. **Generating Bounties**
   - Select target species and danger level
   - Set bounty value
   - Add optional details (location, skills, associates)
   - Click "Generate Bounty"

3. **Managing Bounties**
   - View your bounty collection in the Account dashboard
   - Download bounty data as JSON
   - Share bounties via email
   - Delete unwanted bounties

4. **Getting Yoda's Advice**
   - Click "Seek Yoda's Guidance" on any bounty page
   - Receive tactical advice in Yoda's unique style

## API Integration Details 🔌

The application uses several external APIs:
- OpenAI GPT-4 for text generation
- Replicate for image generation
- Stytch for authentication
- Cloudflare AI Gateway for API management

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- Star Wars and all related properties are trademarks of Lucasfilm Ltd.
- Special thanks to the Flask, MongoDB, and Python communities
```

This README provides comprehensive setup instructions while maintaining an engaging Star Wars theme. The emojis and clear formatting make it visually appealing and easy to follow. The installation guide is detailed enough for both beginners and experienced developers to get the application running.
