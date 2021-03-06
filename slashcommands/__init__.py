import asyncio, functools, enum, json, re
import requests, deepdiff

_API_BASE_URL = "https://discord.com/api/v8/"

# discord.com/developers/docs/interactions/slash-commands#interaction-response-interactionresponsetype
_INTERACTION_RESPONSE_MESSAGE = 4
_INTERACTION_RESPONSE_DEFER = 5

_commandsSetup = { "global": {}, "guild": {} }
_commandsLookup = {}
_commandMetadata = None
_applicationID = None
_applicationToken = None
_eventLoop = None
_allowedMentions = None

async def _request( endpoint, method = "GET", data = None, files = None ):
	global _applicationToken, _eventLoop

	authorizationHeader = { "Authorization": "Bot " + _applicationToken }

	responseCode = 429
	while responseCode == 429:
		if files and data:
			payload = { f"file{ num }": ( file.filename, file.fp ) for num, file in enumerate( files ) }
			payload[ "payload_json" ] = ( None, json.dumps( data ), "application/json" )
			response = await _eventLoop.run_in_executor( None, functools.partial( requests.request, method, _API_BASE_URL + endpoint, files = payload, headers = authorizationHeader ) )
		elif files and not data:
			payload = { f"file{ num }": ( file.filename, file.fp ) for num, file in enumerate( files ) }
			response = await _eventLoop.run_in_executor( None, functools.partial( requests.request, method, _API_BASE_URL + endpoint, files = payload, headers = authorizationHeader ) )
		elif not files and data:
			response = await _eventLoop.run_in_executor( None, functools.partial( requests.request, method, _API_BASE_URL + endpoint, json = data, headers = authorizationHeader ) )
		else:
			response = await _eventLoop.run_in_executor( None, functools.partial( requests.request, method, _API_BASE_URL + endpoint, headers = authorizationHeader ) )

		responseCode = response.status_code

		if responseCode == 429:
			retryAfter = response.json()[ "retry_after" ] + 1 # add 1 second to be safe
			await asyncio.sleep( retryAfter )

	try:
		response.raise_for_status()
	except requests.exceptions.HTTPError as httpError:
		raise requests.exceptions.HTTPError( f"{ httpError.response.status_code } for URL { httpError.request.url }: { httpError.response.text }" )

	if response.text:
		return response.json()

async def _allowedMentionsToDict( allowedMentions ):
	dictAllowedMentions = {
		"parse": [],
		"roles": [],
		"users": []
	}

	if allowedMentions.everyone:
		dictAllowedMentions[ "parse" ].append( "everyone" )
	
	if allowedMentions.users:
		if isinstance( allowedMentions.users, list ):
			for userID in allowedMentions.users:
				dictAllowedMentions[ "users" ].append( userID )
		else:
			dictAllowedMentions[ "parse" ].append( "users" )

	if allowedMentions.roles:
		if isinstance( allowedMentions.roles, list ):
			for roleID in allowedMentions.roles:
				dictAllowedMentions[ "roles" ].append( roleID )
		else:
			dictAllowedMentions[ "parse" ].append( "roles" )

	return dictAllowedMentions

class option:
	def __init__( self, **arguments ):
		self.type = arguments[ "type" ].value
		self.name = arguments[ "name" ]
		self.description = arguments[ "description" ]
		self.required = arguments.get( "required", False )
		self.choices = arguments.get( "choices", None )
		self.options = arguments.get( "options", None )

	def __iter__( self ):
		yield "type", self.type
		yield "name", self.name
		yield "description", self.description

		if self.required:
			yield "required", self.required

		if self.choices:
			yield "choices", [ dict( choice ) for choice in self.choices ]

		if self.options:
			yield "options", [ dict( option ) for option in self.options ]

	# discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
	class type( enum.Enum ):
		subCommand = 1
		subCommandGroup = 2
		string = 3
		number = 4
		boolean = 5
		user = 6
		channel = 7
		role = 8

	class choice:
		def __init__( self, name, value ):
			self.name = name
			self.value = value
	
		def __iter__( self ):
			yield "name", self.name
			yield "value", self.value

class user:
	def __init__( self, user ):
		self.id = int( user[ "id" ] )
		self.username = user[ "username" ]
		self.discriminator = user[ "discriminator" ]
		self.avatar = user[ "avatar" ]

		self.publicFlags = user.get( "public_flags", None )
		
		if self.publicFlags:
			self.publicFlags = int( self.publicFlags )

class member:
	def __init__( self, member ):
		self.roleIDs = [ int( roleID ) for roleID in member[ "roles" ] ]
		self.joinedAt = member[ "joined_at" ] # should be datetime.datetime
		self.isDeaf = member[ "deaf" ]
		self.isMute = member[ "mute" ]

		self.nickname = member.get( "nick", None )
		self.boostingSince = member.get( "premium_since", None )
		self.isPending = member.get( "pending", None )
		self.permissions = member.get( "permissions", None )

