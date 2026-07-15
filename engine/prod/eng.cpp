#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include "shader.h"
#include "stb_easy_font.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

#ifdef _WIN32
#include <windows.h>
#endif

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// Resultados FEA
// ---------------------------------------------------------------------------

// Espelha o layout gravado por modelo_matematico/exportar_engine.py.
struct Config {
    std::uint32_t             nSamples = 0;
    float                     pSteel   = 0.0f;
    std::vector<float>        freq;   // [nModes]
    std::vector<float>        x;      // [nSamples]
    std::vector<float>        v;      // [nModes * nSamples]
    std::vector<float>        slope;  // [nModes * nSamples]
    std::vector<std::uint8_t> mat;    // [nSamples]
};

struct BeamData {
    std::uint32_t       nModes = 0;
    float               L = 0.0f;
    float               h = 0.0f;
    std::vector<Config> configs;
};

static fs::path exeDir()
{
#ifdef _WIN32
    char buffer[MAX_PATH];
    DWORD n = GetModuleFileNameA(nullptr, buffer, MAX_PATH);
    if (n > 0 && n < MAX_PATH)
        return fs::path(buffer).parent_path();
#endif
    return fs::current_path();
}

// Procura o asset ao lado do executavel primeiro (para onde o CMake copia),
// depois nos caminhos usuais relativos a raiz do repositorio.
static fs::path findAsset(const std::string& relative)
{
    const fs::path candidates[] = {
        exeDir() / relative,
        fs::current_path() / relative,
        fs::current_path() / "output" / relative,
        fs::current_path() / "engine" / "prod" / relative,
        exeDir() / ".." / relative,
    };

    for (const fs::path& candidate : candidates) {
        std::error_code ec;
        if (fs::exists(candidate, ec))
            return candidate;
    }

    return fs::path(relative);
}

template <typename T>
static bool readInto(std::ifstream& f, T* dst, std::size_t count)
{
    f.read(reinterpret_cast<char*>(dst), static_cast<std::streamsize>(count * sizeof(T)));
    return static_cast<bool>(f);
}

static bool loadBeam(const fs::path& path, BeamData& out)
{
    std::ifstream f(path, std::ios::binary);
    if (!f.is_open()) {
        std::cerr << "ERRO: nao foi possivel abrir " << path << "\n"
                  << "Gere o arquivo com: python -m modelo_matematico.exportar_engine\n";
        return false;
    }

    char magic[4];
    if (!readInto(f, magic, 4) || magic[0] != 'V' || magic[1] != 'I' ||
        magic[2] != 'G' || magic[3] != 'A') {
        std::cerr << "ERRO: " << path << " nao e um arquivo VIGA.\n";
        return false;
    }

    std::uint32_t version = 0;
    std::uint32_t nConfig = 0;

    if (!readInto(f, &version, 1) || !readInto(f, &nConfig, 1) ||
        !readInto(f, &out.nModes, 1) || !readInto(f, &out.L, 1) ||
        !readInto(f, &out.h, 1)) {
        std::cerr << "ERRO: cabecalho truncado em " << path << "\n";
        return false;
    }

    if (version != 1) {
        std::cerr << "ERRO: versao " << version << " nao suportada (esperado 1).\n";
        return false;
    }

    out.configs.resize(nConfig);

    for (std::uint32_t ic = 0; ic < nConfig; ++ic) {
        Config& c = out.configs[ic];

        if (!readInto(f, &c.nSamples, 1) || !readInto(f, &c.pSteel, 1)) {
            std::cerr << "ERRO: configuracao " << ic << " truncada.\n";
            return false;
        }

        const std::size_t n  = c.nSamples;
        const std::size_t nm = out.nModes;

        c.freq.resize(nm);
        c.x.resize(n);
        c.v.resize(nm * n);
        c.slope.resize(nm * n);
        c.mat.resize(n);

        if (!readInto(f, c.freq.data(), nm) || !readInto(f, c.x.data(), n) ||
            !readInto(f, c.v.data(), nm * n) || !readInto(f, c.slope.data(), nm * n) ||
            !readInto(f, c.mat.data(), n)) {
            std::cerr << "ERRO: configuracao " << ic << " truncada.\n";
            return false;
        }
    }

    return true;
}

// ---------------------------------------------------------------------------
// Estado da aplicacao
// ---------------------------------------------------------------------------

