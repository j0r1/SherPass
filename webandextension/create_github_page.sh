#!/bin/bash

./about.sh

for i in index.html \
		about.html \
		favicon.png \
		icon.png \
		icon2.png \
		sherpass3.svg \
		sherpass.css \
		vex-theme-wireframe.css \
		vex.css \
		aes.js \
		bililiteRange.js \
		collections.js \
		jquery.min.js \
		jquery.touchy.min.js \
		main.js \
		networkconnection.js \
		openpgp.js \
		openpgp.min.js \
		openpgp.worker.js \
		openpgp.worker.min.js \
		sherpass-bookmarklet.js \
		sherpass.js \
		vex.dialog.js \
		vex.js ; do
	cp $i ../docs/
done
