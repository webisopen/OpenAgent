import asyncio
import os
from langchain.text_splitter import MarkdownTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.indexes import index, SQLRecordManager
from langchain.schema import Document

from openagent.sources.inputs.pendle_knowledge_base.extractor import docling_extractor
from openagent.sources.inputs.pendle_knowledge_base.recursive_url_loader import RecursiveUrlLoader


async def main():
    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

    page_url = "https://docs.pendle.finance/ProtocolMechanics/LiquidityEngines/AMM"

    # Initialize loader with docling extractor
    loader = RecursiveUrlLoader(
        url=page_url,
        max_depth=3,
        extractor=docling_extractor,
        use_async=True,
    )

    # Initialize text splitter
    text_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)

    # Initialize or load vector store
    index_dir = "pendle_docs_index"
    if os.path.exists(index_dir):
        vector_store = FAISS.load_local(index_dir, embeddings)
    else:
        # Create an empty vector store if it doesn't exist
        vector_store = FAISS.from_documents([Document(page_content="", metadata={})], embeddings)
        vector_store.save_local(index_dir)

    # Initialize record manager for tracking document changes
    record_manager = SQLRecordManager(
        namespace="pendle_docs", 
        db_url="sqlite:///pendle_index.db"
    )
    await record_manager.acreate_schema()

    # Process and index documents incrementally
    docs = []
    async for doc in loader.alazy_load():
        # Split the document
        split_docs = text_splitter.split_documents([doc])
        docs.extend(split_docs)

    print(f"Processing {len(docs)} document chunks")

    # Index documents with incremental updates
    result = await index(
        docs,
        record_manager,
        vector_store,
        cleanup="incremental",
        source_id_key="source"
    )

    print("\nIndexing Results:")
    print(f"Added: {result['num_added']}")
    print(f"Updated: {result['num_updated']}")
    print(f"Skipped: {result['num_skipped']}")
    print(f"Deleted: {result['num_deleted']}")

    # Save the updated vector store
    vector_store.save_local(index_dir)

    # Test search functionality
    query = "What is Pendle's AMM mechanism?"
    results = vector_store.similarity_search(query, k=3)

    print("\nSearch Results:")
    for i, doc in enumerate(results, 1):
        print(f"\nResult {i}:")
        print("Content:", doc.page_content[:200])
        print("Source:", doc.metadata.get('source', 'N/A'))


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
