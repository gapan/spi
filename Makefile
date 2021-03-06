PREFIX ?= /usr/local
DESTDIR ?= /
PACKAGE_LOCALE_DIR ?= /usr/share/locale

.PHONY: all
all: man mo

.PHONY: man
man:
	txt2tags -o man/spi.man man/spi.t2t 

.PHONY: mo
mo:
	for i in `ls po/*.po`; do \
		msgfmt $$i -o `echo $$i | sed "s/\.po//"`.mo; \
	done

.PHONY: updatepo
updatepo:
	for i in `ls po/*.po`; do \
		msgmerge -UNs $$i po/spi.pot; \
	done

.PHONY: pot
pot:
	xgettext -L Python -o po/spi.pot src/spi.py

.PHONY: clean
clean:
	rm -f po/*.mo
	rm -f po/*.po~
	rm -f man/spi.man

.PHONY: install
install:
	install -Dm 755 src/spi $(DESTDIR)/$(PREFIX)/bin/spi
	for i in `ls po/*.po | sed 's/.po//' | xargs -n1 basename` ;do \
		if [ ! -d $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES ]; then \
			mkdir -p $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES; \
		fi;\
	   	msgfmt -o $(DESTDIR)$(PACKAGE_LOCALE_DIR)/$$i/LC_MESSAGES/spi.mo po/$$i.po; \
	done
	install -Dm 644 man/spi.man $(DESTDIR)/$(PREFIX)/man/man8/spi.8

.PHONY: tx-pull
tx-pull:
	tx pull -a
	@for i in `ls po/*.po`; do \
		msgfmt --statistics $$i 2>&1 | grep "^0 translated" > /dev/null \
			&& rm $$i || true; \
	done
	@rm -f messages.mo

.PHONY: tx-pull-f
tx-pull-f:
	tx pull -a -f
	@for i in `ls po/*.po`; do \
		msgfmt --statistics $$i 2>&1 | grep "^0 translated" > /dev/null \
			&& rm $$i || true; \
	done
	@rm -f messages.mo

.PHONY: stat
stat:
	@for i in `ls po/*.po`; do \
		echo "Statistics for $$i:"; \
		msgfmt --statistics $$i 2>&1; \
		echo; \
	done
	@rm -f messages.mo

