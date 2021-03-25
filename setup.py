import setuptools

setuptools.setup(
	name = "slashcommands",
	description = "A wrapper for the Discord Slash Commands API, to be used with discord.py.",
	keywords = "discord slashcommands api wrapper library module development viral32111",

	version = "1.1.0",
	license = "AGPL-3.0-only",
	url = "https://github.com/viral32111/slashcommands",

	author = "viral32111",
	author_email = "contact@viral32111.com",

	python_requires = ">=3.9.2",
	packages = [ "slashcommands" ],
	install_requires = [ "discord.py", "requests", "deepdiff" ],

	classifiers = [
		"Development Status :: 5 - Production/Stable",
		"Intended Audience :: Developers",
		"Topic :: Internet",
		"Topic :: Software Development :: Libraries :: Python Modules",
		"License :: OSI Approved :: GNU Affero General Public License v3",
		"Programming Language :: Python :: 3.9",
		"Natural Language :: English",
		"Operating System :: OS Independent",
	]
)
