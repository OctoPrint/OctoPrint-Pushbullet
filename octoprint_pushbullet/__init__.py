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
                       octoprint.plugin.TemplatePlugin):

	def __init__(self):
		self._bullet = None

	def _connect_bullet(self, apikey):
		if apikey:
			try:
				self._bullet = pushbullet.PushBullet(apikey)
				return True
			except:
				self._logger.exception("Error while instantiating PushBullet")
				return False

	#~~ StartupPlugin

	def on_after_startup(self):
		self._connect_bullet(self._settings.get(["apikey"]))

	#~~ SettingsPlugin

	def on_settings_save(self, data):
		super(PushbulletPlugin, self).on_settings_save(data)

		import threading
		threading.Thread(target=self._connect_bullet, args=(self._settings.get(["apikey"]),))

	def get_settings_defaults(self):
		return dict(
			apikey=None,
			printDone=dict(
				title="Print job finished",
				body="{file} finished printing in {elapsed_time}"
			)
		)

	#~~ TemplatePlugin API

	def get_template_configs(self):
		return [
			dict(type="settings", name="Pushbullet", custom_bindings=False)
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
					self._logger.warn("Exception while fetching snapshot from webcam, sending only a note: {message}".format(message=str(e)))
				else:
					if self._send_file(filename, file, body):
						return
					self._logger.warn("Could not send a file message with the webcam image, sending only a note")

			self._send_note(title, body)


	def _send_note(self, title, body):
		if not self._bullet:
			return
		success, push = self._bullet.push_note(title, body)
		return success

	def _send_file(self, path, file, body):
		try:
			with open(path, "rb") as pic:
				success, file_data = self._bullet.upload_file(pic, os.path.splitext(file)[0] + ".jpg")

			if not success:
				return False

			success, push = self._bullet.push_file(file_data["file_name"], file_data["file_url"], file_data["file_type"], body=body)
			return success
		except:
			return False
		finally:
			try:
				os.remove(path)
			except:
				self._logger.exception("Could not remove temporary snapshot file: %s" % path)

__plugin_name__ = "Pushbullet"
__plugin_implementation__ = PushbulletPlugin()
