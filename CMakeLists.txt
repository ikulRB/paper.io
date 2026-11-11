cmake_minimum_required(VERSION 3.16)
project(PaperIO LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SFML_PATH "${CMAKE_SOURCE_DIR}/external/SFML-3.1.0")

include_directories("${SFML_PATH}/include")
# Путь к заголовкам Clipper2 (оставляем)
include_directories("${CMAKE_SOURCE_DIR}/external/Clipper2/include")

link_directories("${SFML_PATH}/lib")

file(GLOB_RECURSE SOURCES "src/*.cpp")

# --- ДОБАВИТЬ ЭТИ СТРОКИ ---
# Находим и добавляем исходники Clipper2 в список файлов для сборки.
# Проверь, что путь к папке src правильный (там должны лежать clipper.engine.cpp и др.)
file(GLOB CLIPPER_SOURCES "${CMAKE_SOURCE_DIR}/external/Clipper2/src/*.cpp")
list(APPEND SOURCES ${CLIPPER_SOURCES})
# ---------------------------

add_executable(PaperIO ${SOURCES})

target_include_directories(PaperIO PRIVATE include)

target_compile_definitions(PaperIO PRIVATE CLIPPER2_USINGZ=0 CLIPPER2_HAS_EXCEPTIONS=0)

target_link_libraries(PaperIO PRIVATE 
    sfml-graphics 
    sfml-window 
    sfml-system
)

if(WIN32)
    add_custom_command(TARGET PaperIO POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${SFML_PATH}/bin"
        $<TARGET_FILE_DIR:PaperIO>
    )
    add_custom_command(TARGET PaperIO POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        "${CMAKE_SOURCE_DIR}/assets"
        $<TARGET_FILE_DIR:PaperIO>/assets
    )
endif()