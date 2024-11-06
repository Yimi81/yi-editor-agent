import chromadb
import os
# os.environ["OPENAI_API_KEY"] = "sk-proj-r6LyGkn7Bv2PxyQ7zeCKT3BlbkFJ3WqIYOLbOjqqq5q0TrU2"
import json
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.core import Settings
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.xinference import XinferenceEmbedding

from yi_editor_agent.utils.config import OUTPUT_PATH, VECTOR_DB_PATH
from llama_index.core import set_global_handler

set_global_handler("simple")

aoai_api_key = "3d97a348a4a24119ac590d12a4751509"
aoai_endpoint = "https://ai2team.openai.azure.com/"
aoai_api_version = "2024-06-01"
deployment_name = 'ai2team-gpt4o-standard'

# Load the JSON data
with open(os.path.join(OUTPUT_PATH, 'output.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

# Initialize the ChromaDB client
db = chromadb.PersistentClient(path=VECTOR_DB_PATH)

# Get or create the Chroma collection
chroma_collection = db.get_or_create_collection("chroma_collection")

# Assign Chroma as the vector_store to the context
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Process each PrefabInfo as a separate document
info = []
for prefab_info in data["PrefabInfos"]:
    # Create a document for each prefab_info
    document = """
    有一个游戏项目的美术资产描述信息为：{description}，其在项目中的路径为：{path}。
    """
    info.append(document.format(description=prefab_info["Description"]["asset_desc"], path=prefab_info["Path"]))

documents =[Document(text=t) for t in info]


llm = AzureOpenAI(
    engine=deployment_name,
    model="gpt-4o",
    api_key=aoai_api_key,
    azure_endpoint=aoai_endpoint,
    api_version=aoai_api_version,
)

bge_embedding = XinferenceEmbedding(base_url="http://10.3.2.201:9997", model_uid="bge-m3")

Settings.llm = llm
Settings.embed_model = bge_embedding
# Create the index from the documents
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

# Create a query engine and query
query_engine = index.as_chat_engine()
response = query_engine.chat("帮我找到一个棕色的餐桌的Prefab, 输出对应的路径")
print(response)