class command:
	def __init__( self, payload ):
		self.__data = payload.get( "data", None )
		self.__member = payload.get( "member", None )
		self.__user = payload.get( "user", None )

		self.id = int( payload[ "id" ] )
		self.guildID = payload.get( "guild_id", None )
		self.channelID = payload.get( "channel_id", None )
		self.arguments = {}

		if self.guildID:
			self.guildID = int( self.guildID )

		if self.channelID:
			self.channelID = int( self.channelID )

		if self.__data:
			self.data = interaction.data( self.__data )

			if self.data.options:
				for option in self.data.options:
					self.arguments = { option.name: option.value for option in self.data.options }

		if self.__member:
			self.member = member( self.__member )
			self.user = user( self.__member[ "user" ] )

		if self.__user:
			self.user = user( self.__user )

		self.isDirectMessage = ( self.__member == None and self.__user != None )

class interaction:
	def __init__( self, payload, client ):
		self.__hasResponded = False
		self.__hasDeferred = False

		self.__type = payload[ "type" ]
		self.__token = payload[ "token" ]
		self.__version = payload[ "version" ]
		self.__data = payload.get( "data", None )
		self.__member = payload.get( "member", None )
		self.__user = payload.get( "user", None )

		self.client = client
		self.id = int( payload[ "id" ] )
		self.guildID = payload.get( "guild_id", None )
		self.channelID = payload.get( "channel_id", None )
		self.arguments = {}

		if self.guildID:
			self.guildID = int( self.guildID )

		if self.channelID:
			self.channelID = int( self.channelID )

		if self.__data:
			self.data = interaction.data( self.__data )

			if self.data.options:
				self.arguments = { option.name: ( option.value if option.value else option.arguments ) for option in self.data.options }

		if self.__member:
			self.member = member( self.__member )
			self.user = user( self.__member[ "user" ] )

		if self.__user:
			self.user = user( self.__user )

		self.isDirectMessage = ( self.__member == None and self.__user != None )

	async def respond( self, *arguments, **optional ):
		if self.__hasResponded:
			raise Exception( "Cannot send another original interaction response, use interaction.followup() instead." )

		if optional.get( "files", None ) and len( arguments ) <= 0:
			raise Exception( "Cannot send files in original interaction response without text content being provided." )

		discordEmbeds = optional.get( "embeds", None )
		jsonDiscordEmbeds = [ embed.to_dict() for embed in discordEmbeds ] if discordEmbeds else None

		allowedMentions = optional.get( "mentions", None )
		if allowedMentions:
			jsonAllowedMentions = await _allowedMentionsToDict( allowedMentions )
		elif _allowedMentions:
			jsonAllowedMentions = await _allowedMentionsToDict( _allowedMentions )
		else:
			jsonAllowedMentions = None

		await _request( "interactions/" + str( self.id ) + "/" + self.__token + "/callback", method = "POST", data = {
			"type": _INTERACTION_RESPONSE_MESSAGE,
			"data": {
				"tts": optional.get( "tts", False ),
				"content": arguments[ 0 ] if len( arguments ) > 0 else None,
				"embeds": jsonDiscordEmbeds,
				"allowed_mentions": jsonAllowedMentions,
				"flags": ( 64 if optional.get( "hidden", False ) else 0 )
			}
		}, files = optional.get( "files", None ) )

		self.__hasResponded = True

		return interaction.original( self.__token, optional.get( "hidden", False ) )

	async def think( self, **optional ):
		if self.__hasDeferred:
			raise Exception( "Cannot send another deferred interaction response." )

		response = await _request( "interactions/" + str( self.id ) + "/" + self.__token + "/callback", method = "POST", data = {
			"type": _INTERACTION_RESPONSE_DEFER,
			"data": {
				"flags": ( 64 if optional.get( "hidden", False ) else 0 )
			}
		} )

		self.__hasDeferred = True

		return interaction.original( self.__token, optional.get( "hidden", False ) )

	class data:
		def __init__( self, data ):
			self.id = int( data[ "id" ] )
			self.name = data[ "name" ]
			self.options = data.get( "options", None )
			self.arguments = None

			if self.options:
				self.options = [ interaction.data.option( option ) for option in self.options ]
				self.arguments = { option.name: option.value for option in self.options }
	
		class option:
			def __init__( self, option ):
				self.name = option[ "name" ]
				self.value = option.get( "value", None )
				self.options = option.get( "options", None )
				self.arguments = None

				if self.options:
					self.options = [ interaction.data.option( option ) for option in self.options ]
					self.arguments = { option.name: ( option.value if option.value else option.arguments ) for option in self.options }

	class original:
		def __init__( self, token, isHidden ):
			self.__interactionToken = token
			self.__isHidden = isHidden

		async def edit( self, *arguments, **optional ):
			discordEmbeds = optional.get( "embeds", None )
			jsonDiscordEmbeds = [ embed.to_dict() for embed in discordEmbeds ] if discordEmbeds else None

			allowedMentions = optional.get( "mentions", None )
			if allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( allowedMentions )
			elif _allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( _allowedMentions )
			else:
				jsonAllowedMentions = None

			await _request( "webhooks/" + str( _applicationID ) + "/" + self.__interactionToken + "/messages/@original", method = "PATCH", data = {
				"content": arguments[ 0 ] if len( arguments ) > 0 else None,
				"embeds": jsonDiscordEmbeds,
				"allowed_mentions": jsonAllowedMentions
			} )

		async def delete( self ):
			if self.__isHidden:
				raise Exception( "Cannot delete an ephemeral response!" )

			await _request( "webhooks/" + str( _applicationID ) + "/" + self.__interactionToken + "/messages/@original", method = "DELETE" )

		async def followup( self, *arguments, **optional ):
			discordEmbeds = optional.get( "embeds", None )
			jsonDiscordEmbeds = [ embed.to_dict() for embed in discordEmbeds ] if discordEmbeds else None

			allowedMentions = optional.get( "mentions", None )
			if allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( allowedMentions )
			elif _allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( _allowedMentions )
			else:
				jsonAllowedMentions = None

			response = await _request( "webhooks/" + str( _applicationID ) + "/" + self.__interactionToken, method = "POST", data = {
				"content": arguments[ 0 ] if len( arguments ) > 0 else None,
				"embeds": jsonDiscordEmbeds,
				"allowed_mentions": jsonAllowedMentions,
				"flags": ( 64 if optional.get( "hidden", False ) else 0 )
			}, files = optional.get( "files", None ) )

			# in the future, create a msg class for all the data returned in the response
			return interaction.followup( self.__interactionToken, int( response[ "id" ] ), optional.get( "hidden", False ) )

	class followup:
		def __init__( self, token, id, isHidden ):
			self.__interactionToken = token
			self.__messageID = id
			self.__isHidden = isHidden

		async def edit( self, *arguments, **optional ):
			discordEmbeds = optional.get( "embeds", None )
			jsonDiscordEmbeds = [ embed.to_dict() for embed in discordEmbeds ] if discordEmbeds else None

			allowedMentions = optional.get( "mentions", None )
			if allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( allowedMentions )
			elif _allowedMentions:
				jsonAllowedMentions = await _allowedMentionsToDict( _allowedMentions )
			else:
				jsonAllowedMentions = None

			await _request( "webhooks/" + str( _applicationID ) + "/" + self.__interactionToken + "/messages/" + str( self.__messageID ), method = "PATCH", data = {
				"content": arguments[ 0 ] if len( arguments ) > 0 else None,
				"embeds": jsonDiscordEmbeds,
				"allowed_mentions": jsonAllowedMentions
			} )

		async def delete( self ):
			if self.__isHidden:
				raise Exception( "Cannot delete an ephemeral response!" )

			await _request( "webhooks/" + str( _applicationID ) + "/" + self.__interactionToken + "/messages/" + str( self.__messageID ), method = "DELETE" )

