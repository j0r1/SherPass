function Log(x)
{
    console.log(x)
}

var startsWith = function(s, start, caseInsensitive)
{
    if (caseInsensitive)
    {
        if (s.substr(0, start.length).toLowerCase() == start.toLowerCase())
            return true;
    }
    else
    {
        if (s.substr(0, start.length) == start)
            return true;
    }
    return false;
}

var endsWith = function(s, end, caseInsensitive)
{
    var l = s.length;

    if (l < end.length)
        return false;

    var startIdx = l-end.length;

    if (caseInsensitive)
    {
        if (s.substr(startIdx).toLowerCase() == end.toLowerCase())
            return true;
    }
    else
    {
        if (s.substr(startIdx) == end)
            return true;
    }

    return false;
}

function createInfoDialog(html)
{
    document.body.style.pointerEvents = "none";
    var dlg = vex.dialog.open({
                message: html, 
                showCloseButton: false, 
                buttons: [],
                });
    return dlg;
}

function closeInfoDialog(dlg)
{
    vex.close(dlg.data().vex.id);
    document.body.style.pointerEvents = "";
}

function textToHTML(text)
{
    return ((text || "") + "")  // make sure it's a string;
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\t/g, "    ")
        .replace(/ /g, "&#8203;&nbsp;&#8203;")
        .replace(/\r\n|\r|\n/g, "<br />");
}

var sherpass = null;
var privKeyURL = null;
var passDirURL = null;

var useLocalTcpConnection = false;
var tcpConnPort = 49374;
var tcpAESKey = null;
var tcpAccessURL = null;

var isIFrame = false;
var filterProtocol = "unknown-protocol";
var filterHost = "";

var lastReceivedDecryptedEntries = null;

function extractHost(s)
{
    var idx = s.indexOf("/");

    if (idx < 0)
        return s;
    return s.substr(0, idx);
}

function main()
{
    //openpgp.initWorker("openpgp.worker.min.js");
    openpgp.initWorker("openpgp.worker.js");
    $("#logo").click(function() { window.open('https://sherpass-lite.appspot.com/about.html','_blank'); });

    $("#configurebtn").click(function() { configure(); });
    $("#reloadbtn").click(function() { reload(); });
    $("#decryptbutton").click(function() { decrypt(); });
    $("#iframeclosebutton").click(function() { closeIFrame(); });
    $("#sessioncachebutton").click(function() { cacheDecryptedData(); });

    if (parent !== window)
    {
        isIFrame = true;
        $(".iframeonly").show();
        $(".mainpageonly").hide();
        $("#filterresults").prop("checked", true);
        $("#filterresults").click(function() { setTimeout(function() { showSpecificRows(); }, 0); });
    }
    else
    {
        $("#filterresults").prop("checked", false);
        $(".iframeonly").hide();
        $(".mainpageonly").show();
    }

    vex.defaultOptions.className = 'vex-theme-wireframe';
    vex.closeByEscape = function() { }

    if (localStorage["DropboxPrivKeyURL"])
        privKeyURL = localStorage["DropboxPrivKeyURL"];
    if (localStorage["DropboxPassDirURL"])
        passDirURL = localStorage["DropboxPassDirURL"];

    if (localStorage["UseLocalTcpConnection"])
        useLocalTcpConnection = ( localStorage["UseLocalTcpConnection"] == "true") ? true:false;
    if (localStorage["LocalTcpPort"])
        tcpConnPort = localStorage["LocalTcpPort"]
    if (localStorage["LocalTcpAccessURL"])
        tcpAccessURL = localStorage["LocalTcpAccessURL"];
    if (localStorage["LocalTcpAESKey"])
        tcpAESKey = localStorage["LocalTcpAESKey"];

    if (!useLocalTcpConnection)
    {
        if (privKeyURL && passDirURL)
            setTimeout(reload, 0);
        else
            setTimeout(configure, 0);
    }
    else
    {
        $("#decryptbutton").hide();
        setTimeout(reload, 0);
    }

    createBookmarkletURL();

    console.log(window.location.protocol);
    if (window.location.protocol == "chrome-extension:")
    {
        $("#sherpassversion").text(" (Chrome extension)");
        $(".mainpageonly").hide();
    }
    else
        $("#sherpassversion").text(" (Web page)");
}

