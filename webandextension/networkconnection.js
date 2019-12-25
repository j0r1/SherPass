NetworkConnection = function()
{
	var m_callBack = null;
	var m_xhr = null;
	var m_data = null;
	var m_this = this;
	
	var getIdentifier = function(len)
	{
		var str = "";
		var chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

		for(var i = 0 ; i < len ; i++ )
			str += chars.charAt(Math.floor(Math.random() * chars.length));

		return str;
	}

	this.open = function(URL, contentType, data, callBack, method, arraybuffer)
	{
		if (m_xhr !== null)
			throw "NetworkConnection.open: already opening a connection";

		var m = "";

		if (typeof(method) === 'undefined') 
			m = "POST";
		else
			m = method;

		m_data = data;
		m_callBack = callBack;
		request(URL, contentType, m, arraybuffer);
	}

	var request = function(URL, contentType, method, arraybuffer)
	{
		m_xhr = new XMLHttpRequest();
    
		m_xhr.dateId = getIdentifier(8);

		Log("NetworkConnection: Performing " + method + " with id " + m_xhr.dateId + " for URL " + URL);

		m_xhr.open(method, URL, true);
		m_xhr.setRequestHeader("Cache-Control", "no-cache");
		if (contentType)
			m_xhr.setRequestHeader("Content-Type", contentType);

		m_xhr.onreadystatechange = function()
		{
			//Log("NetworkConnection: Got response for " + this.dateId);
			//Log("   readyState: " + this.readyState);
			//Log("   response code: " + this.status);
			//Log("   response statusText: " + this.statusText);

			if (m_xhr == null) // already handled this
			{
				Log("NetworkConnection: Already handled response for this id, ignoring");
				return;
			}

			if (m_xhr.readyState == 4) // done
			{
				Log("NetworkConnection: Response is " + m_xhr.status + " " + m_xhr.statusText);

				if (m_callBack)
                {
                    var response = null;
                    if (m_xhr.responseType == "arraybuffer")
                        response = m_xhr.response;
                    else
                        response = m_xhr.responseText;

					m_callBack(m_xhr.status, m_xhr.statusText, response, m_this);
                }

				m_xhr = null;
			}
		};

        if (arraybuffer)
        {
            m_xhr.responseType = 'arraybuffer';
        }

		m_xhr.send(m_data);
	}

	this.get = function(url, callback, arraybuffer)
	{
		this.open(url, null, null, function(statusCode, statusText, response, instance)
		{
			if (callback)
				callback(response, statusCode, statusText);
		}, "GET", arraybuffer);
	}

	this.post = function(url, data, callback, arraybuffer)
	{
		var query = "";	

		if (typeof(data) == 'object')
			query += NetworkConnection.objToPostString(data);
		else
			query += "" + data;

		//console.log(query);

		this.open(url, "application/x-www-form-urlencoded", query, function(statusCode, statusText, response, instance)
		{
			if (callback)
				callback(response, statusCode, statusText);
		}, "POST", arraybuffer);
	}
}

NetworkConnection.get = function(url, callback, arraybuffer)
{
	var n = new NetworkConnection();

	n.get(url, callback, arraybuffer);
}

NetworkConnection.objToPostString = function(d)
{
	var count = 0;
	var s = "";

	for (var p in d)
	{
		var name = p;

		if (count != 0)
			s += "&";

		s += encodeURIComponent(name);
		s += "=";
		s += encodeURIComponent("" + d[p]);
		count++;
	}

	return s;
}

NetworkConnection.post = function(url, data, callback, arraybuffer)
{
	var n = new NetworkConnection();

	n.post(url, data, callback, arraybuffer);
}

