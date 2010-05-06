#
# twitter-plugin.py
# This file is part of twitter-plugin
#
# Copyright (C) Ryuzo Yamamoto
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
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from random import getrandbits
from time import time

import rhythmdb, rb
import gobject
import gtk, gtk.glade
import gconf, gnomevfs, gnome
import os
import hmac, hashlib
import sys
import urllib
import urllib2
import urlparse

VERSION = '2.00'
gconf_keys = {
    'username': '/apps/rhythmbox/plugins/twitter-plugin/username',
    'password': '/apps/rhythmbox/plugins/twitter-plugin/password',
    'access_token': '/apps/rhythmbox/plugins/twitter-plugin/access_token',
    'access_token_secret': '/apps/rhythmbox/plugins/twitter-plugin/access_token_secret'
    }

consumer_tokens = {
    'key': '******',
    'secret': '******'
    }

twitter_urls = {
    'access_token': 'https://api.twitter.com/oauth/access_token',
    'post': 'http://twitter.com/statuses/update.json'
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

	def song_change(self, player, entry):
		#audiotwit users change the next line to True
		audioTwit = False
		artist = None
		album = None
		title = None
		if entry:
			artist = self.get_song_info(entry)[0]
			album = self.get_song_info(entry)[1]
			title = self.get_song_info(entry)[2]
		else:
			return

		response = "#nowlistening to "
		if artist != None:
			if title != None:
				response += title + " by "
			if artist.replace(" ", "") == artist: response += "#"
			response += artist
		if album != None:
			if response:
				response += " from " + album + "."
				lastFmUrl = "http://www.last.fm/search?q=" + urllib.quote(artist + " " + title)
				lastFmUrl = lastFmUrl.replace("%20", "%2B")
				lastFmUrl = self.shorten_url(lastFmUrl)
				if len(response + " " + lastFmUrl) <= 140: response += " " + lastFmUrl
			else:
				response = " the " + album + " album."
		if audioTwit == True: response = "@listensto " + artist + " - " + title
		newStatus = response
		if response and newStatus != self.lastStatus:
			self.post(newStatus)
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

	def create_account_dialog(self, dialog=None):
		if not dialog:
			glade_file = self.find_file("twitter-plugin-account.glade")
			dialog = TwitterAccountDialog (self, glade_file).get_dialog()
		dialog.present()
		return dialog

	def shorten_url(self, url):
		return urllib.urlopen("http://is.gd/api.php?longurl=" + url).read()

	def post(self, message):
		# self.create_account_dialog()
		self.setup_access_token()
	
		# build parameters to post
		params = {
			'oauth_consumer_key' : consumer_tokens['key'],
			'oauth_signature_method' : 'HMAC-SHA1',
			'oauth_timestamp' : str(int(time())),
			'oauth_nonce' : str(getrandbits(64)),
			'oauth_version' : '1.0',
			'oauth_token' : self.access_token,
			}
		params['status'] = urllib.quote(message, '')
		params['oauth_signature'] = hmac.new(
			'%s&%s' % (consumer_tokens['secret'], self.access_token_secret),
			'&'.join([
				'POST',
				urllib.quote(twitter_urls['post'], ''),
				urllib.quote('&'.join(['%s=%s' % (x, params[x])
									   for x in sorted(params)]), '')
				]),
			hashlib.sha1).digest().encode('base64').strip()
		del params['status']

		# post with oauth token
		req = urllib2.Request(twitter_urls['post'], data = urllib.urlencode(params))
		req.add_data(urllib.urlencode({'status' : message}))
		req.add_header('Authorization', 'OAuth %s' % ', '.join(
			['%s="%s"' % (x, urllib.quote(params[x], '')) for x in params]))
		res = urllib2.urlopen(req)
	
	def setup_access_token(self):
		gconf_client = gconf.client_get_default()

		if gconf_client.get_string(gconf_keys['access_token']) != None:
			self.access_token = gconf_client.get_string(gconf_keys['access_token'])
			self.access_token_secret = gconf_client.get_string(gconf_keys['access_token_secret'])
			return

		params = {
			'oauth_consumer_key' : consumer_tokens['key'],
			'oauth_signature_method' : 'HMAC-SHA1',
			'oauth_timestamp' : str(int(time())),
			'oauth_nonce' : str(getrandbits(64)),
			'oauth_version' : '1.0',
			'x_auth_mode' : 'client_auth',
			'x_auth_username' : gconf_client.get_string(gconf_keys['username']),
			'x_auth_password' : gconf_client.get_string(gconf_keys['password'])
			}
		params['oauth_signature'] = hmac.new(
			'%s&%s' % (consumer_tokens['secret'], ''),
			'&'.join([
				'POST',
				urllib.quote(twitter_urls['access_token'], ''),
				urllib.quote('&'.join(['%s=%s' % (x, params[x])
									   for x in sorted(params)]), '')
				]),
			hashlib.sha1).digest().encode('base64').strip()
		
		req = urllib2.Request(twitter_urls['access_token'], data = urllib.urlencode(params))
		res = urllib2.urlopen(req)
		token = urlparse.parse_qs(res.read())
		token_key = token['oauth_token'][0]
		token_secret = token['oauth_token_secret'][0]
		gconf_client.set_string(gconf_keys['access_token'], token_key)
		gconf_client.set_string(gconf_keys['access_token_secret'], token_secret)
		self.access_token = token_key
		self.access_token_secret = token_secret
        
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

class TwitterAccountDialog (object):
	def __init__(self, plugin, glade_file):
		self.plugin = plugin
		self.gconf = gconf.client_get_default()
		gladexml = gtk.glade.XML(glade_file)

		self.dialog = gladexml.get_widget('account_dialog')
		self.username_entry = gladexml.get_widget('username_entry')
		self.password_entry = gladexml.get_widget('password_entry')

		self.dialog.connect("response", self.dialog_response)
		self.username_entry.connect("changed", self.username_entry_changed)
		self.password_entry.connect("changed", self.password_entry_changed)

	def get_dialog (self):
		return self.dialog

	def dialog_response (self, dialog, response):
		dialog.hide()
		self.plugin.setup_access_token();

	def username_entry_changed (self, entry):
		username_text = self.username_entry.get_text()
		self.plugin.username = username_text
		
	def password_entry_changed (self, entry):
		password_text = self.password_entry.get_text()
		self.plugin.password = password_text
