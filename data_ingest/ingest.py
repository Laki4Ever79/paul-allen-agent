"""
Data Ingestion Script for PineconeDB
This script performs the following actions:

Loads configuration from environment variables (.env file).
Accepts a command-line argument for the input data file.
Loads text data from the specified local file.
Connects to Pinecone and creates a new serverless index, deleting any old one.
Configures LlamaIndex settings for embedding and text parsing.
Chunks the documents, creates embeddings, and stores them in the Pinecone index.
"""
import os
import logging
import sys
import argparse
from dotenv import load_dotenv

import pinecone
from pinecone import ServerlessSpec # New import for Pinecone Serverless
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

def main():
    """Main function to handle the data ingestion pipeline."""
    # Set up command-line argument parsing for the input file.
    parser = argparse.ArgumentParser(description="Ingest data from a local file into a Pinecone index.")
    parser.add_argument(
        "--input-file",
        type=str,
        default="./data_ingest/paul_allen_data.txt",
        help="The path to the input text file."
    )
    args = parser.parse_args()
    input_file = args.input_file

    # Load configuration from the .env file.
    load_dotenv()

    # Pinecone and OpenAI settings
    # Ensure these environment variables are defined in your .env file
    pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_region = os.getenv("PINECONE_REGION") # Default region for serverless
    pinecone_cloud = os.getenv("PINECONE_CLOUD") # Default cloud provider for serverless
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # Embedding model settings
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    # Ensure embedding_dim is loaded as an integer.
    try:
        embedding_dim = int(os.getenv("EMBEDDING_DIM", "1024"))
    except (ValueError, TypeError):
        logging.error("EMBEDDING_DIM environment variable must be a valid integer. Defaulting to 1024.")
        embedding_dim = 1024

    # Validate that all necessary API keys are present.
    if not all([pinecone_index_name, pinecone_api_key, openai_api_key]):
        raise ValueError("PINECONE_INDEX_NAME, PINECONE_API_KEY, or OPENAI_API_KEY is not set in the .env file.")

    logging.info(f"Configuration loaded. Using Pinecone index: '{pinecone_index_name}'")

    # Loading input file
    if not os.path.exists(input_file):
        logging.error(f"Input file not found at: {input_file}")
        sys.exit(1) # Exit the script if the file doesn't exist.

    logging.info(f"Loading data from '{input_file}'...")
    reader = SimpleDirectoryReader(input_files=[input_file])
    documents = reader.load_data()
    logging.info(f"Successfully loaded {len(documents)} document(s).")

    # Pinecone index setup
    logging.info("Initializing Pinecone client...")
    pc = pinecone.Pinecone(api_key=pinecone_api_key)

    # Check if the index already exists and delete it for a fresh start.
    if pinecone_index_name in pc.list_indexes().names():
        logging.warning(f"Pinecone index '{pinecone_index_name}' already exists. Deleting it.")
        pc.delete_index(pinecone_index_name)

    # Create a new serverless index with the specified configuration.
    logging.info(f"Creating new Pinecone index '{pinecone_index_name}' with {embedding_dim} dimensions...")
    pc.create_index(
        name=pinecone_index_name,
        dimension=embedding_dim,
        metric="cosine",
        spec=ServerlessSpec( # Use ServerlessSpec for serverless indexes
            cloud=pinecone_cloud,
            region=pinecone_region
        )
    )
    pinecone_index = pc.Index(pinecone_index_name)
    logging.info("Pinecone index created successfully.")

    # Configure the global LlamaIndex settings for the embedding model and node parser.
    Settings.embed_model = OpenAIEmbedding(
        model=embedding_model,
        dimensions=embedding_dim,
        api_key=openai_api_key
    ) # Chunk size 256 as 512 was proven too wide
    Settings.node_parser = SentenceSplitter(chunk_size=256, chunk_overlap=20)

    # Create the PineconeVectorStore and StorageContext.
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    logging.info("Creating VectorStoreIndex and ingesting documents into Pinecone...")
    # This command triggers the chunking, embedding, and indexing process.
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True
    )

    logging.info("--- INGESTION COMPLETE ---")
    logging.info(f"Data from '{input_file}' is now indexed in Pinecone index '{pinecone_index_name}'.")

if __name__ == "__main__":
    main()