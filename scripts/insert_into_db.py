import numpy as np
import pandas as pd
import psycopg
import torch
from load_datasets import HuggingFaceDatasets
from loguru import logger
from pgvector.psycopg import register_vector
from PIL import Image
from tqdm.auto import tqdm
from transformers import CLIPModel, CLIPProcessor, CLIPTokenizerFast


class PostgreSQLDatabase:
    def __init__(self, database_name: str) -> None:
        self.database_name = database_name
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.connect()
        self.setup_pgvector_extension()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        if exc_type:
            logger.error(f"Error: {exc_type} - {exc_val}")
            return False
        return True

    def connect(self):
        try:
            self.conn = psycopg.connect(dbname=self.database_name)
            self.cur = self.conn.cursor()
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def disconnect(self):
        try:
            self.cur.close()
            self.conn.close()
            logger.info("Disconnected from database")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")

    def setup_pgvector_extension(self):
        try:
            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            register_vector(self.conn)
            logger.info("pgvector extension initialized")
        except Exception as e:
            logger.error(f"Error creating pgvector extension: {e}")

    def create_table(self):
        try:
            self.cur.execute("""
            DROP TABLE IF EXISTS image_metadata;

            CREATE TABLE image_metadata (
                image_id INTEGER PRIMARY KEY,
                coco_url TEXT,
                caption TEXT,
                recaption TEXT,
                image_filepath TEXT,
                img_emb vector(512)
            )
            """)
            logger.info("Table created")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            raise

    def insert_data(self, df: pd.DataFrame, embeddings: np.ndarray):
        self.create_table()

        df["image_filepath"] = df["image_filepath"].apply(lambda x: x.split("/")[-1])
        df["img_emb"] = embeddings.T.tolist()

        # Prepare the insert statement
        insert_sql = """
        INSERT INTO image_metadata (image_id, coco_url, caption, recaption, image_filepath, img_emb)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        # Convert dataframe to list of tuples
        data = []
        for _, row in df.iterrows():
            data.append(
                (
                    row["image_id"],
                    row["coco_url"],
                    row["caption"],
                    row["recaption"],
                    row["image_filepath"],
                    row["img_emb"],
                )
            )

        self.cur.executemany(insert_sql, data)
        self.conn.commit()
        logger.info("Data inserted successfully!")


class CLIP:
    def __init__(
        self, model_id: str = "openai/clip-vit-base-patch32", device: str = None
    ) -> None:
        logger.info(f"Initializing CLIP model: {model_id}")
        self.device = device or (
            "cuda"
            if torch.cuda.is_available()
            else "mps"
            if torch.backends.mps.is_available()
            else "cpu"
        )

        logger.info(f"Using device: {self.device}")

        self.tokenizer = CLIPTokenizerFast.from_pretrained(model_id)
        self.processor = CLIPProcessor.from_pretrained(model_id)
        self.model = CLIPModel.from_pretrained(model_id).to(self.device)

    def encode_image(self, image_paths: str, batch_size: int = 128) -> np.ndarray:
        logger.info(f"Computing image embeddings in batches of {batch_size}")
        image_embeddings = None

        for i in tqdm(range(0, len(image_paths), batch_size)):
            batch_paths = image_paths[i : i + batch_size]

            # Load and process images
            batch_images = []
            for path in batch_paths:
                try:
                    img = Image.open(path).convert("RGB")
                    batch_images.append(img)
                except Exception as e:
                    logger.error(f"Error loading image {path}: {str(e)}")
                    continue

            if not batch_images:
                logger.warning(f"No valid images in batch starting at index {i}")
                continue

            batch = self.processor(
                text=None, images=batch_images, return_tensors="pt", padding=True
            )["pixel_values"].to(self.device)

            batch_emb = self.model.get_image_features(pixel_values=batch)
            batch_emb = batch_emb.squeeze(0)
            batch_emb = batch_emb.cpu().detach().numpy()

            if image_embeddings is None:
                image_embeddings = batch_emb
            else:
                image_embeddings = np.concatenate((image_embeddings, batch_emb), axis=0)

        image_embeddings = image_embeddings.T / np.linalg.norm(image_embeddings, axis=1)

        logger.info(
            f"Finished processing. Final embedding shape: {image_embeddings.shape}"
        )
        return image_embeddings

    def encode_text(self, text: str) -> np.ndarray:
        logger.info(f"Computing text embedding for: {text}")
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        text_emb = self.model.get_text_features(**inputs)
        text_emb = text_emb.cpu().detach().numpy()
        return text_emb.flatten()


if __name__ == "__main__":
    ds = HuggingFaceDatasets("UCSC-VLAA/Recap-COCO-30K")
    ds.save_images("data/saved_images_coco_30k", num_images=1000)

    clip = CLIP(model_id="openai/clip-vit-base-patch32")
    image_embeddings = clip.encode_image(ds.image_paths, batch_size=256)

    with PostgreSQLDatabase("retrieval_db") as db:
        db.insert_data(ds.pandas_df, image_embeddings)
