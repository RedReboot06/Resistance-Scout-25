import os
import asyncio
import discord
import requests
import pandas as pd
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
DEBUG_CHANNEL_ID = int(os.getenv("DEBUG_CHANNEL_ID"))
NEXUS_API_KEY = os.getenv("NEXUS_API_KEY")
EVENT_KEY = os.getenv("EVENT_KEY")
TIME_SHIFT = -5  # Eastern Standard Time (EST) is UTC-5

EST = timezone(timedelta(hours=TIME_SHIFT))  # Eastern Standard Time
# Nexus API Endpoint
NEXUS_API_URL = f"https://frc.nexus/api/v1/event/{EVENT_KEY}"

# Read CSV (Assuming it's structured like the table in the PDF)
CSV_FILE = "scout_schedule.csv"  # Ensure correct file placement
schedule_df = pd.read_csv(CSV_FILE)
# Initialize Discord Bot
intents = discord.Intents.default()
intents.messages = True  # Enable message intents
client = commands.Bot(command_prefix="!", intents=intents)

async def send_debug_message(message):
    """Send debug message to the specified debug channel."""
    channel = client.get_channel(DEBUG_CHANNEL_ID)
    if channel:
        for i in range(0, len(message), 2000):
            await channel.send(message[i:i+2000])
    else:
        print(f"⚠️ Warning: Debug channel with ID {DEBUG_CHANNEL_ID} not found.")

async def fetch_match_schedule():
    """Fetch match schedule from the Nexus API."""
    headers = {"Nexus-Api-Key": NEXUS_API_KEY}
    response = requests.get(NEXUS_API_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        await send_debug_message(f"✅ API Response received: {data}")
        return data.get("matches", [])  # Use .get() to avoid KeyErrors
    else:
        await send_debug_message(f"❌ Error fetching match data: {response.status_code} - {response.text}")
        return []

async def send_match_notification(channel, match_info):
    """Sends a Discord message for a scheduled match."""
    match_number = int(match_info["label"].split()[-1])  # Extract match number from "Qualification X"

    # Ensure times exist
    if "times" not in match_info or "estimatedStartTime" not in match_info["times"]:
        await send_debug_message(f"⚠️ Warning: Missing 'estimatedStartTime' in match data: {match_info}")
        return  # Skip this match

    match_time_utc = datetime.fromtimestamp(match_info["times"]["estimatedStartTime"] / 1000, timezone.utc)
    match_time = match_time_utc.astimezone(EST)  # Convert to Eastern Standard Time

    # Get scouts & roles from CSV
    match_row = schedule_df[schedule_df["Match #"] == match_number]
    if match_row.empty:
        await send_debug_message(f"⚠️ Warning: No matching entry found in CSV for Match {match_number}.")
        return  # Skip this match

    scout_manager = match_row.iloc[0]["Scout Manager"]
    scouts = match_row.iloc[0][["Scout", "Scout.1", "Scout.2", "Scout.3", "Scout.4", "Scout.5"]].dropna().tolist()
    drive_team = match_row.iloc[0][["Drive 1", "Drive 2", "HP 1", "HP 2"]].dropna().tolist()

    message = (
        f"📢 **Match {match_number} Reminder!**\n"
        f"🕒 Scheduled Time: {match_time.strftime('%I:%M %p EST')}\n"
        f"👨‍💼 **Scout Manager**: {scout_manager}\n"
        f"🔍 **Scouts**: {', '.join(scouts)}\n"
        f"🚗 **Drive Team**: {', '.join(drive_team)}"
    )

    await channel.send(message)

async def schedule_notifications():
    """Schedules Discord messages for each match."""
    await client.wait_until_ready()
    channel = client.get_channel(DISCORD_CHANNEL_ID)

    matches = await fetch_match_schedule()
    now = datetime.now(timezone.utc)

    for match in matches:
        if "times" not in match or "estimatedStartTime" not in match["times"]:
            await send_debug_message(f"⚠️ Warning: Missing 'estimatedStartTime' in match data: {match}")
            continue  # Skip this match

        match_time = datetime.fromtimestamp(match["times"]["estimatedStartTime"] / 1000, timezone.utc)
        notification_time = match_time - timedelta(minutes=7)  # 7 minutes before the match
        delay = (notification_time - now).total_seconds()

        await send_debug_message(f"⏳ Match {match['label']} notification will be sent in {delay:.2f} seconds.")

        if delay > 0:
            asyncio.create_task(notification_task(delay, channel, match))
        else:
            await send_debug_message(f"⚠️ Warning: Match {match['label']} has already started. Skipping.")

async def notification_task(delay, channel, match):
    """Handles the delay and sends match notifications."""
    await asyncio.sleep(delay)
    await send_match_notification(channel, match)

@client.event
async def on_ready():
    await send_debug_message(f"✅ Logged in as {client.user}")
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    await channel.send("✅ Bot is online and ready!")  # Test message
    await schedule_notifications()

client.run(DISCORD_TOKEN)