import os
import fitz  # PyMuPDF
from PIL import Image
import io
import torch
from transformers import CLIPProcessor, CLIPModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from llm_backend.utils.logger import logger


class MultimodalProcessor:
    def __init__(self, model_name="openai/clip-vit-base-patch32", device="cpu"):
        self.device = device
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        logger.info(f"MultimodalProcessor initialized with {model_name} on {device}")

    def extract_images_from_pdf(self, pdf_path):
        """Extracts images and their context from a PDF file."""
        doc = fitz.open(pdf_path)
        images_data = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_context = page.get_text()[:500]  # Context for the image
            image_list = page.get_images(full=True)

            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]

                # Convert to PIL Image
                image = Image.open(io.BytesIO(image_bytes))

                images_data.append(
                    {
                        "image": image,
                        "image_bytes": image_bytes,
                        "page": page_num + 1,
                        "context": text_context,
                        "ext": base_image["ext"],
                    }
                )

        logger.info(f"Extracted {len(images_data)} images from {pdf_path}")
        return images_data

    def encode_text(self, text):
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(
            self.device
        )
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
        return text_features.cpu().numpy()[0].tolist()

    def encode_image(self, image):
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)
        return image_features.cpu().numpy()[0].tolist()

    async def index_pdf_images(
        self, client: QdrantClient, col_name: str, pdf_path: str
    ):
        """Extracts and indexes images into a Qdrant collection."""
        images_data = self.extract_images_from_pdf(pdf_path)
        points = []

        for i, img_data in enumerate(images_data):
            img_emb = self.encode_image(img_data["image"])

            # Use filename + index as deterministic ID
            import hashlib

            point_id = hashlib.md5(f"{pdf_path}_{i}".encode()).hexdigest()
            # Convert hex to UUID format for Qdrant if needed, but hex string is fine for query_points

            payload = {
                "source": os.path.basename(pdf_path),
                "page": img_data["page"],
                "context": img_data["context"],
                "type": "image",
            }

            points.append(
                PointStruct(id=point_id, vector={"image": img_emb}, payload=payload)
            )

        if points:
            client.upsert(collection_name=col_name, points=points)
            logger.info(
                f"Indexed {len(points)} images from {pdf_path} into '{col_name}'"
            )

    async def search_images_by_text(
        self, client: QdrantClient, col_name: str, query_text: str, top_k=5
    ):
        """Cross-modal search: Text to Image."""
        query_emb = self.encode_text(query_text)

        results = client.query_points(
            collection_name=col_name,
            query=query_emb,
            using="image",
            limit=top_k,
            with_payload=True,
        ).points
        return results
