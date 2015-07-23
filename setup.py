# coding=utf-8
import setuptools
import octoprint_setuptools

setuptools.setup(**octoprint_setuptools.create_plugin_setup_parameters(
	identifier="octobullet",
	name="OctoPrint-Pushbullet",
	version="0.1.4",
	description="Pushes notifications about finished print jobs via Pushbullet",
	author="Gina Häußge",
	mail="osd@foosel.net",
	url="http://github.com/OctoPrint/OctoPrint-Pushbullet",
	# this dependency link is needed until pushbullety.py 0.8.2 gets released
	# on PyPI with https://github.com/randomchars/pushbullet.py/pull/46 included
	dependency_links=["https://github.com/foosel/pushbullet.py/archive/master.zip#egg=pushbullet.py.fixed-dev"],
	requires=[
		"OctoPrint>=1.2.4",
		"requests",
		"pushbullet.py.fixed==dev"
	]
))