async def _ready( payload ):
	global _applicationID, _commandsSetup, _commandsLookup

	_applicationID = payload[ "application" ][ "id" ]

	globalCommandsResponse = await _request( "applications/" + _applicationID + "/commands" )
	existingGlobalCommands = { command[ "name" ]: command for command in globalCommandsResponse }

	for name, metadata in _commandsSetup[ "global" ].items():
		commandOptions = [ dict( option ) for option in metadata[ "options" ] ] if metadata[ "options" ] else None
		
		if name in existingGlobalCommands.keys():
			command = existingGlobalCommands.pop( name )

			if commandOptions and command.get( "options", None ):
				hasOptionsChanged = ( len( deepdiff.DeepDiff( commandOptions, command[ "options" ], ignore_order = True ) ) > 0 )
			elif commandOptions != command.get( "options", None ):
				hasOptionsChanged = True
			else:
				hasOptionsChanged = False

			if metadata[ "description" ] != command[ "description" ] or hasOptionsChanged:
				await _request( "applications/" + _applicationID + "/commands/" + command[ "id" ], method = "PATCH", data = {
					"description": metadata[ "description" ],
					"options": commandOptions
				} )

			_commandsLookup[ int( command[ "id" ] ) ] = metadata[ "function" ]
		else:
			createdCommand = await _request( "applications/" + _applicationID + "/commands", method = "POST", data = {
				"name": name,
				"description": metadata[ "description" ],
				"options": commandOptions
			} )

			_commandsLookup[ int( createdCommand[ "id" ] ) ] = metadata[ "function" ]

		for name in existingGlobalCommands:
			await _request( "applications/" + _applicationID + "/commands/" + existingGlobalCommands[ name ][ "id" ], method = "DELETE" )

	commandGuildIDs = list( _commandsSetup[ "guild" ].keys() )
	for guildID in commandGuildIDs:
		guildCommandsResponse = await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands" )
		existingGuildCommands = { command[ "name" ]: command for command in guildCommandsResponse }

		for name, metadata in _commandsSetup[ "guild" ][ guildID ].items():
			commandOptions = [ dict( option ) for option in metadata[ "options" ] ] if metadata[ "options" ] else None
	
			if name in existingGuildCommands.keys():
				command = existingGuildCommands.pop( name )

				if commandOptions and command.get( "options", None ):
					hasOptionsChanged = ( len( deepdiff.DeepDiff( commandOptions, command[ "options" ], ignore_order = True ) ) > 0 )
				elif commandOptions != command.get( "options", None ):
					hasOptionsChanged = True
				else:
					hasOptionsChanged = False

				if metadata[ "description" ] != command[ "description" ] or hasOptionsChanged:
					await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands/" + command[ "id" ], method = "PATCH", data = {
						"description": metadata[ "description" ],
						"options": commandOptions
					} )

				_commandsLookup[ int( command[ "id" ] ) ] = metadata[ "function" ]
			else:
				createdCommand = await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands", method = "POST", data = {
					"name": name,
					"description": metadata[ "description" ],
					"options": commandOptions
				} )

				_commandsLookup[ int( createdCommand[ "id" ] ) ] = metadata[ "function" ]

		for name in existingGuildCommands:
			await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands/" + existingGuildCommands[ name ][ "id" ], method = "DELETE" )

	payloadGuildIDs = [ int( guild[ "id" ] ) for guild in payload[ "guilds" ] if int( guild[ "id" ] ) not in commandGuildIDs ]
	for guildID in payloadGuildIDs:
		guildCommandsResponse = await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands" )
		for command in guildCommandsResponse:
			await _request( "applications/" + _applicationID + "/guilds/" + str( guildID ) + "/commands/" + command[ "id" ], method = "DELETE" )