struct AppState {
    BeamData beam;
    int   config    = 100;
    int   mode      = 0;
    float scale     = 0.25f;
    float scaleMax  = 0.41f;
    float speed     = 1.0f;
    bool  paused    = false;
    bool  showSpine = true;
    bool  showHud   = true;
    bool  dirty     = true;
};

static AppState app;

// A vista e ortografica e uniforme nos dois eixos: a viga aparece na proporcao
// real de 60:1. A altura da caixa vem da largura e do aspecto da janela, e a
// escala da deflexao e limitada para o modo nao sair do quadro.
static glm::mat4 projection(int width, int height, float L, float h)
{
    const float xLo = -0.25f;
    const float xHi = L + 0.15f;
    const float w   = xHi - xLo;

    const float aspect = (height > 0) ? (float)width / (float)height : 1.0f;
    const float boxH   = w / std::max(aspect, 0.01f);

    app.scaleMax = std::max(0.05f, boxH * 0.5f * 0.94f - h);
    app.scale    = std::min(app.scale, app.scaleMax);

    return glm::ortho(xLo, xHi, -boxH * 0.5f, boxH * 0.5f, -1.0f, 1.0f);
}

static void framebufferSizeCallback(GLFWwindow*, int width, int height)
{
    glViewport(0, 0, width, height);
}

static void keyCallback(GLFWwindow* window, int key, int, int action, int mods)
{
    if (action != GLFW_PRESS && action != GLFW_REPEAT)
        return;

    const int nConfig = (int)app.beam.configs.size();
    const int nModes  = (int)app.beam.nModes;
    const int step    = (mods & GLFW_MOD_SHIFT) ? 10 : 1;

    switch (key) {
        case GLFW_KEY_ESCAPE:
            glfwSetWindowShouldClose(window, true);
            break;
        case GLFW_KEY_LEFT:
            app.config = std::max(0, app.config - step);
            app.dirty = true;
            break;
        case GLFW_KEY_RIGHT:
            app.config = std::min(nConfig - 1, app.config + step);
            app.dirty = true;
            break;
        case GLFW_KEY_UP:
            app.mode = std::min(nModes - 1, app.mode + 1);
            app.dirty = true;
            break;
        case GLFW_KEY_DOWN:
            app.mode = std::max(0, app.mode - 1);
            app.dirty = true;
            break;
        case GLFW_KEY_EQUAL:
        case GLFW_KEY_KP_ADD:
            app.scale = std::min(app.scaleMax, app.scale + 0.02f);
            break;
        case GLFW_KEY_MINUS:
        case GLFW_KEY_KP_SUBTRACT:
            app.scale = std::max(0.02f, app.scale - 0.02f);
            break;
        case GLFW_KEY_PERIOD:
            app.speed = std::min(4.0f, app.speed * 1.25f);
            break;
        case GLFW_KEY_COMMA:
            app.speed = std::max(0.1f, app.speed / 1.25f);
            break;
        case GLFW_KEY_SPACE:
            app.paused = !app.paused;
            break;
        case GLFW_KEY_S:
            app.showSpine = !app.showSpine;
            break;
        case GLFW_KEY_H:
            app.showHud = !app.showHud;
            break;
        case GLFW_KEY_R:
            app.config = 100;
            app.mode   = 0;
            app.scale  = 0.25f;
            app.speed  = 1.0f;
            app.paused = false;
            app.dirty  = true;
            break;
        default:
            break;
    }
}

// ---------------------------------------------------------------------------
// Malha
// ---------------------------------------------------------------------------

// Cada amostra da linha neutra gera dois vertices, um por face da viga. O
// vertex shader os separa em +-h/2 ao longo da normal da curva escalada.
static void buildMesh(const BeamData& beam, int ic, int mode,
                      std::vector<float>& ribbon,
                      std::vector<unsigned int>& indices,
                      std::vector<float>& spine)
{
    const Config& c = beam.configs[ic];
    const std::size_t n = c.nSamples;

    const float* v = &c.v[(std::size_t)mode * n];
    const float* s = &c.slope[(std::size_t)mode * n];

    ribbon.clear();
    spine.clear();
    indices.clear();
    ribbon.reserve(n * 2 * 5);
    spine.reserve(n * 5);
    indices.reserve((n - 1) * 6);

    for (std::size_t i = 0; i < n; ++i) {
        const float m = (float)c.mat[i];

        for (float side : {-1.0f, 1.0f}) {
            ribbon.push_back(c.x[i]);
            ribbon.push_back(v[i]);
            ribbon.push_back(s[i]);
            ribbon.push_back(side);
            ribbon.push_back(m);
        }

        spine.push_back(c.x[i]);
        spine.push_back(v[i]);
        spine.push_back(s[i]);
        spine.push_back(0.0f);
        spine.push_back(m);
    }

    for (unsigned int i = 0; i + 1 < n; ++i) {
        const unsigned int b0 = 2 * i;
        const unsigned int t0 = b0 + 1;
        const unsigned int b1 = 2 * (i + 1);
        const unsigned int t1 = b1 + 1;

        indices.insert(indices.end(), {b0, b1, t1, b0, t1, t0});
    }
}

