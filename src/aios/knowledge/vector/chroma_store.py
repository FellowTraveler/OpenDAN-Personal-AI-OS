from .vector_base import VectorBase
from ..object import ObjectID
import chromadb
import logging
import os


class ChromaVectorStore(VectorBase):
    def __init__(self, root_dir, model_name: str) -> None:
        super().__init__(model_name)

        logging.info(
            "will init chroma vector store, model={}".format(model_name)
        )

        directory = os.path.join(root_dir, "vector")
        logging.info("will use vector store: {}".format(directory))

        client = chromadb.PersistentClient(
            path=directory, settings=chromadb.Settings(anonymized_telemetry=False)
        )
        # client = chromadb.Client()

        collection_name = "coll_{}".format(model_name)
        logging.info("will init chroma colletion: %s", collection_name)

        collection = client.get_or_create_collection(collection_name)
        self.collection = collection

    async def insert(self, vector: [float], id: ObjectID):
        logging.info(f"will insert vector: {len(vector)} id: {str(id)}")
        logging.debug(f"vector is {vector}")
        self.collection.add(
            embeddings=vector,
            ids=str(id),
        )

    async def query(self, vector: [float], top_k: int) -> [ObjectID]:
        ret = self.collection.query(
            query_embeddings=vector,
            n_results=top_k,
        )
        logging.info(f"query result {ret}")
        if len(ret['ids']) == 0:
            return []
        return list(map(ObjectID.from_base58, ret["ids"][0]))

    async def delete(self, id: ObjectID):
        self.collection.delete(
            ids=id,
        )