function configure()
{
    vex.dialog.open({
        contentCSS: { width: "90%" },
        message: '<h2>Configuration</h2>',
        input: "" +
            "Connect to local running SherPass application: <input type='checkbox' id='configtype'>" + 
            "<div id='webconfig'>"+
            "<h3>Enter Dropbox URLs</h3>"+
            "Private key:<br><input id='keyurl' name='keyurl' type='text' placeholder='https://www.dropbox.com/s/XXXXXXXXXXXXXX/file.privkey' /><br>" +
            "Password directory file:<br><input id='passurl' name='passurl' type='text' placeholder='https://www.dropbox.com/s/YYYYYYYYYYYY/filewithsharedfiles.txt' /><br>" +
            "</div>" +
            "<div id='localconfig'>" +
            "<h3>Local connection information</h3>"+
            "Local port:<br><input id='tcpport' type='number' name='tcpport'><br>" +
            "Access URL:<br><input id='accessurl' type='text' name='accessurl'><br>" +
            "AES Key:<br><input id='aeskey' type='text' name='aeskey'><br>" +
            "</div>",

        afterOpen: function(content)
        {
            $("#configtype").click(onChangeConfigType);
            $("#configtype").prop("checked", useLocalTcpConnection);
            if (useLocalTcpConnection)
            {
                $("#webconfig").hide();
                $("#localconfig").show();
            }
            else
            {
                $("#webconfig").show();
                $("#localconfig").hide();
            }
            
            if (privKeyURL)
                $("#keyurl").attr("value", privKeyURL);
            if (passDirURL)
                $("#passurl").attr("value", passDirURL);

            $("#tcpport").attr("value", tcpConnPort);
            if (tcpAESKey)
                $("#aeskey").attr("value", tcpAESKey);
            if (tcpAccessURL)
                $("#accessurl").attr("value", tcpAccessURL);
        },
        callback: function(data) 
        {
            if (data === false) 
            {
                // cancelled
                return;
            }

            useLocalTcpConnection = $("#configtype").is(':checked');
            localStorage["UseLocalTcpConnection"] = "" + useLocalTcpConnection;

            if (!useLocalTcpConnection)
            {
                privKeyURL = data.keyurl;
                passDirURL = data.passurl;
                $("#decryptbutton").show();
            }
            else
            {
                tcpConnPort = data.tcpport;
                tcpAccessURL = data.accessurl;
                tcpAESKey = data.aeskey;
                $("#decryptbutton").hide();
            }

            setTimeout(function() { reload(); }, 0);
        }
    });
}

function onChangeConfigType()
{
    if($("#configtype").is(':checked'))
    {
        $("#webconfig").hide();
        $("#localconfig").show();
    }
    else
    {
        $("#webconfig").show();
        $("#localconfig").hide();
    }
}

var privateKey = null;
var encryptedEntries = [ ];
var decryptedEntries = [ ];

function getExtraPart(extra)
{
    var shortened = false;
    var maxlen = 20;
    var sub = extra;

    if (extra.length > maxlen)
    {
        sub = sub.substr(0, maxlen);
        shortened = true;
    }

    var idx = sub.indexOf("\n");

    if (idx >= 0)
    {
        sub = sub.substr(0, idx);
        shortened = true;
    }

    if (shortened)
        sub += "...";

    return sub;
}

function showPassword(entry)
{
    return function()
    {
        vex.dialog.alert(textToHTML(entry["password"]));
    }
}

function sendToParent(s, tr)
{
    return function()
    {
        var obj = { "type": "sherpass-message", "subtype": "input", "value": s };
        var sendStr = JSON.stringify(obj);

        parent.postMessage(sendStr,'*');

        $(tr).removeClass("notselected");
        $(tr).addClass("isselected");

        $(".notselected").hide();
        $("#filterresults").prop("checked", true);
    }
}

