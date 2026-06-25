#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <iostream> 

const char *vertexShaderSource = "#version 330 core\n"
    "layout (location = 0) in vec3 aPos;\n"
    "void main()\n"
    "{\n"
    " gl_Position = vec4(aPos.x, aPos.y, aPos.z, 1.0);\n"
    "}\0";
    
const char *fragmentShaderSource = "#version 330 core\n"
    "out vec4 FragColor;\n"
    "void main()\n"
    "{\n"
    "   FragColor = vec4(1.0f, 0.5f, 0.2f, 1.0f);\n"
    "}\n\0";

void framebuffer_size_callback(GLFWwindow* window, int width, int height){
    glViewport(0,0,width,height);
}

void processInput(GLFWwindow *window){
    // input + key, if user pressed the escape key, close GLFW
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) 
        glfwSetWindowShouldClose(window, true); 
}

int main(){
    // glfw: initialize and configure 
    // -----------------------------
    glfwInit(); // Initialize GLFW
    
    // glfwWindowHint sets a window option to an integer value
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);  // OpenGL major version
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);  // OpenGL minor version

    // Core profile gives us the modern OpenGL subset, without the old compatibility cruft
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    // glfw window creation
    // -----------------------------
    // window object that holds all the windowing data and is required 
    // by most of GLFW's other functions
    GLFWwindow* window = glfwCreateWindow(800, 600, "LearnOpenGL", NULL, NULL); // set width, height and name of the window
    if (window == NULL){ 
        std::cout << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }

    // tell GLFW to make the context of our window the main context on the current thread
    glfwMakeContextCurrent(window);
    // tell GLFW to call the frame...callback function on every window resize 
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback); 

    // Initialize GLAD before we call any OpenGL function
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)){ // defines function based on which OS
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    // build and compile our shader program 
    // ------------------------------------
    // vertex shader set up and check success
    unsigned int vertexShader;
    vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
    glCompileShader(vertexShader);  

    int success;
    char infoLog[512];
    glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);

    if(!success){
        glGetShaderInfoLog(vertexShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::VERTEX::COMPILATION_FAILED\n" << 
            infoLog << std::endl;
    }

    // fragment shader set up and check success
    unsigned int fragmentShader;
    fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &fragmentShaderSource, NULL);
    glCompileShader(fragmentShader);
    glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, &success);

    if (!success){
        glGetShaderInfoLog(fragmentShader, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::FRAGMENT::COMPILATION_FAILED\n" << 
            infoLog << std::endl;
    }

    // link shaders to when activate it, render objects
    unsigned int shaderProgram = glCreateProgram();
    glAttachShader(shaderProgram, vertexShader);
    glAttachShader(shaderProgram, fragmentShader);
    glLinkProgram(shaderProgram);
    glGetProgramiv(shaderProgram, GL_LINK_STATUS, &success);

    if (!success){
        glGetProgramInfoLog(shaderProgram, 512, NULL, infoLog);
        std::cout << "ERROR::SHADER::PROGRAM::LINKING_FAILED\n" << 
            infoLog << std::endl;
    }
    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    // set up vertex data (and buffer(s)) and configure vertex attributes
    // ------------------------------------
    float vertices[] = {
        0.5f, 0.5f, 0.0f, // top right
        0.5f, -0.5f, 0.0f, // bottom right
        -0.5f, -0.5f, 0.0f, // bottom left
        -0.5f, 0.5f, 0.0f // top left
    };

    unsigned int indices[] = {
        0, 1, 3, // first triangle
        1, 2, 3 // second triangle
    };

    // Vertex Buffer Object, stores vertex data in the GPU's memory 
    unsigned int VBO, VAO, EBO;
    glGenVertexArrays(1, &VAO); 
    glGenBuffers(1, &VBO); // generate 1 buffer object and writes its ID into VBO
    glGenBuffers(1, &EBO);

    glBindVertexArray(VAO);

    // 0. copy our vertices array in a buffer for OpenGL to use
    glBindBuffer(GL_ARRAY_BUFFER, VBO); // bind newly created buffer to the GL array buffer
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW); // copies the previously defined vertex data into the buffer's memory  

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO); // bind newly created buffer to the GL array buffer
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, GL_STATIC_DRAW); // copies the index data into the EBO's memory

    // 1. set the vertex attributes pointers
    // position vertex attribute (va), size of the va, type of data, normalized or not, stride, offset of position data begins
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // first 2 param set the location of the lower left corner of the window
    //glViewport(0,0,800,600); // set width and height of the rendering window

    glBindBuffer(GL_ARRAY_BUFFER, 0);

    // render loop, keeps running until we tell GLFW to stop
    // ------------------------------------
    while (!glfwWindowShouldClose(window)){
        // input 
        processInput(window);
        
        // render commands
        glClearColor(0.2f, 0.3f, 0.3f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        
        // 2. use our shader program when we want to render an object
        glUseProgram(shaderProgram);

        // 3. draw the object
        glBindVertexArray(VAO);
        //glDrawArrays(GL_TRIANGLES, 0, 3);
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);
        glBindVertexArray(0); 
        
        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glDeleteVertexArrays(1, &VAO);
    glDeleteBuffers(1, &VBO);
    glDeleteProgram(shaderProgram);

    glfwTerminate(); // clean up all the resources
    return 0;
}