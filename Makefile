
INSTALL_PATH=${HOME}/.gnome2/rhythmbox/plugins/twitter-plugin

install:
	install -d $(DESTDIR)$(INSTALL_PATH)
	install -t $(DESTDIR)$(INSTALL_PATH) -m644 twitter-plugin-pin.glade twitter-plugin-prefes.glade twitter-plugin.py  twitter-plugin.rb-plugin README
	install -d $(DESTDIR)$(INSTALL_PATH)/oauth2
	install -t $(DESTDIR)$(INSTALL_PATH)/oauth2 -m644 oauth2/__init__.py
	install -d $(DESTDIR)$(INSTALL_PATH)/icon
	install -t $(DESTDIR)$(INSTALL_PATH)/icon icon/32.png icon/accept.png icon/music.png icon/user.png

clean:
    # none
