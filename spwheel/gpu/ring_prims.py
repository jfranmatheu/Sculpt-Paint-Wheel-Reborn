"""Ring primitives: anti-aliased annular sectors (a wedge of a ring, a whole ring, a disc).

Ported from flexspace ``gpu/ring_prims.py``. Drawn in the current model-view (wheel-local units under the
wheel's matrix, so ``prefs.scale`` applies), edges anti-aliased with ``fwidth`` at any scale.

    sector(cx, cy, r0, r1, a0=0, a1=2pi, fill, border=None, border_w=0, gap=0, round_=0, soft=0) -> bool
        r0 / r1     inner / outer radius (r0 = 0: a disc or a pie slice).
        a0 / a1     angles in radians, counter-clockwise from +x (a1 - a0 >= 2pi: the whole ring).
        fill        RGBA; border: RGBA of an inner stroke ``border_w`` wide.
        gap         a clear band that wide between neighbouring sectors (half on each side).
        round_      corner rounding of the sector (units).
        soft        an extra blur of the edge (a soft shadow: a dark fill and a few units of softness).
"""
from math import pi, tau

import bpy
import gpu
from gpu.types import GPUShaderCreateInfo, GPUStageInterfaceInfo
from gpu_extras.batch import batch_for_shader

from ..core.gpu.state_control import CM_GPU_BLEND


_state: dict = {'shader': None, 'failed': False, 'batch': None}

_VERT = '''
void main()
{
  v_p = (pos * 2.0 - 1.0) * (u_geom.w + u_style.w + 2.0);
  vec2 q = u_geom.xy + v_p;
  gl_Position = u_mvp0 * q.x + u_mvp1 * q.y + u_mvp3; /* (The model-view-projection at z = 0.) */
}
'''

_FRAG = '''
vec3 srgb_to_lin(vec3 c) {
  /* Exact sRGB -> linear (pow(c, 2.2) crushes the darks). */
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
void main()
{
  float r = length(v_p);
  float r0 = u_geom.z, r1 = u_geom.w;
  float gap = u_style.y * 0.5, rr = u_style.z, soft = u_style.w;
  /* Radial distance (outside > 0), the sector shrunk by the rounding. */
  float dr = max(r0 - r, r - r1) + rr;
  if (r0 <= 0.0) {
    dr = r - r1 + rr;
  }
  /* Angular distance (iq's pie): the sector turned so that its middle is +y, folded about it. */
  float half_a = u_ang.y;
  float da = -1e6;
  if (half_a < 3.14159) {
    float t = 1.5707963 - u_ang.x;
    float c = cos(t), s = sin(t);
    vec2 q = vec2(c * v_p.x - s * v_p.y, s * v_p.x + c * v_p.y);
    q.x = abs(q.x);
    vec2 cs = vec2(sin(half_a), cos(half_a));
    da = length(q - cs * max(dot(q, cs), 0.0)) * sign(cs.y * q.x - cs.x * q.y);
    da += gap + rr;
  }
  vec2 dd = vec2(dr, da);
  float d = length(max(dd, 0.0)) + min(max(dd.x, dd.y), 0.0) - rr;
  float fw = max(fwidth(d), 1e-4);
  float cov = clamp(0.5 - d / (fw + soft), 0.0, 1.0);
  if (soft > 0.0) {
    cov = smoothstep(0.0, 1.0, cov);
  }
  if (cov <= 0.0) {
    discard;
  }
  vec4 pf = vec4(u_fill.rgb * u_fill.a, u_fill.a);
  float tb = (u_style.x > 0.0) ? clamp(0.5 - (-d - u_style.x) / fw, 0.0, 1.0) * u_border.a : 0.0;
  vec4 col = vec4(u_border.rgb, 1.0) * tb + pf * (1.0 - tb);
  col *= cov;
  /* (Same colour handling as the other wheel shaders.) */
  fragColor = vec4(srgb_to_lin(col.rgb / max(col.a, 1e-5)), col.a);
}
'''


def _shader():
    if _state['shader'] is not None or _state['failed'] or bpy.app.background:
        return _state['shader']
    try:
        iface = GPUStageInterfaceInfo('spw_ring_sector_iface')
        iface.smooth('VEC2', 'v_p')
        info = GPUShaderCreateInfo()
        # Within 128 B of push constants: of the MVP only the columns a z = 0 point needs (0, 1, 3).
        info.push_constant('VEC4', 'u_mvp0')
        info.push_constant('VEC4', 'u_mvp1')
        info.push_constant('VEC4', 'u_mvp3')
        info.push_constant('VEC4', 'u_geom')    # (cx, cy, r0, r1)
        info.push_constant('VEC4', 'u_style')   # (border width, gap, rounding, softness)
        info.push_constant('VEC4', 'u_fill')
        info.push_constant('VEC4', 'u_border')
        info.push_constant('VEC2', 'u_ang')     # (middle angle, half sweep)
        info.vertex_in(0, 'VEC2', 'pos')
        info.vertex_out(iface)
        info.fragment_out(0, 'VEC4', 'fragColor')
        info.vertex_source(_VERT)
        info.fragment_source(_FRAG)
        sh = gpu.shader.create_from_info(info)
        _state['batch'] = batch_for_shader(sh, 'TRI_FAN', {'pos': ((0, 0), (1, 0), (1, 1), (0, 1))})
        _state['shader'] = sh
    except Exception as ex:  # (Never again this session.)
        print("[spwheel.ring_prims] shader failed:", ex)
        _state['failed'] = True
    return _state['shader']