function createTableForEntries(decEntries)
{
    decEntries.sort(function(a, b)
    {
        var s1 = a["description"].toLowerCase();
        var s2 = b["description"].toLowerCase();

        if (s1 < s2)
            return -1;
        return 1;
    });

    var table = document.createElement("table");
    table.style.border = "solid 1px";
    table.style.width = "100%";

    var tr = document.createElement("tr");
    table.appendChild(tr);

    var headers = [ "Type", "Description", "Host", "Login", "Password", "Extra info" ];
    for (var i = 0 ; i < headers.length ; i++)
    {
        var th = document.createElement("th");
        tr.appendChild(th);
        th.innerHTML = headers[i];
        th.style.border = "solid 1px";
    }

    function addTD(tr, s, shortString)
    {
        var td = document.createElement("td");
        td.style.border = "solid 1px";
        tr.appendChild(td);

        if (shortString)
            td.innerHTML = textToHTML(shortString);
        else
            td.innerHTML = textToHTML(s);
        if (isIFrame)
        {
            var h = sendToParent(s, tr);

            td.ondblclick = h;
            jQuery(td).bind('touchy-swipe', h);
        }
    }

    var num = decEntries.length;
    for (var i = 0 ; i < num ; i++)
    {
        var entry = decEntries[i];
        var match = true;

        if (isIFrame && filterHost)
        {
            match = false;

            if (entry["type"] == filterProtocol)
            {
                // We want the host regexp to match the actual parent host exactly
                
                try
                {
                    var hostRegEx = new RegExp(entry["host"]);
                    var result = hostRegEx.exec(filterHost);

                    //console.log("RegEx result: ");
                    //console.log(result);

                    if (result && result.length == 1 && result[0] == filterHost)
                        match = true;
                }
                catch(e)
                {
                    console.log("Error interpreting " + entry["host"] + " as RegExp");
                }
            }
        }

        tr = document.createElement("tr");
        table.appendChild(tr);
        if (!match)
            tr.className = "nomatch notselected";
        else
            tr.className = "notselected";

        addTD(tr, entry["type"]);
        addTD(tr, entry["description"]);
        addTD(tr, entry["host"]);
        addTD(tr, entry["login"]);

        td = document.createElement("td");
        td.style.border = "solid 1px";
        tr.appendChild(td);
        if (!isIFrame)
        {
            td.innerHTML = "(click&nbsp;to&nbsp;view)";
            td.onclick = showPassword(entry);
        }
        else 
        {
            var h = sendToParent(entry["password"], tr);

            td.innerHTML = "(double&nbsp;click/swipe&nbsp;to&nbsp;use)";
            td.ondblclick = h;
            jQuery(td).bind('touchy-swipe', h);
        }

        addTD(tr, entry["extra"], getExtraPart(entry["extra"]));
    }

    return table;
}

function onDoneDecrypting(decrypted)
{
    $("#resultdiv").empty();
    var collections = new Collections(document.getElementById("resultdiv"));

    if (!("collections" in decrypted)) // old behaviour
        decrypted = { "collections": [ { "name": "(unnamed)", "entries": decrypted } ], "activecollection": 0 };
    
    var activeTab = decrypted["activecollection"];
    var coll = decrypted["collections"];
        
    for (var i = 0 ; i < coll.length ; i++)
    {
        var entries = coll[i]["entries"];
        var name = coll[i]["name"];
        var elem = null;

        if (entries.length == 0)
        {
            elem = document.createElement("div");
            $(elem).text("No password received or none could be decrypted");
        }
        else
            elem = createTableForEntries(entries);

        var d = document.createElement("div");
		$(d).addClass("collection");
        d.appendChild(elem);

        var dmsg = document.createElement("div");
        $(dmsg).text("No matching entries were found for the current filter (hostname or last clicked item)");
        $(dmsg).addClass("notfoundmessage");
		d.appendChild(dmsg);

        collections.setTab(i, name, d);
    }

    collections.activateTab(activeTab);
    showSpecificRows();
}

function showSpecificRows()
{
    var selElems = $(".isselected");
    selElems.removeClass("isselected");
    selElems.addClass("notselected");

    $(".notselected").show();

    if($("#filterresults").is(':checked'))
        $(".nomatch").hide();
    else
        $(".nomatch").show();

    var tabDivs = $(".collection");
    for (var i = 0 ; i < tabDivs.length ; i++)
    {
        var num = $(tabDivs[i]).find("tr:not(.nomatch)").length - 1; // -1 for the header
        console.log("Found " + num + " entries for tab " + i);

        if (num == 0 && $("#filterresults").is(':checked'))
        {
            $(tabDivs[i]).find(".notfoundmessage").show();
        }
        else
        {
            $(tabDivs[i]).find(".notfoundmessage").hide();
        }
    }

}

function cacheDecryptedData()
{
    if (lastReceivedDecryptedEntries)
        sessionStorage["SherPassCache"] = JSON.stringify(lastReceivedDecryptedEntries);
}

var reload = (function()
{
    var counter = 0;

    return function()
    {
        counter++;

        if (counter == 1 && sessionStorage["SherPassCache"] != undefined)
        {
            var decEntries = JSON.parse(sessionStorage["SherPassCache"]);
            if (decEntries)
            {
                lastReceivedDecryptedEntries = decEntries;

                setTimeout(function() { onDoneDecrypting(decEntries); }, 0);
            }
        }
        else
        {
            if (useLocalTcpConnection)
                reloadLocal();
            else
                reloadWeb();
        }
    }
})();

