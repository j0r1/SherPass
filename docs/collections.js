var SimpleCollections = function(parentElement)
{
    var _this = this;
    var mainDiv = null;

    this.setTab = function(idx, name, contents)
    {
        var h = document.createElement("h3");
        $(h).text(name);

        mainDiv.appendChild(h);
        mainDiv.appendChild(contents);
    }

    this.activateTab = function(idx)
    {
    }

    var init = function()
    {
        mainDiv = document.createElement("div");
        parentElement.appendChild(mainDiv);
    }

    init();
}

var TabCollections = function(parentElement)
{
    var _this = this;
    var mainDiv = null;
    var nameList = null;
    var contentDiv = null;

    function getTabHeaderName(i)
    {
        return "collname" + i;
    }

    function getTabDivName(i)
    {
        return "coll" + i;
    }

    this.setTab = function(idx, name, contents)
    {
        var li = document.createElement("li");
        var a = document.createElement("a");

        a.onclick = (function(idx) { return function() { _this.activateTab(idx); return false; } })(idx);
        a.setAttribute("href", "#");
        $(a).addClass("tabnamelink");
        $(a).text(name);

        li.appendChild(a);
        nameList.appendChild(li);
        $(li).addClass("anytabname");
        li.id = getTabHeaderName(idx);

        var d = document.createElement("div");
        d.appendChild(contents);
        contentDiv.appendChild(d);
        $(d).css("padding", "10px");

        $(d).addClass("singletab");
        d.id = getTabDivName(idx);

        if (idx == 1) // from the second tab, we'll show some tabs
        {
            $(contentDiv).css("border-top", "1px solid");
            $(nameList).show();
        }
    }

    this.activateTab = function(idx)
    {
        $(".singletab").hide().removeClass("activetab");
        $("#" + getTabDivName(idx)).show().addClass("activetab");

        $(".anytabname").removeClass("activetabname");
        $("#" + getTabHeaderName(idx)).addClass("activetabname");
    }

    var init = function()
    {
        mainDiv = document.createElement("div");
        parentElement.appendChild(mainDiv);
        $(mainDiv).css("padding-top", "10px");

        nameList = document.createElement("ul");
        mainDiv.appendChild(nameList);
        nameList.id = "tabnames";
        $(nameList).hide();

        contentDiv = document.createElement("div");
        mainDiv.appendChild(contentDiv);
        contentDiv.id = "tabcontentdiv";
    }

    init();
}

var Collections = TabCollections;
