import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from openai import OpenAI
import time
import requests
import os
import string  # For punctuation removal
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Set up OpenAI client using environment variables
client = OpenAI(
    base_url=os.getenv("NILLION_BASE_URL"),
    api_key=os.getenv("NILLION_API_KEY"),
)

# Bitcoin price prediction API URL from environment variable
ANALYSIS_API_URL = os.getenv("ANALYSIS_API_URL")

# Telegram Bot Token from environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Handler for the /start command
async def start(update, context):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Hello! I'm your AI assistant. I can:\n"
        "1. Answer questions about AI, AGI, and cryptocurrencies\n"
        "2. Predict Bitcoin prices when you ask specifically about Bitcoin\n\n"
        "Just chat with me naturally - I'll figure out what you want!"
    )

# Function to fetch Bitcoin price prediction from an external API
def get_bitcoin_prediction():
    """Fetches the latest Bitcoin price prediction from an external API."""
    try:
        response = requests.get(ANALYSIS_API_URL)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Sorry, couldn't fetch Bitcoin price prediction at the moment."}
    except Exception as e:
        return {"error": f"Error getting prediction: {str(e)}"}

# Helper function to check for keywords in the message
def contains_keywords(message, keywords):
    """Checks if the message contains any of the keywords as whole words, ignoring case and punctuation."""
    translator = str.maketrans('', '', string.punctuation)
    clean_message = message.translate(translator).lower()
    words = clean_message.split()
    return any(word in words for word in keywords)

# Format the Bitcoin prediction data into a readable response
def format_prediction_response(prediction_data):
    """Formats Bitcoin prediction data into a human-readable string."""
    if "error" in prediction_data:
        return prediction_data["error"]
    
    latest_date = prediction_data.get("latest_date", "N/A")
    latest_price = prediction_data.get("latest_price", "N/A")
    next_pred = prediction_data.get("next_day_prediction", {})
    signal = prediction_data.get("signal", "N/A")
    
    response = (
        f"*Bitcoin Price Prediction*\n"
        f"- *Latest Date*: {latest_date}\n"
        f"- *Latest Price*: ${latest_price:.2f}\n"
        f"- *Next Day Prediction* (for {next_pred.get('ds', 'N/A')}):\n"
        f"  - Predicted Price: ${next_pred.get('TimeGPT', 'N/A'):.2f}\n"
        f"  - 50% Confidence Interval: ${next_pred.get('TimeGPT-lo-50', 'N/A'):.2f} - ${next_pred.get('TimeGPT-hi-50', 'N/A'):.2f}\n"
        f"- *Signal*: {signal.capitalize()}"
    )
    return response

# Handle incoming text messages
async def handle_message(update, context):
    """Processes user messages and responds accordingly."""
    user_message = update.message.text
    bitcoin_keywords = ["bitcoin", "btc"]
    prediction_keywords = ["price", "prediction", "forecast", "trend", "signal"]
    
    try:
        if contains_keywords(user_message, bitcoin_keywords) and contains_keywords(user_message, prediction_keywords):
            start_time = time.time()
            prediction_data = get_bitcoin_prediction()
            formatted_response = format_prediction_response(prediction_data)
            end_time = time.time()
            await update.message.reply_text(f"{formatted_response}\n\n(Response time: {end_time - start_time:.2f}s)")
        else:
            start_time = time.time()
            response = client.chat.completions.create(
                model="meta-llama/Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant. Answer the user's question."},
                    {"role": "user", "content": user_message}
                ]
            )
            content = response.choices[0].message.content
            end_time = time.time()
            await update.message.reply_text(f"{content}\n\n(Response time: {end_time - start_time:.2f}s)")
    except Exception as e:
        await update.message.reply_text(f"Sorry, I encountered an error: {str(e)}")

# Main function to start the bot
def main():
    """Sets up and runs the Telegram bot."""
    # Check for required environment variables
    required_vars = ["NILLION_BASE_URL", "NILLION_API_KEY", "ANALYSIS_API_URL", "TELEGRAM_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return

    # Initialize the Telegram application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()