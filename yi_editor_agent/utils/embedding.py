import chromadb
import os
os.environ["OPENAI_API_KEY"] = "sk-proj-r6LyGkn7Bv2PxyQ7zeCKT3BlbkFJ3WqIYOLbOjqqq5q0TrU2"
import json
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext, Document
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from yi_editor_agent.utils.config import OUTPUT_PATH, VECTOR_DB_PATH


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
    document = {
        "Name": prefab_info["Name"],
        "Path": prefab_info["Path"],
        # "Type": prefab_info["Type"],
        # "Tags": prefab_info["Tags"],
        # "Layer": prefab_info["Layer"],
        # "CreationDate": prefab_info["CreationDate"],
        # "ModificationDate": prefab_info["ModificationDate"],
        # "ThumbnailPaths": prefab_info["ThumbnailPaths"],
        "Description": prefab_info["Description"]["asset_desc"]
    }
    info.append(json.dumps(document))

documents =[Document(text=t) for t in info]

openai_embedding = OpenAIEmbedding(api_key=os.environ["OPENAI_API_KEY"], model="text-embedding-3-large")
Settings.embed_model = openai_embedding
# Create the index from the documents
index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)

# Create a query engine and query
query_engine = index.as_query_engine()
response = query_engine.query("帮我找到一个棕色的餐桌的Prefab, 输出对应的路径")
print(response)
