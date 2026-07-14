#version 330 core

layout (location = 0) in float aX;
layout (location = 1) in float aV;
layout (location = 2) in float aSlope;
layout (location = 3) in float aSide;
layout (location = 4) in float aMat;

uniform mat4  uProj;
uniform float uAmp;
uniform float uHalfH;

out float vMat;

// A malha guarda apenas a linha neutra: x, a forma modal normalizada v e a
// inclinacao dv/dx. A espessura da viga e reconstruida aqui deslocando o
// vertice em +-h/2 ao longo da normal da curva JA escalada por uAmp. Escalar
// vertices com a espessura pre-somada afinaria a viga junto com a deflexao.
void main()
{
    float y    = aV * uAmp;
    float dydx = aSlope * uAmp;

    vec2 normal = normalize(vec2(-dydx, 1.0));
    vec2 pos    = vec2(aX, y) + aSide * uHalfH * normal;

    gl_Position = uProj * vec4(pos, 0.0, 1.0);
    vMat = aMat;
}