def sector(cx: float, cy: float, r0: float, r1: float, a0: float = 0.0, a1: float = tau, fill=(1, 1, 1, 1),
           border=None, border_w: float = 0.0, gap: float = 0.0, round_: float = 0.0, soft: float = 0.0) -> bool:
    sh = _shader()
    if sh is None:
        return False
    sweep = a1 - a0
    half = pi if sweep >= tau - 1e-6 else max(sweep * .5, 0.0)
    mvp = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    with CM_GPU_BLEND('ALPHA'):
        sh.bind()
        sh.uniform_float('u_mvp0', mvp.col[0])
        sh.uniform_float('u_mvp1', mvp.col[1])
        sh.uniform_float('u_mvp3', mvp.col[3])
        sh.uniform_float('u_geom', (float(cx), float(cy), max(float(r0), 0.0), float(r1)))
        sh.uniform_float('u_ang', ((a0 + a1) * .5, half))
        sh.uniform_float('u_style', (float(border_w), float(gap), float(round_), float(soft)))
        sh.uniform_float('u_fill', tuple(float(v) for v in fill))
        sh.uniform_float('u_border', tuple(float(v) for v in (border or (0.0, 0.0, 0.0, 0.0))))
        _state['batch'].draw(sh)
    return True


# ----- Capsule (a pill: a rectangle with round ends) ---------------------------------------------------------
# One anti-aliased shape (so a translucent fill has no darker overlaps), with the same border / colour handling
# as the sectors.

_cap_state: dict = {'shader': None, 'failed': False, 'batch': None}

_CAP_VERT = '''
void main()
{
  v_p = (pos * 2.0 - 1.0) * vec2(u_geom.z + u_geom.w + 2.0, u_geom.w + 2.0);
  vec2 q = u_geom.xy + v_p;
  gl_Position = u_mvp0 * q.x + u_mvp1 * q.y + u_mvp3;
}
'''

_CAP_FRAG = '''
vec3 srgb_to_lin(vec3 c) {
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
void main()
{
  /* Distance to a capsule: half straight length u_geom.z, radius u_geom.w. */
  vec2 q = vec2(max(abs(v_p.x) - u_geom.z, 0.0), v_p.y);
  float d = length(q) - u_geom.w;
  float fw = max(fwidth(d), 1e-4);
  float cov = clamp(0.5 - d / fw, 0.0, 1.0);
  if (cov <= 0.0) {
    discard;
  }
  vec4 pf = vec4(u_fill.rgb * u_fill.a, u_fill.a);
  float tb = (u_style.x > 0.0) ? clamp(0.5 - (-d - u_style.x) / fw, 0.0, 1.0) * u_border.a : 0.0;
  vec4 col = vec4(u_border.rgb, 1.0) * tb + pf * (1.0 - tb);
  col *= cov;
  fragColor = vec4(srgb_to_lin(col.rgb / max(col.a, 1e-5)), col.a);
}
'''


def _cap_shader():
    if _cap_state['shader'] is not None or _cap_state['failed'] or bpy.app.background:
        return _cap_state['shader']
    try:
        iface = GPUStageInterfaceInfo('spw_capsule_iface')
        iface.smooth('VEC2', 'v_p')
        info = GPUShaderCreateInfo()
        info.push_constant('VEC4', 'u_mvp0')
        info.push_constant('VEC4', 'u_mvp1')
        info.push_constant('VEC4', 'u_mvp3')
        info.push_constant('VEC4', 'u_geom')    # (cx, cy, half straight length, radius)
        info.push_constant('VEC4', 'u_style')   # (border width, -, -, -)
        info.push_constant('VEC4', 'u_fill')
        info.push_constant('VEC4', 'u_border')
        info.vertex_in(0, 'VEC2', 'pos')
        info.vertex_out(iface)
        info.fragment_out(0, 'VEC4', 'fragColor')
        info.vertex_source(_CAP_VERT)
        info.fragment_source(_CAP_FRAG)
        sh = gpu.shader.create_from_info(info)
        _cap_state['batch'] = batch_for_shader(sh, 'TRI_FAN', {'pos': ((0, 0), (1, 0), (1, 1), (0, 1))})
        _cap_state['shader'] = sh
    except Exception as ex:  # (Never again this session.)
        print("[spwheel.ring_prims] capsule shader failed:", ex)
        _cap_state['failed'] = True
    return _cap_state['shader']


def capsule(x: float, y: float, w: float, h: float, fill=(1, 1, 1, 1), border=None, border_w: float = 0.0) -> bool:
    """A pill with its bottom-left corner at (x, y), ``w`` wide and ``h`` high (round ends of radius h / 2)."""
    sh = _cap_shader()
    if sh is None:
        return False
    r = h * 0.5
    mvp = gpu.matrix.get_projection_matrix() @ gpu.matrix.get_model_view_matrix()
    with CM_GPU_BLEND('ALPHA'):
        sh.bind()
        sh.uniform_float('u_mvp0', mvp.col[0])
        sh.uniform_float('u_mvp1', mvp.col[1])
        sh.uniform_float('u_mvp3', mvp.col[3])
        sh.uniform_float('u_geom', (float(x + w * 0.5), float(y + r), max(float(w * 0.5 - r), 0.0), float(r)))
        sh.uniform_float('u_style', (float(border_w), 0.0, 0.0, 0.0))
        sh.uniform_float('u_fill', tuple(float(v) for v in fill))
        sh.uniform_float('u_border', tuple(float(v) for v in (border or (0.0, 0.0, 0.0, 0.0))))
        _cap_state['batch'].draw(sh)
    return True
