/* App-wide htmx tweaks. */
(function () {
    "use strict";

    // Keep shareable URLs clean: drop empty query params (e.g. untouched
    // filter selects) from every htmx request.
    document.body.addEventListener("htmx:configRequest", function (event) {
        var params = event.detail.parameters;
        Object.keys(params).forEach(function (key) {
            if (params[key] === "") delete params[key];
        });
    });
})();
