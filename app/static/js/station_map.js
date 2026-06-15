// app/static/js/station_map.js
// Embedded Leaflet map of selectable tide stations. Pins fill the existing form.
(function () {
  'use strict';

  var COUNTRY_COLORS = { USA: '#1f6feb', Canada: '#d1242f' };

  function fillForm(stationId, name) {
    var search = document.getElementById('station_search');
    var hidden = document.getElementById('station_id');
    if (!search || !hidden) return;
    search.value = name + ' (' + stationId + ')';
    hidden.value = stationId;
    document.querySelector('.form-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
    var year = document.getElementById('year');
    if (year) year.focus();
    if (window.plausible) {
      plausible('Map Station Selected', { props: { station_id: stationId, place_name: name } });
    }
  }
  window._tideMapFillForm = fillForm; // exposed for popup button + e2e

  function popupHtml(props) {
    var div = document.createElement('div');
    div.className = 'station-popup';
    var name = document.createElement('span');
    name.className = 'popup-name';
    name.textContent = props.name;
    var meta = document.createElement('span');
    meta.className = 'popup-meta';
    meta.textContent = props.country + ' · ' + props.station_id;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'quick-generate-btn';
    btn.textContent = 'Use this station';
    btn.addEventListener('click', function () { fillForm(props.station_id, props.name); });
    div.appendChild(name); div.appendChild(meta); div.appendChild(btn);
    return div;
  }

  function init() {
    var el = document.getElementById('station-map');
    if (!el || typeof L === 'undefined') return;

    var map = L.map(el, { scrollWheelZoom: false }).setView([45, -100], 3);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    var clusters = L.markerClusterGroup({ chunkedLoading: true });
    map.addLayer(clusters);

    var markersByCountry = { USA: [], Canada: [] };

    function rebuild(country) {
      clusters.clearLayers();
      var show = [];
      Object.keys(markersByCountry).forEach(function (c) {
        if (country === 'all' || country === c) show = show.concat(markersByCountry[c]);
      });
      clusters.addLayers(show);
      if (show.length) {
        var group = L.featureGroup(show);
        map.fitBounds(group.getBounds().pad(0.1));
      }
    }

    window.tideMap = { showCountry: rebuild };

    fetch('/api/stations.geojson')
      .then(function (r) { return r.json(); })
      .then(function (geo) {
        geo.features.forEach(function (f) {
          var p = f.properties;
          var coords = f.geometry.coordinates; // [lng, lat]
          var color = COUNTRY_COLORS[p.country] || '#666';
          var marker = L.circleMarker([coords[1], coords[0]], {
            radius: 5, color: color, weight: 1, fillColor: color, fillOpacity: 0.7,
          });
          marker.bindPopup(function () { return popupHtml(p); });
          (markersByCountry[p.country] || (markersByCountry[p.country] = [])).push(marker);
        });
        // Respect the current country filter selection on first paint.
        var checked = document.querySelector('input[name="country_filter"]:checked');
        rebuild(checked ? checked.value : 'all');
      })
      .catch(function (e) {
        console.error('Failed to load station map data:', e);
        var msg = document.createElement('p');
        msg.style.padding = '1rem';
        msg.textContent = 'Map data could not be loaded.';
        el.textContent = '';
        el.appendChild(msg);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
