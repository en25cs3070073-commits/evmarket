/* EV Analytics Hub - built-in interactive views.
 *
 * These charts are computed in the browser from static/data/facts.json, which is
 * serialised straight from the v_ev_data SQL view. They are not Tableau; the
 * Tableau embed appears below them once the workbook is published.
 */
(function () {
  "use strict";

  var PALETTE = ["#0f766e", "#2563eb", "#d97706", "#dc2626", "#7c3aed",
                "#0891b2", "#65a30d", "#db2777", "#475569", "#ca8a04"];

  var FILTERS = [
    { col: "brand", label: "Manufacturer" },
    { col: "model_year", label: "Year" },
    { col: "body_type", label: "Vehicle category" },
    { col: "battery_technology", label: "Battery technology" },
    { col: "country_of_origin", label: "Manufacturing country" },
    { col: "market_segment", label: "Market segment" }
  ];

  var PAGES = {
    market: ["kpi", "trend", "mfg", "cat", "heat", "topmodels"],
    battery: ["chemunits", "chemgwh", "scatter", "box", "charge", "stack"],
    global: ["geo", "grid", "value", "table"],
    story: ["scene1", "scene2", "scene3", "scene4"]
  };

  var CHARTS = {
    kpi: { title: "Headline figures", build: buildKpi },
    trend: { title: "Annual sales volume", note: "Sum of annual_sales_units by model_year.", build: buildTrend },
    mfg: { title: "Leading manufacturers", note: "Top 10 by units. Share is share of dataset sales, not national market share.", build: buildMfg },
    cat: { title: "Category contribution", note: "Square size is units; colour is sales-weighted range.", build: buildCat },
    heat: { title: "Satisfaction by manufacturer and category", note: "Mean customer_rating. Cells with fewer than 3 rows are suppressed.", build: buildHeat },
    topmodels: { title: "Best-rated models", note: "Filtered to models with at least 50,000 lifetime units so low-volume vehicles cannot top the ranking.", build: buildTopModels },

    chemunits: { title: "Chemistry share by vehicles", note: "Counting cars.", build: buildChemUnits },
    chemgwh: { title: "Chemistry share by energy demand", note: "Counting kilowatt-hours. This ranking differs from the one beside it, and that difference is the finding.", build: buildChemGwh },
    scatter: { title: "Battery capacity against driving range", note: "Each band is one body type: pooled correlation is weak, within-category correlation is strong.", build: buildScatter },
    box: { title: "Range distribution by category", note: "Unweighted model means, so outliers are individual vehicles.", build: buildBox },
    charge: { title: "DC refill time 10-80%", note: "Sales-weighted average charging_time_min_10_80 by chemistry.", build: buildCharge },
    stack: { title: "Chemistry adoption by manufacturer", note: "Top 8 brands, shown as share within each brand.", build: buildStack },

    geo: { title: "Manufacturing geography", note: "Units by country of origin.", build: buildGeo },
    grid: { title: "CO2e avoided per vehicle against grid intensity", note: "Passenger vehicles only. Pooling trucks reverses this ranking.", build: buildGrid },
    value: { title: "Best value: dollars per mile of range", note: "Passenger models with at least 100,000 lifetime units.", build: buildValue },
    table: { title: "Model detail", note: "Top 20 by lifetime units in the current selection.", build: buildTable },

    scene1: { title: "Scene 1 - A maturing market, not a stalling one", build: scene(1) },
    scene2: { title: "Scene 2 - Leadership changed hands and the field widened", build: scene(2) },
    scene3: { title: "Scene 3 - Two chemistries, two different answers", build: scene(3) },
    scene4: { title: "Scene 4 - Where the next gains are", build: scene(4) }
  };

  var ROWS = [];
  var PAGE = null;
  var state = {};

  /* ---------- helpers ---------- */

  function sum(rows, f) {
    var t = 0;
    for (var i = 0; i < rows.length; i++) t += f(rows[i]);
    return t;
  }

  function wavg(rows, vf, wf) {
    var w = sum(rows, wf);
    return w ? sum(rows, function (r) { return vf(r) * wf(r); }) / w : 0;
  }

  function group(rows, keyf) {
    var m = new Map();
    rows.forEach(function (r) {
      var k = keyf(r);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r);
    });
    return m;
  }

  function fmt(n, digits) {
    return Number(n).toLocaleString("en-US", {
      maximumFractionDigits: digits === undefined ? 0 : digits
    });
  }

  function compact(n) {
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + "M";
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + "k";
    return n.toFixed(0);
  }

  function filtered() {
    return ROWS.filter(function (r) {
      return FILTERS.every(function (f) {
        var v = state[f.col];
        return !v || String(r[f.col]) === String(v);
      });
    });
  }

  function layout(extra) {
    var base = {
      margin: { l: 60, r: 20, t: 10, b: 50 },
      font: { family: "system-ui, sans-serif", size: 12, color: "#10202a" },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      autosize: true,
      showlegend: false
    };
    for (var k in extra) base[k] = extra[k];
    return base;
  }

  function draw(el, traces, lay) {
    if (!window.Plotly) { el.innerHTML = "<p class='muted'>Chart library did not load.</p>"; return; }
    Plotly.newPlot(el, traces, lay, { displayModeBar: false, responsive: true });
  }

  function empty(el) {
    el.innerHTML = "<p class='muted'>No rows match the current filters.</p>";
  }

  /* ---------- KPI ---------- */

  function buildKpi(rows, el) {
    var models = new Set(rows.map(function (r) { return r.brand + "|" + r.model_name; }));
    var items = [
      ["Units", compact(sum(rows, function (r) { return r.annual_sales_units; }))],
      ["Models", fmt(models.size)],
      ["Brands", fmt(new Set(rows.map(function (r) { return r.brand; })).size)],
      ["Avg range", fmt(wavg(rows, function (r) { return r.driving_range_miles; },
        function (r) { return r.annual_sales_units; })) + " mi"],
      ["Avg price", "$" + fmt(wavg(rows, function (r) { return r.price_usd; },
        function (r) { return r.annual_sales_units; }))],
      ["Battery demand", fmt(wavg(rows, function (r) { return r.gwh_battery_demand; },
        function () { return 1; }) * rows.length / 1000, 1) + " TWh"]
    ];
    el.className = "kpi-row";
    el.innerHTML = items.map(function (i) {
      return "<div class='kpi'><span class='kpi-v'>" + i[1] + "</span><span class='kpi-l'>" + i[0] + "</span></div>";
    }).join("");
  }

  /* ---------- market ---------- */

  function buildTrend(rows, el) {
    var g = group(rows, function (r) { return r.model_year; });
    var years = Array.from(g.keys()).sort(function (a, b) { return a - b; });
    var units = years.map(function (y) { return sum(g.get(y), function (r) { return r.annual_sales_units; }); });
    draw(el, [{
      type: "scatter", mode: "lines+markers", x: years, y: units,
      line: { color: PALETTE[0], width: 3 }, marker: { size: 7 },
      text: units.map(compact), hovertemplate: "%{x}: %{y:,.0f} units<extra></extra>"
    }], layout({ xaxis: { title: "Model year", dtick: 1 }, yaxis: { title: "Units" } }));
  }

  function buildMfg(rows, el) {
    var g = group(rows, function (r) { return r.brand; });
    var arr = [];
    g.forEach(function (v, k) { arr.push([k, sum(v, function (r) { return r.annual_sales_units; })]); });
    arr.sort(function (a, b) { return b[1] - a[1]; });
    arr = arr.slice(0, 10);
    var total = sum(rows, function (r) { return r.annual_sales_units; });
    draw(el, [{
      type: "bar", orientation: "h",
      y: arr.map(function (a) { return a[0]; }).reverse(),
      x: arr.map(function (a) { return a[1]; }).reverse(),
      marker: { color: PALETTE[0] },
      text: arr.map(function (a) { return (100 * a[1] / total).toFixed(1) + "%"; }).reverse(),
      textposition: "auto",
      hovertemplate: "%{y}: %{x:,.0f} units<extra></extra>"
    }], layout({ margin: { l: 120, r: 30, t: 10, b: 40 }, xaxis: { title: "Units" } }));
  }

  function buildCat(rows, el) {
    var g = group(rows, function (r) { return r.body_type; });
    var labels = [], values = [], colors = [];
    g.forEach(function (v, k) {
      labels.push(k);
      values.push(sum(v, function (r) { return r.annual_sales_units; }));
      colors.push(wavg(v, function (r) { return r.driving_range_miles; },
        function (r) { return r.annual_sales_units; }));
    });
    draw(el, [{
      type: "treemap", labels: labels, parents: labels.map(function () { return ""; }),
      values: values, branchvalues: "total",
      marker: { colors: colors, colorscale: "Teal", showscale: true,
                colorbar: { title: "Avg mi" } },
      textinfo: "label+value+percent",
      hovertemplate: "%{label}: %{value:,.0f} units<extra></extra>"
    }], layout({ margin: { l: 0, r: 0, t: 0, b: 0 } }));
  }

  function buildHeat(rows, el) {
    var byBrand = group(rows, function (r) { return r.brand; });
    var brands = [];
    byBrand.forEach(function (v, k) {
      if (sum(v, function (r) { return r.annual_sales_units; }) >= 50000) brands.push([k, sum(v, function (r) { return r.annual_sales_units; })]);
    });
    brands.sort(function (a, b) { return b[1] - a[1]; });
    brands = brands.slice(0, 10).map(function (b) { return b[0]; });
    var cats = Array.from(new Set(rows.map(function (r) { return r.body_type; }))).sort();

    var z = [], y = [], x = cats;
    brands.forEach(function (b) {
      var row = cats.map(function (c) {
        var sub = rows.filter(function (r) { return r.brand === b && r.body_type === c; });
        return sub.length >= 3
          ? sub.reduce(function (a, r) { return a + r.customer_rating; }, 0) / sub.length
          : null;
      });
      z.push(row); y.push(b);
    });
    draw(el, [{
      type: "heatmap", z: z, x: x, y: y,
      colorscale: [[0, "#f1f5f9"], [0.5, "#5eead4"], [1, "#0f766e"]],
      zmin: 3.0, zmax: 4.9, xgap: 3, ygap: 3,
      hovertemplate: "%{y} / %{x}<br>rating %{z:.2f}<extra></extra>"
    }], layout({ margin: { l: 120, r: 20, t: 10, b: 70 } }));
  }

  function modelGroups(rows) {
    var g = group(rows, function (r) { return r.brand + " " + r.model_name; });
    var out = [];
    g.forEach(function (v, k) {
      out.push({
        name: k, rows: v,
        units: sum(v, function (r) { return r.annual_sales_units; }),
        rating: v.reduce(function (a, r) { return a + r.customer_rating; }, 0) / v.length,
        range: wavg(v, function (r) { return r.driving_range_miles; },
          function (r) { return r.annual_sales_units; }),
        price: wavg(v, function (r) { return r.price_usd; }, function (r) { return r.annual_sales_units; })
      });
    });
    return out;
  }

  function buildTopModels(rows, el) {
    var m = modelGroups(rows).filter(function (x) { return x.units >= 50000; });
    m.sort(function (a, b) { return b.rating - a.rating; });
    m = m.slice(0, 12);
    if (!m.length) return empty(el);
    draw(el, [{
      type: "bar", orientation: "h",
      y: m.map(function (x) { return x.name; }).reverse(),
      x: m.map(function (x) { return x.rating; }).reverse(),
      marker: { color: PALETTE[1] },
      text: m.map(function (x) { return compact(x.units); }).reverse(),
      textposition: "auto",
      hovertemplate: "%{y}<br>rating %{x:.2f}<extra></extra>"
    }], layout({ margin: { l: 170, r: 40, t: 10, b: 40 }, xaxis: { title: "Mean rating", range: [3, 5] } }));
  }

  /* ---------- battery ---------- */

  function chemSeries(rows) {
    var g = group(rows, function (r) { return r.battery_technology; });
    var out = [];
    g.forEach(function (v, k) {
      out.push({
        tech: k,
        units: sum(v, function (r) { return r.annual_sales_units; }),
        gwh: sum(v, function (r) { return r.gwh_battery_demand; }),
        range: wavg(v, function (r) { return r.driving_range_miles; },
          function (r) { return r.annual_sales_units; }),
        charge: wavg(v, function (r) { return r.charging_time_min_10_80; },
          function (r) { return r.annual_sales_units; })
      });
    });
    return out.sort(function (a, b) { return b.units - a.units; });
  }

  function buildChemUnits(rows, el) {
    var s = chemSeries(rows);
    draw(el, [{
      type: "pie", labels: s.map(function (x) { return x.tech; }),
      values: s.map(function (x) { return x.units; }), hole: 0.45,
      marker: { colors: PALETTE },
      textinfo: "percent",
      hovertemplate: "%{label}: %{value:,.0f} units (%{percent})<extra></extra>"
    }], layout({ margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: true,
                 legend: { orientation: "h", y: -0.1 } }));
  }

  function buildChemGwh(rows, el) {
    var s = chemSeries(rows).slice().sort(function (a, b) { return b.gwh - a.gwh; });
    draw(el, [{
      type: "bar", x: s.map(function (x) { return x.tech; }),
      y: s.map(function (x) { return x.gwh; }),
      marker: { color: PALETTE },
      text: s.map(function (x) { return compact(x.gwh); }), textposition: "auto",
      hovertemplate: "%{x}: %{y:,.1f} GWh<extra></extra>"
    }], layout({ yaxis: { title: "GWh demand" } }));
  }

  function buildScatter(rows, el) {
    var traces = Array.from(new Set(rows.map(function (r) { return r.body_type; }))).map(function (bt, i) {
      var sub = rows.filter(function (r) { return r.body_type === bt; });
      return {
        type: "scatter", mode: "markers", name: bt,
        x: sub.map(function (r) { return r.battery_capacity_kwh; }),
        y: sub.map(function (r) { return r.driving_range_miles; }),
        text: sub.map(function (r) { return r.brand + " " + r.model_name; }),
        marker: { size: 7, color: PALETTE[i % PALETTE.length], opacity: 0.75 },
        hovertemplate: "%{text}<br>%{x:.0f} kWh, %{y:.0f} mi<extra></extra>"
      };
    });
    draw(el, traces, layout({
      showlegend: true, legend: { orientation: "h", y: -0.2 },
      xaxis: { title: "Battery capacity (kWh)" },
      yaxis: { title: "Driving range (miles)" }
    }));
  }

  function buildBox(rows, el) {
    var cats = Array.from(new Set(rows.map(function (r) { return r.body_type; }))).sort();
    var traces = cats.map(function (c, i) {
      var sub = rows.filter(function (r) { return r.body_type === c; });
      return {
        type: "box", name: c, y: sub.map(function (r) { return r.driving_range_miles; }),
        marker: { color: PALETTE[i % PALETTE.length] }, boxpoints: "suspectedoutliers"
      };
    });
    draw(el, traces, layout({ showlegend: false, yaxis: { title: "Range (miles)" } }));
  }

  function buildCharge(rows, el) {
    var s = chemSeries(rows).filter(function (x) { return x.charge > 0; })
      .sort(function (a, b) { return a.charge - b.charge; });
    draw(el, [{
      type: "bar", x: s.map(function (x) { return x.tech; }),
      y: s.map(function (x) { return x.charge; }),
      marker: { color: PALETTE[4] },
      text: s.map(function (x) { return x.charge.toFixed(0) + "m"; }), textposition: "auto",
      hovertemplate: "%{x}: %{y:.1f} min<extra></extra>"
    }], layout({ yaxis: { title: "Minutes 10-80%" } }));
  }

  function buildStack(rows, el) {
    var total = sum(rows, function (r) { return r.annual_sales_units; });
    var byBrand = group(rows, function (r) { return r.brand; });
    var ranked = [];
    byBrand.forEach(function (v, k) { ranked.push([k, sum(v, function (r) { return r.annual_sales_units; })]); });
    ranked.sort(function (a, b) { return b[1] - a[1]; });
    var brands = ranked.slice(0, 8).map(function (x) { return x[0]; });
    var techs = Array.from(new Set(rows.map(function (r) { return r.battery_technology; })));

    var traces = techs.map(function (t, i) {
      return {
        type: "bar", name: t,
        x: brands,
        y: brands.map(function (b) {
          var sub = rows.filter(function (r) { return r.brand === b && r.battery_technology === t; });
          return sub.length ? sum(sub, function (r) { return r.annual_sales_units; }) : 0;
        }),
        marker: { color: PALETTE[i % PALETTE.length] },
        hovertemplate: "%{x} / " + t + ": %{y:,.0f} units<extra></extra>"
      };
    });
    draw(el, traces, layout({
      barmode: "stack", showlegend: true, legend: { orientation: "h", y: -0.25 },
      yaxis: { title: "Units" }
    }));
  }

  /* ---------- global ---------- */

  function buildGeo(rows, el) {
    var g = group(rows, function (r) { return r.country_of_origin; });
    var labels = [], values = [], colors = [];
    g.forEach(function (v, k) {
      labels.push(k);
      values.push(sum(v, function (r) { return r.annual_sales_units; }));
      colors.push(sum(v, function (r) { return r.gwh_battery_demand; }));
    });
    draw(el, [{
      type: "treemap", labels: labels, parents: labels.map(function () { return ""; }),
      values: values, branchvalues: "total",
      marker: { colors: colors, colorscale: "Blues", colorbar: { title: "GWh" } },
      textinfo: "label+percent",
      hovertemplate: "%{label}: %{value:,.0f} units<extra></extra>"
    }], layout({ margin: { l: 0, r: 0, t: 0, b: 0 } }));
  }

  function buildGrid(rows, el) {
    var cars = rows.filter(function (r) {
      return ["Sedan", "SUV", "Hatchback"].indexOf(r.body_type) >= 0;
    });
    var g = group(cars, function (r) { return r.country_of_origin; });
    var arr = [];
    g.forEach(function (v, k) {
      arr.push({
        country: k, grid: v[0].grid_intensity_kgco2_per_kwh,
        saved: v.reduce(function (a, r) { return a + r.est_annual_co2e_saved_tonnes; }, 0) / v.length,
        n: v.length
      });
    });
    arr = arr.filter(function (x) { return x.n >= 5; })
      .sort(function (a, b) { return b.saved - a.saved; });
    if (!arr.length) return empty(el);
    draw(el, [{
      type: "bar", x: arr.map(function (x) { return x.country; }),
      y: arr.map(function (x) { return x.saved; }),
      marker: { color: arr.map(function (x) { return x.grid; }), colorscale: "YlOrRd",
                showscale: true, colorbar: { title: "kg/kWh" } },
      text: arr.map(function (x) { return x.saved.toFixed(2); }), textposition: "auto",
      customdata: arr.map(function (x) { return x.grid; }),
      hovertemplate: "%{x}: %{y:.2f} t/vehicle/yr<br>grid %{customdata:.2f}<extra></extra>"
    }], layout({
      xaxis: { title: "Manufacturing country (grid intensity as colour)", tickangle: -35 },
      yaxis: { title: "t CO2e avoided per vehicle / yr" }, margin: { l: 60, r: 60, t: 10, b: 90 }
    }));
  }

  function buildValue(rows, el) {
    var cars = rows.filter(function (r) {
      return ["Sedan", "SUV", "Hatchback"].indexOf(r.body_type) >= 0;
    });
    var m = modelGroups(cars).filter(function (x) { return x.units >= 100000; });
    m.forEach(function (x) { x.perMile = x.price / x.range; });
    m.sort(function (a, b) { return a.perMile - b.perMile; });
    m = m.slice(0, 12);
    if (!m.length) return empty(el);
    draw(el, [{
      type: "bar", orientation: "h",
      y: m.map(function (x) { return x.name; }).reverse(),
      x: m.map(function (x) { return x.perMile; }).reverse(),
      marker: { color: PALETTE[5] },
      text: m.map(function (x) { return "$" + x.perMile.toFixed(0); }).reverse(),
      textposition: "auto",
      hovertemplate: "%{y}: $%{x:.0f} per mile<extra></extra>"
    }], layout({ margin: { l: 170, r: 40, t: 10, b: 40 }, xaxis: { title: "USD per mile of range" } }));
  }

  function buildTable(rows, el) {
    var m = modelGroups(rows).sort(function (a, b) { return b.units - a.units; }).slice(0, 20);
    if (!m.length) return empty(el);
    var head = ["Model", "Category", "Chemistry", "Country", "Units", "Range", "Price", "Rating"];
    var body = m.map(function (x) {
      var r0 = x.rows[0];
      return [x.name, r0.body_type, r0.battery_technology, r0.country_of_origin,
              fmt(x.units), fmt(x.range) + " mi", "$" + fmt(x.price), x.rating.toFixed(2)];
    });
    el.innerHTML = "<div class='table-scroll'><table class='data-table'><thead><tr>" +
      head.map(function (h) { return "<th>" + h + "</th>"; }).join("") +
      "</tr></thead><tbody>" +
      body.map(function (row) {
        return "<tr>" + row.map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>";
      }).join("") + "</tbody></table></div>";
  }

  /* ---------- story ---------- */

  function scene(n) {
    return function (rows, el) {
      var wrap = document.createElement("div");
      wrap.className = "scene";
      var cap = document.createElement("p");
      cap.className = "scene-cap";
      var plot = document.createElement("div");
      plot.className = "plot";
      el.appendChild(wrap);
      wrap.appendChild(cap);
      wrap.appendChild(plot);

      var all = rows;
      if (n === 1) {
        var g = group(all, function (r) { return r.model_year; });
        var years = Array.from(g.keys()).sort(function (a, b) { return a - b; });
        var u = years.map(function (y) { return sum(g.get(y), function (r) { return r.annual_sales_units; }); });
        var first = u[0], last = u[u.length - 1];
        var growth = u.map(function (x, i) { return i ? (x - u[i - 1]) / u[i - 1] * 100 : null; });
        var lastG = growth[growth.length - 1];
        var growthText = (lastG === null || isNaN(lastG))
          ? "not computable with one year in scope" : lastG.toFixed(1) + "%";
        cap.innerHTML = "Volume rises from <strong>" + compact(first) + "</strong> units in " +
          years[0] + " to <strong>" + compact(last) + "</strong> in " + years[years.length - 1] +
          ", but the growth rate falls to <strong>" + growthText + "</strong>. " +
          "Weighted price drops while weighted range climbs - this is a market maturing, not stalling.";
        draw(plot, [{
          type: "scatter", mode: "lines+markers", x: years, y: u,
          line: { color: PALETTE[0], width: 3 }, marker: { size: 8 }
        }], layout({ yaxis: { title: "Units" }, xaxis: { dtick: 1 } }));
      } else if (n === 2) {
        var byy = group(all, function (r) { return r.model_year; });
        var ys = Array.from(byy.keys()).sort(function (a, b) { return a - b; });
        var leaders = ys.map(function (y) {
          var bg = group(byy.get(y), function (r) { return r.brand; });
          var best = [null, -1];
          bg.forEach(function (v, k) {
            var s = sum(v, function (r) { return r.annual_sales_units; });
            if (s > best[1]) best = [k, s];
          });
          return best[0];
        });
        cap.innerHTML = "The leader each year was <strong>" + leaders.join(" &rarr; ") +
          "</strong>. Meanwhile the top five hold a shrinking share and the number of active brands " +
          "grows from <strong>" + new Set(all.filter(function (r) { return r.model_year === ys[0]; })
            .map(function (r) { return r.brand; })).size + "</strong> to <strong>" +
          new Set(all.map(function (r) { return r.brand; })).size + "</strong>: the field is widening.";
        buildMfg(all, plot);
      } else if (n === 3) {
        var allChem = chemSeries(all);
        var s = allChem.filter(function (x) { return x.units > 100000; });
        var tu = sum(allChem, function (x) { return x.units; });
        var tg = sum(allChem, function (x) { return x.gwh; });
        var txt = s.map(function (x) {
          return "<li><strong>" + x.tech + "</strong>: " + (100 * x.units / tu).toFixed(1) +
            "% of vehicles but " + (100 * x.gwh / tg).toFixed(1) + "% of energy demand</li>";
        }).join("");
        cap.innerHTML = "Counting cars and counting kilowatt-hours give different rankings." +
          "<ul>" + txt + "</ul>";
        buildChemGwh(all, plot);
      } else {
        // Mirrors Q15 exactly: latest year, unweighted means, Sedan/SUV only,
        // emerging share measured against that year's whole volume.
        var years = Array.from(new Set(all.map(function (r) { return r.model_year; })))
          .sort(function (a, b) { return a - b; });
        var lastY = years[years.length - 1];
        var scope = all.filter(function (r) { return r.model_year === lastY; });
        var cars = scope.filter(function (r) {
          return r.body_type === "Sedan" || r.body_type === "SUV";
        });
        var solid = cars.filter(function (r) { return r.battery_technology === "Semi-Solid-State"; });
        var li = cars.filter(function (r) {
          return ["LFP", "NMC", "NCA"].indexOf(r.battery_technology) >= 0;
        });
        var emerging = scope.filter(function (r) {
          return ["Semi-Solid-State", "Sodium-Ion"].indexOf(r.battery_technology) >= 0;
        });
        if (!solid.length) {
          cap.innerHTML = "No solid-state passenger vehicles are in the current selection for " +
            lastY + ".";
          buildGrid(scope, plot);
          return;
        }
        var mean = function (list, f) {
          return list.reduce(function (a, r) { return a + f(r); }, 0) / list.length;
        };
        var sr = mean(solid, function (r) { return r.driving_range_miles; });
        var lr = mean(li, function (r) { return r.driving_range_miles; });
        var share = 100 * sum(emerging, function (r) { return r.annual_sales_units; }) /
          sum(scope, function (r) { return r.annual_sales_units; });
        cap.innerHTML = "In " + lastY + ", solid-state passenger cars average <strong>" +
          sr.toFixed(1) + "</strong> miles against <strong>" + lr.toFixed(1) +
          "</strong> for lithium-ion - but emerging chemistries are only <strong>" +
          share.toFixed(3) + "%</strong> of that year's volume, and solid-state cells carry the " +
          "highest manufacturing footprint of any chemistry in the dataset.";
        buildGrid(scope, plot);
      }
    };
  }

  /* ---------- shell ---------- */

  function buildFilterBar(host, onChange) {
    host.className = "filters";
    FILTERS.forEach(function (f) {
      var values = Array.from(new Set(ROWS.map(function (r) { return r[f.col]; })))
        .sort(function (a, b) { return a > b ? 1 : -1; });
      var wrap = document.createElement("label");
      wrap.className = "filter";
      var sel = document.createElement("select");
      sel.innerHTML = "<option value=''>All</option>" + values.map(function (v) {
        return "<option value='" + v + "'>" + v + "</option>";
      }).join("");
      sel.onchange = function () { state[f.col] = sel.value; onChange(); };
      wrap.innerHTML = "<span>" + f.label + "</span>";
      wrap.appendChild(sel);
      host.appendChild(wrap);
    });
    var reset = document.createElement("button");
    reset.className = "reset";
    reset.textContent = "Reset";
    reset.onclick = function () {
      state = {};
      host.querySelectorAll("select").forEach(function (s) { s.value = ""; });
      onChange();
    };
    host.appendChild(reset);
  }

  function render() {
    var rows = filtered();
    var count = document.getElementById("rowcount");
    if (count) count.textContent = rows.length + " of " + ROWS.length + " rows in scope";
    PAGE.forEach(function (id) {
      var host = document.getElementById("c-" + id);
      if (!host) return;
      if (!rows.length && id !== "kpi") { empty(host); return; }
      CHARTS[id].build(rows, host);
    });
  }

  function init() {
    var shell = document.getElementById("charts");
    if (!shell) return;
    PAGE = PAGES[shell.dataset.page] || [];
    var ids = PAGE;

    shell.innerHTML = ids.map(function (id) {
      var c = CHARTS[id];
      return "<section class='chart'><h3>" + c.title + "</h3>" +
        (c.note ? "<p class='muted'>" + c.note + "</p>" : "") +
        "<div class='plot' id='c-" + id + "'></div></section>";
    }).join("");

    fetch("/static/data/facts.json")
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (d) {
        ROWS = d.rows.map(function (line) {
          var o = {};
          d.cols.forEach(function (name, i) { o[name] = line[i]; });
          return o;
        });
        document.getElementById("loading").hidden = true;
        // Filters must be built after the data arrives, or the option lists are empty.
        buildFilterBar(document.getElementById("filters"), render);
        render();
      })
      .catch(function (e) {
        document.getElementById("loading").innerHTML =
          "<p class='muted'>Could not load the dataset (" + e.message + "). " +
          "Run <code>python scripts/build_site_data.py</code> to regenerate it.</p>";
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
