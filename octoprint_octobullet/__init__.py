# coding=utf-8
from __future__ import absolute_import

__author__ = "Gina Häußge <gina@octoprint.org>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'
__copyright__ = "Copyright (C) 2015 The OctoPrint Project - Released under terms of the AGPLv3 License"

import os

import time
import traceback
import octoprint.util
import octoprint.plugin

from octoprint.events import Events
from octoprint.server import admin_permission
from flask.ext.login import current_user

import pushbullet
import flask

import sarge

class PushbulletPlugin(octoprint.plugin.EventHandlerPlugin,
		       octoprint.plugin.ProgressPlugin,
                       octoprint.plugin.SettingsPlugin,
                       octoprint.plugin.StartupPlugin,
                       octoprint.plugin.TemplatePlugin,
                       octoprint.plugin.SimpleApiPlugin,
                       octoprint.plugin.AssetPlugin):

	def __init__(self):
		self._bullet = None
		self._channel = None
		self._sender = None
		self._interval_percent = 5
		self._message_count = 0
		self._quiet_time_sec = 1800
		self._last_message = 0
		self._time_remaining_format = "{days:d}d {hours:02d}h {minutes:02d}min"
		self._eta_strftime = "%H:%M %d-%m"

	def _connect_bullet(self, apikey, channel_name=""):
		self._bullet, self._sender = self._create_sender(apikey, channel_name)

	#~~ progress message helpers
	def _sanitize_current_data(self, currentData):
		if (currentData["progress"]["printTimeLeft"] == None):
			currentData["progress"]["printTimeLeft"] = currentData["job"]["estimatedPrintTime"]
		if (currentData["progress"]["printTimeLeft"] == None):
			self._logger.debug("Still got no print time {}".format(currentData["progress"]["printTimeLeft"]))
			currentData["progress"]["printTimeLeft"] = 1000
		if (currentData["progress"]["filepos"] == None):
			currentData["progress"]["filepos"] = 0
		if (currentData["progress"]["printTime"] == None):
			currentData["progress"]["printTime"] = currentData["job"]["estimatedPrintTime"]

		currentData["progress"]["printTimeLeftString"] = "No ETL yet"
		currentData["progress"]["printTimeString"] = "Not started yet"
		currentData["progress"]["ETA"] = "No ETA yet"
		#Add additional data
		try:
			currentData["progress"]["printTimeLeftString"] = self._get_time_from_seconds(currentData["progress"]["printTimeLeft"])
			currentData["progress"]["printTimeString"] = self._get_time_from_seconds(currentData["progress"]["printTime"])
			currentData["progress"]["ETA"] = time.strftime(self._eta_strftime, time.localtime(time.time() + currentData["progress"]["printTimeLeft"]))
		except Exception as e:
			self._logger.warning("Caught an exception trying to parse data: {0}\n Error is: {1}\nTraceback:{2}".format(currentData,e,traceback.format_exc()))
			
		return currentData

	def _get_time_from_seconds(self, seconds):
		days, seconds = divmod(seconds, 86400)
		hours, seconds = divmod(seconds, 3600)
		minutes, seconds = divmod(seconds, 60)
		return self._time_remaining_format.format(**locals())
	
	#~~ PrintProgressPlugin
	def on_print_progress(self, storage, path, progress):
		if(progress % self._interval_percent == 0):
			self._quiet_time_sec = int(self._settings.get(["quiet_minutes"])) * 60
			if self._quiet_time_sec == 0:
				self._quiet_time_sec = 7* 24 * 3600 # use a week if we don't want messages
			self._logger.debug("Progress: {} {} {}".format(storage,path,progress))
			try:
				currentData = self._printer.get_current_data()
				currentData = self._sanitize_current_data(currentData)
			except Exception as e:
				self._logger.info("Caught an exception {0}\nTraceback:{1}".format(e,traceback.format_exc()))

			self._logger.debug("Remaining {} ({})".format(currentData["progress"]["printTimeLeftString"],currentData["progress"]["printTimeLeftOrigin"]))
			self._logger.debug("Total Print time {}".format(currentData["progress"]["printTimeString"]))
			self._logger.debug("Estimated Completion  {}".format(currentData["progress"]["ETA"]))
			# first 3 messages, re-calculate interval (not first, analysis estimate can be inacurate)
			self._message_count += 1
			if self._message_count < 4 and self._message_count > 1:
				total_job = currentData["progress"]["printTime"] + currentData["progress"]["printTimeLeft"]
				self._interval_percent = int(100 * self._quiet_time_sec / total_job)
				if self._interval_percent == 0:
					self._interval_percent = 1
				self._logger.debug("Set interval to {} percent count {} Total estimated {}".format(self._interval_percent, self._message_count,total_job))
				
			# Suppress message if print is nearly done or interval calculation is off
			need_message = True
			if(currentData["progress"]["printTime"] < (self._quiet_time_sec * 0.5  + self._last_message)):
				self._logger.debug("Skip message {} since print is only been running {} since last at {}".format(self._message_count, currentData["progress"]["printTime"], self._last_message))
				need_message = False
					 
			if(currentData["progress"]["printTimeLeft"] < self._quiet_time_sec):
				self._logger.debug("Skip trailing message since print is nearly done {} of {}".format(currentData["progress"]["printTimeLeft"], self._quiet_time_sec))
				need_message = False

			if need_message:
				self._last_message = currentData["progress"]["printTime"]
				path = currentData["job"]["file"]["path"]
				eta = currentData["progress"]["ETA"]
				print_time = currentData["progress"]["printTimeString"]
				remaining = currentData["progress"]["printTimeLeftString"]
			
				title = self._settings.get(["printProgress", "title"]).format(**locals())
				body = self._settings.get(["printProgress", "body"]).format(**locals())
				filename = os.path.splitext(path)[0] + ".jpg"

				self._send_message_with_webcam_image(title, body, filename=filename)
			
													    
	
	#~~ StartupPlugin

	def on_after_startup(self):
		self._connect_bullet(self._settings.get(["access_token"]),
		                     self._settings.get(["push_channel"]))

	#~~ SettingsPlugin

	def on_settings_load(self):
		data = octoprint.plugin.SettingsPlugin.on_settings_load(self)

		# only return our restricted settings to admin users - this is only needed for OctoPrint <= 1.2.16
		restricted = ("access_token", "push_channel")
		for r in restricted:
			if r in data and (current_user is None or current_user.is_anonymous() or not current_user.is_admin()):
				data[r] = None

		return data

	def on_settings_save(self, data):
		octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

		import threading
		thread = threading.Thread(target=self._connect_bullet, args=(self._settings.get(["access_token"]),
		                                                             self._settings.get(["push_channel"])))
		thread.daemon = True
		thread.start()

	def get_settings_defaults(self):
		return dict(
			quiet_minutes = 0,
			access_token=None,
			push_channel=None,
			printDone=dict(
				title="Print job finished",
				body="{file} finished printing in {elapsed_time}"
			),
			printProgress=dict(
				title="Print job {progress}% complete",
				body="{progress}% {path}\n{print_time}\n{remaining} left\n{eta} finish"
			)
		)

	def get_settings_restricted_paths(self):
		# only used in OctoPrint versions > 1.2.16
		return dict(admin=[["access_token"], ["push_channel"]])

	#~~ TemplatePlugin API

	def get_template_configs(self):
		return [
			dict(type="settings", name="Pushbullet", custom_bindings=True)
		]

	#~~ AssetPlugin API

	def get_assets(self):
		return dict(js=["js/octobullet.js"])

	#~~ SimpleApiPlugin

	def get_api_commands(self):
		return dict(test=["token"])

	def on_api_command(self, command, data):
		if not admin_permission.can():
			return flask.make_response("Insufficient rights", 403)

		if not command == "test":
			return

		message = data.get("message", "Testing, 1, 2, 3, 4...")
		token = data["token"]
		channel = data.get("channel", None)

		_, sender = self._create_sender(token, channel)

		result = self._send_message_with_webcam_image("Test from the OctoPrint PushBullet Plugin", message, sender=sender)
		return flask.make_response(flask.jsonify(result=result))

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
			filename = os.path.splitext(file)[0] + ".jpg"

			self._send_message_with_webcam_image(title, body, filename=filename)

		if event == Events.PRINT_STARTED:
			self._interval_percent = 5
			self._message_count = 0
			self._last_message = 0


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

				# update method: pip
				pip="https://github.com/OctoPrint/OctoPrint-Pushbullet/archive/{target_version}.zip"
			)
		)

	##~~ Internal utility methods

	def _send_message_with_webcam_image(self, title, body, filename=None, sender=None):
		if filename is None:
			import random, string
			filename = "{}.jpg".format(random.choice(string.ascii_letters) * 16)

		if sender is None:
			sender = self._sender

		if not sender:
			return False

		snapshot_url = self._settings.global_get(["webcam", "snapshot"])
		if snapshot_url:
			try:
				import urllib
				snapshot_path, headers = urllib.urlretrieve(snapshot_url)
			except Exception as e:
				self._logger.exception(
					"Exception while fetching snapshot from webcam, sending only a note: {message}".format(
						message=str(e)))
			else:
				# ffmpeg can't guess file type it seems
				os.rename(snapshot_path, snapshot_path + ".jpg")
				snapshot_path += ".jpg"

				# flip or rotate as needed
				self._process_snapshot(snapshot_path)

				if self._send_file(sender, snapshot_path, filename, body):
					return True
				self._logger.warn("Could not send a file message with the webcam image, sending only a note")

		return self._send_note(sender, title, body)

	def _send_note(self, sender, title, body):
		try:
			sender.push_note(title, body)
		except:
			self._logger.exception("Error while pushing a note")
			return False
		return True

	def _send_file(self, sender, path, filename, body):
		try:
			with open(path, "rb") as pic:
				try:
					file_data = self._bullet.upload_file(pic, filename)
				except Exception as e:
					self._logger.exception("Error while uploading snapshot, sending only a note: {}".format(str(e)))
					return False

			sender.push_file(file_data["file_name"], file_data["file_url"], file_data["file_type"], body=body)
			return True
		except Exception as e:
			self._logger.exception("Exception while uploading snapshot to Pushbullet, sending only a note: {message}".format(message=str(e)))
			return False
		finally:
			try:
				os.remove(path)
			except:
				self._logger.exception("Could not remove temporary snapshot file {}".format(path))

	def _create_sender(self, token, channel=None):
		try:
			bullet = pushbullet.PushBullet(token)
			sender = bullet

			# Setup channel object if channel setting is present
			if channel:
				for channel_obj in self._bullet.channels:
					if channel_obj.channel_tag == channel:
						sender = channel_obj
						self._logger.info("Connected to PushBullet on channel {}".format(channel))
						break
				else:
					self._logger.warn("Could not find channel {}, please check your configuration!".format(channel))

			self._logger.info("Connected to PushBullet")
			return bullet, sender
		except:
			self._logger.exception("Error while instantiating PushBullet")
			return None, None

	def _process_snapshot(self, snapshot_path, pixfmt="yuv420p"):
		hflip  = self._settings.global_get_boolean(["webcam", "flipH"])
		vflip  = self._settings.global_get_boolean(["webcam", "flipV"])
		rotate = self._settings.global_get_boolean(["webcam", "rotate90"])
		ffmpeg = self._settings.global_get(["webcam", "ffmpeg"])
		
		if not ffmpeg or not os.access(ffmpeg, os.X_OK) or (not vflip and not hflip and not rotate):
			return

		ffmpeg_command = [ffmpeg, "-y", "-i", snapshot_path]

		rotate_params = ["format={}".format(pixfmt)] # workaround for foosel/OctoPrint#1317
		if rotate:
			rotate_params.append("transpose=2") # 90 degrees counter clockwise
		if hflip:
			rotate_params.append("hflip") 		# horizontal flip
		if vflip:
			rotate_params.append("vflip")		# vertical flip

		ffmpeg_command += ["-vf", sarge.shell_quote(",".join(rotate_params)), snapshot_path]
		self._logger.info("Running: {}".format(" ".join(ffmpeg_command)))

		p = sarge.run(ffmpeg_command, stdout=sarge.Capture(), stderr=sarge.Capture())
		if p.returncode == 0:
			self._logger.info("Rotated/flipped image with ffmpeg")
		else:
			self._logger.warn("Failed to rotate/flip image with ffmpeg, "
			                  "got return code {}: {}, {}".format(p.returncode,
			                                                      p.stdout.text,
			                                                      p.stderr.text))

__plugin_name__ = "Pushbullet"
def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = PushbulletPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		"octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}

