"use client";

import { useEffect, useRef } from "react";

/**
 * Animated assistant orb — WebGL fragment shader.
 *
 * Tiny hand-rolled WebGL setup, no deps. Renders a soft radial sphere
 * tinted with the app's --primary color, with fbm noise giving the
 * fluid metaball / Siri-style motion. Falls back to a CSS-only static
 * dot if WebGL isn't available.
 *
 * - Reads `--primary` from `:root` (HSL → RGB) so it follows the theme.
 *   Re-reads on `<html>` class changes (theme toggle).
 * - Hover ramp: listens to the closest `.assistant-orb-host` parent's
 *   mouseenter/mouseleave and passes a 0→1 uniform that the shader
 *   uses to push intensity, contrast, and animation speed.
 * - Pauses the RAF loop when the document is hidden (browsers throttle
 *   anyway, this is belt-and-braces).
 * - Respects `prefers-reduced-motion` (no time advance, halo only).
 */
const VERT = `
attribute vec2 a;
varying vec2 v;
void main() {
  v = a * 0.5 + 0.5;
  gl_Position = vec4(a, 0.0, 1.0);
}
`;

const FRAG = `
precision highp float;
varying vec2 v;
uniform float u_time;
uniform float u_hover;   // 0..1, smoothed
uniform vec3  u_color;   // primary (linear RGB)

#define PI 3.14159265

// Hash & value noise.
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i),                hash(i + vec2(1.0, 0.0)), u.x),
    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}
float fbm(vec2 p) {
  float s = 0.0;
  float a = 0.55;
  for (int i = 0; i < 5; i++) {
    s += a * noise(p);
    p *= 2.05;
    a *= 0.5;
  }
  return s;
}

void main() {
  vec2 uv = v - 0.5;
  float d = length(uv);
  float ang = atan(uv.y, uv.x);

  // Time scales with hover (faster when active).
  float t = u_time * mix(0.45, 1.10, u_hover);

  // Animated radial wobble: a few angular harmonics so the rim breathes.
  float wob = fbm(vec2(ang * 1.4 + t * 0.7, t * 0.3)) - 0.5;
  float rimMid    = 0.41 + wob * 0.030;
  float rimWidth  = mix(0.060, 0.090, u_hover);          // wider, more visible

  // Pulsing brightness around the ring — bands of light travel around.
  float bandPulse = 0.55 + 0.45 *
    (sin(ang * 3.0 + t * 1.6) * sin(ang * 2.0 - t * 1.1)) * 0.5;
  // Soft Gaussian rim band.
  float r = (d - rimMid) / rimWidth;
  float rim = exp(-r * r) * (0.75 + 0.55 * bandPulse);

  // Wider inner shell at low alpha — gives the rim depth, fades inward.
  float shellD = (d - (rimMid - 0.05)) / 0.16;
  float shell  = exp(-shellD * shellD) * mix(0.20, 0.32, u_hover);
  shell *= step(d, rimMid + 0.005);

  // Iridescence: stronger contrast, faster cycles, more colors.
  float hueAng = ang / (2.0 * PI) + 0.5;
  float cyc1 = sin(hueAng * 6.0 * PI + t * 2.2) * 0.5 + 0.5;
  float cyc2 = cos(hueAng * 4.0 * PI - t * 1.4) * 0.5 + 0.5;
  float cyc3 = sin(hueAng * 2.0 * PI + t * 0.7) * 0.5 + 0.5;
  vec3 tintCyan    = mix(u_color, vec3(0.30, 0.95, 1.00), 0.75);
  vec3 tintMagenta = mix(u_color, vec3(1.00, 0.50, 0.95), 0.75);
  vec3 tintWarm    = mix(u_color, vec3(1.00, 0.90, 0.55), 0.55);
  vec3 rimCol = mix(u_color, tintCyan,    cyc1);
  rimCol      = mix(rimCol,  tintMagenta, cyc2 * 0.75);
  rimCol      = mix(rimCol,  tintWarm,    cyc3 * 0.45);
  // Bright gleam where bands peak.
  rimCol += vec3(0.30) * pow(bandPulse, 2.0);

  // Interior wisps: visible, drifting, bigger movement.
  vec2 flow = vec2(t * 0.85, -t * 0.65);
  float w1 = fbm(uv * 5.0 + flow);
  float w2 = fbm(uv * 8.5 - flow * 0.7 + 9.7);
  float wisp = mix(w1, w2, 0.5);
  float interiorMask = smoothstep(rimMid, 0.0, d);
  // Pop the wisps with contrast so they read as real motion.
  wisp = smoothstep(0.35, 0.85, wisp);
  float interior = wisp * interiorMask * mix(0.22, 0.40, u_hover);

  // Specular reflection — bright drifting spot inside the bubble.
  vec2 specPos = vec2(-0.12 + sin(t * 0.7) * 0.04,
                       0.16 + cos(t * 0.5) * 0.030);
  float specD = length(uv - specPos) / 0.085;
  float spec = exp(-specD * specD) * mix(0.65, 1.00, u_hover);

  // Smaller faster highlight, lower right.
  vec2 sp2 = vec2(0.13 + sin(t * 1.3) * 0.04,
                 -0.09 + cos(t * 1.7) * 0.030);
  float sp2D = length(uv - sp2) / 0.05;
  float spec2 = exp(-sp2D * sp2D) * 0.45;

  // Outer halo — glow outside the rim, breathes.
  float haloD = (d - (rimMid + 0.08)) / 0.08;
  float haloPulse = 0.85 + 0.20 * sin(t * 0.9);
  float halo = exp(-haloD * haloD) * mix(0.28, 0.50, u_hover) * haloPulse;
  halo *= step(d, rimMid + 0.30);

  // Compose. Color contribution scaled by its own coverage.
  vec3  col   = rimCol * rim
              + u_color * shell * 1.1
              + u_color * interior * 1.2
              + vec3(1.0) * (spec + spec2)
              + rimCol * halo * 0.85;
  float alpha = rim * 0.95
              + shell * 0.65
              + interior * 0.90
              + (spec + spec2) * 0.90
              + halo * 0.65;

  gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
}
`;

