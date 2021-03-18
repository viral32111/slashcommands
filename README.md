# Slash Commands

This is a wrapper around the [Discord Slash Commands API](https://discord.com/developers/docs/interactions/slash-commands), to be used with [discord.py](https://github.com/Rapptz/discord.py).

## Example

```python
import discord, slashcommands

client = discord.Client()
print( "Loading..." )

@slashcommands.new( "A simple test command to check if everything works." )
async def test( interaction ):
	await interaction.respond( "This is a global test, " + interaction.member[ "user" ][ "username" ] + "!" )

@client.event
async def on_ready():
	print( "Ready!" )

@client.event
async def on_socket_response( payload ):
	await slashcommands.run( payload, client )

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
