import os

from datasets import load_dataset
from loguru import logger


class HuggingFaceDatasets:
    """
    Class to handle Hugging Face datasets, loading and processing them.
    """

    def __init__(self, dataset_id: str):
        self.dataset = load_dataset(dataset_id, split="all")

        logger.info(f"Loading dataset: {dataset_id}")

    def select(self, indices: list[int]) -> "HuggingFaceDatasets":
        """
        Select specific examples from the dataset by index.

        Args:
            indices: List of indices to select
        """
        self.dataset = self.dataset.select(indices)
        return self

    def select_columns(self, column_names: str | list[str]) -> "HuggingFaceDatasets":
        """
        Select specific columns from the dataset.

        Args:
            column_names: Single column name or list of column names to keep

        Returns:
            HuggingFaceDatasets: Dataset with only the selected columns
        """
        if isinstance(column_names, str):
            column_names = [column_names]

        self.dataset = self.dataset.select_columns(column_names)
        return self

    def save_images(self, save_dir: str):
        logger.info(f"Saving images to folder: {save_dir}")

        def save_image_to_disk(example, save_dir):
            filename = f"{example['image_id']}.jpg"
            filepath = os.path.join(save_dir, filename)
            example["image"].save(filepath)
            return {"image_filepath": filepath}

        os.makedirs(save_dir, exist_ok=True)

        # Update the dataset in place with new image filepaths
        self.dataset = self.dataset.map(
            lambda x: save_image_to_disk(x, save_dir), desc="Saving images", num_proc=8
        )
