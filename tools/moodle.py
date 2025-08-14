import requests

# Para archivos
from tools.tools import extract_text_from_pdf_bytes

# Variables de entorno
import os
from dotenv import load_dotenv


# === CONFIGURACIÓN ===
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path)

MOODLE_URL = os.getenv("MOODLE_URL") 
TOKEN = os.getenv("TOKEN")
ENDPOINT = f"{MOODLE_URL}/webservice/rest/server.php"




def get_self_id() -> dict:
    """
    Obtiene informacion del usuario que esta conectado con el token en el endpoint dado.
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'core_webservice_get_site_info'\n
    Algunos de los datos que devuelve esta funcion dentro del diccionario son:\n
        -userid    -> id del usuario
        -username  -> nombre del usuario
    entre otros    
    """
    
    params = {
        "wstoken": TOKEN,
        "wsfunction": "core_webservice_get_site_info",
        "moodlewsrestformat": "json"
    }

    response = requests.get(ENDPOINT, params=params)

    if response.status_code == 200:
        info = response.json()
        # print("✔️ Nombre de usuario:", info["username"])
        # print("🆔 ID de usuario:", info["userid"])
        return info
    else:
        raise ConnectionRefusedError(f"❌ Error al obtener info del sitio: {response.status_code}\n{response.text}")


def get_user_courses(user_id: int) -> list[dict]:
    """
    Obtiene la lista de cursos en las que se encuentre el usuario.\n
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'core_enrol_get_users_courses'\n
    Cada curso viene dado en formato de diccionario, y contiene datos como:\n
        -id        -> id del curso
        -shortname -> Nombre corto del curso
        -fullname  -> Nombre largo del curso
        -visible   -> Visibilidad del curso (1,0)
        -category  -> ID de la categoria del curso
        -startdate -> Fecha de inicio del curso
        -enddate   -> Fecha de finalizacion del curso
    entre otros
    """

    params = {
        "wstoken": TOKEN,
        "wsfunction": "core_enrol_get_users_courses",
        "moodlewsrestformat": "json",
        "userid": user_id
    }

    # === LLAMADA A MOODLE ===
    response = requests.get(ENDPOINT, params=params)
    cursos = response.json()

    return cursos


def get_course_forums(course_id: int) -> list[dict]:
    """
    Devuelve una lista de todos los foros que contiene el curso\n
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'mod_forum_get_forums_by_courses'\n
    Cada Foro viene dado en formato de diccionario, y contiene datos como:\n
        -id     -> id del foro
        -course -> id del curso al que pertenece
        -type   -> tipo de foro
        -name   -> nombre del foro
    entre otros
    """

    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_forum_get_forums_by_courses",
        "moodlewsrestformat": "json",
        "courseids[0]": course_id
    }
    response = requests.get(ENDPOINT, params=params)
    return response.json()


def get_forum_content(forum_id: int) -> list[dict]:
    """
    Devuelve una lista del contenido del foro\n
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'mod_forum_get_forum_discussions'\n
    El contenido del Foro viene dado en formato de diccionario, y contiene datos como:\n
        -discussions -> lista de discuciones dentro de un foro (tambien son diccionarios)
            -id                     -> 
            -discussion             -> ID de la discusion
            -name                   -> Nombre de la discusion
            -timemodified           -> Utilma Fecha de modificacion (Edicion o respuesta a cualquier mensaje dentro de la conversacion)
            -subject                -> Asunto de la discusion
            -message                -> Texto inicial de la discusion (mensaje inicial)
            -userfullname           -> Nombre completo del usuario que envio el primer mensaje/ inicio la disusion
            -usermodifiedfullname   -> Nombre completo del ultimo usuario que interactuo con la discucion (genero un mensaje, edito un mensaje, borro un mensaje)
            -numreplies             -> Numero de respuestas/mensajes hijos de la conversacion

        -warnings    -> lista de advertencias dentro del foro
    """

    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_forum_get_forum_discussions",
        "moodlewsrestformat": "json",
        "forumid": forum_id
    }
    response = requests.get(ENDPOINT, params=params)
    return response.json()


