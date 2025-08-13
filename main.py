import requests

import os
from dotenv import load_dotenv

import tools.moodle as moodle

# === CONFIGURACIÓN ===
current_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path)


MOODLE_URL = os.getenv("MOODLE_URL")  # Cambiar por tu URL
TOKEN = os.getenv("TOKEN")       # Cambiar por tu token real
ENDPOINT = f"{MOODLE_URL}/webservice/rest/server.php"


# ID del usuario del token (¡importante!)
user = moodle.get_self_id(TOKEN, ENDPOINT)
USER_ID = user["userid"]  # reemplazalo con el ID real del usuario

#lista de cursos
courses = moodle.get_user_courses(TOKEN, ENDPOINT, USER_ID)


for course in courses:
    print(f"[{course['id']}] {course['fullname']}")
