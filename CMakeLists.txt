
IF (BUILD_GUI)
    PYSIDE_WRAP_RC(Hulls_QRC_SRCS Resources/Hulls.qrc)
ENDIF (BUILD_GUI)

SET(Hulls_SRCS
    Init.py
    InitGui.py
    Hulls.py
    HullsGui.py
)
SOURCE_GROUP("" FILES ${Hulls_SRCS})

ADD_CUSTOM_TARGET(Hulls ALL
    SOURCES ${Hulls_SRCS} ${Hulls_QRC_SRCS}
)

fc_copy_sources(Hulls "${CMAKE_BINARY_DIR}/Mod/Hulls" ${Hulls_SRCS})

IF (BUILD_GUI)
    fc_target_copy_resource(Hulls
        ${CMAKE_CURRENT_BINARY_DIR}
        ${CMAKE_BINARY_DIR}/Mod/Hulls
        Hulls_rc.py)
ENDIF (BUILD_GUI)

INSTALL(
    FILES
        ${Hulls_SRCS}
        ${Hulls_QRC_SRCS}
    DESTINATION
        Mod/Hulls
)

SET(HullsGuiIcon_SVG
    Resources/icons/HullsWorkbench.svg
)

fc_copy_sources(Hulls "${CMAKE_BINARY_DIR}/Mod/Hulls" ${HullsGuiIcon_SVG})
INSTALL(FILES ${HullsGuiIcon_SVG} DESTINATION "Mod/Hulls/Resources/icons")
