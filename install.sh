#!/bin/sh

install -d -m 755 $DESTDIR/usr/bin
install -m 755 src/spi $DESTDIR/usr/bin/
install -d -m 755 $DESTDIR/usr/man/man8
install -m 644 man/spi.man $DESTDIR/usr/man/man8/spi.8
