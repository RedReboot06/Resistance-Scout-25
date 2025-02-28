import os
import discord
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEBUG_CHANNEL_ID = int(os.getenv("DEBUG_CHANNEL_ID"))

intents = discord.Intents.default()
intents.messages = True  # Enable message intents
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    await monitor_for_update_event()

async def monitor_for_update_event():
    debug_channel = client.get_channel(DEBUG_CHANNEL_ID)
    if not debug_channel:
        print(f"⚠️ Warning: Debug channel with ID {DEBUG_CHANNEL_ID} not found.")
        return

    while True:
        await asyncio.sleep(5)  # Check every 5 seconds
        async for message in debug_channel.history(limit=10):
            if message.content == "!UPDATE EVENT":
                await debug_channel.send("Please provide the new event key:")
                def check(m):
                    return m.author == message.author and m.channel == message.channel
                try:
                    new_event_key_msg = await client.wait_for("message", check=check, timeout=60)
                    new_event_key = new_event_key_msg.content

                    # Update the .env file
                    with open('.env', 'r') as file:
                        lines = file.readlines()
                    with open('.env', 'w') as file:
                        key_updated = False
                        for line in lines:
                            if line.startswith("EVENT_KEY="):
                                file.write(f"EVENT_KEY={new_event_key}")
                                key_updated = True
                            else:
                                file.write(line)

                    # Reload the new environment variables
                    load_dotenv()
                    global EVENT_KEY, NEXUS_API_URL
                    EVENT_KEY = os.getenv("EVENT_KEY")
                    NEXUS_API_URL = f"https://frc.nexus/api/v1/event/{EVENT_KEY}"
                    
                    await debug_channel.send(f"✅ Event key updated to {new_event_key}")

                    # Stop prompting for new keys repeatedly
                    return
                except asyncio.TimeoutError:
                    await debug_channel.send("❌ You took too long to provide a new event key. Please try again.")
                    return  # Stop the loop and wait for the next !UPDATE EVENT command

client.run(DISCORD_TOKEN)
