var SherPassBookmarklet = function(resourceBase, noscripts)
{
    console.log(noscripts);

    var _this = this
    var initialized = false;
    var initializing = false;

    var m_iFrameDiv = null;
    var m_inputElem = null;

    var initializeOverlay = function()
    {
        console.log("HERE");
        m_iFrameDiv = document.createElement("div");

        var iFrame = document.createElement("iframe");
        m_iFrameDiv.appendChild(iFrame);

        iFrame.width = "100%";
        iFrame.height = "100%";

        m_iFrameDiv.style.display = "none";
        m_iFrameDiv.style.position = "fixed";
        m_iFrameDiv.style.top = "0px";
        m_iFrameDiv.style.left = "0px";
        m_iFrameDiv.style.backgroundColor = "#ffffff";
        m_iFrameDiv.style.opacity = "0.9";
        m_iFrameDiv.style.width = "100%";
        m_iFrameDiv.style.height = "100%";
        m_iFrameDiv.style.zIndex = "2147483647";

        document.body.appendChild(m_iFrameDiv);

        iFrame.setAttribute("src", resourceBase + "/index.html");
        iFrame.onload = function()
        {
            console.log("Sending message from bookmarklet to iframe");
            //iFrame.contentWindow.postMessage("parent:" + window.location.href, "https://sherpass-lite.appspot.com");
            iFrame.contentWindow.postMessage("parent:" + window.location.href, "*");
        }
    }

    var m_oldOverFlow = null;

    var showOverlay = function()
    {
        m_oldOverFlow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        m_iFrameDiv.style.display = "";
    }

    var closeOverlay = function()
    {
        document.body.style.overflow = m_oldOverFlow;
        m_iFrameDiv.style.display = "none";
    }

    var resourcesInitialized = function()
    {
        console.log("Resources initialized");
        
        //vex.defaultOptions.className = "vex-theme-wireframe";
        
        initializing = false;
        initialized = true;

        initializeOverlay();

        window.addEventListener("message", function(msg)
        {
            console.log("Got message: " + msg.data);

            try
            {
                var obj = JSON.parse(msg.data);

                console.log(obj);
                if (obj["type"] == "sherpass-message")
                {
                    closeOverlay();

                    if (obj["subtype"] == "input")
                    {
                        try
                        {
                            console.log("Simulating keypress");

                            bililiteRange(m_inputElem).bounds('selection').sendkeys('(empty)').select();
                        }
                        catch(e)
                        {
                            // Just ignore and try the rest
                        }

                        jQuery(m_inputElem).val(obj["value"]);
                        m_inputElem = null;
                        console.log("Value set");
                    }
                }
            }
            catch(err)
            {
                console.log("Error interpreting message as JSON data: " + err);
            }
        });

        setTimeout(function() { _this.run(); }, 0);
    }

    var init = function(_this)
    {
        var resources = [ 
            //                { type: "link", url: resourceBase + "/vex.css" },
            //                { type: "link", url: resourceBase + "/vex-theme-wireframe.css" },
                        ];

        if (!noscripts)
        {
            resources.push( { type: "script", url: resourceBase + "/jquery.min.js" } );
            resources.push( { type: "script", url: resourceBase + "/jquery.touchy.min.js" } );
            resources.push( { type: "script", url: resourceBase + "/bililiteRange.js" } );
            //resources.push( { type: "script", url: resourceBase + "/vex.js" });
            //resources.push( { type: "script", url: resourceBase + "/vex.dialog.js" });
        }

        function createLoadCallback(idx)
        {
            return function()
            {
                console.log(resources[idx].url + " loaded");

                if (idx+1 == resources.length)
                    resourcesInitialized();
                else
                {
                    processResource(idx+1);
                }
            }
        }

        function processResource(idx)
        {
            var obj = resources[idx];

            if (obj.type == "link")
            {
                var s = document.createElement("link");
                
                s.setAttribute("rel", "stylesheet");
                s.setAttribute("href", obj.url);
                s.onload = createLoadCallback(idx);

                console.log("Loading: " + obj.url);

                document.head.appendChild(s);
            }
            else if (obj.type == "script")
            {
                var s = document.createElement("script");
                
                s.src = obj.url;
                s.onload = createLoadCallback(idx);

                document.body.appendChild(s);
            }
        }

        console.log(resources.length);

        if (resources.length > 0)
            processResource(0); // start resource retrieval
        else
            resourcesInitialized();
    }

    var m_processInputTimer = null;

    this.run = function()
    {
        console.log("run");

        if (initializing)
            return;
        if (!initialized)
        {
            initializing = true;
            init(this);
            return;
        }

        if (m_processInputTimer != null)
            clearInterval(m_processInputTimer);

        m_processInputTimer = setInterval(processInputfields, 1000);
        setTimeout(processInputfields, 0);
    }

    var getHandler = function(elem)
    {
        return function()
        {
            m_inputElem = elem;
            showOverlay();
        }
    }

    var processInputfields = function()
    {
        var inputFields = document.getElementsByTagName("input");
        for (var i = 0 ; i < inputFields.length ; i++)
        {
            var elem = inputFields[i];

            if (elem.processedBySherPass)
                continue;

            elem.processedBySherPass = true;

            var t = elem.getAttribute("type");

            //console.log("Input name: " + elem.getAttribute("name"));
            //console.log("Input type: " + t);
            if (t == null || t == "text" || t == "password" || t == "email" || t == "url")
            {
                var h = getHandler(elem);

                elem.ondblclick = h;
                jQuery(elem).bind("touchy-swipe", h);

                elem.style.backgroundColor = "#cfc";
                //elem.placeholder = "(double click/swipe for SherPass)";
            }
        }
    }
}

SherPassBookmarklet.instance = null;

SherPassBookmarklet.run = function(resourceBase, noscripts)
{
    console.log("resourceBase is " + resourceBase);
    if (!SherPassBookmarklet.instance)
    {
        SherPassBookmarklet.instance = new SherPassBookmarklet(resourceBase, noscripts);
        console.log("Allocated new instance");
    }

    SherPassBookmarklet.instance.run();
}


