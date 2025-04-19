# Utility functions for the bot
import discord
from discord.ext import commands
import logging

# Set up logging
logger = logging.getLogger(__name__)

async def has_permission(ctx):
    """Check if a user has permission to use admin commands."""
    # Server owner always has permission
    if ctx.author.id == ctx.guild.owner_id:
        return True
    
    # Moderator role ID
    MODERATOR_ROLE_ID = 1344104617092452534
    
    # Check for admin role, administrator permission, or moderator role
    return (ctx.author.guild_permissions.administrator or 
            any(role.name.lower() in ["admin", "moderator"] for role in ctx.author.roles) or
            any(role.id == MODERATOR_ROLE_ID for role in ctx.author.roles))

def create_embed(title, description, color=discord.Color.blue()):
    """Create a Discord embed with the given parameters."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed

def format_squad_details(squad, members=None):
    """Format squad details for display in embeds."""
    details = f"**Description:** {squad['description']}\n"
    
    if members:
        details += f"\n**Members ({len(members)}):**\n"
        for member in members:
            role = member.get("role", "Member")
            details += f"• {member['mlbb_username']} (ID: {member['mlbb_id']}) - {role}\n"
    
    return details