function reloadWeb()
{
    var loadDlg = createInfoDialog("Loading...<br><span id='loadingstatus'></span>");

    sherpass = new SherPass();
    
    sherpass.onfatalloaderror = function(msg) 
    {
        closeInfoDialog(loadDlg);
        vex.dialog.alert({
            message: textToHTML(msg), 
            callback: function()
            {
                setTimeout(function() { configure(); }, 0);
            }
        });
    }
    
    sherpass.onloadingprivatekey = function() 
    { 
        $("#loadingstatus").text("Loading private key");
    }

    sherpass.onobtainedprivatekey = function(url) 
    { 
        localStorage["DropboxPrivKeyURL"] = url;
    }

    sherpass.onloadingpassinfourls = function() 
    { 
        $("#loadingstatus").text("Obtaining URLs for the password info files");
    }

    sherpass.onobtainedpasswordurls = function(url) 
    { 
        localStorage["DropboxPassDirURL"] = url
    }

    sherpass.onloadingindividualpassfiles = function(num) 
    { 
        $("#loadingstatus").html("Obtaining each password info file: <span id='passfileprogress'></id>");
        $("#passfileprogress").text("0/" + num);
    }

    sherpass.onloadedpassfile = function(i, num) 
    { 
        $("#passfileprogress").text("" + i + "/" + num);
    }

    sherpass.onloadedallpassfiles = function() 
    {
        closeInfoDialog(loadDlg);
        setTimeout(decrypt, 0);
    }

    sherpass.load(privKeyURL, passDirURL);
}

function getPassPhrase(decryptCallback)
{
    vex.dialog.open({
        message: 'Enter passphrase:',
        input: "<input id='passphrase' name='passphrase' type='password' required />",
        callback: function(data) 
        {
            if (data === false) 
            {
                // cancelled
                return;
            }

            decryptCallback(data.passphrase);
        }
    });
}

function decrypt()
{
    if (!sherpass)
    {
        vex.dialog.alert("Nothing to decrypt");
        return;
    }

    getPassPhrase(function(passphrase) 
    {
        setTimeout(function() { sherpass.decrypt(passphrase); }, 0);

        var decDlg = createInfoDialog("Decrypting " + sherpass.getTotalNumberOfEntries() + " entries<br>" +
                                      "Success: <span id='decryptsuccess'></span><br>" +
                                      "Failed: <span id='decryptfailed'></span>");

        sherpass.onfataldecrypterror = function(msg) 
        {
            closeInfoDialog(decDlg);
            vex.dialog.alert(textToHTML(msg));
        }

        sherpass.onstartdecrypting = function() 
        { 
            $("#decryptsuccess").text("0");
            $("#decryptfailed").text("0");
        }

        sherpass.ondecryptstatus = function(numGood, numBad, numTotal) 
        {
            $("#decryptsuccess").text("" + numGood);
            $("#decryptfailed").text("" + numBad);
        }

        sherpass.ondonedecrypting = function(numGood, numBad) 
        { 
            closeInfoDialog(decDlg);
            
            var num = sherpass.getNumberOfDecryptedEntries();
            var decEntries = [ ];
            for (var i = 0 ; i < num ; i++)
            {
                var entry = JSON.parse(sherpass.getDecryptedEntry(i));
                decEntries.push(entry);
            }

            lastReceivedDecryptedEntries = decEntries;
            setTimeout(function() { onDoneDecrypting(decEntries); }, 0);
        }
    });
}

function closeIFrame()
{
    if (!isIFrame)
        return;

    var obj = { "type": "sherpass-message", "subtype": "close", "value": "" };
    var sendStr = JSON.stringify(obj);

    parent.postMessage(sendStr,'*');
}

window.addEventListener('message', function(msg) 
{
    console.log("Message from parent:");
    console.log(msg.data);
    
    var prefix = "parent:";

    if (!startsWith(msg.data, prefix))
        return;

    var parentUrl = msg.data.substr(prefix.length);
    var httpPrefix = "http://";
    var httpsPrefix = "https://";
    
    if (startsWith(parentUrl, httpPrefix, true))
    {
        filterProtocol = "HTTP";
        filterHost = extractHost(parentUrl.substr(httpPrefix.length));
    }
    else if (startsWith(parentUrl, httpsPrefix, true))
    {
        filterProtocol = "HTTPS";
        filterHost = extractHost(parentUrl.substr(httpsPrefix.length));
    }

    console.log(filterProtocol + " " + filterHost);
    // We've just found out what the parent URL is, we're going to rebuild the table
    // if possible so the filtering will work
    $("#parenthost").text(filterHost + " (" + filterProtocol + ")");
    setTimeout(function() { if (lastReceivedDecryptedEntries) onDoneDecrypting(lastReceivedDecryptedEntries); }, 0);
});