function readPrimaryRGB(): [number, number, number] {
  if (typeof window === "undefined") return [0.45, 0.6, 0.4];
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue("--primary")
    .trim();
  // raw is "H S% L%" — e.g. "110 22% 45%"
  const m = raw.match(/(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%/);
  if (!m) return [0.45, 0.6, 0.4];
  const h = parseFloat(m[1]) / 360;
  const s = parseFloat(m[2]) / 100;
  const l = parseFloat(m[3]) / 100;
  return hslToRgb(h, s, l);
}

function hslToRgb(h: number, s: number, l: number): [number, number, number] {
  if (s === 0) return [l, l, l];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const hue = (t: number) => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  return [hue(h + 1 / 3), hue(h), hue(h - 1 / 3)];
}

function compile(gl: WebGLRenderingContext, type: number, src: string) {
  const sh = gl.createShader(type)!;
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    console.error(gl.getShaderInfoLog(sh));
    gl.deleteShader(sh);
    return null;
  }
  return sh;
}

export function AssistantOrb({ size = 56 }: { size?: number }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const gl = canvas.getContext("webgl", {
      alpha: true,
      premultipliedAlpha: false,
      antialias: true,
    });
    if (!gl) return; // falls back to no-op; the radial-gradient CSS shows through.

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;

    const vs = compile(gl, gl.VERTEX_SHADER, VERT);
    const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return;
    const prog = gl.createProgram()!;
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      console.error(gl.getProgramInfoLog(prog));
      return;
    }
    gl.useProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
      gl.STATIC_DRAW
    );
    const aLoc = gl.getAttribLocation(prog, "a");
    gl.enableVertexAttribArray(aLoc);
    gl.vertexAttribPointer(aLoc, 2, gl.FLOAT, false, 0, 0);

    const uTime = gl.getUniformLocation(prog, "u_time");
    const uHover = gl.getUniformLocation(prog, "u_hover");
    const uColor = gl.getUniformLocation(prog, "u_color");

    let color = readPrimaryRGB();

    // Theme: re-read on <html> class change.
    const themeObserver = new MutationObserver(() => {
      color = readPrimaryRGB();
    });
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    // Hover: smoothed 0→1 driven by parent's mouseenter/leave.
    let hoverTarget = 0;
    let hoverNow = 0;
    const host = canvas.closest(".assistant-orb-host") as HTMLElement | null;
    const onEnter = () => { hoverTarget = 1; };
    const onLeave = () => { hoverTarget = 0; };
    host?.addEventListener("mouseenter", onEnter);
    host?.addEventListener("mouseleave", onLeave);

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.clearColor(0, 0, 0, 0);

    let raf = 0;
    let running = !document.hidden;
    const start = performance.now();

    function frame(now: number) {
      const t = reduceMotion ? 0 : (now - start) / 1000;
      // Smooth hover (~150 ms time constant on enter, ~250 ms on leave).
      const k = hoverTarget > hoverNow ? 0.12 : 0.06;
      hoverNow += (hoverTarget - hoverNow) * k;

      gl!.clear(gl!.COLOR_BUFFER_BIT);
      gl!.uniform1f(uTime, t);
      gl!.uniform1f(uHover, hoverNow);
      gl!.uniform3f(uColor, color[0], color[1], color[2]);
      gl!.drawArrays(gl!.TRIANGLE_STRIP, 0, 4);

      if (running) raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    function onVis() {
      running = !document.hidden;
      if (running) raf = requestAnimationFrame(frame);
      else cancelAnimationFrame(raf);
    }
    document.addEventListener("visibilitychange", onVis);

    return () => {
      cancelAnimationFrame(raf);
      themeObserver.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      host?.removeEventListener("mouseenter", onEnter);
      host?.removeEventListener("mouseleave", onLeave);
      gl.deleteProgram(prog);
      gl.deleteBuffer(buf);
      gl.deleteShader(vs);
      gl.deleteShader(fs);
    };
  }, [size]);

  return (
    <span
      aria-hidden
      className="relative inline-block"
      style={{ width: size, height: size }}
    >
      <canvas
        ref={canvasRef}
        style={{
          width: "100%",
          height: "100%",
          display: "block",
          background: "transparent",
        }}
      />
    </span>
  );
}