def get_discussion_posts(discussion_id: int) -> dict:
    """
    Devuelve todos los posts de una discusión (post inicial y todas las respuestas).
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'mod_forum_get_discussion_posts'\n
    El contenido de la discusion viene dada en formato de diccionario, y contiene datos como:\n
        -posts              -> Lista de 'posts' o mensajes de la discusion (cada post es un diccionarios)
            -id             -> id del post
            -message        -> Mensaje del post
            -author         -> diccionario con info del autor (id, fullname, etc.)
            -discussionid   -> id de la discusion
            -hasparent      -> Bool, tiene un post padre (es respuesta o mensaje inicial)
            -parentid       -> id del post padre (si es q existe, si no None)
            -timecreated    -> momento de la creacion del post
            -sonpost        -> lista de post hijos. cada post tiene el mismo formato que este

        -ratinginfo         -> diccionariorio con las Calificaciones de la discusion
        -warnings           -> Alertas
    """
    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_forum_get_discussion_posts",
        "moodlewsrestformat": "json",
        "discussionid": discussion_id
    }

    response = requests.get(ENDPOINT, params=params)
    if response.status_code == 200:
        # return response.json().get("posts", [])
        response = response.json()
        # response['posts'] = response['posts'][::-1]
        response = organize_posts_by_hierarchy(response)

        return response
    else:
        raise Exception(f"Error al obtener posts de discusión {discussion_id}:\n{response.text}")


def organize_posts_by_hierarchy(response: dict) -> dict:
    """
    Modifica el diccionario 'response' para que:
    - Cada post tenga una clave 'replies' con una lista de sus respuestas directas.
    - Los posts que son hijos se eliminen del nivel raíz.
    """
    posts = response.get("posts", [])
    post_index = {post["id"]: post for post in posts}

    # Inicializar lista vacía de hijos
    for post in posts:
        post["replies"] = []

    # Construir la jerarquía
    for post in posts:
        parent_id = post.get("parentid")
        if parent_id is not None and parent_id in post_index:
            parent_post = post_index[parent_id]
            parent_post["replies"].append(post)

    # Dejar solo los posts raíz (sin parent)
    response["posts"] = [post for post in posts if post.get("parentid") is None]

    return response


def get_conversations(post: dict, course_id: str = None) -> list[dict]:
    """
    Obtiene las conversaciones a modo de diccionario, cargando los textos de los mensajes, asociandolos a los post padres y registrando quien envio cada mensaje (nombre de usuario, rol en el curso, etc.)\n
    estuctura del diccionario:
        -discussion     -> id del la discusion
        -id_user        -> usuario que envio la ultima respuesta de la conversacion
        -content        -> lista de Mensajes 
            -id_post    -> id del post/mensaje
            -id_user    -> id del usuario que mando el mensaje
            -user_roles   -> rol del usuario que mando el mensaje
            -user_name  -> nombre del usuario que mando el mensaje
            -text       -> texto del mensaje
    """

    conversations = []

    def recorrer_rama(nodo, camino_actual = []):
        # Añadir el mensaje actual al camino
        camino_actual.append({
            "id_post": nodo["id"],
            "id_user": nodo["author"]["id"],
            "user_name": nodo["author"]["fullname"],
            "user_roles": [],
            "text": nodo["message"]
        })

        # Si no tiene más replies, es el final de una conversación
        if not nodo.get("replies"):
            conversations.append({
                "discussion": nodo["discussionid"],
                "id_user": nodo["author"]["id"],
                "content": camino_actual
            })
        else:
            for hijo in nodo["replies"]:
                recorrer_rama(hijo, camino_actual.copy())

    recorrer_rama(post)

    if course_id:
        for i in range (len(conversations)):
            for j in range (len(conversations[i]['content'])):
                user_id = conversations[i]['content'][j]['id_user']
                conversations[i]['content'][j]['user_roles'] = get_user_course_data(
                    course_id, 
                    user_id
                )['roles']


    return conversations


