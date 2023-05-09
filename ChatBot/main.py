# Import necessary modules
import os

import gradio as gr
import numpy as np
from dotenv import load_dotenv
from langchain import OpenAI
from llama_index import Document
from llama_index import GPTSimpleVectorIndex, LLMPredictor, ServiceContext
from sentence_transformers import SentenceTransformer

# Load env ariables from .env file
load_dotenv()
api_key = os.getenv("API_SECRET_KEY")

# Set OpenAI API key as environment variable
os.environ["OPENAI_API_KEY"] = api_key

model = SentenceTransformer('paraphrase-distilroberta-base-v1')


def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def get_airline_file(airline_name, directory_path):
    for file in os.listdir(directory_path):
        if airline_name.lower() in file.lower():
            return os.path.join(directory_path, file)
    return None


def is_related(airline_name, question, min_similarity=0.2):
    file_path = get_airline_file(airline_name, "Knowledge")
    if file_path is None:
        return False

    with open(file_path, "r", encoding='utf-8') as f:
        doc_text = f.read()

    question_embedding = model.encode([question])[0]
    doc_embedding = model.encode([doc_text])[0]
    similarity = cosine_similarity(question_embedding, doc_embedding)

    return similarity > min_similarity


def construct_index(airline_name, directory_path):
    file_path = get_airline_file(airline_name, directory_path)
    if file_path is None:
        return None

    with open(file_path, "r", encoding='utf-8') as f:
        doc_text = f.read()

    num_outputs = 200
    llm_predictor = LLMPredictor(llm=OpenAI(temperature=0.7, model_name="text-davinci-003", max_tokens=num_outputs))
    service_context = ServiceContext.from_defaults(llm_predictor=llm_predictor)
    doc = Document(text=doc_text)
    index = GPTSimpleVectorIndex.from_documents([doc], service_context=service_context)
    directory_path = "AirLineJson"
    filename = f"{airline_name}_index.json"
    file_path = os.path.join(directory_path, filename)
    index.save_to_disk(file_path)
    return index


def chatbot(airline_name, input_text):
    if is_related(airline_name, input_text):
        index = construct_index(airline_name, "Knowledge")
        directory_path = "AirLineJson"
        filename = f"{airline_name}_index.json"
        file_path = os.path.join(directory_path, filename)
        index.save_to_disk(file_path)
        index = GPTSimpleVectorIndex.load_from_disk(file_path)
        response = index.query(input_text, response_mode="compact")
        return response.response
    else:
        return "I'm sorry, I cannot answer questions unrelated to my knowledge base."



iface = gr.Interface(fn=chatbot,
                     inputs=[gr.inputs.Textbox(lines=1, label="Enter the airline name"),
                             gr.inputs.Textbox(lines=7, label="Enter your text")],
                     outputs="text",
                     title="TLDR")

iface.launch(share=True)
