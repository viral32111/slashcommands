# Slash Commands

This is a wrapper around the [Discord Slash Commands API](https://discord.com/developers/docs/interactions/slash-commands), to be used with [discord.py](https://github.com/Rapptz/discord.py).

## Installation

The best way to install this is by running `pip install git+https://github.com/viral32111/slashcommands` (you must use the GitHub link because this package is not published on PyPI).

Alternatively, you can manually install this by [downloading the latest release](https://github.com/viral32111/slashcommands/releases/latest) (or cloning this repository) then running `pip install .` while in the directory.

## Example

```python
# Import modules
import discord, slashcommands, asyncio

# Create the client
client = discord.Client()
print( "Loading..." )

# Create a test command
@slashcommands.new( "A simple test command to check if everything works." )
async def test( interaction ):
	message = await interaction.respond( f"This is a test, { interaction.user.username }!" )
	await message.followup( "Do you like my reply @everyone?", mentions = discord.AllowedMentions.none() )

# Create a sleep command
@slashcommands.new( "Another test command for deferred responses.", options = [ slashcommands.option(
	type = slashcommands.option.type.number,
	name = "time",
	description = "How long to sleep for.",
	required = True
) ] )
async def sleep( interaction ):
	message = await interaction.think()
	await asyncio.sleep( int( interaction.arguments[ "time" ] ) )
	await message.edit( "Finished!" )

# Create a warn command
@slashcommands.new( "Warn a member with a provided reason.", options = [ slashcommands.option(
	type = slashcommands.option.type.user,
	name = "member",
	description = "The member to warn.",
	required = True
), slashcommands.option(
	type = slashcommands.option.type.string,
	name = "reason",
	description = "Why you are warning this member.",
	required = True
) ] )
async def warn( interaction ):
	await interaction.respond( f"You warned <@{ interaction.arguments[ 'member' ] }> for { interaction.arguments[ 'reason' ] }.", hidden = True )

# Runs when we're ready
@client.event
async def on_ready():
	print( "Ready!" )

# Runs when we receive a gateway event
@client.event
async def on_socket_response( payload ):
	await slashcommands.run( payload, client )

# Start the client
client.run( "BOT-TOKEN-HERE" )
```

## License

Copyright (C) 2021 [viral32111](https://viral32111.com).

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see https://www.gnu.org/licenses.
