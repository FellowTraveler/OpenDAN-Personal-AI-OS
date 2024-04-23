import os
import logging
import json
from aios import *

class EmbeddingEnvironment(SimpleEnvironment):
    def __init__(self, workspace: str) -> None:
        super().__init__(workspace)
        self.path = os.path.join(AIStorage.get_instance().get_myai_dir(), "knowledge/indices/embedding")
        self._default_text_model = "all-MiniLM-L6-v2"
        self._default_image_model = "clip-ViT-B-32"

        query_param = {
            "tokens": "key words to query", 
            "types": "prefered knowledge types, one or more of [text, image]",
            "limit": "index of query result"
        }
        self.add_ai_function(SimpleAIFunction("query_knowledge", 
                                            "vector query content from local knowledge base",
                                            self._query, 
                                            query_param))
        
    def __get_vector_store(self, model_name: str) -> ChromaVectorStore:
        return ChromaVectorStore(self.path, model_name)
    
    async def query_objects(self, tokens: str, types: list[str], topk: int) -> [ObjectID]:
        texts = []
        if "text" in types:
            vector = await ComputeKernel.get_instance().do_text_embedding(tokens, self._default_text_model)
            texts = await self.__get_vector_store(self._default_text_model).query(vector, topk)
        images = []
        if "image" in types:
            vector = await ComputeKernel.get_instance().do_text_embedding(tokens, self._default_image_model)
            images = await self.__get_vector_store(self._default_image_model).query(vector, topk)
        return texts + images
    
        
    def tokens_from_objects(self, object_ids: [ObjectID]) -> list[str]:
        results = dict()
        for object_id in object_ids:
            parents = KnowledgeStore().get_relation_store().get_related_root_objects(object_id)
            # last parent is the root object
            root_object_id = parents[0] if parents else object_id
            logging.info(f"object_id: {str(object_id)} root_object_id: {str(root_object_id)}")
            if str(root_object_id) in results:
                results[str(root_object_id)].append(object_id)
            else:
                results[str(root_object_id)] = [root_object_id, object_id]
        content = ""
        result_desc = []
        for result in results.values():
            # first element in result is the root object
            root_object_id = result[0]
            if root_object_id.get_object_type() == ObjectType.Email:
                email = KnowledgeStore().load_object(root_object_id)
                desc = email.get_desc()
                desc["type"] = "email"
                desc["contents"] = []
                result_desc.append(desc)
                upper_list = desc["contents"]
                result = result[1:]
            else:
                upper_list = result_desc
            
            for object_id in result:
                if object_id.get_object_type() == ObjectType.Chunk:
                    upper_list.append({"type": "text", "content": KnowledgeStore().get_chunk_reader().get_chunk(object_id).read().decode("utf-8")})
                if object_id.get_object_type() == ObjectType.Image:
                    # image = self.load_object(object_id)
                    desc = dict()
                    desc["id"] = str(object_id)
                    desc["type"] = "image"
                    upper_list.append(desc)
                if object_id.get_object_type() == ObjectType.Video:
                    video = KnowledgeStore().load_object(object_id)
                    desc = video.get_desc()
                    desc["type"] = "video"
                    upper_list.append(desc)
                else:
                    pass
        content += json.dumps(result_desc)
        content += ".\n"  

        return content
    
    async def _query(self, tokens: str, types: list[str] = ["text"], index: str=0):
        index = int(index)
        object_ids = await self.query_objects(tokens, types, 4)
        if len(object_ids) <= index:
            return "*** I have no more information for your reference.\n"
        else:
            content = "*** I have provided the following known information for your reference with json format:\n"
            return content + self.tokens_from_objects(object_ids[index:index+1])

def init(workspace: str) -> EmbeddingEnvironment:
    return EmbeddingEnvironment(workspace)