def _register( function ):
	global _commandMetadata, _commandsSetup

	commandName = function.__name__
	_commandMetadata[ "function" ] = function

	if not re.match( r'^[\w-]{1,32}$', commandName ):
		raise Exception( "Invalid command name! Must be alphanumeric & between 1 and 32 characters." )

	if len( _commandMetadata[ "description" ] ) < 1 or len( _commandMetadata[ "description" ] ) > 100:
		raise Exception( "Invalid command description! Must be between 1 and 100 characters." )

	if _commandMetadata[ "options" ]:
		if len( _commandMetadata[ "options" ] ) > 25:
			raise Exception( "Commands can only have up to 25 options!" )

		for option in _commandMetadata[ "options" ]:
			if option.choices:
				if len( option.choices ) > 25:
					raise Exception( "Command options can only have up to 25 choices!" )

	if _commandMetadata[ "guild" ]:
		if _commandMetadata[ "guild" ] not in _commandsSetup[ "guild" ]:
			_commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ] = {}
	
		if len( _commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ] ) >= 100:
			raise Exception( "Cannot have more than 100 guild commands per guild." )

		if commandName in _commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ]:
			raise Exception( "Cannot register more than one command for this guild with the same name." )

		_commandsSetup[ "guild" ][ _commandMetadata[ "guild" ] ][ commandName ] = _commandMetadata
	else:
		if len( _commandsSetup[ "global" ] ) >= 100:
			raise Exception( "Cannot have more than 100 global commands." )

		if commandName in _commandsSetup[ "global" ]:
			raise Exception( "Cannot register more than one command globally with the same name." )

		_commandsSetup[ "global" ][ commandName ] = _commandMetadata

	_commandMetadata = None

def new( description, **optional ):
	global _commandMetadata

	_commandMetadata = {
		"description": description,
		"guild": optional.get( "guild", None ),
		"options": optional.get( "options", None )
	}

	return _register

async def run( payload, client ):
	global _applicationToken, _commandsLookup, _eventLoop

	if payload[ "t" ] == "READY":
		_applicationToken = client.http.token
		_eventLoop = client.loop

		await _ready( payload[ "d" ] )

	elif payload[ "t" ] == "INTERACTION_CREATE":
		await _commandsLookup[ int( payload[ "d" ][ "data" ][ "id" ] ) ]( interaction( payload[ "d" ], client ) )
		return command( payload[ "d" ] )
