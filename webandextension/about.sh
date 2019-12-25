#!/bin/bash

(
cat << EOF
<!doctype html>
<html itemscope itemtype="http://schema.org/Product">
    <head>
    	<title>SherPass</title>
        <link rel="stylesheet" href="sherpass.css">
        <link rel="shortcut icon" href="/favicon.png" type="image/png">

	<meta property="og:image" content="https://sherpass-lite.appspot.com/icon2.png" />
	<meta property="og:url" content="https://sherpass-lite.appspot.com/about.html" />
	<meta property="og:description" content="Manage your passwords, share them if you need to." />
	<meta property="og:site_name" content="SherPass" />
	<meta property="og:title" content="SherPass" />
	
	<meta itemprop="name" content="SherPass">
	<meta itemprop="description" content="Manage your passwords, share them if you need to.">
	<meta itemprop="image" content="https://sherpass-lite.appspot.com/icon.png">
	<style>
		body {
   			line-height: 1.6;
		}
	</style>
    </head>
    <body>

	<div id="logo2div">
    		<img id="logo2" src="sherpass3.svg" onclick="window.open('/','_self');" /><br>
	</div>

EOF

VERSION=`cat ../VERSION_PY3`
sed -e "s/VERSIONPLACEHOLDER/$VERSION/g" about.txt | Markdown.pl

cat << EOF

    </body>
</html>
EOF

) > about.html
