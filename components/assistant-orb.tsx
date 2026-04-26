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

// Hash & value noise.
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
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

  // Time accelerates on hover.
  float t = u_time * mix(0.18, 0.55, u_hover);

  // Two flow fields drifting opposite directions: gives the swirl.
  float n1 = fbm(uv * 3.5 + vec2( t * 0.6,  t * 0.4));
  float n2 = fbm(uv * 5.0 + vec2(-t * 0.5,  t * 0.7) + 11.3);
  float n  = mix(n1, n2, 0.5);

  // Soft circular mask + fluid edge ripple from the noise.
  float edgeSoft = mix(0.020, 0.060, u_hover);
  float radius  = 0.46 + (n - 0.5) * 0.05;
  float mask    = smoothstep(radius, radius - edgeSoft, d);
  float halo    = smoothstep(0.62, 0.46, d) * mix(0.18, 0.32, u_hover);

  // Color: deep accent in center, brighter accent toward edges, modulated by noise.
  vec3 deep   = u_color * 0.55;
  vec3 bright = mix(u_color, vec3(1.0), 0.35);
  float radialMix = smoothstep(0.0, 0.45, d);            // center → edge
  float swirlMix  = smoothstep(0.35, 0.75, n);
  vec3 col = mix(deep, bright, radialMix * 0.6 + swirlMix * 0.4);

  // Specular: small white highlight that drifts gently.
  vec2 specOff = vec2(-0.14 + sin(t * 0.8) * 0.02,
                       0.16 + cos(t * 0.6) * 0.015);
  float spec = smoothstep(0.10, 0.0, length(uv - specOff));
  col += vec3(spec) * mix(0.35, 0.6, u_hover);

  // Hover slightly brightens the whole sphere.
  col *= mix(1.0, 1.15, u_hover);

  // Halo (premultiplied alpha-friendly).
  vec3 haloCol = u_color * halo;
  vec3 outCol  = col * mask + haloCol * (1.0 - mask);
  float a = clamp(mask + halo, 0.0, 1.0);

  gl_FragColor = vec4(outCol, a);
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
