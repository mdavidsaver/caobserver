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
    function ReloadTimer(elem, opts) {
        this.period = (opts.period || 15)*1000;
        this.url = opts.url || "";
        this.elem = elem;
        if(!this.elem) {
            console.log("No element!");
        }
    }
    
    ReloadTimer.prototype = {
        updatenow: function() {
            this.stop();
            var self=this;

            this.request = $.ajax({
                url: location.search,
                mimeType: "text/html",
                ifModified:true,
            })
            .done(this.havedata.bind(this))
            .fail(function(req, sts, err) {
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
 
        havedata: function(data, sts, jhdr) {
            console.log("Status "+sts+" "+jhdr.status);
            if(data==undefined || jhdr.status==304)
                return;
            var newelem = $(this.elem.selector, data);
            if(newelem.length==0) {
                console.log("Element not found??");
            }
            this.elem.replaceWith(newelem);
        },
        
    }

    // Periodically reload element (when page is not hidden)
    $.fn.xReload = function(opts) {
        var self = new ReloadTimer(this, opts || {});

        $(document).on("xShown", self.updatenow.bind(self));
        $(document).on("xHidden", self.stop.bind(self));

        this.data("xReload", self);
        self.starttimer();
        return this;
    }
}(jQuery));
