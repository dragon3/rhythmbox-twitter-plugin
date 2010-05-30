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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.	If not, see <http://www.gnu.org/licenses/>.
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
import base64
import webbrowser

from twitter import Api, User

import urlparse
import oauth2 as oauth

VERSION = '1.02'

gconf_keys = {
	'access_token': '/apps/rhythmbox/plugins/twitter-plugin/access_token',
	'access_token_secret': '/apps/rhythmbox/plugins/twitter-plugin/access_token_secret',
	'screen_name': '/apps/rhythmbox/plugins/twitter-plugin/screen_name',
	}

CONSUMER_TOKENS = {
	'key': 'NXlrU3psc1VIWjZkaHJhRTB5WG01UQ==',
	'secret': 'RFBEbXRoVzRJQXUxcUdrSmV2VTdDc2RhS3FUdmdPN2tDMFlEY3g1OG1J',
	}

TWITTER_OAUTH_URL_BASE = 'https://api.twitter.com/oauth'
TWITTER_URLS = {
	'request_token': TWITTER_OAUTH_URL_BASE + '/request_token',
	'authorize': TWITTER_OAUTH_URL_BASE + '/authorize',
	'access_token': TWITTER_OAUTH_URL_BASE + '/access_token',
	'authenticate': 'http://twitter.com/oauth/authenticate',
	'post': 'http://twitter.com/statuses/update.json'
	}

class TwitterPlugin(rb.Plugin):

	def __init__(self):
		rb.Plugin.__init__(self)
			
	def activate(self, shell):
		self.shell = shell
		player = shell.get_player()

		self.lastStatus = ""
		self.db = None

		# consumer tokens
		self.consumer_key = self.decode_token(CONSUMER_TOKENS['key'])
		self.consumer_secret = self.decode_token(CONSUMER_TOKENS['secret'])

		# twitter access info
		self.access_token = None
		self.access_token_secret = None
		self.screen_name = None
		gconf_client = gconf.client_get_default()
		if gconf_client.get_string(gconf_keys['access_token']) != None:
			self.access_token = gconf_client.get_string(gconf_keys['access_token'])
			self.access_token_secret = gconf_client.get_string(gconf_keys['access_token_secret'])
			self.screen_name = gconf_client.get_string(gconf_keys['screen_name'])

		# oauth.Consumer object
		self.consumer = None

		# dialog opened
		self.configure_dialog = None

		self.psc_id = player.connect ('playing-song-changed', self.song_change)
		if player.get_playing_entry():
			self.song_change (player, player.get_playing_entry())

	def deactivate(self, shell):
		self.shell.get_player().disconnect (self.psc_id)
		del self.psc_id

		del self.lastStatus
		if self.db:
			del self.db

		if self.consumer:
			del self.consumer
		if self.consumer_key:
			del self.consumer_key
		if self.consumer_secret:
			del self.consumer_secret
		if self.access_token:
			del self.access_token
		if self.access_token_secret:
			del self.access_token_secret
		if self.screen_name:
			del self.screen_name

		del self.shell

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
			self.configure_dialog = TwitterConfigureDialog (self, glade_file)
			dialog = self.configure_dialog.get_dialog()
		dialog.present()
		return dialog

	def create_pin_dialog(self, dialog=None, request_token=None):
		if not dialog:
			glade_file = self.find_file("twitter-plugin-pin.glade")
			dialog = TwitterPinDialog (self, glade_file, request_token).get_dialog()
		dialog.present()
		return dialog

	def shorten_url(self, url):
		return urllib.urlopen("http://is.gd/api.php?longurl=" + url).read()

	def post(self, message):
		if self.access_token == None:
			self.prepare_twitter_account()

		params = {
			'oauth_consumer_key' : self.consumer_key,
			'oauth_signature_method' : 'HMAC-SHA1',
			'oauth_timestamp' : str(int(time())),
			'oauth_nonce' : str(getrandbits(64)),
			'oauth_version' : '1.0',
			'oauth_token' : self.access_token,
			}
		params['status'] = urllib.quote(message, '')
		params['oauth_signature'] = hmac.new(
			'%s&%s' % (self.consumer_secret, self.access_token_secret),
			'&'.join([
				'POST',
				urllib.quote(TWITTER_URLS['post'], ''),
				urllib.quote('&'.join(['%s=%s' % (x, params[x])
									   for x in sorted(params)]), '')
				]),
			hashlib.sha1).digest().encode('base64').strip()
		del params['status']

		# post with oauth token
		req = urllib2.Request(TWITTER_URLS['post'], data = urllib.urlencode(params))
		req.add_data(urllib.urlencode({'status' : message}))
		req.add_header('Authorization', 'OAuth %s' % ', '.join(
			['%s="%s"' % (x, urllib.quote(params[x], '')) for x in params]))
		res = urllib2.urlopen(req)

	######################################################################
	# internal utility method
	######################################################################
	
	def prepare_twitter_account(self):
		gconf_client = gconf.client_get_default()
		self.connect_twitter_account()

	def connect_twitter_account(self):
		self.consumer = oauth.Consumer(self.consumer_key, self.consumer_secret)
		client = oauth.Client(self.consumer)
		request_token = self.get_request_token(client)

		authorization_url = "%s?oauth_token=%s" % (TWITTER_URLS['authorize'], request_token['oauth_token'])
		# print >> sys.stderr, "authorization_url: " + authorization_url
		webbrowser.open_new(authorization_url)

		self.create_pin_dialog(request_token=request_token)
		
	def get_access_token(self, pin, request_token):
		token = oauth.Token(request_token['oauth_token'],
							request_token['oauth_token_secret'])
		token.set_verifier(pin)
		client = oauth.Client(self.consumer, token)
		resp, content = client.request(TWITTER_URLS['access_token'], "POST")
		access_token = dict(urlparse.parse_qsl(content))

		# save gconf
		gconf_client = gconf.client_get_default()
		gconf_client.set_string(gconf_keys['access_token'], access_token['oauth_token'])
		gconf_client.set_string(gconf_keys['access_token_secret'], access_token['oauth_token_secret'])
		gconf_client.set_string(gconf_keys['screen_name'], access_token['screen_name'])

		self.access_token = access_token['oauth_token']
		self.access_token_secret = access_token['oauth_token_secret']
		self.screen_name = access_token['screen_name']

		if self.configure_dialog:
			self.configure_dialog.update_username()
			self.configure_dialog = None

	def get_request_token(self, client):
		resp, content = client.request(TWITTER_URLS['request_token'], "GET")
		if resp['status'] != '200':
			raise Exception("Invalid response %s." % resp['status'])
		return dict(urlparse.parse_qsl(content))
		
	def decode_token(self, token):
		return base64.b64decode(token)

