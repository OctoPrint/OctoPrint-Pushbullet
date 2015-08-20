# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <osd@foosel.net>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os

import octoprint.plugin
from octoprint.events import Events

import pushbullet

class PushbulletPlugin(octoprint.plugin.EventHandlerPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.WizardPlugin):

	def __init__(self):
		self._bullet = None

	def _connect_bullet(self, apikey):
		if apikey:
			try:
				self._bullet = pushbullet.PushBullet(apikey)
				self._logger.info("Connected to PushBullet")
				return True
			except:
				self._logger.exception("Error while instantiating PushBullet")
				return False

	#~~ StartupPlugin

	def on_after_startup(self):
		self._connect_bullet(self._settings.get(["access_token"]))

	#~~ SettingsPlugin

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		import threading
		thread = threading.Thread(target=self._connect_bullet, args=(self._settings.get(["access_token"]),))
		thread.daemon = True
		thread.start()

	def get_settings_defaults(self):
		return dict(
			access_token=None,
			printDone=dict(
				title="Print job finished",
				body="{file} finished printing in {elapsed_time}"
			)
		)

	#~~ TemplatePlugin API

	def get_template_configs(self):
		return [
			dict(type="settings", name="Pushbullet", custom_bindings=False),
			dict(type="wizard", name="Pushbullet", custom_bindings=False)
		]

	#~~ EventHandlerPlugin

	def on_event(self, event, payload):

		if event == Events.PRINT_DONE:
			file = os.path.basename(payload["file"])
			elapsed_time_in_seconds = payload["time"]

			import datetime
			import octoprint.util
			elapsed_time = octoprint.util.get_formatted_timedelta(datetime.timedelta(seconds=elapsed_time_in_seconds))

			title = self._settings.get(["printDone", "title"]).format(**locals())
			body = self._settings.get(["printDone", "body"]).format(**locals())

			snapshot_url = self._settings.globalGet(["webcam", "snapshot"])
			if snapshot_url:
				try:
					import urllib
					filename, headers = urllib.urlretrieve(snapshot_url)
				except Exception as e:
					self._logger.exception("Exception while fetching snapshot from webcam, sending only a note: {message}".format(message=str(e)))
				else:
					if self._send_file(filename, file, body):
						return
					self._logger.warn("Could not send a file message with the webcam image, sending only a note")

			self._send_note(title, body)

	##~~ WizardPlugin

	def is_wizard_required(self):
		return self._settings.get(["access_token"]) is None

	##~~ Softwareupdate hook

	def get_update_information(self):
		return dict(
			octobullet=dict(
				displayName="Pushbullet Plugin",
				displayVersion=self._plugin_version,

				# version check: github repository
				type="github_release",
				user="OctoPrint",
				repo="OctoPrint-Pushbullet",
				current=self._plugin_version,

				# update method: pip w/ dependency links
				pip="https://github.com/OctoPrint/OctoPrint-Pushbullet/archive/{target_version}.zip",
				dependency_links=True
			)
		)

	##~~ Internal utility methods

	def _send_note(self, title, body):
		if not self._bullet:
			return
		try:
			self._bullet.push_note(title, body)
		except:
			self._logger.exception("Error while pushing a note")
			return False
		return True

	def _send_file(self, path, file, body):
		try:
			with open(path, "rb") as pic:
				try:
					file_data = self._bullet.upload_file(pic, os.path.splitext(file)[0] + ".jpg")
				except Exception as e:
					self._logger.exception("Error while uploading snapshot, sending only a note: {}".format(str(e)))
					return False

			self._bullet.push_file(file_data["file_name"], file_data["file_url"], file_data["file_type"], body=body)
			return True
		except Exception as e:
			self._logger.exception("Exception while uploading snapshot to Pushbullet, sending only a note: {message}".format(message=str(e)))
			return False
		finally:
			try:
				os.remove(path)
			except:
				self._logger.exception("Could not remove temporary snapshot file: %s" % path)

__plugin_name__ = "Pushbullet"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PushbulletPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

