# Librerias Para API
from fastapi import FastAPI, Request
import uvicorn

# Libreria para moodle
import moodle

# IA
import IA

# para evitar deadlock de webhooks
import asyncio


# Crear APP
app = FastAPI()

# Recibir eventos por webhook
@app.post("/webhook")
async def moodle_webhook_listener(request: Request):
    data = await request.json()
    print("Nuevo evento recibido:", data)

    if data["eventname"] == "\\mod_forum\\event\\post_created":
        # respond_discussion(data['other']['discussionid'], int(data["courseid"]))
        asyncio.create_task(respond_discussion(data['other']['discussionid'], int(data["courseid"])))

    elif data["eventname"] == "\\mod_forum\\event\\discussion_created":
        # respond_discussion(data['objectid'], int(data["courseid"]))
        asyncio.create_task(respond_discussion(data['objectid'], int(data["courseid"])))




    return {"status": "ok"}


async def respond_discussion(discussion_id: int, course_id: int = None):
    """
    Responder a una discusion utilizando IA y todos los contenidos del curso.
    Esta funcion sponde SI y SOLO SI el usuario registrado con el Token esta dentro del curso, y tiene los permisos necesarios.
    """

    print(f"Nuevo mensaje de la discusion: {discussion_id}\nPerteneciente al curso: {course_id}")

    user_id = moodle.get_self_id()["userid"]
    courses = moodle.get_user_courses(user_id)
    print("1.")

    if any(course["id"] == course_id for course in courses):
        print("2.")

        conversations = moodle.get_discussion_posts(discussion_id)
        conversations = moodle.get_conversations(conversations['posts'][0], course_id)

        for conversation in conversations:
            print("3.")

            if conversation['id_user'] != user_id:
                teacher = False
                print("4.")

                for rol in conversation["content"][-1]["user_roles"]:
                    if rol['shortname'] in ('teacher', 'editingteacher'):
                        teacher = True

                if not teacher:
                    print("5.")
                    print("RESPONDIENDO**********\n"*5)

                    course_content = moodle.get_course_contents(course_id)
                    course_name = next((course["shortname"] for course in courses if course["id"] == course_id), "None")
                    course_content_embedding = []
                    general_info = f"Nombre del Curso: {course_name}\n"

                    # Get course content embeding
                    for section in course_content:
                        print(f"\n📚 Sección: {section['name']}")

                        for module in section.get("modules", []):
                            print(f"  📄 Recurso: {module['name']} - tipo: {module['modname']}")

                            for content in module.get("contents", []):
                                if "mimetype" in content and content["mimetype"] == "application/pdf":
                                    download = moodle.download_file(content["fileurl"], content["mimetype"])

                                    if section['name'].lower() == "informacion general":
                                        general_info += f"\nFuente de la informacion (nombre del archivo): {module['name']}\nContenido del archivo:\n{download}\n"

                                    else:
                                        # embedding = IA.get_embedding(download)
                                        course_content_embedding.append({"source": module['name'], "text": download, "embedding": None})

                    course_content_embedding = IA.get_embeding_list(course_content_embedding)
                    print(course_content_embedding)

                    # Chat history
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

                    # search related content
                    question_embedding = IA.get_embedding(conversation['content'][0]['text'])
                    question_related_content = IA.find_similar_content(question_embedding, course_content_embedding)

                    with open(r"files/system_prompts/Forum_Respond.txt", "r") as file:
                        system_prompt = file.read()
                        system_prompt += f"""La siguiente Informacion es la Informacion General Del Curso. Utilizala para deducir el contenido general del curso: \n{general_info}\n\n"""

                        system_prompt += "La siguiente Informacion es el Contenido Del Curso que considermaos util para esta pregunta, puedes o no utilizarlo:\n"
                        for content in question_related_content:
                            system_prompt += f"\nFuente de la informacion (nombre del archivo): {content['source']}:\n{content['text']}"

                    # response
                    # response = IA.generate_response(conversation['content'][-1]['text'], system_prompt, chat)
                    # moodle.reply_to_post(conversation['content'][-1]['id_post'], response)
                    # print("Respuesta enviada correctamente.")
                    # ⬇️ ESTA ES LA CLAVE: no bloquees el loop
                    await asyncio.to_thread(
                        moodle.reply_to_post,
                        conversation['content'][-1]['id_post'],
                        IA.generate_response(conversation['content'][-1]['text'], system_prompt, chat)
                    )










if __name__ == "__main__":
    uvicorn.run("__main__:app", host="0.0.0.0", port=8765, reload=True)