class TwitterConfigureDialog (object):
	def __init__(self, plugin, glade_file):
		self.plugin = plugin
		self.gconf = gconf.client_get_default()
		gladexml = gtk.glade.XML(glade_file)

		self.dialog = gladexml.get_widget('preferences_dialog')
		self.username_button = gladexml.get_widget('username_button')
		self.username_button_label = gladexml.get_widget('username_button_label')
		self.username_button_image = gladexml.get_widget('username_button_image')
		if plugin.screen_name:
			self.username_button_image.set_visible(False)
			self.username_button_label.set_label(plugin.screen_name)

		self.dialog.connect("response", self.dialog_response)
		self.username_button.connect("pressed", self.connect)

	def update_username (self):
		self.username_button_image.set_visible(True)
		self.username_button_label.set_label(self.plugin.screen_name)
		
	def get_dialog (self):
		return self.dialog

	def connect (self, connect_button):
		self.plugin.connect_twitter_account()

	def dialog_response (self, dialog, response):
		dialog.hide()

class TwitterPinDialog (object):
	def __init__(self, plugin, glade_file, request_token):
		self.plugin = plugin
		self.request_token = request_token
		self.gconf = gconf.client_get_default()
		gladexml = gtk.glade.XML(glade_file)

		self.dialog = gladexml.get_widget('pin_dialog')
		self.pin_entry = gladexml.get_widget('pin_entry')

		self.dialog.connect("response", self.dialog_response)

	def get_dialog (self):
		return self.dialog

	def dialog_response (self, dialog, response):
		pin = self.pin_entry.get_text()
		if pin != None:
			self.plugin.get_access_token(pin, self.request_token)
		dialog.hide()
