import re, shutil, sys

shutil.copy("ingestion_pipeline.py", "ingestion_pipeline.py.bak2")
shutil.copy("llm_client.py", "llm_client.py.bak2")

with open("ingestion_pipeline.py", "r", encoding="utf-8") as f:
    src = f.read()

new_chunker = '''class Chunker:
    SENTENCE_END_RE = re.compile(r"[.!?\u05c3]\\s")

    def __init__(self, cfg: Config, detector: TimeAnchorDetector):
        self.cfg = cfg
        self.detector = detector

    def chunk_document(self, doc_id: str, paragraphs: list[dict]
    ) -> tuple[list[Chunk], list[TimeAnchor], list[str]]:
        state = RollingTimeState()
        anchors: list[TimeAnchor] = []
        chunks: list[Chunk] = []
        buffer: list[str] = []
        buf_start = 0
        overlap_text = ""

        def flush(end_index: int) -> None:
            nonlocal overlap_text
            if not buffer:
                return
            text = (overlap_text + "\\n" + "\\n".join(buffer)) if overlap_text else "\\n".join(buffer)
            lesson_n, lesson_d, status, dist = state.stamp()
            parts = list(self._soft_split(text))
            for part_i, part in enumerate(parts):
                cid = hashlib.sha256(f"{doc_id}|{buf_start}|{part_i}|{part[:64]}".encode()).hexdigest()[:24]
                chunks.append(Chunk(
                    chunk_id=cid, doc_id=doc_id, text=part,
                    paragraph_range=(buf_start, end_index),
                    lesson_number=lesson_n, lesson_date=lesson_d,
                    temporal_status=status, anchor_distance=dist,
                ))
            if parts:
                last = parts[-1]
                overlap_text = last[-self.cfg.chunk_overlap_chars:] if len(last) > self.cfg.chunk_overlap_chars else last
            buffer.clear()

        for i, par in enumerate(paragraphs):
            anchor = self.detector.detect(par, i)
            if anchor:
                flush(i - 1)
                overlap_text = ""
                state.update(anchor)
                anchors.append(anchor)
                buf_start = i + 1
                continue
            state.step()
            buffer.append(par["text"])
            if sum(len(t) for t in buffer) >= self.cfg.chunk_target_chars:
                flush(i)
                buf_start = i + 1
        flush(len(paragraphs) - 1)
        return chunks, anchors, state.warnings

    def _soft_split(self, text: str) -> Iterable[str]:
        if len(text) <= self.cfg.chunk_hard_max_chars:
            yield text
            return
        log.warning("chunk \u05d1\u05d0\u05d5\u05e8\u05da %d \u05ea\u05d5\u05d5\u05d9\u05dd - \u05de\u05e4\u05e6\u05dc\u05d9\u05dd \u05d1\u05d2\u05d1\u05d5\u05dc \u05de\u05e9\u05e4\u05d8 \u05d4\u05e7\u05e8\u05d5\u05d1 \u05dc\u05e1\u05e3", len(text))
        start = 0
        n = len(text)
        while start < n:
            target_end = min(start + self.cfg.chunk_target_chars, n)
            if target_end >= n:
                yield text[start:n]
                break
            window_start = max(start + int(self.cfg.chunk_target_chars * 0.6), start + 1)
            search_region = text[window_start:target_end + 200]
            match = None
            for m in self.SENTENCE_END_RE.finditer(search_region):
                match = m
            if match:
                cut = window_start + match.end()
            else:
                space_idx = text.rfind(" ", start, target_end)
                cut = space_idx + 1 if space_idx > start else target_end
            yield text[start:cut]
            start = cut

'''

pattern = re.compile(r"class Chunker:.*?(?=\n# -{5,}\n# \u05e9\u05dc\u05d1 4\u05d0)", re.S)
matches = pattern.findall(src)
print(f"matches found: {len(matches)}")

if matches:
    src_new = pattern.sub(lambda m: new_chunker, src, count=1)
    with open("ingestion_pipeline.py", "w", encoding="utf-8") as f:
        f.write(src_new)
    print("SUCCESS: Chunker replaced")
else:
    print("FAILED: pattern not found, no changes made")
    sys.exit(1)

with open("llm_client.py", "r", encoding="utf-8") as f:
    llm_src = f.read()

if "timeout=" not in llm_src:
    llm_new = re.sub(
        r"(resp = requests\.post\(OPENROUTER_URL, headers=headers,)",
        r"\1 timeout=60,",
        llm_src
    )
    if llm_new != llm_src:
        with open("llm_client.py", "w", encoding="utf-8") as f:
            f.write(llm_new)
        print("SUCCESS: timeout=60 added to llm_client.py")
    else:
        print("FAILED: could not add timeout, check llm_client.py manually")
else:
    print("timeout already present, skipping")

