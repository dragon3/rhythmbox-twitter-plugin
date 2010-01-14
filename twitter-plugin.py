#
# twitter-plugin.py
# This file is part of twitter-plugin
# $Id: /mirror/codecheck.in/platform/rhythmbox/twitter-plugin/twitter-plugin.py 14100 2009-03-08T14:06:27.637680Z dragon3  $
#
# Copyright (C) 2008 - 2009 Ryuzo Yamamoto
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import rhythmdb, rb
import gobject
import gtk, gtk.glade
import gconf, gnomevfs, gnome
import twitter
import os

gconf_keys = {	'username': '/apps/rhythmbox/plugins/twitter-plugin/username',
		'password': '/apps/rhythmbox/plugins/twitter-plugin/password'
		}

class TwitterPlugin(rb.Plugin):

	def __init__(self):
		rb.Plugin.__init__(self)
			
	def activate(self, shell):
		self.shell = shell
		player = shell.get_player()

		
		self.psc_id = player.connect ('playing-song-changed', self.song_change)
		self.lastStatus = ""
		if player.get_playing_entry():
			self.song_change (player, player.get_playing_entry())
		self.db = None
	
	def deactivate(self, shell):
		self.shell.get_player().disconnect (self.psc_id)
		del self.psc_id
		if self.db:
			del self.db
		del self.shell
		del self.lastStatus

	def get_twitter_api(self):
		username = gconf.client_get_default().get_string(gconf_keys['username'])
		password = gconf.client_get_default().get_string(gconf_keys['password'])

		api = twitter.Api(username, password);
		api.SetSource('rhythmboxtwitterplugin')
		api.SetXTwitterHeaders('Rhythmbox twitter-plugin', 'http://trac.codecheck.in/share/browser/platform/rhythmbox/twitter-plugin', '0.1')
		return api
		
	def song_change(self, player, entry):
		artist = None
		album = None
		title = None
		if entry:
			artist = self.get_song_info(entry)[0]
			album = self.get_song_info(entry)[1]
			title = self.get_song_info(entry)[2]
		response = ""
		if artist != None:
			response = artist
		# if album != None:
		#	if response:
		#		response += " - " + album
		#	else:
		#		response = album
		# elif title != None:
		if title != None:
 			if response:
 				response += " - " + title
 			else:
 				response = title
		newStatus = 'Listening to '+response
		if response and newStatus != self.lastStatus:
			self.get_twitter_api().PostUpdate(newStatus)
			self.lastStatus = newStatus
		
	def get_song_info(self, entry):
		self.db = self.shell.get_property('db')
		artist = self.db.entry_get (entry, rhythmdb.PROP_ARTIST) or None
		album = self.db.entry_get (entry, rhythmdb.PROP_ALBUM) or None
		title = self.db.entry_get(entry,rhythmdb.PROP_TITLE) or None
		return (artist,album,title)

	def create_configure_dialog(self, dialog=None):
		if not dialog:
			glade_file = self.find_file("twitter-plugin-prefes.glade")
			dialog = TwitterConfigureDialog (glade_file).get_dialog()
		dialog.present()
		return dialog
	
class TwitterConfigureDialog (object):
	def __init__(self, glade_file):
		self.gconf = gconf.client_get_default()
		gladexml = gtk.glade.XML(glade_file)

		self.dialog = gladexml.get_widget('preferences_dialog')
		self.username_entry = gladexml.get_widget('username_entry')
		self.password_entry = gladexml.get_widget('password_entry')

		username_text = self.gconf.get_string(gconf_keys['username']) or ""
		password_text = self.gconf.get_string(gconf_keys['password']) or ""
		
		self.username_entry.set_text(username_text)
		self.password_entry.set_text(password_text)

		self.dialog.connect("response", self.dialog_response)
		self.username_entry.connect("changed", self.username_entry_changed)
		self.password_entry.connect("changed", self.password_entry_changed)

	def get_dialog (self):
		return self.dialog

	def dialog_response (self, dialog, response):
		dialog.hide()

	def username_entry_changed (self, entry):
		username_text = self.username_entry.get_text()
		self.gconf.set_string(gconf_keys['username'], username_text)
		
	def password_entry_changed (self, entry):
		password_text = self.password_entry.get_text()
		self.gconf.set_string(gconf_keys['password'], password_text)
