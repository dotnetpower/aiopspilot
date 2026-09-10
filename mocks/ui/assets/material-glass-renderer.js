(function () {
  "use strict";

  var body = document.body;
  if (!body.classList.contains("cs-material-study")) return;

  var variants = {
    "is-essential-grid": {
      seed: 5011,
      base: [235, 237, 234],
      mottle: 5,
      grain: 2,
      pores: 0,
      aggregates: 0,
      trowel: 0,
      formwork: false,
      pattern: "grid",
      displacement: 1.2,
      mounts: false
    },
    "is-essential-marble": {
      seed: 6029,
      base: [240, 237, 230],
      mottle: 6,
      grain: 1,
      pores: 0,
      aggregates: 0,
      trowel: 0,
      formwork: false,
      pattern: "calacatta-gold",
      displacement: 1.5,
      mounts: false
    },
    "is-essential": {
      seed: 4079,
      base: [222, 224, 220],
      mottle: 18,
      grain: 5,
      pores: 140,
      aggregates: 52,
      trowel: 8,
      formwork: "minimal",
      displacement: 1.8,
      mounts: false
    },
    "is-clear-aggregate": {
      seed: 1103,
      base: [190, 193, 188],
      mottle: 34,
      grain: 15,
      pores: 520,
      aggregates: 260,
      trowel: 18,
      formwork: false,
      displacement: 2.2
    },
    "is-soft-frost": {
      seed: 2309,
      base: [201, 195, 185],
      mottle: 28,
      grain: 12,
      pores: 760,
      aggregates: 80,
      trowel: 32,
      formwork: false,
      displacement: 1.6
    },
    "is-structural-laminate": {
      seed: 3719,
      base: [169, 178, 175],
      mottle: 30,
      grain: 16,
      pores: 340,
      aggregates: 120,
      trowel: 12,
      formwork: true,
      displacement: 2.8
    }
  };

  var calacattaProfiles = [
    { angle: -0.24, scale: 1.10, flipX: false, flipY: false, offsetX: -0.03, offsetY: 0.02 },
    { angle: -0.13, scale: 1.06, flipX: true, flipY: false, offsetX: 0.04, offsetY: -0.03 },
    { angle: -0.05, scale: 1.02, flipX: false, flipY: true, offsetX: -0.05, offsetY: -0.01 },
    { angle: 0.04, scale: 1.08, flipX: true, flipY: true, offsetX: 0.02, offsetY: 0.04 },
    { angle: 0.12, scale: 1.04, flipX: false, flipY: false, offsetX: 0.05, offsetY: -0.04 },
    { angle: 0.19, scale: 1.12, flipX: true, flipY: false, offsetX: -0.02, offsetY: 0.03 },
    { angle: 0.27, scale: 1.08, flipX: false, flipY: true, offsetX: 0.03, offsetY: 0.01 },
    { angle: 0.34, scale: 1.14, flipX: true, flipY: true, offsetX: -0.04, offsetY: -0.02 },
    { angle: -0.31, scale: 1.16, flipX: false, flipY: false, offsetX: 0.01, offsetY: 0.05 },
    { angle: 0.08, scale: 1.00, flipX: true, flipY: false, offsetX: 0.00, offsetY: -0.05 }
  ];

  var variantName = Object.keys(variants).find(function (name) {
    return body.classList.contains(name);
  });
  if (!variantName) {
    throw new Error("Material study requires a registered concrete variant.");
  }

  function resolveCalacattaPattern() {
    var raw = new URLSearchParams(window.location.search).get("pattern");
    if (raw !== null) {
      if (!/^(?:[1-9]|10)$/.test(raw)) {
        throw new Error("Calacatta pattern MUST be an integer from 1 through 10.");
      }
      return Number(raw);
    }
    var randomValue = new Uint32Array(1);
    window.crypto.getRandomValues(randomValue);
    return randomValue[0] % calacattaProfiles.length + 1;
  }

  var config = Object.assign({}, variants[variantName]);
  if (config.pattern === "calacatta-gold") {
    var calacattaPattern = resolveCalacattaPattern();
    config.patternIndex = calacattaPattern - 1;
    config.seed += calacattaPattern * 7919;
    body.dataset.calacattaPattern = String(calacattaPattern);
  }
  var resizeTimer = 0;
  var lastWidth = 0;
  var lastHeight = 0;

  function seededRandom(seed) {
    var value = seed >>> 0;
    return function () {
      value += 0x6d2b79f5;
      var result = value;
      result = Math.imul(result ^ result >>> 15, result | 1);
      result ^= result + Math.imul(result ^ result >>> 7, result | 61);
      return ((result ^ result >>> 14) >>> 0) / 4294967296;
    };
  }

  function channel(value) {
    return Math.max(0, Math.min(255, Math.round(value)));
  }

  function rgba(rgb, alpha) {
    return "rgba(" + rgb.map(channel).join(",") + "," + alpha + ")";
  }

  function drawMottle(context, width, height, random) {
    var source = document.createElement("canvas");
    source.width = 48;
    source.height = 36;
    var sourceContext = source.getContext("2d");
    if (!sourceContext) throw new Error("Concrete mottle canvas is unavailable.");
    var image = sourceContext.createImageData(source.width, source.height);
    for (var index = 0; index < image.data.length; index += 4) {
      var offset = (random() - 0.5) * config.mottle;
      image.data[index] = channel(config.base[0] + offset);
      image.data[index + 1] = channel(config.base[1] + offset);
      image.data[index + 2] = channel(config.base[2] + offset);
      image.data[index + 3] = 178;
    }
    sourceContext.putImageData(image, 0, 0);
    context.save();
    context.globalAlpha = 0.74;
    context.imageSmoothingEnabled = true;
    context.filter = "blur(24px)";
    context.drawImage(source, -32, -32, width + 64, height + 64);
    context.restore();
  }

  function drawGrain(context, width, height, random) {
    var grain = document.createElement("canvas");
    grain.width = width;
    grain.height = height;
    var grainContext = grain.getContext("2d");
    if (!grainContext) throw new Error("Concrete grain canvas is unavailable.");
    var image = grainContext.createImageData(width, height);
    for (var index = 0; index < image.data.length; index += 4) {
      var tone = config.base[0] + (random() - 0.5) * config.grain * 2;
      image.data[index] = channel(tone);
      image.data[index + 1] = channel(tone + 1);
      image.data[index + 2] = channel(tone);
      image.data[index + 3] = 20 + Math.floor(random() * 26);
    }
    grainContext.putImageData(image, 0, 0);
    context.drawImage(grain, 0, 0);
  }

  function drawPores(context, width, height, random) {
    for (var index = 0; index < config.pores; index += 1) {
      var radius = 0.4 + random() * (random() < 0.08 ? 5.2 : 2.2);
      var x = random() * width;
      var y = random() * height;
      context.beginPath();
      context.ellipse(x, y, radius * (0.7 + random() * 0.8), radius, random() * Math.PI, 0, Math.PI * 2);
      context.fillStyle = rgba([62, 68, 65], 0.035 + random() * 0.12);
      context.fill();
      if (radius > 2.6) {
        context.beginPath();
        context.ellipse(x - 0.6, y - 0.6, radius * 0.52, radius * 0.42, 0, 0, Math.PI * 2);
        context.fillStyle = rgba([245, 246, 242], 0.08);
        context.fill();
      }
    }
  }

  function drawAggregates(context, width, height, random) {
    for (var index = 0; index < config.aggregates; index += 1) {
      var radius = 0.7 + random() * 3.2;
      var shade = random() < 0.5 ? [91, 99, 94] : [224, 225, 219];
      context.beginPath();
      context.arc(random() * width, random() * height, radius, 0, Math.PI * 2);
      context.fillStyle = rgba(shade, 0.05 + random() * 0.13);
      context.fill();
    }
  }

  function drawTrowelMarks(context, width, height, random) {
    context.save();
    context.lineCap = "round";
    for (var index = 0; index < config.trowel; index += 1) {
      var x = random() * width;
      var y = random() * height;
      var length = 120 + random() * 520;
      context.beginPath();
      context.moveTo(x, y);
      context.bezierCurveTo(
        x + length * 0.3,
        y + (random() - 0.5) * 26,
        x + length * 0.7,
        y + (random() - 0.5) * 26,
        x + length,
        y + (random() - 0.5) * 14
      );
      context.strokeStyle = rgba(random() < 0.5 ? [245, 245, 240] : [87, 92, 88], 0.025 + random() * 0.04);
      context.lineWidth = 1 + random() * 3;
      context.stroke();
    }
    context.restore();
  }

  function drawGrid(context, width, height) {
    if (config.pattern !== "grid") return;
    context.save();
    for (var x = 0; x <= width; x += 72) {
      context.beginPath();
      context.moveTo(x + 0.5, 0);
      context.lineTo(x + 0.5, height);
      context.strokeStyle = rgba([91, 105, 100], x % 288 === 0 ? 0.13 : 0.07);
      context.lineWidth = 1;
      context.stroke();
    }
    for (var y = 0; y <= height; y += 72) {
      context.beginPath();
      context.moveTo(0, y + 0.5);
      context.lineTo(width, y + 0.5);
      context.strokeStyle = rgba([91, 105, 100], y % 288 === 0 ? 0.13 : 0.07);
      context.lineWidth = 1;
      context.stroke();
    }
    context.restore();
  }

  function drawMarble(context, width, height, random) {
    if (config.pattern !== "calacatta-gold") return;
    context.save();
    context.lineCap = "round";
    var profile = calacattaProfiles[config.patternIndex];
    context.translate(
      width / 2 + profile.offsetX * width,
      height / 2 + profile.offsetY * height
    );
    context.rotate(profile.angle);
    context.scale(
      profile.flipX ? -profile.scale : profile.scale,
      profile.flipY ? -profile.scale : profile.scale
    );
    context.translate(-width / 2, -height / 2);

    function drawMarbleCloud(centerX, centerY, radiusX, radiusY, color, alpha, count) {
      context.save();
      context.filter = "blur(18px)";
      for (var cloudIndex = 0; cloudIndex < count; cloudIndex += 1) {
        var cloudX = centerX + (random() - 0.5) * radiusX;
        var cloudY = centerY + (random() - 0.5) * radiusY;
        context.beginPath();
        context.ellipse(
          cloudX,
          cloudY,
          radiusX * (0.14 + random() * 0.24),
          radiusY * (0.10 + random() * 0.20),
          random() * Math.PI,
          0,
          Math.PI * 2
        );
        context.fillStyle = rgba(color, alpha * (0.55 + random() * 0.65));
        context.fill();
      }
      context.restore();
    }

    function drawMineralPocket(origin, scale) {
      context.save();
      for (var layer = 0; layer < 5; layer += 1) {
        var sides = 5 + Math.floor(random() * 3);
        context.beginPath();
        for (var side = 0; side < sides; side += 1) {
          var angle = Math.PI * 2 * side / sides + (random() - 0.5) * 0.25;
          var radius = scale * (0.30 + random() * 0.42);
          var x = origin[0] + Math.cos(angle) * radius;
          var y = origin[1] + Math.sin(angle) * radius * 0.55;
          if (side === 0) context.moveTo(x, y);
          else context.lineTo(x, y);
        }
        context.closePath();
        context.fillStyle = rgba([204, 181, 137], 0.020 + layer * 0.007);
        context.strokeStyle = rgba([158, 127, 75], 0.06 + layer * 0.018);
        context.lineWidth = 0.7;
        context.fill();
        context.stroke();
      }
      context.restore();
    }

    function point(x, y, jitterX, jitterY) {
      return [
        x * width + (random() - 0.5) * jitterX,
        y * height + (random() - 0.5) * jitterY
      ];
    }

    function traceVein(points) {
      context.beginPath();
      context.moveTo(points[0][0], points[0][1]);
      for (var index = 1; index < points.length - 1; index += 1) {
        var next = points[index + 1];
        context.quadraticCurveTo(
          points[index][0],
          points[index][1],
          (points[index][0] + next[0]) / 2,
          (points[index][1] + next[1]) / 2
        );
      }
      var last = points[points.length - 1];
      context.lineTo(last[0], last[1]);
    }

    function strokeVein(points, color, alpha, lineWidth) {
      traceVein(points);
      context.strokeStyle = rgba(color, alpha);
      context.lineWidth = lineWidth;
      context.stroke();
    }

    function branchFrom(origin, angle, length) {
      var perpendicular = angle + Math.PI / 2;
      return [
        [origin[0], origin[1]],
        [
          origin[0] + Math.cos(angle) * length * 0.35 + Math.cos(perpendicular) * (random() - 0.5) * 34,
          origin[1] + Math.sin(angle) * length * 0.35 + Math.sin(perpendicular) * (random() - 0.5) * 34
        ],
        [
          origin[0] + Math.cos(angle) * length * 0.72 + Math.cos(perpendicular) * (random() - 0.5) * 48,
          origin[1] + Math.sin(angle) * length * 0.72 + Math.sin(perpendicular) * (random() - 0.5) * 48
        ],
        [
          origin[0] + Math.cos(angle) * length,
          origin[1] + Math.sin(angle) * length
        ]
      ];
    }

    var families = [
      [
        [-90, height * 0.08],
        point(0.12, 0.12, 70, 70),
        point(0.28, 0.31, 90, 90),
        point(0.46, 0.38, 100, 110),
        point(0.66, 0.64, 100, 120),
        point(0.84, 0.73, 90, 100),
        [width + 90, height * 0.92]
      ],
      [
        [width * 0.69, -90],
        point(0.64, 0.16, 80, 80),
        point(0.76, 0.31, 90, 90),
        point(0.70, 0.49, 80, 100),
        point(0.84, 0.66, 90, 100),
        point(0.80, 0.84, 70, 90),
        [width * 0.90, height + 90]
      ],
      [
        [-90, height * 0.76],
        point(0.15, 0.68, 80, 80),
        point(0.30, 0.81, 90, 100),
        point(0.47, 0.72, 90, 90),
        point(0.60, 0.91, 80, 80),
        [width * 0.70, height + 80]
      ]
    ];

    var secondaryFamilies = [
      [
        point(0.02, 0.42, 30, 50),
        point(0.13, 0.35, 50, 60),
        point(0.25, 0.47, 60, 70),
        point(0.39, 0.43, 50, 60)
      ],
      [
        point(0.58, 0.08, 50, 40),
        point(0.67, 0.18, 60, 60),
        point(0.62, 0.31, 50, 70),
        point(0.74, 0.40, 60, 60)
      ],
      [
        point(0.52, 0.64, 60, 60),
        point(0.63, 0.58, 60, 60),
        point(0.73, 0.71, 70, 70),
        point(0.88, 0.67, 60, 60)
      ],
      [
        point(0.18, 0.91, 50, 40),
        point(0.29, 0.82, 70, 60),
        point(0.41, 0.90, 70, 50),
        point(0.52, 0.84, 60, 50)
      ]
    ];

    drawMarbleCloud(width * 0.16, height * 0.23, width * 0.34, height * 0.30, [142, 145, 141], 0.045, 18);
    drawMarbleCloud(width * 0.76, height * 0.46, width * 0.38, height * 0.34, [154, 148, 137], 0.038, 20);
    drawMarbleCloud(width * 0.36, height * 0.84, width * 0.40, height * 0.22, [133, 139, 136], 0.035, 15);
    drawMarbleCloud(width * 0.90, height * 0.78, width * 0.20, height * 0.26, [187, 164, 122], 0.032, 10);
    drawMarbleCloud(width * 0.48, height * 0.48, width * 0.24, height * 0.20, [176, 158, 127], 0.026, 12);

    families.forEach(function (family, familyIndex) {
      var mainVein = familyIndex < 2;
      strokeVein(family, [132, 135, 132], mainVein ? 0.016 : 0.011, (mainVein ? 62 : 36) + random() * 28);
      strokeVein(family, [116, 122, 119], mainVein ? 0.034 : 0.024, (mainVein ? 18 : 11) + random() * 9);
      strokeVein(family, [99, 108, 104], mainVein ? 0.082 : 0.062, (mainVein ? 5 : 3.5) + random() * 4);
      strokeVein(family, [72, 84, 80], mainVein ? 0.11 : 0.085, 2.4 + random() * 1.8);

      if (familyIndex < 2) {
        var goldSection = family.slice(familyIndex + 1, familyIndex + 5);
        strokeVein(goldSection, [192, 164, 114], 0.032, 13 + random() * 8);
        strokeVein(goldSection, [170, 139, 84], 0.12, 2.4 + random() * 2.8);
        strokeVein(goldSection, [137, 103, 58], 0.18, 1.8 + random() * 1.5);
      }

      var branchCount = familyIndex < 2 ? 3 : 2;
      for (var branchIndex = 0; branchIndex < branchCount; branchIndex += 1) {
        var anchor = family[1 + Math.floor(random() * (family.length - 2))];
        var direction = (random() < 0.5 ? -1 : 1) * (0.35 + random() * 0.65);
        var branch = branchFrom(anchor, direction, 90 + random() * 210);
        var goldBranch = familyIndex < 2 && branchIndex === 0;
        strokeVein(branch, goldBranch ? [184, 151, 96] : [110, 119, 115], goldBranch ? 0.07 : 0.04, 5 + random() * 3);
        strokeVein(branch, goldBranch ? [143, 108, 60] : [78, 90, 85], goldBranch ? 0.14 : 0.08, 2 + random() * 1.2);
      }
    });

    secondaryFamilies.forEach(function (family, familyIndex) {
      strokeVein(family, [135, 137, 133], 0.014, 24 + random() * 16);
      strokeVein(family, [108, 115, 111], 0.042, 7 + random() * 5);
      strokeVein(family, [79, 91, 86], 0.085, 2.2 + random() * 1.8);
      if (familyIndex === 1 || familyIndex === 3) {
        strokeVein(family.slice(1), [190, 163, 112], 0.030, 9 + random() * 5);
        strokeVein(family.slice(1), [158, 126, 75], 0.13, 2 + random() * 1.5);
      }
    });

    drawMineralPocket(families[0][3], 50);
    drawMineralPocket(families[1][2], 38);
    drawMineralPocket(families[2][3], 32);
    drawMineralPocket(secondaryFamilies[2][1], 28);

    context.restore();
  }

  function drawFormwork(context, width, height, random) {
    if (!config.formwork) return;
    function drawTieHole(x, y, opacity) {
      context.beginPath();
      context.arc(x, y, 6, 0, Math.PI * 2);
      context.fillStyle = rgba([66, 76, 72], opacity);
      context.fill();
      context.beginPath();
      context.arc(x - 1, y - 1, 3, 0, Math.PI * 2);
      context.fillStyle = rgba([231, 235, 231], opacity * 0.8);
      context.fill();
    }
    context.save();
    if (config.formwork === "minimal") {
      context.strokeStyle = rgba([67, 78, 74], 0.08);
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(0, Math.round(height * 0.56));
      context.lineTo(width, Math.round(height * 0.56));
      context.stroke();
      drawTieHole(72, Math.round(height * 0.24), 0.12);
      drawTieHole(width - 72, Math.round(height * 0.72), 0.12);
      context.restore();
      return;
    }
    context.strokeStyle = rgba([67, 78, 74], 0.18);
    context.lineWidth = 1;
    var rowHeight = 168;
    for (var y = rowHeight; y < height; y += rowHeight) {
      context.beginPath();
      context.moveTo(0, y + (random() - 0.5) * 3);
      context.lineTo(width, y + (random() - 0.5) * 3);
      context.stroke();
    }
    for (var row = 0; row * rowHeight < height; row += 1) {
      var seam = 180 + random() * (width - 360);
      context.beginPath();
      context.moveTo(seam, row * rowHeight);
      context.lineTo(seam, Math.min(height, (row + 1) * rowHeight));
      context.stroke();
      [84, width - 84].forEach(function (x) {
        var holeY = row * rowHeight + rowHeight / 2;
        drawTieHole(x, holeY, 0.25);
      });
    }
    context.restore();
  }

  function installRefractionFilter() {
    if (document.getElementById("physical-glass-refraction")) return;
    var namespace = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(namespace, "svg");
    svg.setAttribute("class", "material-filter-defs");
    svg.setAttribute("aria-hidden", "true");
    var filter = document.createElementNS(namespace, "filter");
    filter.setAttribute("id", "physical-glass-refraction");
    filter.setAttribute("x", "-8%");
    filter.setAttribute("y", "-8%");
    filter.setAttribute("width", "116%");
    filter.setAttribute("height", "116%");
    var turbulence = document.createElementNS(namespace, "feTurbulence");
    turbulence.setAttribute("type", "fractalNoise");
    turbulence.setAttribute("baseFrequency", "0.009 0.028");
    turbulence.setAttribute("numOctaves", "1");
    turbulence.setAttribute("seed", String(config.seed % 97));
    turbulence.setAttribute("result", "refraction-noise");
    var displacement = document.createElementNS(namespace, "feDisplacementMap");
    displacement.setAttribute("in", "SourceGraphic");
    displacement.setAttribute("in2", "refraction-noise");
    displacement.setAttribute("scale", String(config.displacement));
    displacement.setAttribute("xChannelSelector", "R");
    displacement.setAttribute("yChannelSelector", "G");
    filter.append(turbulence, displacement);
    svg.append(filter);
    document.body.append(svg);
  }

  function installMounts() {
    if (config.mounts === false) return;
    document.querySelectorAll(".glass-slide").forEach(function (slide) {
      ["tl", "tr", "bl", "br"].forEach(function (position) {
        var mount = document.createElement("span");
        mount.className = "glass-mount is-" + position;
        mount.setAttribute("aria-hidden", "true");
        slide.append(mount);
      });
    });
  }

  function renderConcrete() {
    var width = Math.max(1440, Math.min(2200, Math.ceil(window.innerWidth * 1.35)));
    var height = Math.max(1200, Math.min(2000, Math.ceil(document.documentElement.scrollHeight * 1.15)));
    if (Math.abs(width - lastWidth) < 96 && Math.abs(height - lastHeight) < 96) return;
    lastWidth = width;
    lastHeight = height;
    var canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    var context = canvas.getContext("2d", { alpha: false });
    if (!context) throw new Error("Concrete renderer canvas is unavailable.");
    var random = seededRandom(config.seed + width * 13 + height * 17);
    context.fillStyle = "rgb(" + config.base.join(",") + ")";
    context.fillRect(0, 0, width, height);
    drawMottle(context, width, height, random);
    drawMarble(context, width, height, random);
    drawGrain(context, width, height, random);
    drawGrid(context, width, height);
    drawTrowelMarks(context, width, height, random);
    drawAggregates(context, width, height, random);
    drawPores(context, width, height, random);
    drawFormwork(context, width, height, random);
    var texture = 'url("' + canvas.toDataURL("image/jpeg", 0.9) + '")';
    document.documentElement.style.setProperty("--concrete-texture", texture);
    document.documentElement.style.setProperty("--texture-width", width + "px");
    document.documentElement.style.setProperty("--texture-height", height + "px");
    body.classList.add("is-material-ready");
  }

  installRefractionFilter();
  installMounts();
  renderConcrete();

  window.addEventListener("resize", function () {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(renderConcrete, 180);
  });
})();
