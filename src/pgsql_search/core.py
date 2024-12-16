import glob
from pathlib import Path

import pandas as pd
from datasets import Dataset

from .database import PostgreSQLDatabase
from .loader import HuggingFaceDatasets

__all__ = ["search_fts"]


def search_fts(query: str):
    """
    Search for the query in the full-text search index in the database.
    """
    return query


def insert_dataset(df: pd.DataFrame):
    """
    Load a Hugging Face dataset into a PostgreSQL database.
    """


def embed_image():
    """
    Turn image into a vector embedding.
    """
    pass


def embed_text():
    """
    Turn text into a vector embedding.
    """
    pass


def search_image():
    pass


def search_text():
    pass


def search_hybrid():
    pass
