import json
import os
import re

from transformers import AutoConfig

from papermage import Document
from papermage.visualizers import plot_entities_on_page
import streamlit as st
import spacy

from papermage_components.constants import MAT_IE_TYPES


PARSED_PAPER_FOLDER = "data/Midyear_Review_Papers_Parsed"

CUSTOM_MODELS_KEY = "custom_models"


@st.cache_resource
def load_document(doc_filename):
    with open(os.path.join(PARSED_PAPER_FOLDER, doc_filename)) as f:
        document = Document.from_json(json.load(f))
    return document


@st.cache_resource
def get_spacy_pipeline():
    return spacy.load("en_core_sci_md", exclude=["tagger", "parser", "ner", "lemmatizer"])


def infer_tagging_models(doc: Document) -> list[str]:
    return [
        layer.replace("TAGGED_ENTITIES_", "")
        for layer in doc.layers
        if layer.startswith("TAGGED_ENTITIES_")
    ]


@st.cache_data
def get_hf_entity_types(model_name):
    model_config = AutoConfig.from_pretrained(model_name)
    # TODO: do not hardcode the label logic!
    model_types = set(
        [re.sub("[BIO]-", "", label) for label in model_config.label2id if label != "O"]
    )
    return model_types


def get_entity_types(model_names):
    all_entity_types = set()
    for model_name in model_names:
        if model_name == "MatIE":
            all_entity_types.update([e_type for e_type in MAT_IE_TYPES])
        elif model_name == "GPT-3.5":
            all_entity_types.update([e_type for e_type in MAT_IE_TYPES])
        else:
            all_entity_types.update(get_hf_entity_types(model_name))

    return all_entity_types


def highlight_section_on_page(document, page_number, section_name, paragraph):
    page = document.pages[page_number]
    page_image = page.images[0]
    section_entities = [
        e
        for e in page.reading_order_sections
        if e.metadata["section_name"] == section_name
        and e.metadata["paragraph_reading_order"] == paragraph
    ]
    highlighted = plot_entities_on_page(
        page_image,
        section_entities,
        box_width=2,
        box_alpha=0.2,
        box_color="green",
        page_number=page_number,
    )
    return highlighted