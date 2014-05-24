PREFIX ?= /usr/local
DESTDIR ?= /
PACKAGE_LOCALE_DIR ?= /usr/share/locale

all: man mo

man:
	txt2tags -o man/spi.man man/spi.t2t 

mo:
	for i in `ls po/*.po`; do \
		msgfmt $$i -o `echo $$i | sed "s/\.po//"`.mo; \
	done

updatepo:
	for i in `ls po/*.po`; do \
		msgmerge -UNs $$i po/spi.pot; \
	done

pot:
	xgettext -L Python -o po/spi.pot src/spi.py

clean:
	rm -f po/*.mo
	rm -f po/*.po~
	rm -f man/spi.man

install:
	install -Dm 755 src/spi $(DESTDIR)/$(PREFIX)/bin/spi
	install -Dm 755 src/spi $(DESTDIR)/usr/libexec/spi.py
	for i in `ls po/*.po | sed 's/.po//' | xargs -n1 basename` ;do \
		if [ ! -d $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES ]; then \
			mkdir -p $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES; \
		fi;\
	   	msgfmt -o $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES/spi.mo po/$$i.po; \
	done
	install -Dm 644 man/spi.man $(DESTDIR)/$(PREFIX)/man/man8/spi.8


.PHONY: all man mo updatepo pot clean install
