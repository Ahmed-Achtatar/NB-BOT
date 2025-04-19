# Discord bot implementation
import os
import discord
from discord.ext import commands
import logging
from db import ensure_data_files_exist
from commands import register_commands

# Set up logging
logger = logging.getLogger(__name__)

# Discord Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='nb!', intents=intents)

@bot.event
async def on_ready():
    """Event handler for when the bot is connected and ready."""
    logger.info(f'Bot logged in as {bot.user.name} ({bot.user.id})')
    
    # Ensure data files exist
    ensure_data_files_exist()
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="MLBB Squad Manager | nb!help"))
    
    logger.info("Bot is ready!")

def run_bot():
    """Run the Discord bot."""
    # Register all commands
    register_commands(bot)
    
    # Get the token from environment variable
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("No Discord bot token found in environment variables!")
        return
    
    # Start the bot
    logger.info("Starting Discord bot...")
    bot.run(token)

if __name__ == "__main__":
    run_bot()
