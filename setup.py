from setuptools import setup

setup(
	name = "slashcommands",
	description = "A wrapper for the Discord Slash Commands API, to be used with discord.py.",
	keywords = "discord slashcommands api wrapper library module development viral32111",

	version = "0.1.0",
	license = "GNU AGPLv3",
	url = "https://github.com/viral32111/slashcommands",

	author = "viral32111",
	author_email = "contact@viral32111.com",

	python_requires = ">=3.9.2",
	packages = [ "slashcommands" ],
	install_requires = [ "discord.py", "requests" ],

	classifiers = [
		"Development Status :: 3 - Alpha",
		"Intended Audience :: Developers",
		"Topic :: Software Development :: Libraries :: Python Modules",
		"License :: OSI Approved :: GNU Affero General Public License v3",
		"Programming Language :: Python :: 3.9",
	]
)