static void setBeamAttribs()
{
    const GLsizei stride = 5 * sizeof(float);

    for (int i = 0; i < 5; ++i) {
        glVertexAttribPointer(i, 1, GL_FLOAT, GL_FALSE, stride,
                              (void*)(std::size_t)(i * sizeof(float)));
        glEnableVertexAttribArray(i);
    }
}

// ---------------------------------------------------------------------------

// --config N --mode N --scale F --paused: define o estado inicial sem depender
// do teclado. Util para scripts e para abrir a janela direto num caso de
// interesse. As teclas continuam valendo depois.
static void parseArgs(int argc, char** argv)
{
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        const bool hasValue = (i + 1 < argc);

        if (arg == "--paused") {
            app.paused = true;
        } else if (arg == "--config" && hasValue) {
            app.config = std::atoi(argv[++i]) - 1;
        } else if (arg == "--mode" && hasValue) {
            app.mode = std::atoi(argv[++i]) - 1;
        } else if (arg == "--scale" && hasValue) {
            app.scale = (float)std::atof(argv[++i]);
        } else {
            std::cerr << "Argumento ignorado: " << arg << "\n";
        }
    }
}

int main(int argc, char** argv)
{
    BeamData& beam = app.beam;

    if (!loadBeam(findAsset("viga.bin"), beam))
        return 1;

    if (beam.configs.empty() || beam.nModes == 0) {
        std::cerr << "ERRO: arquivo sem configuracoes.\n";
        return 1;
    }

    parseArgs(argc, argv);

    app.config = std::clamp(app.config, 0, (int)beam.configs.size() - 1);
    app.mode   = std::clamp(app.mode, 0, (int)beam.nModes - 1);
    app.scale  = std::clamp(app.scale, 0.02f, 0.41f);

    std::cout << "Resultados FEA carregados: " << beam.configs.size()
              << " configuracoes, " << beam.nModes << " modos, L = " << beam.L
              << " m, h = " << beam.h << " m\n\n"
              << "  <- / ->      composicao (Shift: passo de 10)\n"
              << "  cima/baixo   modo de vibracao\n"
              << "  + / -        escala da deflexao\n"
              << "  , / .        velocidade da animacao\n"
              << "  espaco       pausa\n"
              << "  S            linha neutra\n"
              << "  H            mostra/oculta o painel\n"
              << "  R            reset\n"
              << "  Esc          sair\n\n";

    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_SAMPLES, 4);

    GLFWwindow* window = glfwCreateWindow(1400, 400, "gaveaEngine", nullptr, nullptr);
    if (window == nullptr) {
        std::cerr << "ERRO: falha ao criar a janela GLFW.\n";
        glfwTerminate();
        return 1;
    }

    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebufferSizeCallback);
    glfwSetKeyCallback(window, keyCallback);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cerr << "ERRO: falha ao inicializar o GLAD.\n";
        glfwTerminate();
        return 1;
    }

    glEnable(GL_MULTISAMPLE);

    const fs::path shaderDir = findAsset("shaders");
    Shader beamShader((shaderDir / "viga.vs").string().c_str(),
                      (shaderDir / "viga.fs").string().c_str());
    Shader plainShader((shaderDir / "plain.vs").string().c_str(),
                       (shaderDir / "plain.fs").string().c_str());

    unsigned int ribbonVAO, ribbonVBO, ribbonEBO, spineVAO, spineVBO;
    glGenVertexArrays(1, &ribbonVAO);
    glGenBuffers(1, &ribbonVBO);
    glGenBuffers(1, &ribbonEBO);
    glGenVertexArrays(1, &spineVAO);
    glGenBuffers(1, &spineVBO);

    // Engaste (TRIANGLE_STRIP) seguido da linha neutra indeformada (LINES).
    const float wallHalf = 0.12f;
    const float staticVerts[] = {
        -0.10f, -wallHalf,
        -0.10f,  wallHalf,
         0.00f, -wallHalf,
         0.00f,  wallHalf,
         0.00f,   0.00f,
        beam.L,   0.00f,
    };

    unsigned int staticVAO, staticVBO;
    glGenVertexArrays(1, &staticVAO);
    glGenBuffers(1, &staticVBO);
    glBindVertexArray(staticVAO);
    glBindBuffer(GL_ARRAY_BUFFER, staticVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(staticVerts), staticVerts, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 2 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // HUD de texto. stb_easy_font monta cada caractere com quads (4 vertices de
    // 16 bytes: x,y,z,rgba) em pixels, y para baixo. O core profile nao desenha
    // GL_QUADS, entao um EBO estatico converte cada quad em dois triangulos e a
    // cor vem do uniforme uColor do plainShader (ignoramos z e a cor por vertice).
    const int kMaxTextQuads = 4000;
    unsigned int textVAO, textVBO, textEBO;
    glGenVertexArrays(1, &textVAO);
    glGenBuffers(1, &textVBO);
    glGenBuffers(1, &textEBO);
    glBindVertexArray(textVAO);
    glBindBuffer(GL_ARRAY_BUFFER, textVBO);
    glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)kMaxTextQuads * 4 * 16, nullptr, GL_DYNAMIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, (void*)0);
    glEnableVertexAttribArray(0);

    std::vector<unsigned int> textIdx((std::size_t)kMaxTextQuads * 6);
    for (int q = 0; q < kMaxTextQuads; ++q) {
        const unsigned int b = 4u * (unsigned int)q;
        textIdx[6 * q + 0] = b + 0; textIdx[6 * q + 1] = b + 1; textIdx[6 * q + 2] = b + 2;
        textIdx[6 * q + 3] = b + 0; textIdx[6 * q + 4] = b + 2; textIdx[6 * q + 5] = b + 3;
    }
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, textEBO);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, textIdx.size() * sizeof(unsigned int),
                 textIdx.data(), GL_STATIC_DRAW);

    // Desenha uma string (pode conter '\n') em pixels do HUD. Assume que o
    // plainShader ja esta em uso com a projecao de tela ativa.
    static char textBuf[80000];
    auto drawText = [&](float x, float y, const char* s,
                        float r, float g, float b) {
        int quads = stb_easy_font_print(x, y, const_cast<char*>(s), nullptr,
                                        textBuf, sizeof(textBuf));
        if (quads <= 0)
            return;
        quads = std::min(quads, kMaxTextQuads);
        glBindVertexArray(textVAO);
        glBindBuffer(GL_ARRAY_BUFFER, textVBO);
        glBufferSubData(GL_ARRAY_BUFFER, 0, (GLsizeiptr)quads * 4 * 16, textBuf);
        plainShader.setVec4("uColor", r, g, b, 1.0f);
        glDrawElements(GL_TRIANGLES, quads * 6, GL_UNSIGNED_INT, 0);
    };

    const char* legend =
        "<- / ->      composicao (Shift: passo de 10)\n"
        "cima/baixo   modo de vibracao\n"
        "+ / -        escala da deflexao\n"
        ", / .        velocidade da animacao\n"
        "espaco       pausa\n"
        "S            linha neutra\n"
        "H            mostra/oculta o painel\n"
        "R            reset\n"
        "Esc          sair";

    std::vector<float> ribbon, spine;
    std::vector<unsigned int> indices;
    GLsizei indexCount = 0;
    GLsizei spineCount = 0;

    double t0 = glfwGetTime();
    double tSim = 0.0;

    while (!glfwWindowShouldClose(window)) {
        const double now = glfwGetTime();
        const double dt = now - t0;
        t0 = now;

        if (!app.paused)
            tSim += dt * app.speed;

        if (app.dirty) {
            buildMesh(beam, app.config, app.mode, ribbon, indices, spine);
            indexCount = (GLsizei)indices.size();
            spineCount = (GLsizei)(spine.size() / 5);

            glBindVertexArray(ribbonVAO);
            glBindBuffer(GL_ARRAY_BUFFER, ribbonVBO);
            glBufferData(GL_ARRAY_BUFFER, ribbon.size() * sizeof(float),
                         ribbon.data(), GL_DYNAMIC_DRAW);
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ribbonEBO);
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.size() * sizeof(unsigned int),
                         indices.data(), GL_DYNAMIC_DRAW);
            setBeamAttribs();

            glBindVertexArray(spineVAO);
            glBindBuffer(GL_ARRAY_BUFFER, spineVBO);
            glBufferData(GL_ARRAY_BUFFER, spine.size() * sizeof(float),
                         spine.data(), GL_DYNAMIC_DRAW);
            setBeamAttribs();

            app.dirty = false;
        }

        const Config& cfg = beam.configs[app.config];
        const float freq = cfg.freq[app.mode];

        int width, height;
        glfwGetFramebufferSize(window, &width, &height);
        const glm::mat4 proj = projection(width, height, beam.L, beam.h);

        // As frequencias reais vao de 4 Hz ate ~400 Hz. Anima-las em tempo real
        // faria os modos altos baterem contra os 60 Hz da tela e virarem ruido,
        // entao todos oscilam num ritmo visual fixo. A frequencia fisica correta
        // aparece no titulo da janela.
        const float visualHz = 0.5f;
        const float phase = 2.0f * 3.14159265f * visualHz * (float)tSim;
        const float amp = app.paused ? app.scale : app.scale * std::sin(phase);

        glClearColor(0.09f, 0.10f, 0.11f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        plainShader.use();
        plainShader.setMat4("uProj", glm::value_ptr(proj));
        glBindVertexArray(staticVAO);
        plainShader.setVec4("uColor", 0.30f, 0.31f, 0.33f, 1.0f);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        plainShader.setVec4("uColor", 0.38f, 0.39f, 0.41f, 1.0f);
        glDrawArrays(GL_LINES, 4, 2);

        beamShader.use();
        beamShader.setMat4("uProj", glm::value_ptr(proj));
        beamShader.setFloat("uAmp", amp);
        beamShader.setFloat("uHalfH", 0.5f * beam.h);
        beamShader.setVec3("uSteel", 0.165f, 0.471f, 0.839f);
        beamShader.setVec3("uTitanium", 0.929f, 0.631f, 0.000f);

        beamShader.setFloat("uShade", 1.0f);
        glBindVertexArray(ribbonVAO);
        glDrawElements(GL_TRIANGLES, indexCount, GL_UNSIGNED_INT, 0);

        if (app.showSpine) {
            beamShader.setFloat("uShade", 0.45f);
            glBindVertexArray(spineVAO);
            glDrawArrays(GL_LINE_STRIP, 0, spineCount);
        }

        // HUD por cima de tudo. Projecao de tela em pixels (y para baixo),
        // ampliada por textScale para o texto ficar legivel. A linha de status
        // carrega a mesma informacao que antes ficava no titulo da janela.
        if (app.showHud) {
            const float textScale = 2.0f;
            const glm::mat4 hudProj = glm::ortho(0.0f, (float)width / textScale,
                                                 (float)height / textScale, 0.0f,
                                                 -1.0f, 1.0f);
            plainShader.use();
            plainShader.setMat4("uProj", glm::value_ptr(hudProj));

            char status[256];
            std::snprintf(status, sizeof(status),
                          "config %d/%d   %.1f%% aco   modo %d   f = %.3f Hz   "
                          "escala %.2f%s",
                          app.config + 1, (int)beam.configs.size(),
                          100.0f * cfg.pSteel, app.mode + 1, freq, app.scale,
                          app.paused ? "   PAUSADO" : "");
            drawText(8.0f, 8.0f, status, 0.85f, 0.86f, 0.88f);

            const float legendH = (float)stb_easy_font_height(const_cast<char*>(legend));
            drawText(8.0f, (float)height / textScale - legendH - 8.0f, legend,
                     0.62f, 0.64f, 0.68f);
        }

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glDeleteVertexArrays(1, &ribbonVAO);
    glDeleteVertexArrays(1, &spineVAO);
    glDeleteVertexArrays(1, &staticVAO);
    glDeleteVertexArrays(1, &textVAO);
    glDeleteBuffers(1, &ribbonVBO);
    glDeleteBuffers(1, &ribbonEBO);
    glDeleteBuffers(1, &spineVBO);
    glDeleteBuffers(1, &staticVBO);
    glDeleteBuffers(1, &textVBO);
    glDeleteBuffers(1, &textEBO);

    glfwTerminate();
    return 0;
}
