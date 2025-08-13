# Acerca de
Este sistema es un asistenete academico virtual de moodle diseñado para funcionar de manera independiente en uno o multiples cursos.

## Puede
* Responder consultas de alumnos por los foros utilizando el contenido del curso y una Inteligencia Artificial para generar respuestas personales, certeras y acorde al curso.


# Requisitos de Moodle
* Moodel 3.8.2 o superior
* Tener instalado en el Moodle el pugin de Webhooks ([click aqui para descargar](https://moodle.org/plugins/local_webhooks))
* Tener permisos de administrador en el sitio


#  Configuracion del moodle
1. Crear un usuario basico para el Asistente academico
2. Crear un servicio Externo para el asistente academico
    * "Administracion del sitio"->"Extenciones"->"servicios web"->"servicios externos"->Añadir
    * Marcar como habilitado
    * Permitir descargar archivos
    * Permitir subir ficheros
3. Darle al servicio externo las siguientes funciones
    * core_webservice_get_site_info
    * core_enrol_get_users_courses
    * mod_forum_get_forums_by_courses
    * mod_forum_get_forum_discussions
    * mod_forum_get_discussion_posts
    * core_user_get_users_by_field
    * core_enrol_get_enrolled_users
    * mod_forum_add_discussion_post
    * core_course_get_contents
4. Vincular el servicio externo al usuario asignado
    * "Administracion del sitio"->"Extenciones"->"servicios web"->"Administrar fichas(tokens)"->Añadir
    * Ingresar nombre de usuario del usuario creado previamente
    * seleccionar el servicio creado para el bot
5. Seleccionar l token creado para el servicio con el usuario
    * incluir el token en el archivo.env, creando una variable llamada TOKEN
    * TOKEN = tu_token
6. Crear un nuevo webhook
    * "Administracion del sitio"->"Servidor"->"Servidor"->"webhook"->"agregar servicio"
    * incluir la url del webhook del servidor donde se instalo el sistema
    * Marcar los siguientes eventos:
        * \mod_forum\event\discussion_created
        * \mod_forum\event\post_created
7. ejecutar el programa


# Configuracion del .env
Se debe incluir un archivo .env que contenga las siguientes variables de entorno:
~~~
TOKEN = tu_token
MOODLE_URL = url_de_tu_moodle
OPENAI_API_KEY = API_key_de_OpenAI
~~~


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

