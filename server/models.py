from dataclasses import dataclass


@dataclass
class NoteChunk:
    text: str
    source_path: str
    title: str
    tags: str
