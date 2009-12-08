
INSTALL_PATH=/usr/lib/rhythmbox/plugins/twitter-plugin/

install:
	install -d $(DESTDIR)$(INSTALL_PATH)
	install -t $(DESTDIR)$(INSTALL_PATH) -m644 twitter-plugin-prefes.glade twitter-plugin.py twitter-plugin.rb-plugin README

clean:
    # none
