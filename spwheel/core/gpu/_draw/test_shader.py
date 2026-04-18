from __future__ import annotations

from .shader_builder import ShaderBuilder


def example_points_shader_builder() -> ShaderBuilder:
    return (
        ShaderBuilder("example_points", "POINTS", ndim=3, tooltip="Example points shader")
        .vertex_source(
            """
            void main()
            {
                gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0);
                gl_PointSize = size;
            }
            """
        )
        .fragment_source(
            """
            void main()
            {
                fragColor = color;
            }
            """
        )
        .uniform_float("size", default=10.0, tooltip="Size of the points")
        .uniform_vec4("color", default=(1.0, 1.0, 1.0, 1.0), tooltip="Color of the points")
    )


def example_auto_ndim_agnostic_shader_builder() -> ShaderBuilder:
    return (
        ShaderBuilder("example_auto", "ALL", ndim=0, tooltip="Example auto shader")
        .vertex_source(
            """
            void main()
            {
                gl_Position = vec4(pos, 1.0);
            }
            """
        )
        .fragment_source(
            """
            void main()
            {
                fragColor = color;
            }
            """
        )
        .uniform_vec4("color", default=(0.2, 0.8, 0.4, 1.0), tooltip="Color of the shape")
    )


def example_with_sampler_builder() -> ShaderBuilder:
    return (
        ShaderBuilder("example_texture", "TRIS", ndim=2, tooltip="Example texture shader")
        .vert_in_uv("uv", add_to_vertex_out=True, tooltip="Texture coordinates")
        .vertex_source(
            """
            void main()
            {
                v_uv = uv;
                gl_Position = vec4(pos, 0.0, 1.0);
            }
            """
        )
        .fragment_source(
            """
            void main()
            {
                fragColor = texture(tex, v_uv);
            }
            """
        )
        .sampler("tex", "FLOAT_2D", tooltip="Texture to sample")
    )


def example_generate_draw_py(out_path: str | None = None) -> None:
    example_points_shader_builder()._build()
    example_auto_ndim_agnostic_shader_builder()._build()
    example_with_sampler_builder()._build()


def init():
    example_generate_draw_py()
