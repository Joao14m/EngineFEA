#ifndef GAVEA_SHADER_H
#define GAVEA_SHADER_H

#include <glad/glad.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

class Shader {
    public:
        unsigned int ID;

        Shader(const char* vertexPath, const char* fragmentPath);

        void use() const;
        void setBool(const std::string &name, bool value) const;
        void setInt(const std::string &name, int value) const;
        void setFloat(const std::string &name, float value) const;
        void setVec3(const std::string &name, float x, float y, float z) const;
        void setVec4(const std::string &name, float x, float y, float z, float w) const;
        void setMat4(const std::string &name, const float* value) const;

    private:
        static unsigned int compile(const char* source, GLenum type, const char* label);
};

inline Shader::Shader(const char* vertexPath, const char* fragmentPath)
{
    std::string vertexCode;
    std::string fragmentCode;

    std::ifstream vShaderFile(vertexPath);
    std::ifstream fShaderFile(fragmentPath);

    if (!vShaderFile.is_open())
        std::cerr << "ERRO::SHADER::ARQUIVO_NAO_LIDO: " << vertexPath << std::endl;

    if (!fShaderFile.is_open())
        std::cerr << "ERRO::SHADER::ARQUIVO_NAO_LIDO: " << fragmentPath << std::endl;

    std::stringstream vStream, fStream;
    vStream << vShaderFile.rdbuf();
    fStream << fShaderFile.rdbuf();

    vertexCode = vStream.str();
    fragmentCode = fStream.str();

    unsigned int vertex = compile(vertexCode.c_str(), GL_VERTEX_SHADER, "VERTEX");
    unsigned int fragment = compile(fragmentCode.c_str(), GL_FRAGMENT_SHADER, "FRAGMENT");

    ID = glCreateProgram();
    glAttachShader(ID, vertex);
    glAttachShader(ID, fragment);
    glLinkProgram(ID);

    int success;
    char infoLog[512];
    glGetProgramiv(ID, GL_LINK_STATUS, &success);
    if (!success) {
        glGetProgramInfoLog(ID, 512, nullptr, infoLog);
        std::cerr << "ERRO::SHADER::LINK\n" << infoLog << std::endl;
    }

    glDeleteShader(vertex);
    glDeleteShader(fragment);
}

inline unsigned int Shader::compile(const char* source, GLenum type, const char* label)
{
    unsigned int shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    int success;
    char infoLog[512];
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        std::cerr << "ERRO::SHADER::COMPILACAO::" << label << "\n" << infoLog << std::endl;
    }

    return shader;
}

inline void Shader::use() const
{
    glUseProgram(ID);
}

inline void Shader::setBool(const std::string &name, bool value) const
{
    glUniform1i(glGetUniformLocation(ID, name.c_str()), (int)value);
}

inline void Shader::setInt(const std::string &name, int value) const
{
    glUniform1i(glGetUniformLocation(ID, name.c_str()), value);
}

inline void Shader::setFloat(const std::string &name, float value) const
{
    glUniform1f(glGetUniformLocation(ID, name.c_str()), value);
}

inline void Shader::setVec3(const std::string &name, float x, float y, float z) const
{
    glUniform3f(glGetUniformLocation(ID, name.c_str()), x, y, z);
}

inline void Shader::setVec4(const std::string &name, float x, float y, float z, float w) const
{
    glUniform4f(glGetUniformLocation(ID, name.c_str()), x, y, z, w);
}

inline void Shader::setMat4(const std::string &name, const float* value) const
{
    glUniformMatrix4fv(glGetUniformLocation(ID, name.c_str()), 1, GL_FALSE, value);
}

#endif
