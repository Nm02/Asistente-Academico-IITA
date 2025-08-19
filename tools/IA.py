import os
import requests

# Calcular Tokens
import tiktoken

# Busqueda por similitud de embedings (diferencia de cocenos)
import faiss
import numpy as np


# Variables de entorno
API_KEY = os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"


def generate_response(prompt: str, system_prompt: str = "", chat_history: list[dict] = [], model: str = "gpt-4.1") -> str:
    """
    Función para realizar solicitud con contexto
    """

    url = API_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    messages = [{"role": "system", "content": system_prompt}]   # Cargar system prompt
    messages.extend(chat_history)                               # Cargar mensajes previos
    messages.append({"role": "user", "content": prompt})        # Cargar ultimo mensaje (el que debe ser respondido)

    # Cargar el contenido de la conversacion al body
    body = {
        "model": model,
        "messages": messages
    }

    # realizamos la solicitud y guardamos una respuesta
    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        # Extraemos el texto de la respuesta y lo devolvemos
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return reply
    else:
        # En caso de que gemini devuelva un error, lo mostramos
        print("Error:", response.status_code, response.text)
        return None
    
def get_tag(prompt: str, tags: list[dict], system_prompt: str = "", chat_history: list[dict] = [], model: str = "gpt-4.1") -> list[str]:
    """
    Función para realizar solicitud con contexto y asignar tags desde una lista dada.

    Parámetros:
        prompt (str): El mensaje del usuario.
        tags (list[dict]): Lista de diccionarios con formato {"name": nombre_tag, "description": descripcion_tag}.
        system_prompt (str): Mensaje del sistema para el contexto.
        chat_history (list[dict]): Historial de mensajes previos.
        model (str): Modelo de IA a utilizar.

    Retorna:
        list[str]: Lista de nombres de tags asignados.
    """

    url = API_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    # Crear un mensaje con la lista de tags formateada
    tags_description = "\n".join([f"- {tag['name']}: {tag['description']}" for tag in tags])
    system_prompt += f"\n\nA continuación, se te proporciona una lista de tags disponibles:\n{tags_description}\n\nTu tarea es asignar los tags más relevantes al mensaje del usuario, devolviendo únicamente los nombres de los tags en formato de lista JSON."

    messages = [{"role": "system", "content": system_prompt}]   # Cargar system prompt
    messages.extend(chat_history)                               # Cargar mensajes previos
    messages.append({"role": "user", "content": prompt})        # Cargar último mensaje (el que debe ser respondido)

    # Cargar el contenido de la conversación al body
    body = {
        "model": model,
        "messages": messages
    }

    # Realizamos la solicitud y guardamos una respuesta
    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        # Extraemos el texto de la respuesta y lo devolvemos como lista de tags
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        try:
            assigned_tags = eval(reply)  # Convertir la respuesta en lista
            if isinstance(assigned_tags, list) and all(isinstance(tag, str) for tag in assigned_tags):
                return assigned_tags
            else:
                print("Error: Respuesta no tiene el formato esperado.")
                return []
        except Exception as e:
            print("Error al procesar la respuesta:", e)
            return []
    else:
        # En caso de que la IA devuelva un error, lo mostramos
        print("Error:", response.status_code, response.text)
        return []


def get_embedding(text: str, model: str = "text-embedding-3-small") -> list:
    """
    Genera un embedding para un texto dado usando la API de OpenAI.

    Parámetros:
        text (str): El texto a convertir en embedding.
        api_key (str): Tu clave de API de OpenAI.
        model (str): Modelo de embedding (por defecto: text-embedding-3-small).

    Retorna:
        list: Vector embedding (lista de floats).
    """

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "input": text,
        "model": model
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Lanza excepción si hubo error
    return response.json()["data"][0]["embedding"]


