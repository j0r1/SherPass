// Need to run "npm install socket.io" first

var http = require('http')
var fs = require('fs')
var app = http.createServer(handler);

app.listen(8080);

function endsWith(s, end, caseInsensitive)
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

function handler(req, res) 
{
    console.log(req.user + ":" + req.url)
    
    var url = req.url;
    if (url == '/')
        url = "/index.html";

    // Just load the url interpreted as a file name
    fs.readFile(__dirname + url, function (err, data) 
    {
        if (err) 
        {
            res.writeHead(500);
            return res.end('Error loading ' + url);
        }
        
        var contType = "text/plain";
        var contMap = { 
            "html":     "text/html",
            "txt":      "text/plain",
            "jpg":      "image/jpeg",
            "png":      "image/png",
            "css":      "text/css",
            "doc":      "application/msword",
            "js":       "application/javascript",
            "css":      "text/css",
            "svg":      "image/svg+xml",
        }

        for (var suff in contMap)
        {
            if (endsWith(url, "." + suff, true))
            {
                contType = contMap[suff];
                break;
            }
        }

        res.writeHead(200, {"Content-type": contType});
        res.end(data);
    });
}

