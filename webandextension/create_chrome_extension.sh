#!/bin/bash

./about.sh
mkdir ../chromeextension/

VERSION=`cat ../VERSION_PY3`
sed -e "s/VERSIONPLACEHOLDER/$VERSION/" manifest.json.in >manifest.json

for i in manifest.json \
		background.js \
		bililiteRange.js \
		collections.js \
		start.js \
		index.html \
		favicon.png \
		icon.png \
		sherpass3.svg \
		sherpass.css \
		vex-theme-wireframe.css \
		vex.css \
		aes.js \
		jquery.min.js \
		jquery.touchy.min.js \
		openpgp.js \
		openpgp.min.js \
		openpgp.worker.js \
		openpgp.worker.min.js \
		main.js \
		networkconnection.js \
		sherpass-bookmarklet.js \
		sherpass.js \
		vex.dialog.js \
		vex.js ; do
	cp $i ../chromeextension/
done
