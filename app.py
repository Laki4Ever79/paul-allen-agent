import os
import logging
from dotenv import load_dotenv
import sys

import chainlit as cl

from llama_index.core import (
    VectorStoreIndex,
    Settings,
)
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.agent import ReActAgent
import pinecone

from semantic_router.routers import SemanticRouter
from semantic_router.encoders import OpenAIEncoder

from router import allowed_routes # Import the defined routes from router.py

# Load configuration from the .env file.
load_dotenv()

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

# Ensure OpenAI API Key is loaded before setting LlamaIndex settings
pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
openai_api_key = os.getenv("OPENAI_API_KEY")
embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # Default to 'text-embedding-3-small' if not set

# Ensure it matches the dimension used during ingestion.
try:
    embedding_dim = int(os.getenv("EMBEDDING_DIM", 1024))
except (ValueError, TypeError):
    logging.error("EMBEDDING_DIM environment variable must be a valid integer. Defaulting to 1024.")
    embedding_dim = 1024

if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file.")

Settings.embed_model = OpenAIEmbedding(
    model=embedding_model,
    dimensions=embedding_dim,
    api_key=openai_api_key
)

try:
    semantic_encoder = OpenAIEncoder(
        name=embedding_model, # Use the same embedding model as LlamaIndex
        openai_api_key=openai_api_key
    )
    router_layer = SemanticRouter(encoder=semantic_encoder, routes=allowed_routes, auto_sync="merge-force-local")
    logging.info("Semantic Router layer initialized successfully.")
except Exception as e:
    logging.error(f"Error initializing Semantic Router: {e}")
    # Handle error appropriately, maybe disable routing or exit.


# --------------------------------------------------------------------------
# CHAINLIT APPLICATION LOGIC
# --------------------------------------------------------------------------
@cl.on_chat_start
async def on_chat_start():
    """Initializes the LlamaIndex Agent with a Query Engine Tool."""

    image = cl.Image(path="./public/Paul_Allen.jpg", name="image1", display="inline")
    author_name = "Paul Allen AI Agent"
    header_elements = [
        cl.Text(name="Paul Allen Archives", content="💡 From Microsoft to Megayachts: Ask Anything", display="inline")
    ]

    cl.user_session.set("author_name", author_name)

    await cl.Message(
        content="",
        elements = header_elements,
        author=author_name
    ).send()

    await cl.Message(
        elements=[image],
        content="",
        author=author_name
    ).send()

    await cl.Message(
        content="Hello! Please ask me anything about Microsoft's co-founder - Paul Allen, his life, career, or interests. I am here to help!",
        author=author_name
    ).send()

    try:
        logging.info("Connecting to Pinecone and setting up the agent...")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_region = os.getenv("PINECONE_REGION")

        if not pinecone_api_key or not pinecone_region:
            raise ValueError("PINECONE_API_KEY or PINECONE_ENVIRONMENT not found in .env file.")

        pc = pinecone.Pinecone(api_key=pinecone_api_key) # Environment is set when creating the index
        pinecone_index = pc.Index(pinecone_index_name)
        vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        query_engine = index.as_query_engine(streaming=True, similarity_top_k=3)
        
        paul_allen_tool = QueryEngineTool(
            query_engine=query_engine,
            metadata=ToolMetadata(
                name="paul_allen_knowledge_base",
                description=(
                    "Provides information about the life, career, and interests of Paul Allen. "
                    "Use this tool for any questions related to Paul Allen, Microsoft, his philanthropy, "
                    "yachts, investments, or personal history."
                ),
            ),
        )

        llm = OpenAI(model="gpt-4o", api_key=openai_api_key) # Pass API key to the LLM
        agent = ReActAgent.from_tools([paul_allen_tool], llm=llm, verbose=True)

        cl.user_session.set("agent", agent)
        logging.info("LlamaIndex agent setup complete.")

    except Exception as e:
        logging.error(f"Error during chat start: {e}")
        await cl.Message(content=f"Sorry, an error occurred during setup: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Handles incoming messages, first checking against the router, then passing to the agent.
    """

    # Ensure router_layer is initialized globally or handled if not.
    if 'router_layer' not in globals():
        await cl.Message(content="Semantic Router is not initialized. Please check server logs.").send()
        return

    route_result = router_layer(message.content)
    allowed_route_names = ["paul_allen_questions", "greetings", "farewells", "gratitude"]
    
    if route_result.name not in allowed_route_names:
        # If the route is anything other than our allowed route, we refuse.
        await cl.Message(
            content="I apologize, but I am an AI agent designed specifically to answer questions about Paul Allen. I cannot assist with other topics."
        ).send()
        return

    # If the route is None, it means it's a valid query. Proceed with the agent.
    agent = cl.user_session.get("agent")
    if not agent:
        await cl.Message(content="Sorry, the agent is not available.").send()
        return

    response_stream = await cl.make_async(agent.stream_chat)(message.content)
    
    msg = cl.Message(content="")
    await msg.send()

    # Stream response
    response_text = ""
    for token in response_stream.response_gen:
        response_text += token
        await msg.stream_token(token)
    
    msg.content = response_text
    await msg.update()
