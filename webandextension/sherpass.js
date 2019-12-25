var SherPass = function()
{
    var _this = this;

    this.onfatalloaderror = function(msg) { }
    this.onloadingprivatekey = function(privKeyURL) { }
    this.onobtainedprivatekey = function() { }
    this.onloadingpassinfourls = function() { }
    this.onobtainedpasswordurls = function(url) { }
    this.onloadingindividualpassfiles = function(num) { }
    this.onloadedpassfile = function(i, num) { }
    this.onloadedallpassfiles = function(num) { }

    this.onfataldecrypterror = function(msg) { }
    this.onstartdecrypting = function() { }
    this.ondecryptstatus = function(numGood, numBad, numTotal) { }
    this.ondonedecrypting = function(numGood, numBad) { }

    var m_privateKeyAscii = null;
    var m_encPassData = [ ];
    var m_decPassData = [ ];
    var m_totalEntries = 0;

    var downloadKey = function(keyUrl, passDir)
    {
        NetworkConnection.get(keyUrl, function(response, statusCode, statusText)
        {
            try
            {
                if (statusCode != 200)
                    throw "Unable to obtain private key<br>(" + textToHTML(statusText) + ")";

                if (response.indexOf("-----BEGIN PGP PRIVATE KEY BLOCK-----") < 0)
                    throw "Could download specified private key file, but doesn't look like a private key";
                
                var key = openpgp.key.readArmored(response);
                if (key.keys.length == 0)
                    throw "Unable to obtain a key from the specified private key file";

                m_privateKeyAscii = response;
            }
            catch(err)
            {
                setTimeout(function() { _this.onfatalloaderror(err); }, 0);
                return; 
            }

            // Ok, looks like a private key
            _this.onobtainedprivatekey(privKeyURL);
            _this.onloadingpassinfourls();

            // Make sure the parent callback is finished
            setTimeout(function() { downloadPasswordURLs(passDir) }, 0);
        });
    }

    var downloadPasswordURLs = function(passDir)
    {
        NetworkConnection.get(passDir, function(response, statusCode, statusText)
        {
            try
            {
                if (statusCode != 200)
                    throw "Unable to obtain password file URLs from specified directory file\n(" + statusText + ")";

                // Change lines into array
                var lines = response.split("\n");
                var passFileURLs = [ ];
                for (var i = 0 ; i < lines.length ; i++)
                    passFileURLs.push(lines[i].trim())

                if (passFileURLs.length == 0)
                    throw "No files found at the specified Dropbox directory file"

                console.log(passFileURLs);

                var dbPrefix = "https://www.dropbox.com/";
                var suffix = ".pass";
                var filteredURLs = [ ];
                for (var i = 0 ; i < passFileURLs.length ; i++)
                {
                    var url = passFileURLs[i];

                    if (startsWith(url, dbPrefix, true))
                        url = "https://dl.dropboxusercontent.com/" + url.substr(dbPrefix.length);

                    var idx = url.indexOf("?");
                    if (idx >= 0)
                        url = url.substr(0, idx);

                    if (endsWith(url, suffix, true))
                        filteredURLs.push(url);
                }

                if (filteredURLs.length == 0)
                    throw "Files found at the specified Dropbox directory, but no password files (have .pass extension)";

                m_totalEntries = filteredURLs.length;

                _this.onobtainedpasswordurls(dbPrefix + passDir);
                _this.onloadingindividualpassfiles(filteredURLs.length);

                // Make sure the parent callback is finished
                setTimeout(function() { downloadPasswordFiles(filteredURLs); }, 0);
            }
            catch(err)
            {
                setTimeout(function() { _this.onfatalloaderror(err); }, 0);
            }
        });
    }

    var downloadPasswordFiles = function(urls)
    {
        var encryptedPasswordData = [ ];
        var getHandler = function(idx, urls)
        {
            return function()
            {
                NetworkConnection.get(urls[idx], function(response, statusCode, statusText)
                {
                    if (statusCode != 200)
                    {
                        var message = "Unable to download password file:\n" + urls[idx] + "\n(" + statusText + ")";
                        setTimeout(function() { _this.onfatalloaderror(message); }, 0);
                        return;
                    }

                    encryptedPasswordData.push(response);
                    
                    idx++;
                    _this.onloadedpassfile(idx, urls.length);

                    if (idx >= urls.length)
                    {
                        m_encPassData = encryptedPasswordData;
                        setTimeout(function() { _this.onloadedallpassfiles(urls.length); }, 0);
                        return;
                    }
        
                    var h = getHandler(idx, urls);
                    setTimeout(h, 0);
                });
            }
        }

        var h = getHandler(0, urls);
        h();
    }

    this.load = function(privKeyURL, passDirURL)
    {
        setTimeout(function()
        {
            try
            {
                var dbPrefix = "https://www.dropbox.com/";
                if (!privKeyURL || !startsWith(privKeyURL, dbPrefix, true))
                    throw "No private key URL specified, or not a Dropbox URL";
                if (!passDirURL || !startsWith(passDirURL, dbPrefix, true))
                    throw "No password info directory specified, or not a Dropbox URL";
            }
            catch(err)
            {
                var message = "Couldn't load password info:\n" + err;

                setTimeout(function() { _this.onfatalloaderror(message); }, 0);
            }

            var downPrefix = "https://dl.dropboxusercontent.com/";
            var keyUrl = downPrefix + privKeyURL.substr(dbPrefix.length);
            var passDir = downPrefix + passDirURL.substr(dbPrefix.length);

            _this.onloadingprivatekey();

            setTimeout(function() { downloadKey(keyUrl, passDir); }, 0);
        }, 0);
    }

    this.decrypt = function(passPhrase)
    {
        m_decPassData = [ ];
        if (m_encPassData.length == 0)
        {
            setTimeout(function() { _this.onfataldecrypterror("No password info loaded, nothing to decrypt"); }, 0);
            return;
        }

        _this.onstartdecrypting();
        setTimeout(function() { decryptAll(passPhrase); }, 0);
    }

    var decryptAll = function(passPhrase)
    {
        var privateKey = openpgp.key.readArmored(m_privateKeyAscii);
            
        privateKey.keys[0].decrypt(passPhrase);

        var options = {
            message: null, // will be filled in later
            privateKey: privateKey.keys[0]
        };

        var getHandler = function(idx, good, bad, privateKey)
        {
            var continueDecryption = function()
            {
                _this.ondecryptstatus(good, bad, m_encPassData.length);

                idx++;
                if (idx >= m_encPassData.length)
                {
                    setTimeout(function() { _this.ondonedecrypting(good, bad); }, 0);
                    return;
                }

                var h = getHandler(idx, good, bad, privateKey);
                setTimeout(h, 0);
            }

            return function()
            {
                options.message = openpgp.message.readArmored(m_encPassData[idx]);

                openpgp.decrypt(options).then(function(obj)
                {
                    // We've prefixed it with some random data, remove it again
                    var result = obj.data;
                    var i = result.indexOf("{");

                    if (i >= 0)
                    {
                        m_decPassData.push(result.substr(i));
                        good++;
                    }
                    else
                        bad++;

                    continueDecryption();
                })
                .catch(function(err)
                {
                    bad++;
                    continueDecryption();
                });
            }
        }

        var h = getHandler(0, 0, 0, privateKey);
        setTimeout(h, 0);
    }

    this.getNumberOfDecryptedEntries = function()
    {
        return m_decPassData.length;
    }

    this.getTotalNumberOfEntries = function()
    {
        return m_totalEntries;
    }

    this.getDecryptedEntry = function(idx)
    {
        return m_decPassData[idx];
    }

    this.decryptString = function(encMsg, passPhrase, callback)
    {
        var privateKey = openpgp.key.readArmored(m_privateKeyAscii);
            
        privateKey.keys[0].decrypt(passPhrase);

        var msg = openpgp.message.readArmored(encMsg);
            
        openpgp.decryptMessage(privateKey.keys[0], msg, function(err, result)
        {
            if (err)
            {
                callback(null);
                return;
            }
            var realResult = result.substr(16);
            callback(realResult);
        });
    }
}
