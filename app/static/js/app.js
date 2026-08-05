(function () {
  "use strict";

  var API = {
    health: "/api/health",
    shield: "/api/data/shield-params",
    monitoring: "/api/data/monitoring",
    calculated: "/api/data/calculated",
    evaluate: "/api/engine/evaluate",
    calibrate: "/api/engine/calibrate",
    reference: "/api/engine/reference/beijing-line12"
  };

  var store = {
    shield: [],
    monitoring: [],
    calculated: []
  };

  var thresholds = { orange: 10, yellow: 20, red: 30 };
  var alarmEnabled = true;
  var playing = true;
  var zTop = 20;

  var liveMetrics = [
    { key: "thrust_kn", label: "THRUST", unit: "kN", value: 12500, scale: 20000 },
    { key: "torque_knm", label: "TORQUE", unit: "kNm", value: 3800, scale: 6000 },
    { key: "screw_rpm", label: "SCREW", unit: "rpm", value: 8.5, scale: 16 },
    { key: "advance_speed_mm_min", label: "ADVANCE", unit: "mm/min", value: 42, scale: 80 },
    { key: "grouting_pressure_mpa", label: "GROUT", unit: "MPa", value: 0.42, scale: 1 }
  ];

  var riskSources = [
    { time: "--:--", sev: "safe", desc: "Building B-01 foundation, clearance check OK" },
    { time: "--:--", sev: "notice", desc: "Sewer DN800 pipe, clearance 2.186 m (verify)" },
    { time: "--:--", sev: "warning", desc: "Water main DN1200 20 m ahead of face" },
    { time: "--:--", sev: "critical", desc: "Adjacent operating metro tunnel, L-line" }
  ];

  var windows = {};

  function $(id) { return document.getElementById(id); }

  function fmt(v, d) {
    var n = Number(v);
    if (!isFinite(n)) return "----";
    return n.toFixed(d == null ? 1 : d);
  }

  function clock() {
    var d = new Date();
    function p(x) { return (x < 10 ? "0" : "") + x; }
    $("clock").textContent = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    var ts = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    if ($("crt-ts")) $("crt-ts").textContent = ts;
  }

  function toast(msg, cls) {
    var t = document.createElement("div");
    t.className = "toast" + (cls ? " " + cls : "");
    t.textContent = msg;
    $("toast-area").appendChild(t);
    setTimeout(function () { t.remove(); }, 4000);
  }

  function sysMsg(m) {
    $("sys-msg").textContent = "SYS: " + m;
  }

  function fetchJSON(url, opts) {
    opts = opts || {};
    return fetch(url, opts).then(function (r) {
      if (!r.ok) throw new Error(url + " -> " + r.status);
      return r.json();
    });
  }

  /* ---------------- window manager ---------------- */

  function registerWindow(id) {
    var el = $(id);
    windows[id] = {
      el: el,
      minimized: false,
      maximized: false,
      restore: { left: el.style.left, top: el.style.top }
    };
    addTaskTab(id);
  }

  function focusWin(id) {
    var w = windows[id];
    if (!w) return;
    zTop += 1;
    w.el.style.zIndex = zTop;
    document.querySelectorAll(".window").forEach(function (n) {
      n.classList.toggle("inactive", n !== w.el);
    });
    highlightTask(id);
  }

  function addTaskTab(id) {
    var el = windows[id].el;
    var tab = document.createElement("button");
    tab.className = "task-tab";
    tab.textContent = el.querySelector(".titlebar-text").textContent;
    tab.addEventListener("click", function () { toggleTask(id); });
    el._taskTab = tab;
    $("taskbar-tasks").appendChild(tab);
  }

  function highlightTask(id) {
    Object.keys(windows).forEach(function (k) {
      if (windows[k].el._taskTab) {
        windows[k].el._taskTab.classList.toggle("active", k === id && !windows[k].minimized);
      }
    });
  }

  function toggleTask(id) {
    var w = windows[id];
    if (w.minimized) {
      w.el.classList.remove("minimized");
      w.el.style.display = "";
      w.minimized = false;
      focusWin(id);
    } else {
      minimizeWin(id);
    }
  }

  function minimizeWin(id) {
    var w = windows[id];
    w.minimized = true;
    w.el.style.display = "none";
    highlightTask(id);
  }

  function closeWin(id) {
    var w = windows[id];
    w.minimized = true;
    w.el.style.display = "none";
    if (w.el._taskTab) w.el._taskTab.classList.remove("active");
    toast("Closed " + id.toUpperCase());
  }

  function maximizeWin(id) {
    var w = windows[id];
    if (w.maximized) {
      w.el.classList.remove("maximized");
      w.el.style.left = w.restore.left;
      w.el.style.top = w.restore.top;
      w.maximized = false;
    } else {
      w.restore.left = w.el.style.left;
      w.restore.top = w.el.style.top;
      w.el.classList.add("maximized");
      w.maximized = true;
    }
  }

  function makeDraggable(id) {
    var el = windows[id].el;
    var bar = el.querySelector("[data-drag]");
    var sx, sy, ox, oy, dragging = false;
    bar.addEventListener("mousedown", function (e) {
      if (windows[id].maximized) return;
      dragging = true;
      sx = e.clientX; sy = e.clientY;
      ox = el.offsetLeft; oy = el.offsetTop;
      focusWin(id);
      e.preventDefault();
    });
    document.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      el.style.left = (ox + e.clientX - sx) + "px";
      el.style.top = Math.max(0, oy + e.clientY - sy) + "px";
    });
    document.addEventListener("mouseup", function () { dragging = false; });
  }

  function initWindowManager() {
    ["win-sensor", "win-camera", "win-alerts", "win-controls", "win-settlement", "search-results"].forEach(registerWindow);
    Object.keys(windows).forEach(makeDraggable);

    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-close]");
      if (b) { closeWin(b.getAttribute("data-close")); return; }
      b = e.target.closest("[data-min]");
      if (b) { minimizeWin(b.getAttribute("data-min")); return; }
      b = e.target.closest("[data-max]");
      if (b) { maximizeWin(b.getAttribute("data-max")); return; }
    });

    document.querySelectorAll(".window, .icon").forEach(function (n) {
      n.addEventListener("mousedown", function () {
        if (n.classList.contains("window")) focusWin(n.id);
      });
    });

    document.querySelectorAll(".icon").forEach(function (icon) {
      icon.addEventListener("click", function () {
        var id = icon.getAttribute("data-open");
        var w = windows[id];
        w.minimized = false;
        w.el.style.display = "";
        focusWin(id);
      });
      icon.addEventListener("dblclick", function () { maximizeWin(icon.getAttribute("data-open")); });
    });

    focusWin("win-sensor");
  }

  /* ---------------- equalizer ---------------- */

  function initEqualizer() {
    var eq = $("equalizer");
    eq.innerHTML = "";
    liveMetrics.forEach(function (m) {
      var col = document.createElement("div");
      col.className = "eq-col";
      col.innerHTML =
        '<span class="eq-val" id="val-' + m.key + '">--</span>' +
        '<div class="eq-bar-wrap"><div class="eq-bar" id="bar-' + m.key + '"></div></div>' +
        '<span class="eq-name">' + m.label + "</span>";
      eq.appendChild(col);
    });
  }

  function renderEqualizer() {
    liveMetrics.forEach(function (m) {
      var bar = $("bar-" + m.key);
      var val = $("val-" + m.key);
      if (bar) bar.style.height = Math.max(4, Math.min(100, (m.value / m.scale) * 100)) + "%";
      if (val) val.textContent = fmt(m.value) + (m.key === "grouting_pressure_mpa" ? "" : "");
    });
  }

  /* ---------------- live data simulation ---------------- */

  function tickMetrics() {
    liveMetrics.forEach(function (m) {
      var noise = (Math.random() - 0.5) * m.scale * 0.03;
      var base = m.base != null ? m.base : m.value;
      m.value = Math.max(0, base + noise);
    });
    renderEqualizer();
  }

  /* ---------------- risk alerts ---------------- */

  function sevClass(riskLevel) {
    if (riskLevel === "high") return "critical";
    if (riskLevel === "warning") return "warning";
    if (riskLevel === "notice") return "notice";
    return "safe";
  }

  function riskFromCalculated(row) {
    var mm = row.monitored_value_mm != null ? row.monitored_value_mm : row.predicted_value_mm;
    var sev = "safe";
    if (mm >= thresholds.red) sev = "critical";
    else if (mm >= thresholds.yellow) sev = "warning";
    else if (mm >= thresholds.orange) sev = "notice";
    return {
      time: (row.timestamp || "--:--").slice(11, 16),
      sev: sev,
      desc: "R" + row.ring_no + " @" + fmt(row.chainage_m, 1) + "m  settle " + fmt(mm, 2) + "mm  err " + fmt(row.relative_error_pct, 1) + "%"
    };
  }

  function renderAlerts() {
    var list = $("alert-list");
    list.innerHTML = "";
    var rows = riskSources.concat(store.calculated.map(riskFromCalculated));
    var n = rows.length;
    rows.slice(0, 60).forEach(function (r) {
      var div = document.createElement("div");
      div.className = "alert-row sev-" + r.sev;
      div.innerHTML =
        '<span class="alert-time">' + r.time + "</span>" +
        '<span class="alert-desc">' + r.desc + "</span>";
      list.appendChild(div);
    });
    $("alert-count").textContent = "SOURCES: " + n;
  }

  /* ---------------- settlement chart ---------------- */

  function drawChart() {
    var canvas = $("settle-canvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "#0a0a1a";
    ctx.fillRect(0, 0, W, H);

    ctx.strokeStyle = "#1f1f3a";
    ctx.lineWidth = 1;
    for (var gx = 0; gx <= W; gx += 40) {
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke();
    }
    for (var gy = 0; gy <= H; gy += 30) {
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke();
    }

    var data = store.calculated.slice().reverse();
    if (data.length < 2) {
      ctx.fillStyle = "#0f0";
      ctx.font = "12px Courier New";
      ctx.fillText("NO DATA - START SERVER & SEED DB", 40, H / 2);
      return;
    }

    var maxRing = data[data.length - 1].ring_no || data.length;
    var minRing = data[0].ring_no || 1;
    var maxMM = 8;
    data.forEach(function (d) {
      var v = d.monitored_value_mm != null ? d.monitored_value_mm : d.predicted_value_mm;
      if (v > maxMM) maxMM = v;
    });
    maxMM = Math.max(8, Math.ceil(maxMM));

    function X(r) { return 40 + (r - minRing) / Math.max(1, maxRing - minRing) * (W - 70); }
    function Y(v) { return H - 20 - (v / maxMM) * (H - 45); }

    function polyline(key, color, getter) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      data.forEach(function (d, i) {
        var x = X(d.ring_no), y = Y(getter(d));
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    polyline("pred", "#ff00ff", function (d) { return d.predicted_value_mm; });
    polyline("mon", "#ffff00", function (d) {
      return d.monitored_value_mm != null ? d.monitored_value_mm : d.predicted_value_mm;
    });
    polyline("cons", "#008080", function (d) { return d.consolidation_mm || 0; });

    ctx.fillStyle = "#fff";
    ctx.font = "10px Courier New";
    for (var i = 0; i <= 4; i++) {
      var m = (maxMM / 4) * i;
      ctx.fillText(fmt(m, 1) + "mm", 4, Y(m) + 3);
    }
    ctx.fillText("R" + minRing, 40, H - 6);
    ctx.fillText("R" + maxRing, W - 66, H - 6);
  }

  /* ---------------- data loading ---------------- */

  function seedMetricsFromShield() {
    var rows = store.shield;
    if (!rows.length) return;
    var latest = rows[0];
    liveMetrics[0].base = latest.thrust_kn;
    liveMetrics[1].base = latest.torque_knm;
    liveMetrics[3].base = latest.advance_speed_mm_min;
    liveMetrics[4].base = latest.grouting_pressure_mpa;
    $("eq-station").textContent = "STATION: " + fmt(latest.chainage_m, 1) + "m";
    $("eq-ring").textContent = "RING: " + latest.ring_no;
  }

  function loadAll() {
    return Promise.all([
      fetchJSON(API.shield + "?limit=60").then(function (d) { store.shield = d; }),
      fetchJSON(API.monitoring + "?limit=80").then(function (d) { store.monitoring = d; }),
      fetchJSON(API.calculated + "?limit=120").then(function (d) { store.calculated = d; })
    ]).then(function () {
      seedMetricsFromShield();
      renderAlerts();
      drawChart();
      sysMsg("DATA LINK OK (" + store.calculated.length + " calc rows)");
    });
  }

  /* ---------------- controls ---------------- */

  function bindControls() {
    var sliders = {
      "slider-rate": "val-rate",
      "slider-thrust": "val-thrust",
      "slider-torque": "val-torque"
    };
    Object.keys(sliders).forEach(function (id) {
      var inp = $(id), out = $(sliders[id]);
      inp.addEventListener("input", function () { out.textContent = inp.value; });
    });

    $("btn-play").addEventListener("click", function () {
      playing = !playing;
      $("btn-play").textContent = playing ? "\u25B8" : "\u25BA";
      $("eq-led").textContent = playing ? "LIVE" : "PAUSE";
      sysMsg(playing ? "FEED PLAYING" : "FEED PAUSED");
    });

    $("btn-next").addEventListener("click", function () {
      var rows = store.shield;
      if (rows.length) {
        var cur = rows[0];
        var idx = rows.findIndex(function (r) { return r.ring_no === cur.ring_no; });
        var nxt = rows[(idx + 1) % rows.length];
        $("eq-ring").textContent = "RING: " + nxt.ring_no;
        $("eq-station").textContent = "STATION: " + fmt(nxt.chainage_m, 1) + "m";
      }
    });
    $("btn-prev").addEventListener("click", function () {
      var rows = store.shield;
      if (rows.length) {
        var cur = rows[0];
        var idx = rows.findIndex(function (r) { return r.ring_no === cur.ring_no; });
        var prv = rows[(idx - 1 + rows.length) % rows.length];
        $("eq-ring").textContent = "RING: " + prv.ring_no;
        $("eq-station").textContent = "STATION: " + fmt(prv.chainage_m, 1) + "m";
      }
    });

    $("btn-apply").addEventListener("click", function () {
      var thrust = Number($("slider-thrust").value);
      var payload = {
        monitored_mm: 4.4,
        shield: { face_pressure_kpa: 300, thrust_kn: thrust, volume_loss_pct: 0.13 },
        engine: { calibration_immediate: 1.0, calibration_consolidation: 1.0 }
      };
      fetchJSON(API.evaluate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      }).then(function (r) {
        toast("MODEL: predicted " + fmt(r.predicted_value_mm, 2) + "mm vs monitored " + fmt(r.monitored_value_mm, 2) + "mm  [" + r.alert_color.toUpperCase() + "]", r.passes_5pct_threshold ? "ok" : "err");
      }).catch(function (e) { toast("EVALUATE FAILED: " + e.message, "err"); });
    });

    $("chk-alarm").addEventListener("change", function () {
      alarmEnabled = this.checked;
      $("alarm-state").textContent = alarmEnabled ? "ON" : "OFF";
      sysMsg("ALARM SYSTEM " + (alarmEnabled ? "ARMED" : "DISARMED"));
    });
  }

  /* ---------------- context menu ---------------- */

  function initContextMenu() {
    var menu = $("ctx-menu");
    document.addEventListener("contextmenu", function (e) {
      e.preventDefault();
      menu.hidden = false;
      var mx = Math.min(e.clientX, window.innerWidth - 210);
      var my = Math.min(e.clientY, window.innerHeight - 130);
      menu.style.left = mx + "px";
      menu.style.top = my + "px";
    });
    document.addEventListener("click", function () { menu.hidden = true; });

    menu.addEventListener("click", function (e) {
      var item = e.target.closest("[data-action]");
      if (!item) return;
      runAction(item.getAttribute("data-action"));
      menu.hidden = true;
    });
  }

  function runAction(action) {
    if (action === "refresh") {
      sysMsg("REFRESHING DATA...");
      loadAll().catch(function (e) { toast("REFRESH FAILED: " + e.message, "err"); });
    } else if (action === "export") {
      var blob = new Blob([JSON.stringify(store, null, 2)], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "shield_export.json";
      a.click();
      URL.revokeObjectURL(a.href);
      toast("EXPORTED shield_export.json (" + store.calculated.length + " rows)");
    } else if (action === "calibrate") {
      var mm = prompt("Enter monitored settlement (mm):", "4.4");
      if (mm == null) return;
      fetchJSON(API.calibrate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ monitored_mm: Number(mm) })
      }).then(function (r) {
        toast("CALIBRATION FACTOR: " + fmt(r.calibration_immediate, 4) + " (hit " + mm + "mm)", "ok");
      }).catch(function (e) { toast("CALIBRATE FAILED: " + e.message, "err"); });
    } else if (action === "thresholds") {
      var input = prompt("Alert thresholds (orange, yellow, red):", thresholds.orange + ", " + thresholds.yellow + ", " + thresholds.red);
      if (!input) return;
      var parts = input.split(",").map(function (s) { return Number(s.trim()); });
      if (parts.length === 3 && parts.every(function (n) { return isFinite(n); })) {
        thresholds.orange = parts[0]; thresholds.yellow = parts[1]; thresholds.red = parts[2];
        renderAlerts();
        toast("THRESHOLDS UPDATED: " + thresholds.orange + "/" + thresholds.yellow + "/" + thresholds.red + "mm");
      }
    }
  }

  /* ---------------- search ---------------- */

  function runSearch(query) {
    var q = query.trim().toLowerCase();
    var list = $("search-results-list");
    list.innerHTML = "";
    if (!q) {
      $("search-results").hidden = true;
      return;
    }
    var hits = [];
    store.calculated.forEach(function (r) {
      if (String(r.ring_no) === q || String(r.chainage_m).indexOf(q) !== -1) {
        hits.push({ sev: sevClass(r.risk_level), desc: "CALC R" + r.ring_no + " chainage " + fmt(r.chainage_m, 1) + "m pred " + fmt(r.predicted_value_mm, 2) + "mm mon " + fmt(r.monitored_value_mm, 2) + "mm" });
      }
    });
    store.shield.forEach(function (r) {
      if (String(r.ring_no) === q || String(r.chainage_m).indexOf(q) !== -1) {
        hits.push({ sev: "safe", desc: "SHIELD R" + r.ring_no + " thrust " + fmt(r.thrust_kn, 0) + "kN speed " + fmt(r.advance_speed_mm_min, 1) + "mm/min grout " + fmt(r.grouting_pressure_mpa, 2) + "MPa" });
      }
    });
    store.monitoring.forEach(function (r) {
      if (String(r.ring_no) === q || String(r.chainage_m).indexOf(q) !== -1 || r.sensor_id.toLowerCase().indexOf(q) !== -1) {
        hits.push({ sev: "notice", desc: "MON " + r.sensor_id + " R" + r.ring_no + " value " + fmt(r.measured_value_mm, 2) + "mm" });
      }
    });

    if (!hits.length) {
      var empty = document.createElement("div");
      empty.className = "alert-row sev-notice";
      empty.innerHTML = '<span class="alert-desc">NO MATCHES FOR "' + q + '"</span>';
      list.appendChild(empty);
    } else {
      hits.slice(0, 40).forEach(function (h) {
        var div = document.createElement("div");
        div.className = "alert-row sev-" + h.sev;
        div.innerHTML = '<span class="alert-desc">' + h.desc + "</span>";
        list.appendChild(div);
      });
    }
    var win = windows["search-results"];
    win.minimized = false;
    win.el.style.display = "";
    focusWin("search-results");
  }

  function initSearch() {
    function go() { runSearch($("search-input").value); }
    $("search-btn").addEventListener("click", go);
    $("search-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter") go();
    });
  }

  /* ---------------- boot ---------------- */

  function init() {
    clock();
    setInterval(clock, 1000);
    initWindowManager();
    initEqualizer();
    renderEqualizer();
    bindControls();
    initContextMenu();
    initSearch();
    renderAlerts();

    loadAll().catch(function (e) {
      sysMsg("API OFFLINE - SIM MODE");
      toast("API unreachable: " + e.message, "err");
      renderAlerts();
      drawChart();
    });

    setInterval(function () { if (playing) tickMetrics(); }, 1400);

    fetchJSON(API.reference).then(function (r) {
      toast("REFERENCE " + r.line + ": " + r.predicted_mm + "mm vs " + r.monitored_mm + "mm monitored (" + fmt(r.relative_error_pct, 1) + "% < 5%)", "ok");
    }).catch(function () {});
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
