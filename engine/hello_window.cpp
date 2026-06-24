#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <iostream> 

const char *vertexShaderSource = "#version 330 core\n"
    "layout (location = 0) in vec3 aPos;\n"
    "void main()\n"
    "{\n"
    " gl_Position = vec4(aPos.x, aPos.y, aPos.z, 1.0);\n"
    "}\0";

void framebuffer_size_callback(GLFWwindow* window, int width, int height){
    glViewport(0,0,width,height);
}

void processInput(GLFWwindow *window){
    // input + key, if user pressed the escape key, close GLFW
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) 
        glfwSetWindowShouldClose(window, true); 
}

int main(){
    glfwInit(); // Initialize GLFW
    
    // glfwWindowHint sets a window option to an integer value
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);  // OpenGL major version
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);  // OpenGL minor version

    // Core profile gives us the modern OpenGL subset, without the old compatibility cruft
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

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

    unsigned int vertexShader;
    vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, NULL);
    glCompileShader(vertexShader);  

    int success;
    char infoLog[512];
    glGetShaderiv(vertexShader, GL_COMPILE_STATUS, &success);

    float vertices[] = {
        -0.5f, -0.5f, 0.0f,
        0.5f, -0.5f, 0.0f,
        0.0f, 0.5f, 0.0f
    };

    unsigned int VBO; 
    glGenBuffers(1, &VBO); // generate a buffer ID
    glBindBuffer(GL_ARRAY_BUFFER, VBO); // bind newly created buffer to the GL array buffer
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW); // copies the previously defined vertex data into the buffer's memory  
    
    // Initialize GLAD before we call any OpenGL function
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)){ // defines function based on which OS
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    // first 2 param set the location of the lower left corner of the window
    glViewport(0,0,800,600); // set width and height of the rendering window
    
    // tell GLFW to call the frame...callback function on every window resize 
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback); 

    // render loop, keeps running until we tell GLFW to stop
    while (!glfwWindowShouldClose(window)){
        // input 
        processInput(window);
        
        // render commands
        glClearColor(0.2f, 0.3f, 0.3f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glfwTerminate(); // clean up all the resources
    return 0;
}