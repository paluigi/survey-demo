/* Survey form helpers: live search in the country grids, selection counters,
   clear buttons, and the favourite dropdown that only offers visited countries. */
(function () {
    "use strict";

    // Live search over the checkbox grids.
    document.querySelectorAll(".country-search").forEach(function (input) {
        var grid = document.querySelector(input.dataset.target);
        if (!grid) return;
        input.addEventListener("input", function () {
            var q = input.value.trim().toLowerCase();
            grid.querySelectorAll(".country-option").forEach(function (label) {
                label.hidden = !!q && label.textContent.trim().toLowerCase().indexOf(q) === -1;
            });
        });
    });

    // Selection counters + clear buttons.
    ["visited-grid", "wishlist-grid"].forEach(function (id) {
        var grid = document.getElementById(id);
        var counter = document.querySelector('[data-count-for="#' + id + '"]');
        if (!grid || !counter) return;
        grid.addEventListener("change", function () {
            counter.textContent = grid.querySelectorAll("input:checked").length;
        });
    });

    document.querySelectorAll("[data-clear]").forEach(function (button) {
        var grid = document.querySelector(button.dataset.clear);
        if (!grid) return;
        button.addEventListener("click", function () {
            grid.querySelectorAll("input:checked").forEach(function (box) {
                box.checked = false;
            });
            grid.dispatchEvent(new Event("change", {bubbles: true}));
        });
    });

    // The favourite select only lists ticked "visited" countries.
    var visitedGrid = document.getElementById("visited-grid");
    var favourite = document.getElementById("favourite");
    if (!visitedGrid || !favourite) return;

    function rebuildFavourite() {
        var previous = favourite.value;
        var checked = Array.prototype.slice
            .call(visitedGrid.querySelectorAll("input:checked"))
            .map(function (box) {
                return {code: box.value, name: box.parentElement.querySelector("span").textContent};
            })
            .sort(function (a, b) {
                return a.name.localeCompare(b.name);
            });

        favourite.innerHTML = "";
        var placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = checked.length
            ? "— Select one of your visited countries —"
            : "— Tick some visited countries first —";
        favourite.appendChild(placeholder);
        checked.forEach(function (entry) {
            var option = document.createElement("option");
            option.value = entry.code;
            option.textContent = entry.name;
            favourite.appendChild(option);
        });
        favourite.value = checked.some(function (entry) {
            return entry.code === previous;
        }) ? previous : "";
        favourite.disabled = checked.length === 0;
    }

    visitedGrid.addEventListener("change", rebuildFavourite);
    rebuildFavourite();
})();
