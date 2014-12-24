/// CA Observer
/// 
/// Copyright (C) 2014 Michael Davidsaver
/// 
/// This program is free software: you can redistribute it and/or modify
/// it under the terms of the GNU Affero General Public License as published by
/// the Free Software Foundation, either version 3 of the License, or
/// (at your option) any later version.
/// 
/// See LICENSE for details.

// emit events for window hidden/shown to user
// hidden means minimized or background tab
(function(){
    var ishidden;
    $(document).on("visibilitychange", function() {
        if(document.hidden!=ishidden) {
            if(document.hidden) {
                $(document).triggerHandler("xHidden");
            } else {
                $(document).triggerHandler("xShown");
            }
        }
        ishidden = document.hidden;
    });
    $(document).ready(function() {
        $(document).triggerHandler("xShown");
    })
}());

(function($) {
    // split query string into an dictionary of lists
    $.xquery = (function(parts) {
        if(parts instanceof String) parts = [parts] // some .split() returns '' when no split?
        var result={};
        for (var i=0, len=parts.length; i<len; ++i)
        {
            var p=parts[i].split('=');
            if (p.length != 2 || p[0].length==0) continue;
            var values = result[p[0]] || [];
            values.push(decodeURIComponent(p[1].replace(/\+/g, " ")));
            result[p[0]] = values;
        }
        return result;
    })(window.location.search.substr(1).split('&')) // skip '?' and split into parts

    // pick off the first value or default
    $.xgetQuery = function(key, def) {
        var values = $.xquery[key];
        if(values)
            return values[0];
        else
            return def;
    }

    // Extend/overwrite query parameters
    $.xbuildQuery = function(info) {
        var Q={}, key;
        // copy in existing keys from GET
        for(key in $.xquery) {
            if(key in info)
                continue;
            var val=$.xquery[key];
            if(val instanceof Array)
                val=val[0];
            Q[key] = val;
        }
        // append new keys
        for(key in info) {
            var val=info[key];
            if(val instanceof Array)
                val = [val]
            Q[key] = info[key];
        }
        return Q;
    }
})(jQuery);

(function($) {
    $.fn.xcycleClass = function(classes) {
        var N = classes.length;
        this.each(function(idx,elem){
            var cls = classes[idx%N];
            $(elem).addClass(cls);
        });
        return this
    }
})(jQuery);

// Table which pulls data as JSON
(function($) {
    function LiveTable(elem, opts) {
        this.elem = elem.selector;
        this.pagekey = opts.pagekey || "page";
        this.nextpage = parseInt($.xgetQuery(this.pagekey,"1"), 10);
        this.url = opts.url || "";
        this.period = opts.period || 10000;
        this.mangle = opts.mangle;
        this.total = 0;        
    }
    
    LiveTable.prototype = {
        updatenow: function() {
            this.stop();
            var self=this, args = {};
            args[this.pagekey] = this.nextpage;

            this.request = $.ajax({
                url: this.url,
                dataType:"json",
                data:$.xbuildQuery(args),
                ifModified:true,
            })
            .done(this.havedata.bind(this))
            .fail(function(req, sts, err) {
                self.nextpage = self.page || 1;
                console.log("Request fails: "+sts+" "+err);
            })
            .always(function() {self.request = undefined;})
            .always(this.starttimer.bind(this));
        },
        
        starttimer: function() {
            if(this.request || this.timer) {
                console.log("Skip in progress "+this.request+" "+this.timer);
                return;
            }
            this.stop();
            this.timer = window.setTimeout(this.updatenow.bind(this), this.period);
        },
        
        stop: function() {
            if(this.request) {
                this.request.abort();
                this.request = undefined;
            }
            if(this.timer) {
                window.clearTimeout(this.timer);
                this.timer = undefined;
            }
        },
        
        havedata: function(data) {
            if(data==undefined || !("object_list" in data))
                return;
            if(this.mangle)
                data = this.mangle(data);
            
            if(this.headers==undefined) {
                // Collect column names
                this.headers = $(this.elem).find("thead th").map(function(){
                    return $(this).attr("atag") || "";
                }).get();
                if(this.headers.length==0)
                    console.log("Warning: Table contains no column keys");
            }
            
            // {object_list:[{col1:val1, ...}], page:0, total:0}

            var clen=this.headers.length,
                tag=$("<tbody/>");

            for(var row=0, rlen=data.object_list.length; row<rlen; row+=1) {
                var parts = $("<tr>").appendTo(tag);
                for(var col=0; col<clen; col+=1) {
                    var colname = this.headers[col];
                    $("<td>").text(data.object_list[row][colname] || "<empty>").appendTo(parts);
                }
            }

            tag.find("tr").xcycleClass(["even","odd"]);
            $(this.elem).find("tbody").replaceWith(tag);

            if(this.page!=data.page || this.total!=data.total)
                $(this.elem).triggerHandler("newpage", {page:data.page, total:data.total});
            this.page = data.page;
            this.total = data.total;
        }
    }
    
    $.fn.xLiveTable = function(opts) {
        if(this.length==0)
            console.log("Warning No table");
        var self = new LiveTable(this, opts || {});

        this.on("xUpdate", self.updatenow.bind(self));

        $(document).on("xShown", self.updatenow.bind(self));
        $(document).on("xHidden", self.stop.bind(self));

        this.data("xlivetable", self);
        self.updatenow();
        return this;
    }
}(jQuery));

(function($) {
    $.fn.xPaginator = function(sel, opts) {
        var self=this;
        var page;
        var total;

        if(sel.length==0 || this.length==0)
            console.log("Warning: Paginating nothing");

        this.on("newpage", function(junk, info) {
            sel.find("span.pagenum").text(info.page+"/"+info.total);
            page = info.page;
            total= info.total;
            sel.find(".prevpage").toggleClass("hidden", page<=1);
            sel.find(".nextpage").toggleClass("hidden", page>=total);
        });
    }
}(jQuery));

function mangleCAData(opts) {
    var addrkey = opts.addrkey || "source";

    return function(data) {
        var now = Date.now();
        data.object_list.forEach(function(val) {
            // hostname:port#
            val[addrkey] = val[addrkey].host+":"+val[addrkey].port;

            if('seenLast' in val)
                val.age = relTimeString(now - val.seenLast*1000);
            if('seenFirst' in val)
                val.seenFirst = new Date(val.seenFirst*1000).toLocaleString(undefined,{hour12:false});
            if('time' in val)
                val.time = new Date(val.time*1000).toLocaleString(undefined,{hour12:false});
            if(('next' in val) || ('prev' in val)) {
                if(!('prev' in val)) {
                    val['event'] = "Appears";
                    val['beacon'] = "X -> "+val.next.seq;
                } else if(!('next' in val)) {
                    val['event'] = "Disappears";
                    val['beacon'] = val.prev.seq+" -> X";
                } else {
                    val['event'] = "Glitch";
                    val['beacon'] = val.prev.seq+" -> "+val.next.seq;
                }
            }
        });
        return data;
    }
}

function relTimeString(ts) {
    var days = Math.floor(ts/86400000), // ms/day 1000*60*60*24
        rem  = ts%86400000;
    var hours = Math.floor(rem/3600000); // 1000*60*60
    rem %= 3600000;
    var min = Math.floor(rem/60000); // 1000*60
    rem %= 60000;
    var sec = (rem/1000); // fractional seconds
    var result = "";
    if(days)
        result += days+" days ";
    if(min<10)
        min = "0"+min;
    if(sec<10)
        sec = "0"+sec.toFixed(1);
    else
        sec = sec.toFixed(1);
    return result+" "+hours+":"+min+":"+sec;
}
