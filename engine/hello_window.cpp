#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <iostream> 

void framebuffer_size_callback(GLFWwindow* window, int width, int height){
    glViewport(0,0,width,height);
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

    // Initialize GLAD before we call any OpenGL function
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)){ // defines function based on which OS
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    glViewport(0,0,800,600); // size of the rendering window
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    while (!glfwWindowShouldClose(window)){
        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glfwTerminate();
    return 0;
}