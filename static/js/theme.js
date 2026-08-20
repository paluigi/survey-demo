/* Dark / light theme toggle: persists the choice and notifies listeners
   (map.js re-styles the map when it receives the "themechange" event). */
(function () {
    var root = document.documentElement;
    var button = document.getElementById("theme-toggle");

    function current() {
        return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
    }

    if (button) {
        button.addEventListener("click", function () {
            var next = current() === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            localStorage.setItem("theme", next);
            window.dispatchEvent(new CustomEvent("themechange", {detail: {theme: next}}));
        });
    }
})();
