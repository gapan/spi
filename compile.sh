#! /bin/sh

#use txt2tags to create the man page
(
cd man
txt2tags spi.t2t
#txt2tags apparently doesn't have an option to change the man page
#category number. It should be 8 here.
sed -i "1s/ 1 / 8 /" spi.man
)
