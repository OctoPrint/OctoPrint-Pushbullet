# coding=utf-8
import setuptools
import octoprint_setuptools

parameters = octoprint_setuptools.create_plugin_setup_parameters(
	identifier="octobullet",
	name="OctoPrint-Pushbullet",
	version="0.1.3",
	description="Pushes notifications about finished print jobs via Pushbullet",
	author="Gina Häußge",
	mail="osd@foosel.net",
	url="http://github.com/OctoPrint/OctoPrint-Pushbullet",
	requires=[
		"OctoPrint",
		"requests",
		"pushbullet.py.fixed==dev"
	]
)
parameters["dependency_links"] = [
	"https://github.com/foosel/pushbullet.py/archive/master.zip#egg=pushbullet.py.fixed-dev"
]
setuptools.setup(**parameters)
