(function () {
    // Sequential amber ramp, light (oldest) to dark (newest). Single hue,
    // monotone lightness, dark end still clears 3:1 against dark imagery.
    const dateRamp = ["#FFE0A3", "#FDC161", "#F79E28", "#E67912", "#C25A0A"];

    function hexToRgb(hex) {
        return [
            parseInt(hex.slice(1, 3), 16),
            parseInt(hex.slice(3, 5), 16),
            parseInt(hex.slice(5, 7), 16),
        ];
    }

    function rampColor(fraction) {
        const scaled = Math.max(0, Math.min(1, fraction)) * (dateRamp.length - 1);
        const index = Math.min(Math.floor(scaled), dateRamp.length - 2);
        const [from, to] = [hexToRgb(dateRamp[index]), hexToRgb(dateRamp[index + 1])];
        const t = scaled - index;
        const channels = from.map((c, i) => Math.round(c + (to[i] - c) * t));
        return "rgb(" + channels.join(",") + ")";
    }

    // Hours as a decimal, e.g. 1.75 -> "1h 45m"
    function formatDuration(hours) {
        const minutes = Math.round(hours * 60);
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        return h > 0 ? h + "h " + m + "m" : m + "m";
    }

    function inRange(properties, hideout) {
        return (
            properties.day >= hideout.minDay &&
            properties.day <= hideout.maxDay &&
            hideout.activities.includes(properties.activity)
        );
    }

    window.dashExtensions = Object.assign({}, window.dashExtensions, {
        routes: {
            ramp: dateRamp,

            filter: function (feature, context) {
                return inRange(feature.properties, context.hideout);
            },

            style: function (feature, context) {
                const hideout = context.hideout;
                const properties = feature.properties;

                let color;
                if (hideout.colorBy === "date") {
                    const span = hideout.maxDay - hideout.minDay;
                    const fraction =
                        span > 0 ? (properties.day - hideout.minDay) / span : 1;
                    color = rampColor(fraction);
                } else {
                    color = hideout.activityColors[properties.activity];
                }

                return { color: color, weight: 3, opacity: 0.8 };
            },

            onEachFeature: function (feature, layer, context) {
                const properties = feature.properties;
                layer.bindTooltip(
                    properties.date +
                        " " +
                        properties.time +
                        "<br>" +
                        properties.activity +
                        " &middot; " +
                        properties.distance.toFixed(2) +
                        " mi &middot; " +
                        formatDuration(properties.duration),
                    { sticky: true }
                );
            },
        },
    });
})();
