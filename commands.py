# Command handlers for the Discord bot
import discord
from discord.ext import commands
import logging
import asyncio
from db import (load_squads, save_squads, load_players, save_players,
                find_squad_by_name, find_player_by_id, find_player_by_username,
                find_player_by_mlbb_id, find_squad_members, is_free_agent)
from utils import has_permission

# Set up logging
logger = logging.getLogger(__name__)


def register_commands(bot):
    """Register all commands with the bot."""

    @bot.command(name="help_mlbb")
    async def help_mlbb(ctx):
        """Display help information for all commands."""
        embed = discord.Embed(
            title="MLBB Squad Manager Bot Help",
            description="Here are all the available commands:",
            color=discord.Color.blue())

        # Profile Setup & Management
        embed.add_field(
            name="🎮 Profile Setup & Management",
            value=(
                "`nb!setup` - Interactive profile setup wizard\n"
                "`nb!register <mlbb_id> <mlbb_username>` - Quick register as player\n"
                "`nb!profile [user]` - Show your or another user's profile\n"
                "`nb!profile_update <field> <value>` - Update profile field\n"
                "`nb!set_rank <rank>` - Set max achieved rank\n"
                "`nb!set_winrate <percentage>` - Set overall win rate\n"
                "`nb!set_availability <schedule>` - Set play schedule\n"
            ),
            inline=False
        )

        # Role Management
        embed.add_field(
            name="👥 Role Management",
            value=(
                "`nb!add_role <role> <hero1,hero2,hero3>` - Add role & heroes\n"
                "`nb!remove_role <role>` - Remove a role\n"
                "`nb!search_role <role>` - Find players by role\n"
                "Valid roles: gold, exp, mid, jungle, roam\n"
            ),
            inline=False
        )

        # Squad Management
        embed.add_field(
            name="🏆 Squad Commands",
            value=(
                "`nb!join_squad <squad_name>` - Request to join squad\n"
                "`nb!leave_squad` - Leave current squad\n"
                "`nb!squads` - List all squads\n"
                "`nb!squad_info <name>` - Show squad details\n"
                "`nb!free_agents` - List available players\n"
            ),
            inline=False
        )

        # Admin Commands
        embed.add_field(
            name="🛡️ Admin Commands",
            value=(
                "`nb!squad_create <name> <description>` - Create squad\n"
                "`nb!squad_update <name> <description>` - Update squad\n"
                "`nb!squad_delete <name>` - Delete squad\n"
                "`nb!add_member <squad> <@user> [mlbb_id] [username] [role]` - Add to squad\n"
                "`nb!remove_member <squad> <@user>` - Remove from squad\n"
                "`nb!update_member <@user> <field> <value>` - Update member\n"
            ),
            inline=False
        )

        # Fun & Utility
        embed.add_field(
            name="🎲 Fun & Utility",
            value=(
                "`nb!random_hero` - Pick a random hero\n"
                "`nb!search_player <name or id>` - Search for players\n"
            ),
            inline=False
        )

        # Add footer with prefix info
        embed.set_footer(text="All commands use the prefix 'nb!'")
        
        await ctx.send(embed=embed)

    # Squad management commands
    @bot.command(name="squad_create")
    @commands.check(has_permission)
    async def squad_create(ctx,
                           name: str,
                           *,
                           description: str = "No description provided"):
        """Create a new squad."""
        squads = load_squads()

        # Check if squad already exists
        if find_squad_by_name(name):
            await ctx.send(f"❌ Squad with name '{name}' already exists!")
            return

        # Create new squad
        new_squad = {
            "name": name,
            "description": description,
            "created_by": ctx.author.id,
            "created_at": ctx.message.created_at.isoformat()
        }

        squads.append(new_squad)
        if save_squads(squads):
            embed = discord.Embed(title=f"Squad Created: {name}",
                                  description=description,
                                  color=discord.Color.green())
            embed.set_footer(text=f"Created by {ctx.author.name}")
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to create squad due to an error!")

    @bot.command(name="squad_update")
    @commands.check(has_permission)
    async def squad_update(ctx, name: str, *, description: str):
        """Update squad details."""
        squads = load_squads()

        # Find the squad
        for squad in squads:
            if squad["name"].lower() == name.lower():
                squad["description"] = description
                if save_squads(squads):
                    embed = discord.Embed(title=f"Squad Updated: {name}",
                                          description=description,
                                          color=discord.Color.blue())
                    embed.set_footer(text=f"Updated by {ctx.author.name}")
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Failed to update squad due to an error!")
                return

        await ctx.send(f"❌ Squad '{name}' not found!")

    @bot.command(name="squad_delete")
    @commands.check(has_permission)
    async def squad_delete(ctx, name: str):
        """Delete a squad."""
        squads = load_squads()
        players = load_players()

        # Find the squad
        squad = find_squad_by_name(name)
        if not squad:
            await ctx.send(f"❌ Squad '{name}' not found!")
            return

        # Remove the squad
        squads = [s for s in squads if s["name"].lower() != name.lower()]

        # Update all players who were in this squad
        for player in players:
            if player.get("squad", "").lower() == name.lower():
                player.pop("squad", None)

        # Save changes
        if save_squads(squads) and save_players(players):
            await ctx.send(
                f"✅ Squad '{name}' has been deleted and all members are now free agents."
            )
        else:
            await ctx.send("❌ Failed to delete squad due to an error!")

    @bot.command(name="add_member")
    @commands.check(has_permission)
    async def add_member(ctx,
                         squad_name: str,
                         member: discord.Member,
                         mlbb_id: str = None,
                         mlbb_username: str = None,
                         role: str = "Member"):
        """Add a member to a squad. If the player is already registered, you can omit mlbb_id and mlbb_username."""
        players = load_players()

        # Check if squad exists
        if not find_squad_by_name(squad_name):
            await ctx.send(f"❌ Squad '{squad_name}' not found!")
            return

        # Find player index
        player_index = -1
        existing_player = None
        for i, p in enumerate(players):
            if p["id"] == member.id:
                player_index = i
                existing_player = p
                break

        if existing_player:
            # Update existing player
            if mlbb_id is not None:
                existing_player["mlbb_id"] = mlbb_id
            if mlbb_username is not None:
                existing_player["mlbb_username"] = mlbb_username

            existing_player["squad"] = squad_name
            existing_player["role"] = role
            players[
                player_index] = existing_player  # Update the player in the list
        else:
            # Require MLBB ID and username for new players
            if mlbb_id is None or mlbb_username is None:
                await ctx.send(
                    f"❌ {member.name} is not registered yet! Please provide both MLBB ID and username."
                )
                return

            # Create new player with all required fields
            new_player = {
                "id": member.id,
                "username": member.name,
                "mlbb_id": mlbb_id,
                "mlbb_username": mlbb_username,
                "squad": squad_name,
                "role": role,
                "max_rank": "Unranked",
                "win_rate": "Unknown",
                "availability": "Not specified",
                "roles": {}
            }
            players.append(new_player)

        if save_players(players):
            embed = discord.Embed(
                title=f"Member Added to {squad_name}",
                description=f"{member.mention} has been added to the squad!",
                color=discord.Color.green())
            player_info = existing_player if existing_player else new_player
            embed.add_field(name="MLBB Username",
                            value=player_info["mlbb_username"])
            embed.add_field(name="MLBB ID", value=player_info["mlbb_id"])
            embed.add_field(name="Role", value=role)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to add member due to an error!")

    @bot.command(name="remove_member")
    @commands.check(has_permission)
    async def remove_member(ctx, squad_name: str, member: discord.Member):
        """Remove a member from a squad."""
        players = load_players()

        # Check if squad exists
        if not find_squad_by_name(squad_name):
            await ctx.send(f"❌ Squad '{squad_name}' not found!")
            return

        # Find player
        player = find_player_by_id(member.id)
        if not player:
            await ctx.send(f"❌ {member.name} is not registered as a player!")
            return

        # Check if player is in specified squad
        if player.get("squad", "").lower() != squad_name.lower():
            await ctx.send(
                f"❌ {member.name} is not a member of squad '{squad_name}'!")
            return

        # Remove player from squad
        player.pop("squad", None)
        player.pop("role", None)

        if save_players(players):
            await ctx.send(
                f"✅ {member.mention} has been removed from squad '{squad_name}' and is now a free agent."
            )
        else:
            await ctx.send("❌ Failed to remove member due to an error!")

    @bot.command(name="update_member")
    @commands.check(has_permission)
    async def update_member(ctx, member: discord.Member, field: str, *,
                            value: str):
        """Update member information."""
        players = load_players()

        # Find player
        player = find_player_by_id(member.id)
        if not player:
            await ctx.send(f"❌ {member.name} is not registered as a player!")
            return

        # Update field
        valid_fields = ["mlbb_id", "mlbb_username", "role", "squad"]
        if field.lower() not in valid_fields:
            await ctx.send(
                f"❌ Invalid field! Valid fields are: {', '.join(valid_fields)}"
            )
            return

        # If updating squad, check if it exists
        if field.lower() == "squad" and value.lower() != "none":
            if not find_squad_by_name(value):
                await ctx.send(f"❌ Squad '{value}' not found!")
                return

        # Remove squad assignment if value is "none"
        if field.lower() == "squad" and value.lower() == "none":
            player.pop("squad", None)
            player.pop("role", None)
        else:
            player[field.lower()] = value

        if save_players(players):
            await ctx.send(
                f"✅ Updated {field} for {member.mention} to '{value}'.")
        else:
            await ctx.send("❌ Failed to update member due to an error!")

    # Player commands
    @bot.command(name="setup")
    async def setup_profile(ctx):
        """Interactive profile setup wizard."""
        try:
            # Check if already registered
            players = load_players()
            existing_player = find_player_by_id(ctx.author.id)
            
            embed = discord.Embed(
                title="🎮 MLBB Profile Setup",
                description="Let's set up your profile! I'll guide you through each step.",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            msg = await ctx.send(embed=embed)

            if existing_player:
                embed.description = "You're already registered! Let's update your profile information."
                await msg.edit(embed=embed)
            
            # Step 1: MLBB ID
            embed.description = "Please enter your MLBB ID (Server ID):"
            await msg.edit(embed=embed)
            
            try:
                response = await bot.wait_for(
                    'message',
                    timeout=60.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                mlbb_id = response.content
                
                # Step 2: MLBB Username
                embed.description = "Great! Now enter your MLBB Username:"
                await msg.edit(embed=embed)
                
                response = await bot.wait_for(
                    'message',
                    timeout=60.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                mlbb_username = response.content
                
                # Step 3: Max Rank
                embed.description = "What's your maximum achieved rank? (e.g., Mythical Glory, Mythic, Legend, etc.)"
                await msg.edit(embed=embed)
                
                response = await bot.wait_for(
                    'message',
                    timeout=60.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                max_rank = response.content
                
                # Step 4: Win Rate
                embed.description = "What's your overall win rate? (just the number, e.g., 65)"
                await msg.edit(embed=embed)
                
                response = await bot.wait_for(
                    'message',
                    timeout=60.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                win_rate = f"{response.content}%"
                
                # Step 5: Availability
                embed.description = "When are you usually available to play? (e.g., Weekdays 8PM-11PM GMT+8)"
                await msg.edit(embed=embed)
                
                response = await bot.wait_for(
                    'message',
                    timeout=60.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                availability = response.content
                
                # Step 6: Roles
                embed.description = "Last step! What roles do you play? Enter them in this format:\nrole1: hero1, hero2, hero3\nrole2: hero1, hero2\n\nValid roles: gold, exp, mid, jungle, roam"
                await msg.edit(embed=embed)
                
                response = await bot.wait_for(
                    'message',
                    timeout=120.0,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                
                # Process roles
                roles = {}
                for line in response.content.split('\n'):
                    if ':' in line:
                        role, heroes = line.split(':')
                        role = role.strip().lower()
                        if role in ["gold", "exp", "mid", "jungle", "roam"]:
                            roles[role] = heroes.strip()
                
                # Create or update player profile
                player = {
                    "id": ctx.author.id,
                    "username": ctx.author.name,
                    "mlbb_id": mlbb_id,
                    "mlbb_username": mlbb_username,
                    "max_rank": max_rank,
                    "win_rate": win_rate,
                    "availability": availability,
                    "roles": roles,
                    "squad": existing_player["squad"] if existing_player and "squad" in existing_player else ""
                }
                
                if existing_player:
                    # Update existing player
                    players = [p if p["id"] != ctx.author.id else player for p in players]
                else:
                    # Add new player
                    players.append(player)
                
                if save_players(players):
                    embed.title = "✅ Profile Setup Complete!"
                    embed.description = "Your profile has been successfully created! Use `nb!profile` to view it."
                    embed.color = discord.Color.green()
                    await msg.edit(embed=embed)
                else:
                    embed.description = "❌ An error occurred while saving your profile."
                    embed.color = discord.Color.red()
                    await msg.edit(embed=embed)
                    
            except asyncio.TimeoutError:
                embed.description = "❌ Setup timed out. Please try again using `nb!setup`"
                embed.color = discord.Color.red()
                await msg.edit(embed=embed)
                
        except Exception as e:
            logger.error(f"Error in setup: {e}")
            await ctx.send("❌ An error occurred during setup. Please try again.")

    @bot.command(name="register")
    async def register_player(ctx, mlbb_id: str, *, mlbb_username: str):
        """Register yourself as a player."""
        players = load_players()

        # Check if already registered
        existing_player = find_player_by_id(ctx.author.id)
        if existing_player:
            await ctx.send(
                f"❌ You are already registered! Use `nb!profile_update` to change your information."
            )
            return

        # Create new player
        new_player = {
            "id": ctx.author.id,
            "username": ctx.author.name,
            "mlbb_id": mlbb_id,
            "mlbb_username": mlbb_username
        }

        players.append(new_player)

        if save_players(players):
            embed = discord.Embed(
                title="Player Registered",
                description=
                f"{ctx.author.mention} has been registered as a player!",
                color=discord.Color.green())
            embed.add_field(name="MLBB Username", value=mlbb_username)
            embed.add_field(name="MLBB ID", value=mlbb_id)
            embed.add_field(name="Status", value="Free Agent", inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to register due to an error!")

    @bot.command(name="profile")
    async def show_profile(ctx, member: discord.Member = None):
        """Show player profile."""
        # Default to command author if no member specified
        target = member or ctx.author

        # Find player
        player = find_player_by_id(target.id)
        if not player:
            await ctx.send(f"❌ {target.name} is not registered as a player!")
            return

        # Determine color based on squad status
        embed_color = discord.Color.blue()
        if "squad" in player and player["squad"]:
            embed_color = discord.Color.green()

        # Create embed
        embed = discord.Embed(
            title=f"Player Profile: {player['mlbb_username']}",
            color=embed_color)

        # Basic info
        embed.add_field(name="Discord", value=target.mention)
        embed.add_field(name="MLBB ID", value=player['mlbb_id'])
        embed.add_field(name="MLBB Username", value=player['mlbb_username'])

        # Squad information (with more prominence)
        if "squad" in player and player["squad"]:
            squad_role = player.get("role", "Member")
            embed.add_field(
                name="🏆 Squad Information",
                value=
                f"**Squad**: {player['squad']}\n**Position**: {squad_role}",
                inline=False)
        else:
            embed.add_field(name="Status",
                            value="**Free Agent**\n*Not in any squad*",
                            inline=False)

        # Add new profile details
        if "max_rank" in player:
            embed.add_field(name="Max Rank Achieved",
                            value=player["max_rank"],
                            inline=True)

        if "win_rate" in player:
            embed.add_field(name="Win Rate",
                            value=player["win_rate"],
                            inline=True)

        if "availability" in player:
            embed.add_field(name="Availability",
                            value=player["availability"],
                            inline=False)

        # Add roles and main heroes
        if "roles" in player and player["roles"]:
            roles_text = ""
            for role, heroes in player["roles"].items():
                roles_text += f"**{role.upper()}**: {heroes}\n"

            embed.add_field(name="Preferred Roles & Heroes",
                            value=roles_text,
                            inline=False)

        # Set thumbnail to user's avatar
        embed.set_thumbnail(url=target.display_avatar.url)

        await ctx.send(embed=embed)

    @bot.command(name="profile_update")
    async def update_profile(ctx, field: str, *, value: str):
        """Update your profile information."""
        players = load_players()

        # Find player and their index
        player_index = -1
        player = None
        for i, p in enumerate(players):
            if p["id"] == ctx.author.id:
                player_index = i
                player = p
                break

        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # List of valid fields that can be updated
        valid_fields = [
            "mlbb_id", "mlbb_username", "max_rank", "win_rate", "availability"
        ]
        field = field.lower()  # Normalize field name

        # Validate the field
        if field not in valid_fields:
            await ctx.send(
                f"❌ Invalid field! Valid fields are: {', '.join(valid_fields)}"
            )
            return

        # Special handling for win_rate to ensure % sign
        if field == "win_rate" and not value.endswith('%'):
            value = f"{value}%"

        # Update the field
        player[field] = value

        # Update the player in the list
        players[player_index] = player

        if save_players(players):
            await ctx.send(f"✅ Updated your {field} to '{value}'.")
        else:
            await ctx.send("❌ Failed to update profile due to an error!")

    @bot.command(name="set_rank")
    async def set_rank(ctx, *, rank: str):
        """Set your maximum achieved rank."""
        players = load_players()

        # Find player index
        player_index = -1
        player = None
        for i, p in enumerate(players):
            if p["id"] == ctx.author.id:
                player_index = i
                player = p
                break

        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Update rank
        player["max_rank"] = rank
        players[player_index] = player  # Update the player in the list

        if save_players(players):
            await ctx.send(f"✅ Updated your maximum rank to '{rank}'.")
        else:
            await ctx.send("❌ Failed to update rank due to an error!")

    @bot.command(name="set_winrate")
    async def set_winrate(ctx, win_rate: str):
        """Set your overall win rate percentage."""
        players = load_players()

        # Find player index
        player_index = -1
        player = None
        for i, p in enumerate(players):
            if p["id"] == ctx.author.id:
                player_index = i
                player = p
                break

        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Validate win rate format (basic check)
        if not win_rate.endswith('%'):
            win_rate = f"{win_rate}%"

        # Update win rate
        player["win_rate"] = win_rate
        players[player_index] = player  # Update the player in the list

        if save_players(players):
            await ctx.send(f"✅ Updated your win rate to '{win_rate}'.")
        else:
            await ctx.send("❌ Failed to update win rate due to an error!")

    @bot.command(name="set_availability")
    async def set_availability(ctx, *, availability: str):
        """Set your availability schedule."""
        players = load_players()

        # Find player index
        player_index = -1
        player = None
        for i, p in enumerate(players):
            if p["id"] == ctx.author.id:
                player_index = i
                player = p
                break

        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Update availability
        player["availability"] = availability
        players[player_index] = player  # Update the player in the list

        if save_players(players):
            await ctx.send(f"✅ Updated your availability to '{availability}'.")
        else:
            await ctx.send("❌ Failed to update availability due to an error!")

    @bot.command(name="add_role")
    async def add_role(ctx, role: str, *, heroes: str):
        """Add a preferred role with main heroes."""
        players = load_players()

        # Find player index
        player_index = -1
        player = None
        for i, p in enumerate(players):
            if p["id"] == ctx.author.id:
                player_index = i
                player = p
                break

        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Valid MLBB roles
        valid_roles = ["gold", "exp", "mid", "jungle", "roam"]
        if role.lower() not in valid_roles:
            await ctx.send(
                f"❌ Invalid role! Valid roles are: {', '.join(valid_roles)}")
            return

        # Initialize roles if not exists
        if "roles" not in player:
            player["roles"] = {}

        # Add role with heroes
        player["roles"][role.lower()] = heroes
        players[player_index] = player  # Update the player in the list

        if save_players(players):
            await ctx.send(
                f"✅ Added '{role}' to your preferred roles with heroes: {heroes}"
            )
        else:
            await ctx.send("❌ Failed to add role due to an error!")

    @bot.command(name="remove_role")
    async def remove_role(ctx, role: str):
        """Remove a role from your profile."""
        players = load_players()

        # Find player
        player = find_player_by_id(ctx.author.id)
        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Check if player has roles
        if "roles" not in player or not player["roles"]:
            await ctx.send(f"❌ You don't have any preferred roles set!")
            return

        # Check if role exists in player's roles
        if role.lower() not in player["roles"]:
            await ctx.send(
                f"❌ You don't have '{role}' in your preferred roles!")
            return

        # Remove the role
        del player["roles"][role.lower()]

        if save_players(players):
            await ctx.send(f"✅ Removed '{role}' from your preferred roles.")
        else:
            await ctx.send("❌ Failed to remove role due to an error!")

    @bot.command(name="join_squad")
    async def join_squad(ctx, *, squad_name: str):
        """Request to join a squad. You must be registered first."""
        players = load_players()

        # Find player
        player = find_player_by_id(ctx.author.id)
        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register <mlbb_id> <mlbb_username>` first."
            )
            return

        # Check if player is already in a squad
        if "squad" in player and player["squad"]:
            await ctx.send(
                f"❌ You are already a member of the '{player['squad']}' squad! Leave it first with `nb!leave_squad`."
            )
            return

        # Check if squad exists
        squad = find_squad_by_name(squad_name)
        if not squad:
            await ctx.send(f"❌ Squad '{squad_name}' not found!")
            return

        # Find admins/mods
        guild = ctx.guild
        admins = []
        mod_role = discord.utils.get(
            guild.roles, id=1344104617092452534)  # Moderator role ID

        for member in guild.members:
            # Check if member is admin, mod, or server owner
            if (member.guild_permissions.administrator
                    or (mod_role and mod_role in member.roles)
                    or member.id == guild.owner_id):
                admins.append(member)

        # Notify admins
        admin_mentions = " ".join([
            admin.mention for admin in admins[:3]
        ])  # Limit to first 3 admins to avoid spamming

        embed = discord.Embed(
            title=f"Squad Join Request",
            description=f"{ctx.author.mention} wants to join '{squad_name}'",
            color=discord.Color.gold())

        # Add player info
        embed.add_field(name="MLBB Username",
                        value=player["mlbb_username"],
                        inline=True)
        embed.add_field(name="MLBB ID", value=player["mlbb_id"], inline=True)

        if "max_rank" in player:
            embed.add_field(name="Max Rank",
                            value=player["max_rank"],
                            inline=True)

        if "win_rate" in player:
            embed.add_field(name="Win Rate",
                            value=player["win_rate"],
                            inline=True)

        # Add roles if available
        if "roles" in player and player["roles"]:
            roles_text = ""
            for role, heroes in player["roles"].items():
                roles_text += f"**{role.upper()}**: {heroes}\n"

            embed.add_field(name="Preferred Roles & Heroes",
                            value=roles_text,
                            inline=False)

        embed.set_footer(
            text=
            f"Admins/Mods: Use !add_member {squad_name} {ctx.author.mention} to approve"
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)

        await ctx.send(f"{admin_mentions}\n", embed=embed)
        await ctx.send(
            f"✅ Your request to join '{squad_name}' has been submitted! An admin or moderator will review it."
        )

    @bot.command(name="leave_squad")
    async def leave_squad(ctx):
        """Leave your current squad."""
        players = load_players()

        # Find player
        player = find_player_by_id(ctx.author.id)
        if not player:
            await ctx.send(
                f"❌ You are not registered! Use `nb!register` first.")
            return

        # Check if player is in a squad
        if "squad" not in player or not player["squad"]:
            await ctx.send(f"❌ You are not in any squad!")
            return

        # Store squad name for notification
        squad_name = player["squad"]

        # Remove from squad
        player.pop("squad", None)
        player.pop("role", None)

        if save_players(players):
            embed = discord.Embed(
                title=f"Squad Left",
                description=f"{ctx.author.mention} has left '{squad_name}'",
                color=discord.Color.orange())

            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Failed to leave squad due to an error!")

    # Search commands
    @bot.command(name="squads")
    async def list_squads(ctx):
        """List all available squads."""
        squads = load_squads()

        if not squads:
            await ctx.send("No squads have been created yet!")
            return

        embed = discord.Embed(
            title="MLBB Squads List",
            description=f"There are {len(squads)} squads registered:",
            color=discord.Color.blue())

        for squad in squads:
            # Count members
            members = find_squad_members(squad["name"])
            member_count = len(members) if members else 0

            embed.add_field(
                name=squad["name"],
                value=f"{squad['description']}\nMembers: {member_count}",
                inline=False)

        embed.set_footer(text="Use !squad_info <name> to see squad details")
        await ctx.send(embed=embed)

    @bot.command(name="squad_info")
    async def squad_info(ctx, *, name: str):
        """Show details about a squad including all members."""
        # Find the squad
        squad = find_squad_by_name(name)
        if not squad:
            await ctx.send(f"❌ Squad '{name}' not found!")
            return

        # Find squad members
        members = find_squad_members(name)

        # Create embed
        embed = discord.Embed(title=f"Squad: {squad['name']}",
                              description=squad["description"],
                              color=discord.Color.blue())

        # Add members
        if members:
            member_text = ""
            for member in members:
                member_user = ctx.guild.get_member(member["id"])
                mention = member_user.mention if member_user else f"<@{member['id']}>"
                role = member.get("role", "Member")
                member_text += f"• {mention} - {member['mlbb_username']} (ID: {member['mlbb_id']}) - {role}\n"

            embed.add_field(name=f"Members ({len(members)})",
                            value=member_text,
                            inline=False)
        else:
            embed.add_field(name="Members",
                            value="No members yet",
                            inline=False)

        # Add creation info
        created_by = ctx.guild.get_member(squad["created_by"])
        creator = created_by.name if created_by else "Unknown"
        embed.set_footer(text=f"Created by {creator}")

        await ctx.send(embed=embed)

    @bot.command(name="free_agents")
    async def list_free_agents(ctx):
        """List all players without squads."""
        players = load_players()

        # Filter free agents
        free_agents = [
            p for p in players if "squad" not in p or not p["squad"]
        ]

        if not free_agents:
            await ctx.send("There are no free agents at the moment!")
            return

        embed = discord.Embed(
            title="MLBB Free Agents",
            description=f"There are {len(free_agents)} players without squads:",
            color=discord.Color.blue())

        for player in free_agents:
            member = ctx.guild.get_member(player["id"])
            mention = member.mention if member else f"<@{player['id']}>"

            embed.add_field(
                name=player["mlbb_username"],
                value=f"Discord: {mention}\nID: {player['mlbb_id']}",
                inline=True)

        await ctx.send(embed=embed)

    @bot.command(name="search_player")
    async def search_player(ctx, *, search_term: str):
        """Search for a player by name or MLBB ID."""
        players = load_players()

        # Search by different criteria
        results = []
        search_term_lower = search_term.lower()

        for player in players:
            # Check Discord username
            if search_term_lower in player["username"].lower():
                results.append(player)
            # Check MLBB username
            elif search_term_lower in player["mlbb_username"].lower():
                results.append(player)
            # Check MLBB ID
            elif search_term == player["mlbb_id"]:
                results.append(player)

        if not results:
            await ctx.send(f"❌ No players found matching '{search_term}'!")
            return

        embed = discord.Embed(
            title=f"Player Search Results for '{search_term}'",
            description=f"Found {len(results)} matching players:",
            color=discord.Color.blue())

        for player in results:
            member = ctx.guild.get_member(player["id"])
            mention = member.mention if member else f"<@{player['id']}>"

            status = f"**Squad**: {player['squad']}" if "squad" in player and player[
                "squad"] else "**Status**: Free Agent"

            embed.add_field(
                name=player["mlbb_username"],
                value=f"Discord: {mention}\nID: {player['mlbb_id']}\n{status}",
                inline=True)

        await ctx.send(embed=embed)

    @bot.command(name="random_hero")
    async def random_hero(ctx):
        """Pick a random hero and show their info."""
        import random
        import json
        
        # Load heroes data
        with open("data/heroes.json", 'r') as f:
            data = json.load(f)
            
        # Pick random hero
        hero_name = random.choice(list(data["heroes"].keys()))
        hero_data = data["heroes"][hero_name]
        
        # Create embed
        embed = discord.Embed(
            title=f"Random Hero: {hero_name}",
            color=discord.Color.random()
        )
        embed.set_image(url=hero_data["image"])
        
        await ctx.send(embed=embed)

    @bot.command(name="search_role")
    async def search_role(ctx, role: str):
        """Find players by preferred role."""
        players = load_players()

        # Valid MLBB roles
        valid_roles = ["gold", "exp", "mid", "jungle", "roam"]
        if role.lower() not in valid_roles:
            await ctx.send(
                f"❌ Invalid role! Valid roles are: {', '.join(valid_roles)}")
            return

        # Find players with this role
        results = []
        for player in players:
            if "roles" in player and player["roles"] and role.lower(
            ) in player["roles"]:
                results.append(player)

        if not results:
            await ctx.send(f"❌ No players found with role '{role}'!")
            return

        embed = discord.Embed(title=f"Players with {role.upper()} Role",
                              description=f"Found {len(results)} players:",
                              color=discord.Color.blue())

        for player in results:
            member = ctx.guild.get_member(player["id"])
            mention = member.mention if member else f"<@{player['id']}>"

            status = f"**Squad**: {player['squad']}" if "squad" in player and player[
                "squad"] else "**Status**: Free Agent"
            heroes = f"**Main Heroes**: {player['roles'][role.lower()]}"

            embed.add_field(name=player["mlbb_username"],
                            value=f"Discord: {mention}\n{status}\n{heroes}",
                            inline=True)

        await ctx.send(embed=embed)

    # Error handler
    @bot.event
    async def on_command_error(ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You don't have permission to use this command!")
        else:
            await ctx.send(f"❌ An error occurred: {error}")
            logger.error(f"Command error: {error}")
