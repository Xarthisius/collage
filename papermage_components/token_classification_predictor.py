from abc import ABC
from dataclasses import dataclass
from typing import List

from papermage import Entity, Metadata, Span
from papermage.magelib import Document, Entity, Metadata, SentencesFieldName, Span, TokensFieldName
from papermage.predictors import BasePredictor
from tqdm.auto import tqdm


@dataclass
class EntityCharSpan:
    e_type: str
    start_char: int
    end_char: int
    metadata: dict = None


def map_entities_to_sentence_spans(
    sentence: Entity, entities: list[EntityCharSpan]
) -> list[Entity]:
    all_entities = []

    # compute a map of offsets from the beginning of the sentence to every position in it
    sentence_spans = sentence.spans
    assert len(sentence.text) == sum([span.end - span.start for span in sentence_spans])
    offset_to_span_map = {}
    sentence_offset = 0
    for span_index, span in enumerate(sentence_spans):
        for span_offset in range(span.start, span.end + 1):
            offset_to_span_map[sentence_offset] = (span_index, span_offset)
            sentence_offset += 1

    # using the offset map, get a list of spans for each entity.
    for entity in entities:
        start_span_index, start_span_offset = offset_to_span_map[entity.start_char]
        entity_start = start_span_offset
        end_span_index, end_span_offset = offset_to_span_map[entity.end_char]
        entity_end = end_span_offset

        if start_span_index != end_span_index:
            start_span = Span(entity_start, sentence_spans[start_span_index.end])
            end_span = Span(sentence_spans[end_span_index.start], entity_end)
            intervening_spans = [
                Span(sentence_spans[i].start, sentence_spans[i].end)
                for i in range(start_span_index + 1, end_span_index)
            ]
            spans = [start_span] + intervening_spans + [end_span]
        else:
            spans = [Span(entity_start, entity_end)]

        all_entities.append(Entity(spans=spans, metadata=Metadata(entity_type=entity.e_type)))
    return all_entities


class TokenClassificationPredictorABC(BasePredictor, ABC):
    @property
    def REQUIRED_DOCUMENT_FIELDS(self) -> list[str]:
        return ["reading_order_sections"]

    @property
    def predictor_identifier(self) -> str:
        raise NotImplementedError

    @property
    def preferred_layer_name(self) -> str:
        return f"TAGGED_ENTITIES_{self.predictor_identifier}"

    def tag_entities_in_batch(self, batch: list[str]) -> list[list[EntityCharSpan]]:
        raise NotImplementedError()

    def _predict(self, doc: Document) -> list[Entity]:
        all_entities = []

        # some batch intersect with multiple paragraphs, and we don't want to process them twice
        already_processed_sentences = set()
        for para_idx, paragraph in tqdm(enumerate(doc.reading_order_sections)):

            paragraph_sentences = [
                sentence
                for sentence in paragraph.sentences
                if sentence not in already_processed_sentences
            ]
            if not paragraph_sentences:
                continue

            sentence_texts = [sentence.text.replace("\n", " ") for sentence in paragraph_sentences]

            entities_by_sentence = self.tag_entities_in_batch(sentence_texts)
            for sentence, sentence_entities in zip(paragraph_sentences, entities_by_sentence):
                all_entities.extend(map_entities_to_sentence_spans(sentence, sentence_entities))
            already_processed_sentences.update(paragraph_sentences)

        return all_entities
