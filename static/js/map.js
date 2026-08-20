/* World choropleth on MapLibre GL, following the global-funding-monitor map
 * pattern: a minimal inline style (no tiles), a countries GeoJSON source fed
 * by /api/map/choropleth, a step-expression color ramp recomputed from the
 * data max, click-to-select with a dimmed background, an htmx-driven side
 * card, and theme-aware colors. */
(function () {
    "use strict";

    var container = document.getElementById("map");
    if (!container || typeof maplibregl === "undefined") return;

    var CATS = {
        visited: {prop: "visited", label: "visited"},
        want: {prop: "want", label: "want to visit"},
        favourite: {prop: "favourite", label: "favourite pick"}
    };
    var RAMP = ["#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#1d4ed8"];
    var THEMES = {
        light: {bg: "#eef2f7", border: "#ffffff", zero: "#dbe4f0"},
        dark: {bg: "#0b1220", border: "#334155", zero: "#1e293b"}
    };
    var ACCENT = "#1d4ed8";
    var NO_FILTER = ["==", ["get", "iso2"], ""];

    var state = {
        cat: "visited",
        selected: null,
        data: null,
        max: 0
    };

    var map = new maplibregl.Map({
        container: container,
        style: {
            version: 8,
            sources: {},
            layers: [{id: "bg", type: "background", paint: {"background-color": THEMES.light.bg}}]
        },
        center: [10, 25],
        zoom: 1.2,
        minZoom: 0.3,
        attributionControl: false
    });
    map.addControl(new maplibregl.NavigationControl({visualizePitch: false}), "top-right");

    function theme() {
        return document.documentElement.getAttribute("data-theme") === "dark" ? THEMES.dark : THEMES.light;
    }

    function filtersQuery() {
        var host = document.getElementById("results-data");
        return host && host.dataset.filters ? host.dataset.filters : "";
    }

    function thresholds() {
        // Five color buckets spread over 1..max; floats are fine in step exprs.
        var step = state.max > 0 ? state.max / 5 : 1;
        return [step, 2 * step, 3 * step, 4 * step];
    }

    /* Build the step expression: zero bucket + five ramp buckets over 1..max. */
    function rampExpression() {
        var t = theme();
        if (!state.max) return t.zero;
        var steps = thresholds();
        var expr = ["step", ["get", CATS[state.cat].prop], t.zero];
        for (var i = 0; i < steps.length; i++) {
            expr.push(steps[i], RAMP[i]);
        }
        expr.push(RAMP[4]); // values above the last threshold
        return expr;
    }

    function applyChoropleth() {
        map.setPaintProperty("countries-fill", "fill-color", rampExpression());
        renderLegend();
    }

    function renderLegend() {
        var legend = document.getElementById("map-legend");
        if (!legend) return;
        if (!state.max) {
            legend.hidden = true;
            return;
        }
        legend.hidden = false;
        var s = thresholds();
        var ceil = Math.ceil;
        var bins = [
            [theme().zero, "0"],
            [RAMP[0], "1\u2013" + ceil(s[0])],
            [RAMP[1], (ceil(s[0]) + 1) + "\u2013" + ceil(s[1])],
            [RAMP[2], (ceil(s[1]) + 1) + "\u2013" + ceil(s[2])],
            [RAMP[3], (ceil(s[2]) + 1) + "\u2013" + ceil(s[3])],
            [RAMP[4], "> " + ceil(s[3])]
        ];
        legend.innerHTML = bins.map(function (bin) {
            return '<span class="legend-item"><i style="background:' + bin[0] + '"></i>' + bin[1] + "</span>";
        }).join("");
    }

    function setStatus(text) {
        var status = document.getElementById("map-status");
        if (status) {
            status.hidden = !text;
            status.textContent = text || "";
        }
    }

    function computeMax() {
        var prop = CATS[state.cat].prop;
        var max = 0;
        (state.data.features || []).forEach(function (feature) {
            max = Math.max(max, feature.properties[prop] || 0);
        });
        state.max = max;
    }

    function loadData() {
        setStatus("Loading map\u2026");
        var query = filtersQuery();
        return fetch("/api/map/choropleth" + (query ? "?" + query : ""))
            .then(function (response) {
                if (!response.ok) throw new Error("HTTP " + response.status);
                return response.json();
            })
            .then(function (featureCollection) {
                state.data = featureCollection;
                computeMax();
                map.getSource("countries").setData(featureCollection);
                applyChoropleth();
                if (state.selected) refreshCards();
                setStatus(null);
            })
            .catch(function () {
                setStatus("Could not load map data.");
            });
    }

    function refreshCards() {
        if (!state.selected) return;
        var params = new URLSearchParams(filtersQuery());
        params.set("country", state.selected);
        if (typeof htmx !== "undefined") {
            htmx.ajax("GET", "/partials/map-cards?" + params.toString(), "#map-cards");
        }
    }

    function updateUrl(patch) {
        var url = new URL(window.location.href);
        Object.keys(patch).forEach(function (key) {
            if (patch[key] === null) url.searchParams.delete(key);
            else url.searchParams.set(key, patch[key]);
        });
        window.history.replaceState(null, "", url);
    }

    function selectCountry(code) {
        state.selected = code;
        map.setFilter("selection-line", ["==", ["get", "iso2"], code]);
        map.setPaintProperty("selection-line", "line-width", 2.5);
        map.setPaintProperty("countries-fill", "fill-opacity", [
            "match", ["get", "iso2"], [code], 0.95, 0.12
        ]);
        refreshCards();
        updateUrl({country: code});
    }

    function clearSelection() {
        state.selected = null;
        map.setFilter("selection-line", NO_FILTER);
        map.setPaintProperty("selection-line", "line-width", 0);
        map.setPaintProperty("countries-fill", "fill-opacity", 0.85);
        var side = document.getElementById("map-cards");
        if (side) {
            side.innerHTML = '<p class="muted">Click a country on the map (or a row in the table) to see its numbers.</p>';
        }
        updateUrl({country: null});
    }

    function setCategory(cat, push) {
        if (!CATS[cat]) return;
        state.cat = cat;
        document.querySelectorAll(".cat-chips .chip").forEach(function (chip) {
            chip.classList.toggle("active", chip.dataset.cat === cat);
        });
        if (state.data) {
            computeMax();
            applyChoropleth();
        }
        if (push) updateUrl({cat: cat});
    }

    var popup = new maplibregl.Popup({closeButton: false, closeOnClick: false});

    map.on("load", function () {
        map.addSource("countries", {
            type: "geojson",
            data: {type: "FeatureCollection", features: []}
        });
        map.addLayer({
            id: "countries-fill",
            type: "fill",
            source: "countries",
            paint: {"fill-color": THEMES.light.zero, "fill-opacity": 0.85}
        });
        map.addLayer({
            id: "countries-line",
            type: "line",
            source: "countries",
            paint: {"line-color": THEMES.light.border, "line-width": 0.5}
        });
        map.addLayer({
            id: "selection-line",
            type: "line",
            source: "countries",
            filter: NO_FILTER,
            paint: {"line-color": ACCENT, "line-width": 0}
        });

        // Deep links: /results?cat=want&country=IT
        var params = new URLSearchParams(window.location.search);
        setCategory(params.get("cat") || "visited", false);
        var country = params.get("country");

        loadData().then(function () {
            if (country) selectCountry(country.toUpperCase());
        });
    });

    map.on("click", "countries-fill", function (event) {
        var props = event.features && event.features[0].properties;
        if (props) selectCountry(props.iso2);
    });
    map.on("mouseenter", "countries-fill", function () {
        map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", "countries-fill", function () {
        map.getCanvas().style.cursor = "";
        popup.remove();
    });
    map.on("mousemove", "countries-fill", function (event) {
        var props = event.features && event.features[0].properties;
        if (!props) return;
        var value = props[CATS[state.cat].prop] || 0;
        popup.setLngLat(event.lngLat)
            .setHTML("<strong>" + props.name + "</strong><br>" + value + " " + CATS[state.cat].label)
            .addTo(map);
    });

    document.querySelectorAll(".cat-chips .chip").forEach(function (chip) {
        chip.addEventListener("click", function () {
            setCategory(chip.dataset.cat, true);
        });
    });

    // htmx re-renders the table + summary when filters change; reload the map.
    document.body.addEventListener("htmx:afterSwap", function (event) {
        if (event.target && event.target.id === "results-data") loadData();
    });

    // Table rows and the card's clear button.
    document.addEventListener("click", function (event) {
        var clear = event.target.closest("[data-clear-selection]");
        if (clear) {
            clearSelection();
            return;
        }
        var row = event.target.closest("tr[data-country]");
        if (row) {
            selectCountry(row.dataset.country);
            container.scrollIntoView({behavior: "smooth", block: "nearest"});
        }
    });

    // Theme switch: recolor background, borders and the zero bucket.
    window.addEventListener("themechange", function () {
        var t = theme();
        map.setPaintProperty("bg", "background-color", t.bg);
        map.setPaintProperty("countries-line", "line-color", t.border);
        if (state.data) applyChoropleth();
    });

    window.surveyMap = {select: selectCountry, clear: clearSelection, reload: loadData};
})();