function reloadLocal()
{
    sherpass = null;

    var loadDlg = createInfoDialog("Loading...<br>");

    var handler = function(response, statusCode, statusText)
    {
        try
        {
            if (statusCode != 200)
                throw "Error loading password data from local application\n" + statusText;

            var decrypted = CryptoJS.AES.decrypt(response, tcpAESKey);
            if (!decrypted.toString())
                throw "Unable to decrypt received data: incorrect AES key";
            
            var decString = decrypted.toString(CryptoJS.enc.Utf8);
            var decEntries = JSON.parse(decString);

            // Ok, the settings work, store them for future use
            localStorage["LocalTcpPort"] = "" + tcpConnPort
            localStorage["LocalTcpAccessURL"] = tcpAccessURL
            localStorage["LocalTcpAESKey"] = tcpAESKey

            lastReceivedDecryptedEntries = decEntries;
            setTimeout(function() { onDoneDecrypting(decEntries); }, 0);

            closeInfoDialog(loadDlg);
        }
        catch(err)
        {
            closeInfoDialog(loadDlg);
            vex.dialog.alert(textToHTML(err));
        }
    }

    var wrapperImage = new Image();
    wrapperImage.onload = function()
    {
        try
        {
            var canvas = document.createElement("canvas");
            var context = canvas.getContext("2d");

            canvas.width = wrapperImage.width;
            canvas.height = wrapperImage.height;

            context.drawImage(wrapperImage, 0, 0);
            var imgData = context.getImageData(0, 0, canvas.width, canvas.height);
            var dataLen = imgData.data.length;
            var encodedData = "";

            for (var p = 0 ; p < dataLen ; p += 4)
            {
                encodedData += String.fromCharCode(imgData.data[p]);
                encodedData += String.fromCharCode(imgData.data[p+1]);
                encodedData += String.fromCharCode(imgData.data[p+2]);
            }

            var l = encodedData.length-1;
            while (l >= 0 && encodedData[l] == ' ')
                l--;

            encodedData = encodedData.substr(0, l+1);

            //console.log(encodedData);
            handler(encodedData, 200, "OK");
        }
        catch(err)
        {
            closeInfoDialog(loadDlg);
            vex.dialog.alert(textToHTML("Unable to extract AES encrypted data from locally received information\n" + err));
        }
    }
    wrapperImage.onerror = function(err)
    {
        if (!wrapperImage.tryHTTPSNext)
        {
            console.log("HTTPS also failed");

            closeInfoDialog(loadDlg);
            vex.dialog.alert(textToHTML("Unable to connect to local application\n" + err));
        }
        else
        {
            console.log("HTTP failed, trying HTTPS");

            wrapperImage.tryHTTPSNext = false;
            wrapperImage.src = "https:" + wrapperImage.srcWithoutProtocol;
        }
    }

    wrapperImage.crossOrigin = "Anonymous";
    wrapperImage.srcWithoutProtocol = "//localhost:" + tcpConnPort + "/" + tcpAccessURL + "?" + getRandomIdentifier(64);
    wrapperImage.tryHTTPSNext = true;
    wrapperImage.src = "http:" + wrapperImage.srcWithoutProtocol;
}

function getRandomIdentifier(len)
{
    var str = "";
    var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";

    for(var i = 0 ; i < len ; i++ )
        str += chars.charAt(Math.floor(Math.random() * chars.length));

    return str;
}

function createBookmarkletURL()
{
    var randomFunctionName = getRandomIdentifier(32);
    var resourceBase = window.location.protocol + "//" + document.location.host;
    
    try
    {
        if (chrome.runtime.id)
        {
            resourceBase = "chrome-extension://" + chrome.runtime.id;
            randomFunctionName = "sherpasslet" + extId;
        }
    }
    catch(err)
    {
    }

    var data = "function X() { /* MAINCODEHERE */ return function() { SherPassBookmarklet.run('" + resourceBase + "'); } }";

    data = [ "if (!window." + randomFunctionName + ")",
    "{",
    "    console.log('Here');",
    "    window." + randomFunctionName + " = (" + data + ")()",
    "}",
    "window." + randomFunctionName + "();" ].join("\n");

    data = "void((function() { " + data + " })())";

    $.get("sherpass-bookmarklet.js", function(mainData)
    {
        data = data.replace("/* MAINCODEHERE */", mainData);

        elem = document.getElementById("sherpasslet");
        elem.setAttribute("href", "javascript:" + encodeURIComponent(data));
    });
}

$(document).ready(function() { main(); });
