import ast
import logging
import random
from typing import List
from pathlib import Path

from aidial_interceptors_sdk.utils._env import get_env

from spacy.language import Language
from spacy.training.example import Example

_log = logging.getLogger(__name__)

_PRESIDIO_NLP_MODEL_TRAINING_DATA = get_env(
    "PRESIDIO_NLP_MODEL_TRAINING_DATA",
    "Training data not provided in the environment variable 'PRESIDIO_NLP_MODEL_TRAINING_DATA'."
)


def create_custom_trained_model(default_nlp_model: Language, lang: str):
    examples = add_examples(default_nlp_model)
    trained_model = train_model(nlp=default_nlp_model, examples=examples)
    load_custom_trained_model(trained_model, get_custom_trained_model_name(lang))
    _log.info(f"Custom trained model based on {str(default_nlp_model)} has been created")


def train_model(nlp: Language, examples: List[Example]) -> Language:
    optimizer = nlp.resume_training()
    for _ in range(50):
        random.shuffle(examples)
        losses = {}
        nlp.update(examples, drop=0.25, losses=losses, sgd=optimizer)

    _log.debug(f"Examples size: {len(examples)}")
    return nlp


def ensure_parent_directory_exists(path):
    directory = Path(path).parent
    directory.mkdir(parents=True, exist_ok=True)


def get_custom_trained_model_name(lang: str) -> str:
    return "custom_trained_models/" + lang


def load_custom_trained_model(nlp: Language, custom_trained_model_name: str):
    ensure_parent_directory_exists(custom_trained_model_name)
    nlp.to_disk(custom_trained_model_name)


def add_examples(nlp: Language) -> List[Example]:
    examples = []
    training_data_list = get_training_data()
    for text, annotations in training_data_list:
        examples.append(Example.from_dict(nlp.make_doc(text), annotations))
    return examples


def get_training_data() -> List[dict]:
    try:
        training_data = ast.literal_eval(_PRESIDIO_NLP_MODEL_TRAINING_DATA)

        if not all(isinstance(item, tuple) for item in training_data):
            raise TypeError("Each item in 'PRESIDIO_NLP_MODEL_TRAINING_DATA' must be a tuple.")

        if not all(len(item) == 2 for item in training_data):
            raise TypeError("Each tuple in 'PRESIDIO_NLP_MODEL_TRAINING_DATA' must have exactly 2 elements.")

        if not all(isinstance(item[0], str) and isinstance(item[1], dict) for item in training_data):
            raise TypeError("Each tuple in 'PRESIDIO_NLP_MODEL_TRAINING_DATA' must be a (string, dictionary).")

        return training_data
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Training data is not valid Python literal format: {e}")
    except TypeError as e:
        raise ValueError(f"Training data structure is invalid: {e}")



