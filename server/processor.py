import hashlib
import json
import os
import re
from typing import List

import frontmatter

from .config import CACHE_FILE, CHUNK_SIZE, IGNORE_LIST


class NoteProcessor:
    def __init__(self):
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self, cache_data):
        with open(CACHE_FILE, "w") as f:
            json.dump(cache_data, f)

    def _clean_syntax(self, content: str) -> str:
        # Removes Obsidian wikilink brackets but keeps the text
        content = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", content)
        # Removes Dataview inline fields (key:: value)
        content = re.sub(r"^[A-Za-z0-9_-]+::.*$", "", content, flags=re.MULTILINE)
        return content.strip()

    def _split_recursive(self, text: str) -> List[str]:
        # Split by headers first to keep sections together
        sections = re.split(r"(?m)^(?:#{1,3}\s.*)$", text)
        final_chunks = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            if len(section) <= CHUNK_SIZE:
                final_chunks.append(section)
            else:
                # If section is too big, split by paragraphs
                paragraphs = section.split("\n\n")
                current = ""
                for para in paragraphs:
                    if len(para) > CHUNK_SIZE:
                        # If paragraph is too big, split by sentences
                        if current:
                            final_chunks.append(current.strip())
                            current = ""
                        sentences = re.split(r"(?<=[.!?])\s+", para)
                        for s in sentences:
                            if len(current) + len(s) <= CHUNK_SIZE:
                                current += s + " "
                            else:
                                if current:
                                    final_chunks.append(current.strip())
                                current = s + " "
                    elif len(current) + len(para) <= CHUNK_SIZE:
                        current += para + "\n\n"
                    else:
                        final_chunks.append(current.strip())
                        current = para + "\n\n"
                if current:
                    final_chunks.append(current.strip())
        return final_chunks

    def process_vault(self, vault_path: str):
        all_chunks, new_cache, valid_ids = [], {}, []

        for root, dirs, files in os.walk(vault_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_LIST]

            for file in files:
                if not file.endswith(".md"):
                    continue

                path = os.path.join(root, file)
                rel_path = os.path.relpath(path, vault_path)
                mtime = os.path.getmtime(path)
                f_id = hashlib.md5(rel_path.encode()).hexdigest()
                valid_ids.append(f_id)

                # Check cache: skip if file hasn't changed
                if rel_path in self.cache and self.cache[rel_path] == mtime:
                    new_cache[rel_path] = mtime
                    continue

                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        post = frontmatter.load(f)

                    body = self._clean_syntax(post.content)
                    tags = post.get("tags") or post.get("tag") or []
                    tags_str = ",".join(tags) if isinstance(tags, list) else str(tags)

                    # Extract high-level context
                    title = file[:-3]
                    folder = rel_path.split(os.sep)[0] if os.sep in rel_path else "Root"

                    chunks = self._split_recursive(body)

                    for i, txt in enumerate(chunks):
                        # NEW: Contextual Prepending
                        # We bake the title and folder into the text so the AI knows the context
                        full_context_text = (
                            f"FILE: {title}\n"
                            f"FOLDER: {folder}\n"
                            f"TAGS: {tags_str}\n"
                            f"CONTENT: {txt}"
                        )

                        all_chunks.append(
                            {
                                "id": f"{f_id}_{i}",
                                "text": full_context_text,
                                "metadata": {
                                    "path": rel_path,
                                    "file_id": f_id,
                                    "tags": tags_str,
                                    "title": title,
                                },
                            }
                        )

                    new_cache[rel_path] = mtime
                except Exception as e:
                    print(f"Error processing {rel_path}: {e}")
                    continue

        self._save_cache(new_cache)
        return all_chunks, valid_ids
