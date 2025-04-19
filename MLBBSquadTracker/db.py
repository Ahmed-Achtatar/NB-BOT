# Database operations for the bot
import os
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Paths to data files
DATA_DIR = "data"
SQUADS_FILE = os.path.join(DATA_DIR, "squads.json")
PLAYERS_FILE = os.path.join(DATA_DIR, "players.json")


def ensure_data_files_exist():
    """Ensure that the data directory and files exist."""
    # Create data directory if it doesn't exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.debug(f"Created directory: {DATA_DIR}")

    # Create squads file if it doesn't exist
    if not os.path.exists(SQUADS_FILE):
        with open(SQUADS_FILE, 'w') as f:
            json.dump([], f)
        logger.debug(f"Created file: {SQUADS_FILE}")

    # Create players file if it doesn't exist
    if not os.path.exists(PLAYERS_FILE):
        with open(PLAYERS_FILE, 'w') as f:
            json.dump([], f)
        logger.debug(f"Created file: {PLAYERS_FILE}")


def load_squads():
    """Load squads data from JSON file."""
    try:
        with open(SQUADS_FILE, 'r') as f:
            squads = json.load(f)
            # Ensure each squad has required fields (example for future expansion)
            for squad in squads:
                if "name" not in squad:
                    logger.warning(f"Squad missing 'name' field: {squad}")
            return squads
    except Exception as e:
        logger.error(f"Error loading squads: {e}")
        return []


def save_squads(squads):
    """Save squads data to JSON file."""
    try:
        with open(SQUADS_FILE, 'w') as f:
            json.dump(squads, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving squads: {e}")
        return False


def load_players():
    """Load players data from JSON file, ensuring all required fields exist."""
    try:
        with open(PLAYERS_FILE, 'r') as f:
            players = json.load(f)
            # Add default values for missing fields
            for player in players:
                if "max_rank" not in player:
                    player["max_rank"] = "Unranked"
                if "roles" not in player:
                    player["roles"] = {}
                if "win_rate" not in player:
                    player["win_rate"] = "Unknown"
                if "availability" not in player:
                    player["availability"] = "Not specified"
                if "squad" not in player:
                    player["squad"] = ""  # Ensure squad field exists
            return players
    except Exception as e:
        logger.error(f"Error loading players: {e}")
        return []


def save_players(players):
    """Save players data to JSON file."""
    try:
        with open(PLAYERS_FILE, 'w') as f:
            json.dump(players, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving players: {e}")
        return False


def find_squad_by_name(name):
    """Find a squad by name (case-insensitive)."""
    squads = load_squads()
    for squad in squads:
        if squad["name"].lower() == name.lower():
            return squad
    return None


def find_player_by_id(player_id):
    """Find a player by ID."""
    players = load_players()
    for player in players:
        if player["id"] == player_id:
            return player
    return None


def find_player_by_username(username):
    """Find a player by username (case-insensitive)."""
    players = load_players()
    for player in players:
        if player["username"].lower() == username.lower():
            return player
    return None


def find_player_by_mlbb_id(mlbb_id):
    """Find a player by MLBB ID."""
    players = load_players()
    for player in players:
        if player["mlbb_id"] == mlbb_id:
            return player
    return None


def find_squad_members(squad_name):
    """Find all members of a squad."""
    squad = find_squad_by_name(squad_name)
    if not squad:
        return None

    members = []
    players = load_players()
    target_name = squad["name"].lower()
    for player in players:
        if player["squad"].lower() == target_name:
            members.append(player)

    return members


def is_free_agent(player_id):
    """Check if a player is a free agent (not in a squad)."""
    player = find_player_by_id(player_id)
    if not player:
        return False
    return not player["squad"].strip()  # True if squad is empty or whitespace
