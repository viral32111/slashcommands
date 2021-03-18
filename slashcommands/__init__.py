import json, requests

__API_BASE_URL = "https://discord.com/api/v8/"

_commandsSetup = { "global": {}, "guild": {} }
_commandsLookup = {}
_commandMetadata = None
_applicationID = None
_applicationToken = None

async def _request( endpoint, method = "GET", data = None ):
	global _applicationToken

	if data:
		response = requests.request( method, __API_BASE_URL + endpoint, json = data, headers = {
			"Authorization": "Bot " + _applicationToken
		} )
	else:
		response = requests.request( method, __API_BASE_URL + endpoint, headers = {
			"Authorization": "Bot " + _applicationToken
		} )

	response.raise_for_status()

	if response.text:
		return response.json()

class interaction:
	def __init__( self, payload, client ):
		self.__type = payload[ "type" ]
		self.__token = payload[ "token" ]
		self.__version = payload[ "version" ]
		

		self.client = client
		self.id = int( payload[ "id" ] )
		self.data = payload.get( "data", None )
		self.guild_id = payload.get( "guild_id", None )
		self.channel_id = payload.get( "channel_id", None )
		self.member = payload.get( "member", None )
		self.user = payload.get( "user", None )

		if self.guild_id:
			self.guild_id = int( self.guild_id )

		if self.channel_id:
			self.channel_id = int( self.channel_id )
	
	async def respond( self, content, **optional ):
		await _request( "interactions/" + str( self.id ) + "/" + self.__token + "/callback", method = "POST", data = {
			"type": 4, # ChannelMessageWithSource
			"data": {
				"content": content,
				"flags": ( 64 if optional.get( "hidden", False ) else 0 )
			}
		} )

async def _ready( payload ):
	global _applicationID, _commandsSetup, _commandsLookup

	_applicationID = payload[ "application" ][ "id" ]

	globalCommandsResponse = await _request( "applications/" + _applicationID + "/commands" )
	existingGlobalCommands = { command[ "name" ]: command for command in globalCommandsResponse }

	for name, metadata in _commandsSetup[ "global" ].items():
		if name in existingGlobalCommands.keys():
			command = existingGlobalCommands.pop( name )

			if metadata[ "description" ] != command[ "description" ]: # or if options are different
				patchedCommand = await _request( "applications/" + _applicationID + "/commands/" + command[ "id" ], method = "PATCH", data = {
					"description": metadata[ "description" ]
				} )

			_commandsLookup[ int( command[ "id" ] ) ] = metadata[ "function" ]
		else:
			createdCommand = await _request( "applications/" + _applicationID + "/commands", method = "POST", data = {
				"name": name,
				"description": metadata[ "description" ]
				# "options": metadata[ "options" ]
			} )

			_commandsLookup[ int( createdCommand[ "id" ] ) ] = metadata[ "function" ]

		for name in existingGlobalCommands:
			await _request( "applications/" + _applicationID + "/commands/" + existingGlobalCommands[ name ][ "id" ], method = "DELETE" )

	for guildID in _commandsSetup[ "guild" ].keys():
		guildCommandsResponse = await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands" )
		existingGuildCommands = { command[ "name" ]: command for command in guildCommandsResponse }

		for name, metadata in _commandsSetup[ "guild" ][ guildID ].items():
			if name in existingGuildCommands.keys():
				command = existingGuildCommands.pop( name )

				if metadata[ "description" ] != command[ "description" ]: # or if options are different
					patchedCommand = await _request( "applications/" + _applicationID + + "/guilds/" + str( guildID ) + "/commands/" + command[ "id" ], method = "PATCH", data = {
						"description": metadata[ "description" ]
					} )

				_commandsLookup[ int( command[ "id" ] ) ] = metadata[ "function" ]
			else:
				createdCommand = await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands", method = "POST", data = {
					"name": name,
					"description": metadata[ "description" ]
					# "options": metadata[ "options" ]
				} )

				_commandsLookup[ int( createdCommand[ "id" ] ) ] = metadata[ "function" ]

		for name in existingGuildCommands:
			await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands/" + existingGuildCommands[ name ][ "id" ], method = "DELETE" )

def _register( function ):
	global _commandMetadata, _commandsSetup

	_commandMetadata[ "function" ] = function

	if _commandMetadata[ "guild" ]:
		if _commandMetadata[ "guild" ] not in _commandsSetup[ "guild" ]:
			_commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ] = {}
	
		_commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ][ function.__name__ ] = _commandMetadata
	else:
		_commandsSetup[ "global" ][ function.__name__ ] = _commandMetadata

	_commandMetadata = None

def new( description, **optional ):
	global _commandMetadata

	_commandMetadata = {
		"description": description,
		"options": optional.get( "options", None ),
		"guild": optional.get( "guild", None )
	}

	return _register

async def run( payload, client ):
	global _applicationToken, _commandsLookup

	if payload[ "t" ] == "READY":
		_applicationToken = client.http.token
		await _ready( payload[ "d" ] )

	elif payload[ "t" ] == "INTERACTION_CREATE":
		await _commandsLookup[ int( payload[ "d" ][ "data" ][ "id" ] ) ]( interaction( payload[ "d" ], client ) )

	elif payload[ "t" ] == "APPLICATION_COMMAND_CREATE":
		print( "APPLICATION_COMMAND_CREATE", payload[ "d" ][ "id" ], payload[ "d" ][ "name" ] )

	elif payload[ "t" ] == "APPLICATION_COMMAND_UPDATE":
		print( "APPLICATION_COMMAND_CREATE", payload[ "d" ][ "id" ], payload[ "d" ][ "name" ] )

	elif payload[ "t" ] == "APPLICATION_COMMAND_DELETE":
		print( "APPLICATION_COMMAND_CREATE", payload[ "d" ][ "id" ], payload[ "d" ][ "name" ] )