def get_user_data(user_id: int):
    """
    Devuelve Los datos de un Usuario segun su id.
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'core_user_get_users_by_field'\n
    Los datos del usuario vienen dados en formato de diccionario, y contiene datos como:\n
        -id         -> id de usuario
        -username   -> nombre de usuario
        -firstname  -> nombre
        -lastname   -> apellido
        -fullname   -> nombre completo
        -email      -> email
    """

    params = {
        "wstoken": TOKEN,
        "wsfunction": "core_user_get_users_by_field",
        "moodlewsrestformat": "json",
        "field": "id",
        "values[0]": user_id
    }

    response = requests.get(ENDPOINT, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            return data[0]  # Devolver el primer (y único) usuario
        else:
            raise ValueError(f"No se encontró el usuario con ID {user_id}")
    else:
        raise Exception(f"Error al obtener datos del usuario:\n{response.status_code}\n{response.text}")


def get_user_course_data(course_id: int, user_id: int) -> dict:
    """
    Devuelve Los datos de un Usuario dentro de un curso.
    Para esto, es requerido que el 'servicio Externo' de Moodle tenga la funcion 'core_enrol_get_enrolled_users'\n
    Los datos del usuario dentro del curso vienen dados en formato de diccionario, y contiene datos como:\n
        -id             -> id de usuario
        -username       -> nombre de usuario
        -firstname      -> nombre
        -lastname       -> apellido
        -fullname       -> nombre completo
        -email          -> email
        -roles          -> lista de roles. Cada rol es un diccionario
            -roleid     -> id del rol
            -shortname  -> nombre corto del rol
    """

    params = {
        "wstoken": TOKEN,
        "wsfunction": "core_enrol_get_enrolled_users",
        "moodlewsrestformat": "json",
        "courseid": course_id
    }

    response = requests.get(ENDPOINT, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Error al obtener usuarios del curso {course_id}:\n{response.status_code}\n{response.text}")

    users = response.json()

    if 'exception' in users:
        raise ValueError(users['exception'])

    for user in users:
        if user["id"] == user_id:
            return user

    raise ValueError(f"Usuario con ID {user_id} no encontrado en el curso {course_id}")


def reply_to_post(parent_post_id: int, message: str, subject: str = "Respuesta automática (Beta)") -> dict:
    """
    Publica una respuesta a un post existente en un foro de Moodle.
    
    Requiere que el servicio tenga habilitada la función 'mod_forum_add_discussion_post'.
    
    Parámetros:
    - parent_post_id: ID del post al que se quiere responder
    - message: contenido HTML del mensaje
    - subject: asunto/título de la respuesta
    """
    params = {
        "wstoken": TOKEN,
        "wsfunction": "mod_forum_add_discussion_post",
        "moodlewsrestformat": "json",
        "postid": parent_post_id,
        "subject": subject,
        "message": message,
        "messageformat": 1  # 1 = HTML, 0 = texto plano
    }

    response = requests.post(ENDPOINT, data=params)
    
    if response.status_code != 200:
        raise Exception(f"❌ Error al responder al post {parent_post_id}:\n{response.status_code}\n{response.text}")

    result = response.json()

    if 'exception' in result:
        print(result)
        raise ValueError(result['exception'])
    
    elif "postid" in result:
        return result  # respuesta exitosa
    
    else:
        raise ValueError(f"❌ Moodle no devolvió ID de respuesta: {result}")


def get_course_contents(course_id: int) -> list[dict]:
    """
    Devuelve las secciones del curso, con los recursos (archivos, etiquetas, enlaces, etc.) en cada una.
    Requiere 'core_course_get_contents' habilitada.
    """
    params = {
        "wstoken": TOKEN,
        "wsfunction": "core_course_get_contents",
        "moodlewsrestformat": "json",
        "courseid": course_id
    }

    response = requests.get(ENDPOINT, params=params)

    if response.status_code != 200:
        raise Exception(f"❌ Error al obtener contenidos del curso {course_id}:\n{response.status_code}\n{response.text}")

    return response.json()


def download_file(fileurl: str, file_type: str):
    """
    Descarga un archivo del moodle
    """
    if "token=" not in fileurl:
        if "?" in fileurl:
            fileurl += f"&token={TOKEN}"
        else:
            fileurl += f"?token={TOKEN}"

    headers = {"Authorization": f"Bearer {TOKEN}"}
    response = requests.get(fileurl, headers=headers)
    
    if response.status_code == 200:
        if file_type == "application/pdf":
            text = extract_text_from_pdf_bytes(response.content)
        return text
    else:
        raise Exception(f"❌ Error al descargar archivo:\n{response.status_code}\n{response.text}")






# # Testeo
# if __name__ == "__main__":
#     user_id = get_self_id()["userid"]
#     courses = get_user_courses(user_id)

#     for course in courses:
#         forums = get_course_forums(course["id"])
        
#         print("\n\n","*"*50)
#         print(f"curso: {course['fullname']}\n")

#         for forum in forums:
#             discussions = get_forum_content(forum['id'])

#             for discussion in discussions['discussions']:
#                 print(f"-[{discussion['discussion']}] {discussion['name']}\n")
#                 posts = get_discussion_posts(discussion['discussion'])
                
            
#                 posts = get_conversations(posts['posts'][0], course["id"])


#                 for post in posts:
#                     if post['id_user'] != user_id:
#                         teacher = False

#                         for rol in post["content"][-1]["user_roles"]:
#                             if rol['shortname'] in ('teacher', 'editingteacher'):
#                                 teacher = True

#                         if not teacher:
#                             import IA

#                             course_content = get_course_contents(course["id"])
#                             course_content_embedding = []
#                             general_info = f"Nombre del Curso: {course['fullname']}\n"

#                             # Get course content embeding
#                             for section in course_content:
#                                 print(f"\n📚 Sección: {section['name']}")
#                                 for module in section.get("modules", []):
#                                     print(f"  📄 Recurso: {module['name']} - tipo: {module['modname']}")
#                                     for content in module.get("contents", []):

#                                         if content["mimetype"] == "application/pdf":
#                                             download = download_file(content["fileurl"], content["mimetype"])
                                            

#                                             if section['name'].lower() == "informacion general":
#                                                 general_info += f"\nFuente de la informacion (nombre del archivo): {module['name']}\n{download}\n"

#                                             else:
#                                                 # embedding = IA.get_embedding(download)
#                                                 course_content_embedding.append({"source": module['name'], "text": download, "embedding": None})

#                             course_content_embedding = IA.get_embeding_list(course_content_embedding)

#                             # Chat history
#                             chat = []
#                             for message in post["content"]:
#                                 interaction = {}

#                                 if 'teacher' in message['user_roles'] or 'editingteacher' in message['user_roles']:
#                                     interaction['role'] = 'assistant'
#                                     message_user = f"mensaje del profesor {message['user_name']:}"

#                                 else:
#                                     interaction['role'] = 'user'
#                                     message_user = f"mensaje del alumno {message['user_name']}:"
                                
#                                 interaction["content"] = f"{message_user}{message['text']}" 
#                                 chat.append(interaction)


#                             # search related content
#                             question_embedding = IA.get_embedding(post['content'][0]['text'])
#                             question_related_content = IA.find_similar_content(question_embedding, course_content_embedding)

#                             with open(r"files\system_prompts\Forum_Respond.txt", "r") as file:
#                                 system_prompt = file.read()
#                                 system_prompt += f"""La siguiente Informacion es la Informacion General Del Curso. Utilizala para deducir el contenido general del curso: \n{general_info}\n\n"""

#                                 system_prompt += "La siguiente Informacion es el Contenido Del Curso que considermaos util para esta pregunta, puedes o no utilizarlo:\n"
#                                 for content in question_related_content:
#                                     system_prompt += f"\nFuente de la informacion (nombre del archivo): {content['source']}:\n{content['text']}"

#                             # response
#                             response = IA.generate_response(post['content'][-1]['text'], system_prompt, chat)
#                             reply_to_post(post['content'][-1]['id_post'], response)



                        



