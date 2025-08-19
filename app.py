# Librerias Para API
from fastapi import FastAPI, Request
import uvicorn

# Libreria para moodle
import tools.moodle as moodle

# IA
import tools.IA as IA

# para evitar deadlock de webhooks
import asyncio


# Crear APP
app = FastAPI()

# Recibir eventos por webhook
@app.post("/webhook")
async def moodle_webhook_listener(request: Request):
    data = await request.json()

    if data["eventname"] == "\\mod_forum\\event\\post_created":
        asyncio.create_task(respond_discussion(data['other']['discussionid'], int(data["courseid"])))

    elif data["eventname"] == "\\mod_forum\\event\\discussion_created":
        asyncio.create_task(respond_discussion(data['objectid'], int(data["courseid"])))



    return {"status": "ok"}


async def respond_discussion(discussion_id: int, course_id: int = None):
    """
    Responder a una discusion utilizando IA y todos los contenidos del curso.
    Esta funcion sponde SI y SOLO SI el usuario registrado con el Token esta dentro del curso, y tiene los permisos necesarios.
    """

    print(f"1. Nuevo mensaje de la discusion: {discussion_id}\nPerteneciente al curso: {course_id}")

    user_id = moodle.get_self_id()["userid"]
    courses = moodle.get_user_courses(user_id)

    if any(course["id"] == course_id for course in courses):
        print("2. El asistente si esta en el curso")

        conversations = moodle.get_discussion_posts(discussion_id)
        conversations = moodle.get_conversations(conversations['posts'][0], course_id)

        for conversation in conversations:
            print("3. analizando conversacion...")

            if conversation['id_user'] != user_id:
                teacher = False
                print("4. El utimo mensaje no fue del asistente")

                for rol in conversation["content"][-1]["user_roles"]:
                    if rol['shortname'] in ('teacher', 'editingteacher'):
                        teacher = True

                if not teacher:
                    print("5. El utimo mensaje no fue de un profesor")

                    # Chat history
                    print("**********Obteniendo historial del chat**********\n")
                    chat = []
                    for message in conversation["content"]:
                        interaction = {}

                        if 'teacher' in message['user_roles'] or 'editingteacher' in message['user_roles']:
                            interaction['role'] = 'assistant'
                            message_user = f"mensaje del profesor {message['user_name']:}"

                        else:
                            interaction['role'] = 'user'
                            message_user = f"mensaje del alumno {message['user_name']}:"
                        
                        interaction["content"] = f"{message_user}{message['text']}" 
                        chat.append(interaction)


                    # Determine intent of the conversation
                    print("**********Determinando intención**********\n")
                    tags = [{"name": "consulta de actividad", "description": "Preguntas relacionadas con actividades del curso (cuestionarios, trabajos practicos-TP, ejercicios, et.)."},
                            {"name": "Consulta de contenido", "description": "Preguntas relacionadas con el contenido del curso, pero no con una actividad."},
                            {"name": "consulta general", "description": "Preguntas generales sobre el curso."}]
                    intent = IA.get_tag(conversation['content'][0]['text'], tags=tags)

                    if any(tag['name'] in intent for tag in tags):
                        print(f"Intención detectada: {intent}")

                    else:
                        print(f"Intención no reconocida: {intent}")



                    # Get course content
                    print("**********Obteniendo contenido del curso**********\n")
                    course_name = next((course["fullname"] for course in courses if course["id"] == course_id), "None")

                    general_info = f"\n###Informacion General del Curso llamado {course_name}\n"
                    course_general_content = "###Contenido General del Curso:\n"
                    course_content_embedding = []
                    course_activities = []


                    # Get course content embeding
                    course_content = moodle.get_course_contents(course_id)


                    for section in course_content:
                        print(f"\n📚 Sección: {section['name']}")
                        course_general_content += f"\nSección: {section['name']}\n"

                        for module in section.get("modules", []):
                            print(f"  📄 Recurso: {module['name']} - tipo: {module['modname']}")
                            course_general_content += f"* Archivo/Actividad: {module['name']}\n"

                            match module["modname"]:
                                case "resource":
                                    for content in module.get("contents", []):
                                        if "mimetype" in content and content["mimetype"] == "application/pdf":
                                            download = moodle.download_file(content["fileurl"], content["mimetype"])

                                            if section['name'].lower() == "informacion general":
                                                general_info += f"\nFuente de la informacion (nombre del archivo): {module['name']}\nContenido del archivo:\n{download}\n"

                                            else:
                                                course_content_embedding.append({"source": module['name'], "text": download, "embedding": None})
                        
                    
                    # Get course activities embeding
                    if "consulta de actividad" in intent:
                        print("**********Obteniendo actividades del curso**********\n")
                        assignments = moodle.get_course_assignaments(course_id)

                        for assignment in assignments:
                            section_name = next((section["name"] for section in course_content if any(module["id"] == assignment["cmid"] for module in section["modules"])), "Unknown Section")
                            assignment_info = f"\nActividad: {assignment['name']}\nSección: {section_name}\nDescripción: {assignment.get('intro', 'Sin descripción')}\n"
                            course_general_content += f"\n{assignment_info}"

                            print(assignment_info)

                            # Check for downloadable content in the assignment
                            if "introattachments" in assignment:
                                for attachment in assignment["introattachments"]:
                                    if "mimetype" in attachment and attachment["mimetype"] == "application/pdf":
                                        download = moodle.download_file(attachment["fileurl"], attachment["mimetype"])
                                        course_activities.append({"source": assignment['name'], "text": download})


                    # search related content
                    print("**********Vectorizando**********\n")
                    conversation_text = " ".join([message["text"] for message in conversation["content"][-5:]])
                    conversation_embedding = IA.get_embedding(conversation_text)
                    question_embedding = IA.get_embedding(conversation["content"][-1]["text"])

                    print("**********Buscando contenido relacionado**********\n")
                    course_content_embedding = IA.get_embeding_list(course_content_embedding)
                    question_related_content = IA.find_similar_content(question_embedding, course_content_embedding)
                    conversation_realted_content = IA.find_similar_content(conversation_embedding, course_content_embedding)

                    # search related activities
                    question_related_activities = ""
                    if course_activities:
                        print("**********Buscando actividades relacionadas**********\n")
                        prompt = "Las siguientes son las actividades del curso, busca la que puedan ser mas util para responder la pregunta. devuelve el nombre (source) y el texto (text) de la actividad. sin agregar o modificar nada\n"

                        for activity in course_activities:
                            prompt += f"\n ### Source: {activity['source']} ###\n{activity['text']}\n"

                        question_related_activities = IA.generate_response(conversation['content'][-1]['text'], prompt, chat)




                    # system prompt
                    with open(r"files/system_prompts/Forum_Respond.txt", "r") as file:
                        # Read the system prompt template
                        system_prompt = file.read()

                    # include general information
                    system_prompt += f"{general_info}"
                    system_prompt += f"{course_general_content}"

                    # include course content
                    if "consulta general" not in intent:
                        system_prompt += "\n###Contenido del curso que podria ser util para responder (no es todo el contenido). Intenta no desviarte mucho de este contenido en tus respuestas"
                        for content in question_related_content:
                            system_prompt += f"\nFuente de la informacion (nombre del archivo): {content['source']}:\n{content['text']}\n"

                        if conversation_realted_content:
                            for content in conversation_realted_content:
                                if content['text'] not in system_prompt:
                                    system_prompt += f"\nFuente de la informacion (nombre del archivo): {content['source']}:\n{content['text']}\n"

                    # include course activities
                    if "consulta de actividad" in intent:
                        if question_related_activities:
                            system_prompt += "\n###Contenido de acividades que podria ser util para responder."
                            system_prompt += f"\n{question_related_activities}\n"



                    # response
                    print("**********Respondiendo**********\n")
                    await asyncio.to_thread(
                        moodle.reply_to_post,
                        conversation['content'][-1]['id_post'],
                        IA.generate_response(conversation['content'][-1]['text'], system_prompt, chat)
                    )

                
                else:
                    print("**********El utimo mensaje fue de un profesor**********\n")
            else:
                print("**********El utimo mensaje fue del asistente**********\n")
    else:
        print("**********El asistente no esta en el curso**********\n")


    
async def respond_discussion_test(discussion_id: int, course_id: int = None):

    print(f"1. Nuevo mensaje de la discusion: {discussion_id}\nPerteneciente al curso: {course_id}")

    user_id = moodle.get_self_id()["userid"]
    courses = moodle.get_user_courses(user_id)

    if any(course["id"] == course_id for course in courses):
        print("2. El asistente si esta en el curso")

        conversations = moodle.get_discussion_posts(discussion_id)
        conversations = moodle.get_conversations(conversations['posts'][0], course_id)

        for conversation in conversations:
            print("3. analizando conversacion...")

            if conversation['id_user'] != user_id:
                teacher = False
                print("4. El utimo mensaje no fue del asistente")

                for rol in conversation["content"][-1]["user_roles"]:
                    if rol['shortname'] in ('teacher', 'editingteacher'):
                        teacher = True

                if not teacher:
                    print("5. El utimo mensaje no fue de un profesor")
                    await asyncio.to_thread(
                        moodle.reply_to_post,
                        conversation['content'][-1]['id_post'],
                        "hola<br>mundo"
                    )











if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8765, reload=True)