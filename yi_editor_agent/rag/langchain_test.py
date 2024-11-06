import os
import json

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from yi_editor_agent.utils.config import OUTPUT_PATH, VECTOR_DB_PATH

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "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"

os.environ["AZURE_OPENAI_API_KEY"] = "3d97a348a4a24119ac590d12a4751509"
os.environ["AZURE_OPENAI_ENDPOINT"] = "https://ai2team.openai.azure.com/"

# Load the JSON data
with open(os.path.join(OUTPUT_PATH, "output.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

info = []
for prefab_info in data["PrefabInfos"]:
    # Create a document for each prefab_info
    document = """
    有一个游戏项目的美术资产描述信息为：{description}，其在项目中的路径为：{path}。
    """
    info.append(document.format(description=prefab_info["Description"]["asset_desc"], path=prefab_info["Path"]))

documents = [Document(page_content=t, metadata={"source": "PrefabInfos"}) for t in info]

# Embed
vectorstore = Chroma.from_documents(
    documents,
    embedding=OpenAIEmbeddings(
        base_url="http://10.3.2.201:9997/v1/", api_key="empty", model="bge-m3"
    ),
)

# print(vectorstore.similarity_search("我想要一个餐桌"))

retriever = vectorstore.as_retriever(
    search_type="similarity"
)

llm = AzureChatOpenAI(
    azure_deployment="ai2team-gpt4o-standard",
    api_version="2024-06-01"
)

message = """
Answer this question using the provided context only.

{question}

Context:
{context}
"""

prompt = ChatPromptTemplate.from_messages([("human", message)])

rag_chain = {"context": retriever, "question": RunnablePassthrough()} | prompt | llm


response = rag_chain.invoke("告诉我一个餐桌的Prefab的路径")

print(response.content)