#version 330 core

in float vMat;

out vec4 FragColor;

uniform vec3  uSteel;
uniform vec3  uTitanium;
uniform float uShade;

void main()
{
    vec3 color = mix(uSteel, uTitanium, step(0.5, vMat));
    FragColor = vec4(color * uShade, 1.0);
}
