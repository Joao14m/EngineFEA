# Copia SRC para DST apenas se SRC existir.
#
# `cmake -E copy_if_different` falha quando a origem nao existe, o que quebraria
# o build antes de o usuario rodar o exportador Python pela primeira vez. Este
# script torna a copia opcional e avisa em vez de abortar.

if(EXISTS "${SRC}")
    execute_process(COMMAND "${CMAKE_COMMAND}" -E copy_if_different "${SRC}" "${DST}")
else()
    message(STATUS "${SRC} nao encontrado. Gere-o com: python -m modelo_matematico.exportar_engine")
endif()
