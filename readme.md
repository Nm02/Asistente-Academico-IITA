# Acerca de
Este sistema es un asistenete academico virtual de moodle diseñado para funcionar de manera independiente en uno o multiples cursos.

## Puede
* Responder consultas de alumnos por los foros utilizando el contenido del curso y una Inteligencia Artificial para generar respuestas personales, certeras y acorde al curso.
* 

# Requisitos de Moodle
* Moodel 3.8.2 o superior
* Tener instalado en el Moodle el pugin de Webhooks ([click aqui para descargar](https://moodle.org/plugins/local_webhooks))
* Tener permisos de administrador en el sitio

#  Configuracion

# Uso
Basta con agregar al asistente academico Al curso en cuestion y conectar los webhooks para que empiece a funcionar.
* Los webhooks deben tener los eventos:
    * \mod_forum\event\discussion_created
    * \mod_forum\event\post_created
* El rol de asistente afectara a los contenidos que podra acceder para generar las respuestas
    * Si es profesor (Con o sin permisos de edicion) podra accedeer a todo el contenido del curso.
    * SI es estudiante, solo podra acceder a los contenidos disponibles para todos los estudiantes.


Si se desea que responde de mejor manera, se recomientda:
* Incluir in Tema/Semana/Apartado llamado "Informacion General" en el que se deberia incluir cosas como el porgrama del curso. Esto servira para identificar que consultas debe responder el Asistentente, y cuales no.
* Incluir informacion detallada de el contenido del curso en multiples archivos. Si el Ayudante academico en un profesor, podra acceder a dichos archivos y utilizarlos incluso si estan ocultos para alumnos.