def get_embeding_list(records, model: str = "text-embedding-3-small", skip_existing: bool = True, batch_size: int | None = None):
    """
    Agrega 'embedding' a cada item de 'records' usando una sola request (o batches si se indica).
    
    Parámetros:
        records (list[dict] | dict): Cada item debe tener al menos:
            - "source": cualquier identificador (no se usa para la API, solo se conserva)
            - "text": str con el contenido a vectorizar
            - "embedding": opcional; si existe y skip_existing=True, no se re-embebe
        model (str): Modelo de embeddings de OpenAI.
        skip_existing (bool): Si True, no re-calcula embeddings existentes.
        batch_size (int|None): Si None -> una sola request con todos los textos.
                               Si int -> procesa en lotes de ese tamaño.

    Retorna:
        La misma estructura 'records' con el campo "embedding" agregado/actualizado.
        (Modifica en sitio y también lo devuelve por conveniencia).
    """

    # Permitir pasar un único dict y normalizar a lista
    single_input = False
    if isinstance(records, dict):
        records = [records]
        single_input = True

    # Seleccionar índices a vectorizar (respetando orden)
    indices_to_embed = [
        i for i, rec in enumerate(records)
        if ("text" in rec) and (not (skip_existing and "embedding" in rec and rec["embedding"] is not None))
    ]
    if not indices_to_embed:
        return records[0] if single_input else records  # Nada que hacer

    def _post_embeddings(texts_chunk: list[str]) -> list[list[float]]:
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "input": texts_chunk,
            "model": model
        }
        resp = requests.post(url, headers=headers, json=data)
        resp.raise_for_status()
        return [data["embedding"] for data in resp.json()["data"]]

    # Armar textos en el orden de indices_to_embed
    texts = [records[i]["text"] for i in indices_to_embed]

    if batch_size is None:
        # UNA SOLA REQUEST
        vectors = _post_embeddings(texts)
        for idx, vec in zip(indices_to_embed, vectors):
            records[idx]["embedding"] = vec
    else:
        # En lotes (por si alguna vez lo necesitás)
        start = 0
        while start < len(texts):
            end = start + batch_size
            chunk = texts[start:end]
            chunk_indices = indices_to_embed[start:end]
            vectors = _post_embeddings(chunk)
            for i, vec in zip(chunk_indices, vectors):
                records[i]["embedding"] = vec
            start = end

    return records[0] if single_input else records


def find_similar_content(query_embedding: list[float], documents: list[dict], top_n: int = 1) -> list[dict]:
    """
    Encuentra los `top_n` documentos más similares a un embedding de consulta, utilizando FAISS
    con **similitud coseno** (producto interno sobre vectores normalizados).

    Parámetros:
        query_embedding (list[float]): Vector de embedding de la consulta del usuario.
        documents (list[dict]): Lista de documentos, cada uno con:
            {
                "text": str,
                "source": str,
                "embedding": list[float]
            }
        top_n (int): Cantidad de documentos más similares a retornar.

    Retorna:
        list[dict]: Lista de los top_n documentos más relevantes con su score de similitud (coseno).
    """
    if not documents:
        return []

    # Paso 1: Convertir embeddings de los documentos a matriz NumPy float32
    embedding_dim = len(documents[0]["embedding"])
    doc_vectors = np.array([doc["embedding"] for doc in documents], dtype="float32")

    # Validación simple de dimensiones (opcional)
    if doc_vectors.shape[1] != embedding_dim or len(query_embedding) != embedding_dim:
        raise ValueError("Dimensión de embeddings inconsistente entre documentos y/o query.")

    # Paso 2: Normalizar documentos (L2 = 1) para que IP == coseno
    faiss.normalize_L2(doc_vectors)

    # Paso 3: Crear índice FAISS basado en producto interno (equivale a coseno con vectores normalizados)
    index = faiss.IndexFlatIP(embedding_dim)

    # Paso 4: Agregar los vectores al índice
    index.add(doc_vectors)

    # Paso 5: Convertir y normalizar el embedding de la query a matriz 2D (1 x embedding_dim)
    query_vector = np.array(query_embedding, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(query_vector)

    # Asegurar límites de top_n
    top_n = max(1, min(top_n, len(documents)))

    # Paso 6: Buscar los documentos más similares (scores en [-1, 1], mayor = mejor)
    scores, indices = index.search(query_vector, top_n)

    # Paso 7: Devolver los resultados ordenados con sus scores
    results = []
    for i, (idx, score) in enumerate(zip(indices[0], scores[0]), start=1):
        doc = documents[idx]
        results.append({
            "rank": i,
            "similarity_score": float(score),        # coseno (más alto = mejor)
            "source": doc.get("source", "desconocido"),
            "text": doc["text"]
        })

    return results










# def split_text_into_chunks(text: str, max_tokens: int = 8000, model: str = "text-embedding-3-small") -> list[str]:
#     """
#     Divide un texto largo en partes más pequeñas, respetando el límite de tokens.

#     Parámetros:
#         text (str): El texto completo.
#         max_tokens (int): Máximo de tokens por chunk.
#         model (str): Nombre del modelo (usado para el tokenizador correcto).

#     Retorna:
#         list[str]: Lista de fragmentos del texto.
#     """
#     encoding = tiktoken.encoding_for_model(model)
#     words = text.split()
    
#     chunks = []
#     current_chunk = []

#     for word in words:
#         current_chunk.append(word)
#         token_count = len(encoding.encode(" ".join(current_chunk)))

#         if token_count > max_tokens:
#             current_chunk.pop()  # Eliminar la última palabra que causó overflow
#             chunks.append(" ".join(current_chunk))
#             current_chunk = [word]  # Empezar nuevo chunk con la palabra que sobró

#     if current_chunk:
#         chunks.append(" ".join(current_chunk))

#     return chunks